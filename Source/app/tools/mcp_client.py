from langchain_mcp_adapters.client import MultiServerMCPClient

async def init_mcp_client():
    print("Connecting to MCP Recruitment Tool Server...")
    client = MultiServerMCPClient(
        {
            "recruitment_services": {
                "transport": "http",
                "url": "http://localhost:8000/mcp",
            }
        }
    )
    mcp_tools = await client.get_tools()
    print(f" Successfully loaded {len(mcp_tools)} tools from MCP Server.\n")
    return client, mcp_tools