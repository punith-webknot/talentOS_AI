import logging

from langchain_mcp_adapters.client import MultiServerMCPClient

from Source.app.config.settings import get_settings

logger = logging.getLogger(__name__)


async def init_mcp_client():
    settings = get_settings()
    logger.info("Connecting to MCP Recruitment Tool Server at %s", settings.mcp_url)
    client = MultiServerMCPClient(
        {
            "recruitment_services": {
                "transport": "http",
                "url": settings.mcp_url,
            }
        }
    )
    try:
        mcp_tools = await client.get_tools()
    except (Exception, ExceptionGroup) as exc:
        logger.warning("MCP server unavailable; starting without recruitment tools. error=%s", exc)
        return None, []

    logger.info("Successfully loaded %d tools from MCP Server.", len(mcp_tools))
    return client, mcp_tools
