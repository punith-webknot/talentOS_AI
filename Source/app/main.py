from contextlib import asynccontextmanager
import logging
import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from Source.app.agents.job_agent import create_job_agent
from Source.app.agents.review_alert_agent import create_review_alert_agent
from Source.app.agents.slots_agent import create_slots_agent
from Source.app.agents.supervisor_agent import create_supervisor_agent
from Source.app.api.router import api_router
from Source.app.config.settings import get_settings
from Source.app.tools.agent_tool_registry import (
    JOB_AGENT_TOOL_NAMES,
    REVIEW_ALERT_AGENT_TOOL_NAMES,
    SLOTS_AGENT_TOOL_NAMES,
    SUPERVISOR_AGENT_TOOL_NAMES,
    select_tools,
)
from Source.app.tools.agent_tools import (
    get_job_agent_tool,
    get_review_alert_agent_tool,
    get_slots_agent_tool,
)
from Source.app.tools.mcp_client import MCP_SERVER_NAME, create_mcp_client


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
    started = False
    settings = get_settings()

    try:
        logger.info("Starting application lifespan.")
        mcp_client = create_mcp_client()
        app.state.mcp_client = mcp_client

        # Load tools from the MCP server via connection-based discovery. Each
        # tool call opens a fresh session that carries the current chat user's
        # Authorization header (UserAuthInterceptor), so the MCP server can
        # impersonate the user on backend calls. This trades the old
        # persistent-session binding for a session per tool call.
        try:
            mcp_tools = await mcp_client.get_tools(server_name=MCP_SERVER_NAME)
        except (Exception, ExceptionGroup) as exc:
            logger.warning(
                "MCP server unavailable; starting without recruitment tools. error=%s",
                exc,
            )
            mcp_tools = []
        app.state.mcp_tools = mcp_tools
        logger.info(
            "MCP tools bound for agents: %s",
            [tool.name for tool in mcp_tools] or "(none)",
        )

        logger.info("Connecting to Postgres checkpointer.")
        pool = AsyncConnectionPool(
            settings.database_uri,
            min_size=1,
            max_size=4,
        )
        async with pool:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()
            logger.info("Postgres checkpointer initialized.")

            job_tools = select_tools(mcp_tools, JOB_AGENT_TOOL_NAMES)
            slots_tools = select_tools(mcp_tools, SLOTS_AGENT_TOOL_NAMES)
            review_alert_tools = select_tools(mcp_tools, REVIEW_ALERT_AGENT_TOOL_NAMES)
            supervisor_mcp_tools = select_tools(mcp_tools, SUPERVISOR_AGENT_TOOL_NAMES)

            job_agent = create_job_agent(job_tools, checkpointer)
            slots_agent = create_slots_agent(slots_tools, checkpointer)
            review_alert_agent = create_review_alert_agent(
                review_alert_tools, checkpointer
            )
            supervisor_tools = [
                *supervisor_mcp_tools,
                get_job_agent_tool(job_agent),
                get_slots_agent_tool(slots_agent),
                get_review_alert_agent_tool(review_alert_agent),
            ]
            logger.info(
                "job_agent tools=%s | slots_agent tools=%s | "
                "review_alert_agent tools=%s | supervisor tools=%s",
                [t.name for t in job_tools],
                [t.name for t in slots_tools],
                [t.name for t in review_alert_tools],
                [t.name for t in supervisor_tools],
            )
            supervisor_agent = create_supervisor_agent(supervisor_tools, checkpointer)

            app.state.job_agent = job_agent
            app.state.slots_agent = slots_agent
            app.state.review_alert_agent = review_alert_agent
            app.state.supervisor_agent = supervisor_agent
            started = True
            logger.info("Application startup complete.")
            yield
    except Exception as exc:
        logger.exception("Application lifespan failed.")
        if not started:
            raise RuntimeError("Application startup failed. Check logs for details.") from exc
        raise

app = FastAPI(title="TalentOS AI API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    uvicorn.run("Source.app.main:app", host="127.0.0.1", port=8003, reload=True)
