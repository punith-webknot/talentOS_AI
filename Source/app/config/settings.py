from pathlib import Path
import logging
from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

_SOURCE_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SOURCE_DIR.parent
logger = logging.getLogger(__name__)


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
    mcp_url: str
    model_name: str
    database_uri: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing_fields = sorted(
            {
                err["loc"][-1]
                for err in exc.errors()
                if err.get("type") == "missing" and err.get("loc")
            }
        )
        logger.critical("Invalid configuration. Missing required environment variables: %s", missing_fields)
        raise RuntimeError(
            "Application configuration is invalid. "
            f"Missing required environment variables: {', '.join(missing_fields) or 'unknown'}"
        ) from exc