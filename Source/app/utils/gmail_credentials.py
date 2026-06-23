"""Google credentials using OAuth client config from .env instead of credentials.json."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from psycopg_pool import AsyncConnectionPool

from Source.app.config.settings import get_settings
from Source.app.db.gmail_token_repository import (
    fetch_gmail_token_by_user_id,
    upsert_gmail_token,
)

GMAIL_SCOPES = ["https://mail.google.com/"]
DEFAULT_TOKEN_FILE = "token.json"

OnMissingToken = Literal["raise", "url", "oauth"]


class GmailAuthRequired(Exception):
    """Raised when a user must complete Gmail OAuth before credentials are available."""

    def __init__(self, authorization_url: str, user_id: str) -> None:
        self.authorization_url = authorization_url
        self.user_id = user_id
        super().__init__(
            f"Gmail authorization required for user_id={user_id!r}. "
            f"Visit: {authorization_url}"
        )


def _ensure_gmail_client_configured() -> None:
    settings = get_settings()
    if not settings.gmail_client_id or not settings.gmail_client_secret:
        raise RuntimeError(
            "Gmail OAuth client is not configured. "
            "Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env."
        )


def _create_oauth_flow(scopes: list[str]) -> InstalledAppFlow:
    _ensure_gmail_client_configured()
    return InstalledAppFlow.from_client_config(
        get_settings().gmail_oauth_client_config(),
        scopes=scopes,
    )


def get_gmail_authorization_url(
    user_id: str,
    scopes: list[str] | None = None,
) -> str:
    """Build the Google OAuth URL for a user to authorize Gmail access."""
    scopes = scopes or GMAIL_SCOPES
    flow = _create_oauth_flow(scopes)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=user_id,
    )
    return authorization_url


def _run_local_oauth_flow(scopes: list[str]) -> Credentials:
    """
    Start a local callback server, print the login URL, and return credentials
    after the user authorizes in the browser.
    """
    flow = _create_oauth_flow(scopes)
    print("Gmail authorization required. Open this URL to sign in:")
    return flow.run_local_server(port=0, open_browser=False)


def get_google_credentials_from_env(
    token_file: str = DEFAULT_TOKEN_FILE,
    scopes: list[str] | None = None,
) -> Credentials:
    """
    Same behavior as langchain get_google_credentials, but reads the OAuth
    client config (credentials.json fields) from .env via Settings.
    """
    _ensure_gmail_client_configured()
    settings = get_settings()

    scopes = scopes or GMAIL_SCOPES
    creds = None
    token_path = Path(token_file)

    if token_path.is_file():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = _run_local_oauth_flow(scopes)

        with token_path.open("w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


async def _complete_oauth_and_save(
    pool: AsyncConnectionPool,
    user_id: str,
    scopes: list[str],
) -> Credentials:
    creds = await asyncio.to_thread(_run_local_oauth_flow, scopes)
    await upsert_gmail_token(pool, user_id, creds)
    print(f"Gmail OAuth token saved to database for user_id={user_id!r}.")
    return creds


async def _get_google_credentials_from_db_async(
    user_id: str,
    scopes: list[str] | None = None,
    on_missing_token: OnMissingToken = "raise",
) -> Credentials:
    settings = get_settings()
    scopes = scopes or GMAIL_SCOPES

    async with AsyncConnectionPool(settings.database_uri, open=False) as pool:
        token_info = await fetch_gmail_token_by_user_id(pool, user_id)

        if token_info is None:
            if on_missing_token == "oauth":
                return await _complete_oauth_and_save(pool, user_id, scopes)
            if on_missing_token == "url":
                raise GmailAuthRequired(get_gmail_authorization_url(user_id, scopes), user_id)
            raise RuntimeError(
                f"No Gmail OAuth token found in database for user_id={user_id!r}."
            )

        creds = Credentials.from_authorized_user_info(token_info, scopes)

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                await upsert_gmail_token(pool, user_id, creds)
            elif on_missing_token == "oauth":
                return await _complete_oauth_and_save(pool, user_id, scopes)
            elif on_missing_token == "url":
                raise GmailAuthRequired(get_gmail_authorization_url(user_id, scopes), user_id)
            else:
                raise RuntimeError(
                    f"Gmail OAuth token for user_id={user_id!r} is invalid and "
                    "cannot be refreshed."
                )

        return creds


def get_google_credentials_from_db(
    user_id: str,
    scopes: list[str] | None = None,
    on_missing_token: OnMissingToken = "raise",
) -> Credentials:
    """
    Load Gmail OAuth credentials for a user from the gmail_oauth_tokens table.

    If no token exists (or it cannot be refreshed):
    - on_missing_token=\"raise\": raise RuntimeError
    - on_missing_token=\"url\": raise GmailAuthRequired with the login URL
    - on_missing_token=\"oauth\": print login URL, run local callback, save to DB
    """
    return asyncio.run(
        _get_google_credentials_from_db_async(user_id, scopes, on_missing_token)
    )
