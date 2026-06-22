"""PostgreSQL table for per-user Gmail tokens (token.json fields)."""

import logging

from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

GMAIL_OAUTH_TOKENS_TABLE = "gmail_oauth_tokens"

# token.json field -> column name
TOKEN_JSON_COLUMNS = (
    "token",
    "refresh_token",
    "token_uri",
    "client_id",
    "client_secret",
    "scopes",
    "universe_domain",
    "account",
    "expiry",
)

CREATE_GMAIL_OAUTH_TOKENS_SQL = f"""
CREATE TABLE IF NOT EXISTS {GMAIL_OAUTH_TOKENS_TABLE} (
    user_id TEXT PRIMARY KEY,
    token TEXT NOT NULL,
    refresh_token TEXT,
    token_uri TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret TEXT NOT NULL,
    scopes JSONB NOT NULL,
    universe_domain TEXT NOT NULL,
    account TEXT NOT NULL DEFAULT '',
    expiry TIMESTAMPTZ
);
"""


async def setup_gmail_token_schema(pool: AsyncConnectionPool) -> None:
    """Create the Gmail OAuth tokens table if it does not exist."""
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(CREATE_GMAIL_OAUTH_TOKENS_SQL)
        await conn.commit()
    logger.info("Table '%s' is ready.", GMAIL_OAUTH_TOKENS_TABLE)
