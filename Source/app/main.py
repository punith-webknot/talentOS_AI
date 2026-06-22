from contextlib import asynccontextmanager
import logging
import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from Source.app.agents.job_agent import create_job_agent
from Source.app.agents.supervisor_agent import create_supervisor_agent
from Source.app.api.router import api_router
from Source.app.config.settings import get_settings
from Source.app.db.gmail_token_schema import setup_gmail_token_schema
from Source.app.tools.agent_tools import get_job_agent_tool
from Source.app.tools.mcp_client import init_mcp_client


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        force=True,
    )


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize long-lived app dependencies once at startup."""
    mcp_client = None
    db_pool = None
    started = False
    settings = get_settings()

    try:
        logger.info("Starting application lifespan.")
        mcp_client, mcp_tools = await init_mcp_client()
        app.state.mcp_client = mcp_client

        logger.info("Connecting to Postgres.")
        db_pool = AsyncConnectionPool(settings.database_uri)
        await db_pool.open()
        await setup_gmail_token_schema(db_pool)
        app.state.db_pool = db_pool

        async with AsyncPostgresSaver.from_conn_string(settings.database_uri) as checkpointer:
            await checkpointer.setup()
            logger.info("Postgres checkpointer initialized.")

            job_agent = create_job_agent(mcp_tools, checkpointer)
            job_tool = get_job_agent_tool(job_agent)
            supervisor_agent = create_supervisor_agent(job_tool, checkpointer)

            app.state.job_agent = job_agent
            app.state.supervisor_agent = supervisor_agent
            started = True
            logger.info("Application startup complete.")
            yield
    except Exception as exc:
        logger.exception("Application lifespan failed.")
        if not started:
            raise RuntimeError("Application startup failed. Check logs for details.") from exc
        raise
    finally:
        if db_pool is not None:
            try:
                await db_pool.close()
                logger.info("Postgres connection pool closed.")
            except Exception:
                logger.exception("Failed to close Postgres pool cleanly.")

        close_client = getattr(mcp_client, "aclose", None)
        if callable(close_client):
            try:
                await close_client()
                logger.info("MCP client closed.")
            except Exception:
                logger.exception("Failed to close MCP client cleanly.")

app = FastAPI(title="TalentOS AI API", lifespan=lifespan)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("Request validation failed request_id=%s errors=%s", request_id, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
            "request_id": request_id,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning("HTTP exception request_id=%s status=%s detail=%s", request_id, exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "detail": exc.detail,
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled exception request_id=%s", request_id)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred.",
            "request_id": request_id,
        },
    )


app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("Source.app.main:app", host="127.0.0.1", port=8080, reload=True)
