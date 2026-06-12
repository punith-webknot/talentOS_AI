from langchain_mcp_adapters.client import MultiServerMCPClient

from Source.app.config.settings import settings


async def init_mcp_client():
    print("Connecting to MCP Recruitment Tool Server...")
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
        print(f" MCP server unavailable: {exc}. Starting without recruitment tools.\n")
        return None, []

    print(f" Successfully loaded {len(mcp_tools)} tools from MCP Server.\n")
    return client, mcp_tools
