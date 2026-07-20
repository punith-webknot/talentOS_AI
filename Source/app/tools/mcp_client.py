import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession

from Source.app.config.settings import get_settings

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "recruitment_services"


def create_mcp_client() -> MultiServerMCPClient:
    """Create an MCP multi-server client (does not open a session yet)."""
    settings = get_settings()
    logger.info("Connecting to MCP Recruitment Tool Server at %s", settings.mcp_url)
    return MultiServerMCPClient(
        {
            MCP_SERVER_NAME: {
                "transport": "http",
                "url": settings.mcp_url,
            }
        }
    )


@asynccontextmanager
async def open_mcp_session(
    client: MultiServerMCPClient,
) -> AsyncIterator[tuple[ClientSession | None, list[BaseTool]]]:
    """Keep one MCP HTTP session open for the app lifetime and bind tools to it.

    ``client.get_tools()`` opens a short-lived session for discovery and then
    creates a *new* session on every tool call (POST/DELETE per invocation).
    Loading tools through an explicit session reuses that connection for all
    subsequent tool calls until the context exits.
    """
    session_cm = client.session(MCP_SERVER_NAME)
    try:
        session = await session_cm.__aenter__()
        mcp_tools = await load_mcp_tools(session, server_name=MCP_SERVER_NAME)
    except (Exception, ExceptionGroup) as exc:
        logger.warning(
            "MCP server unavailable; starting without recruitment tools. error=%s",
            exc,
        )
        try:
            await session_cm.__aexit__(None, None, None)
        except Exception:
            logger.debug("Failed to clean up MCP session after startup error.", exc_info=True)
        yield None, []
        return

    logger.info(
        "Successfully loaded %d tools from MCP Server (persistent session).",
        len(mcp_tools),
    )
    try:
        yield session, mcp_tools
    finally:
        await session_cm.__aexit__(None, None, None)
        logger.info("MCP session closed.")
