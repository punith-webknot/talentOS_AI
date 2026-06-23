<<<<<<< HEAD
"""Read and write Gmail OAuth tokens stored in PostgreSQL."""
=======
"""Read/write per-user Gmail OAuth tokens in PostgreSQL."""
>>>>>>> dae2c0c (half cooked gmail service)

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials
from psycopg.rows import dict_row
<<<<<<< HEAD
from psycopg.types.json import Json
from psycopg_pool import AsyncConnectionPool

from Source.app.db.gmail_token_schema import (
=======
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from Source.app.db.gmail_token_schema import (
    GMAIL_OAUTH_PENDING_TABLE,
>>>>>>> dae2c0c (half cooked gmail service)
    GMAIL_OAUTH_TOKENS_TABLE,
    TOKEN_JSON_COLUMNS,
)

logger = logging.getLogger(__name__)

<<<<<<< HEAD
_SELECT_COLUMNS = ", ".join(("user_id", *TOKEN_JSON_COLUMNS))


def _format_expiry(expiry: datetime | str | None) -> str | None:
    if expiry is None:
        return None
    if isinstance(expiry, str):
        return expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def token_row_to_info(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a DB row into token.json-shaped data for Google Credentials."""
    return {
        "token": row["token"],
        "refresh_token": row["refresh_token"],
        "token_uri": row["token_uri"],
        "client_id": row["client_id"],
        "client_secret": row["client_secret"],
        "scopes": row["scopes"],
        "universe_domain": row["universe_domain"],
        "account": row["account"] or "",
        "expiry": _format_expiry(row["expiry"]),
    }


def _normalize_scopes(scopes: Any, creds: Credentials) -> list[str]:
    if isinstance(scopes, list):
        return scopes
    if isinstance(scopes, str):
        return scopes.split()
    if creds.scopes:
        return list(creds.scopes)
    return []


def credentials_to_row(user_id: str, creds: Credentials) -> dict[str, Any]:
    """Serialize Google Credentials into gmail_oauth_tokens column values."""
    info = json.loads(creds.to_json())
    return {
        "user_id": user_id,
        "token": info["token"],
        "refresh_token": info.get("refresh_token"),
        "token_uri": info["token_uri"],
        "client_id": info["client_id"],
        "client_secret": info["client_secret"],
        "scopes": Json(_normalize_scopes(info.get("scopes"), creds)),
        "universe_domain": info.get("universe_domain", "googleapis.com"),
        "account": info.get("account", ""),
        "expiry": info.get("expiry"),
    }


async def fetch_gmail_token_by_user_id(
    pool: AsyncConnectionPool,
    user_id: str,
) -> dict[str, Any] | None:
    """Return token.json-shaped data for the given user, or None if not found."""
    sql = f"""
        SELECT {_SELECT_COLUMNS}
        FROM {GMAIL_OAUTH_TOKENS_TABLE}
        WHERE user_id = %s
    """
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql, (user_id,))
            row = await cur.fetchone()
    if row is None:
        return None
    return token_row_to_info(row)


async def upsert_gmail_token(
=======

def _normalize_scopes(scopes: Any) -> list[str]:
    if not scopes:
        return []
    if isinstance(scopes, list):
        return scopes
    if isinstance(scopes, (set, tuple)):
        return list(scopes)
    if isinstance(scopes, str):
        stripped = scopes.strip()
        if stripped.startswith("["):
            return json.loads(stripped)
        return stripped.split()

    return [str(scopes)]


def _format_expiry_for_google(expiry: datetime | str) -> str:
    if isinstance(expiry, str):
        return expiry.replace("+00:00", "Z")

    if expiry.tzinfo is not None:
        expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)

    return expiry.strftime("%Y-%m-%dT%H:%M:%SZ")


def _credentials_from_row(row: dict[str, Any]) -> Credentials:
    scopes = _normalize_scopes(row["scopes"])

    info = {
        "token": row["token"],
        "refresh_token": row.get("refresh_token"),
        "token_uri": row["token_uri"],
        "client_id": row["client_id"],
        "client_secret": row["client_secret"],
        "scopes": scopes,
        "universe_domain": row["universe_domain"],
        "account": row.get("account") or "",
    }
    if row.get("expiry") is not None:
        info["expiry"] = _format_expiry_for_google(row["expiry"])

    return Credentials.from_authorized_user_info(info, scopes)


def _row_from_credentials(user_id: str, creds: Credentials) -> dict[str, Any]:
    payload = json.loads(creds.to_json())
    return {
        "user_id": user_id,
        "token": payload["token"],
        "refresh_token": payload.get("refresh_token"),
        "token_uri": payload["token_uri"],
        "client_id": payload["client_id"],
        "client_secret": payload["client_secret"],
        "scopes": Jsonb(_normalize_scopes(payload.get("scopes", []))),
        "universe_domain": payload.get("universe_domain", "googleapis.com"),
        "account": payload.get("account", ""),
        "expiry": payload.get("expiry"),
    }


async def get_gmail_credentials(
    pool: AsyncConnectionPool,
    user_id: str,
) -> Credentials | None:
    """Load stored Gmail credentials for a user, if any."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"""
                SELECT {", ".join(TOKEN_JSON_COLUMNS)}
                FROM {GMAIL_OAUTH_TOKENS_TABLE}
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = await cur.fetchone()

    if row is None:
        return None

    return _credentials_from_row(row)


async def upsert_gmail_credentials(
>>>>>>> dae2c0c (half cooked gmail service)
    pool: AsyncConnectionPool,
    user_id: str,
    creds: Credentials,
) -> None:
<<<<<<< HEAD
    """Insert or update a user's Gmail OAuth token row."""
    row = credentials_to_row(user_id, creds)
    sql = f"""
        INSERT INTO {GMAIL_OAUTH_TOKENS_TABLE} (
            user_id, token, refresh_token, token_uri, client_id, client_secret,
            scopes, universe_domain, account, expiry
        ) VALUES (
            %(user_id)s, %(token)s, %(refresh_token)s, %(token_uri)s,
            %(client_id)s, %(client_secret)s, %(scopes)s,
            %(universe_domain)s, %(account)s, %(expiry)s::timestamptz
        )
        ON CONFLICT (user_id) DO UPDATE SET
            token = EXCLUDED.token,
            refresh_token = EXCLUDED.refresh_token,
            token_uri = EXCLUDED.token_uri,
            client_id = EXCLUDED.client_id,
            client_secret = EXCLUDED.client_secret,
            scopes = EXCLUDED.scopes,
            universe_domain = EXCLUDED.universe_domain,
            account = EXCLUDED.account,
            expiry = EXCLUDED.expiry
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, row)
        await conn.commit()
    logger.debug("Upserted Gmail OAuth token for user_id=%s", user_id)
=======
    """Insert or update Gmail OAuth credentials for a user."""
    row = _row_from_credentials(user_id, creds)
    columns = list(row.keys())
    placeholders = ", ".join(f"%({col})s" for col in columns)
    updates = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in columns if col != "user_id"
    )

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO {GMAIL_OAUTH_TOKENS_TABLE} ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT (user_id) DO UPDATE SET {updates}
                """,
                row,
            )
        await conn.commit()

    logger.info("Stored Gmail OAuth token for user_id=%s", user_id)


async def save_oauth_pending(
    pool: AsyncConnectionPool,
    user_id: str,
    code_verifier: str,
) -> None:
    """Store PKCE verifier until the OAuth callback completes."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"""
                INSERT INTO {GMAIL_OAUTH_PENDING_TABLE} (user_id, code_verifier)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET code_verifier = EXCLUDED.code_verifier,
                    created_at = NOW()
                """,
                (user_id, code_verifier),
            )
        await conn.commit()


async def pop_oauth_pending(
    pool: AsyncConnectionPool,
    user_id: str,
) -> str | None:
    """Return and delete the stored PKCE verifier for a user."""
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"""
                DELETE FROM {GMAIL_OAUTH_PENDING_TABLE}
                WHERE user_id = %s
                RETURNING code_verifier
                """,
                (user_id,),
            )
            row = await cur.fetchone()
        await conn.commit()

    if row is None:
        return None

    return row["code_verifier"]


async def has_valid_gmail_token(
    pool: AsyncConnectionPool,
    user_id: str,
) -> bool:
    """Return True when the user has a stored Gmail token."""
    creds = await get_gmail_credentials(pool, user_id)
    if creds is None:
        return False

    if creds.valid:
        return True

    return bool(creds.expired and creds.refresh_token)
>>>>>>> dae2c0c (half cooked gmail service)
