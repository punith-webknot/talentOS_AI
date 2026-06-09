"""
App-wide settings, loaded from environment / .env file.

Currently only used by `jd_creation_agent` to find the talentos-mcp-server.
Other settings are placeholders for the rest of the app to share.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # talentos-backend (the FastAPI HR app)
    TALENTOS_BACKEND_URL: str = "http://localhost:8000"
    TALENTOS_BACKEND_TOKEN: str = ""  # service-to-service JWT (optional for dev)

    # talentos-mcp-server — wraps all recruitment tools (talentos-backend +
    # WebTrak) behind MCP. jd_creation_agent connects to it instead of using
    # local @tool functions. MCP_SERVER_DIR is the path to that project so we
    # can spawn it as a stdio subprocess (`uv run python -m
    # talentos_mcp_server.server`) for local dev. Switch MCP_SERVER_TRANSPORT
    # to "streamable_http" + set MCP_SERVER_URL once it runs as a shared service.
    MCP_SERVER_DIR: str = "/Users/mayurnair/Desktop/talentos_mcp_server"
    MCP_SERVER_TRANSPORT: str = "stdio"  # stdio | streamable_http
    MCP_SERVER_URL: str = "http://localhost:8765/mcp"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
