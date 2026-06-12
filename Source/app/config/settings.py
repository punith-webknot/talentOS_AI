from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_SOURCE_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SOURCE_DIR.parent


def _resolve_env_file() -> Path:
    for candidate in (_REPO_ROOT / ".env", _SOURCE_DIR / ".env"):
        if candidate.is_file():
            return candidate
    return _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        env_file_encoding="utf-8",
    )
    openai_api_key: str
    mcp_url: str = "http://localhost:8000/mcp"
    model_name: str = "gpt-4.1-mini"

settings = Settings()