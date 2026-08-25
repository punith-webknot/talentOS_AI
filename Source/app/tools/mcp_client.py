import logging
from contextvars import ContextVar
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.interceptors import MCPToolCallRequest

from Source.app.config.settings import get_settings

logger = logging.getLogger(__name__)

MCP_SERVER_NAME = "recruitment_services"

# Authorization header (`Bearer <jwt>`) of the end user driving the current
# chat request. Set per request in the chat stream endpoint; the interceptor
# below surfaces it on every MCP tool call so the MCP server can impersonate
# that user when calling the talentOS backend.
_current_user_auth: ContextVar[str | None] = ContextVar("current_user_auth", default=None)


def set_current_user_auth(authorization: str | None) -> None:
    _current_user_auth.set(authorization)


class UserAuthInterceptor:
    """Inject the current chat user's Authorization header into MCP tool calls.

    Tool calls created from a *connection* (not a bound session) open a fresh
    session per invocation, so the modified header lands on every request the
    MCP server receives from this user.
    """

    async def __call__(
        self,
        request: MCPToolCallRequest,
        handler,
    ) -> Any:
        authorization = _current_user_auth.get()
        if authorization:
            request = request.override(headers={"Authorization": authorization})
        return await handler(request)


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
        },
        tool_interceptors=[UserAuthInterceptor()],
    )
