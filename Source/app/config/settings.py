from pathlib import Path
import logging
from functools import lru_cache

from typing import Self

from pydantic import ValidationError, model_validator
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
        populate_by_name=True,
    )
    model_name: str
    evaluation_model_name: str
    openai_api_key: str | None = None
    mcp_url: str
    database_uri: str

    @model_validator(mode="after")
    def validate_openai_api_key(self) -> Self:
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        issues = sorted(
            {
                err.get("msg", "invalid value")
                if err.get("type") != "missing"
                else str(err["loc"][-1])
                for err in exc.errors()
                if err.get("loc")
            }
        )
        logger.critical("Invalid configuration: %s", issues)
        raise RuntimeError(
            "Application configuration is invalid. "
            f"Issues: {', '.join(issues) or 'unknown'}"
        ) from exc
