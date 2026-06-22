"""Google credentials using OAuth client config from .env instead of credentials.json."""

from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from Source.app.config.settings import get_settings

GMAIL_SCOPES = ["https://mail.google.com/"]
DEFAULT_TOKEN_FILE = "token.json"


def get_google_credentials_from_env(
    token_file: str = DEFAULT_TOKEN_FILE,
    scopes: list[str] | None = None,
) -> Credentials:
    """
    Same behavior as langchain get_google_credentials, but reads the OAuth
    client config (credentials.json fields) from .env via Settings.
    """
    settings = get_settings()
    if not settings.gmail_client_id or not settings.gmail_client_secret:
        raise RuntimeError(
            "Gmail OAuth client is not configured. "
            "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env."
        )

    scopes = scopes or GMAIL_SCOPES
    creds = None
    token_path = Path(token_file)

    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                settings.gmail_oauth_client_config(),
                scopes=scopes,
            )
            creds = flow.run_local_server(port=0)

        with token_path.open("w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds
