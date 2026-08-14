from pathlib import Path
import logging
from functools import lru_cache

from typing import Literal, Self

from pydantic import ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SOURCE_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SOURCE_DIR.parent
logger = logging.getLogger(__name__)

LLM_PROVIDER_LITERAL = Literal["openai", "groq"]

OPENAI_BASE_URL = "https://api.openai.com/v1"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# Per-provider fallback models used when MODEL_NAME / EVALUATION_MODEL_NAME
# are not explicitly set, so flipping LLM_PROVIDER "just works".
DEFAULT_MODELS: dict[str, dict[str, str]] = {
    "openai": {
        "model": "gpt-5.4-mini",
        "evaluation": "gpt-5.4-nano",
    },
    "groq": {
        "model": "llama-3.3-70b-versatile",
        "evaluation": "llama-3.1-8b-instant",
    },
}


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
    llm_provider: LLM_PROVIDER_LITERAL = "openai"
    model_name: str | None = None
    evaluation_model_name: str | None = None
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    openai_base_url: str = OPENAI_BASE_URL
    groq_base_url: str = GROQ_BASE_URL
    mcp_url: str
    database_uri: str

    @property
    def active_api_key(self) -> str:
        key = self.groq_api_key if self.llm_provider == "groq" else self.openai_api_key
        if not key:
            raise ValueError(
                f"API key is required for LLM provider '{self.llm_provider}' "
                f"({self._api_key_env_name})"
            )
        return key

    @property
    def active_base_url(self) -> str:
        return self.groq_base_url if self.llm_provider == "groq" else self.openai_base_url

    @property
    def active_model_name(self) -> str:
        return self.model_name or DEFAULT_MODELS[self.llm_provider]["model"]

    @property
    def active_evaluation_model_name(self) -> str:
        return self.evaluation_model_name or DEFAULT_MODELS[self.llm_provider]["evaluation"]

    @property
    def _api_key_env_name(self) -> str:
        return "GROQ_API_KEY" if self.llm_provider == "groq" else "OPENAI_API_KEY"

    @model_validator(mode="after")
    def validate_llm_provider(self) -> Self:
        if self.llm_provider not in DEFAULT_MODELS:
            raise ValueError(
                f"Unsupported LLM_PROVIDER '{self.llm_provider}'. "
                f"Supported: {', '.join(sorted(DEFAULT_MODELS))}"
            )
        if not self.active_api_key:
            raise ValueError(f"{self._api_key_env_name} is required")
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
