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

    # credentials.json fields
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_project_id: str = ""
    gmail_auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    gmail_token_uri: str = "https://oauth2.googleapis.com/token"
    gmail_auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    gmail_redirect_uri: str = "http://localhost"

    def gmail_oauth_client_config(self) -> dict:
        return {
            "installed": {
                "client_id": self.gmail_client_id,
                "project_id": self.gmail_project_id,
                "auth_uri": self.gmail_auth_uri,
                "token_uri": self.gmail_token_uri,
                "auth_provider_x509_cert_url": self.gmail_auth_provider_x509_cert_url,
                "client_secret": self.gmail_client_secret,
                "redirect_uris": [self.gmail_redirect_uri],
            }
        }


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