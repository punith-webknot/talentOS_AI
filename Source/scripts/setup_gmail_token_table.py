"""Standalone script to create the Gmail OAuth tokens table in PostgreSQL."""

import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from psycopg_pool import AsyncConnectionPool

from Source.app.config.settings import get_settings
from Source.app.db.gmail_token_schema import setup_gmail_token_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    async with AsyncConnectionPool(settings.database_uri, open=False) as pool:
        await setup_gmail_token_schema(pool)
    logger.info("Gmail OAuth tokens table created successfully.")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
