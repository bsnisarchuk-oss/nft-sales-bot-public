"""PostgreSQL backend — drop-in replacement for SQLite DB.

Requires asyncpg: pip install asyncpg

Configure via DATABASE_URL env var:
  DATABASE_URL=postgresql://user:pass@host:5432/dbname

Falls back to SQLite if DATABASE_URL is not set.
"""

from __future__ import annotations

import asyncio
import logging
import os

log = logging.getLogger("db_postgres")


def is_postgres_configured() -> bool:
    """Check if PostgreSQL is configured via DATABASE_URL."""
    return bool(os.getenv("DATABASE_URL", "").startswith("postgres"))


SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS chats (
    chat_id BIGINT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    added_by BIGINT NOT NULL DEFAULT 0,
    added_at BIGINT NOT NULL DEFAULT (extract(epoch from now())::bigint)
);

CREATE TABLE IF NOT EXISTS collections (
    raw TEXT PRIMARY KEY,
    b64url TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS chat_collections (
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    collection_raw TEXT NOT NULL REFERENCES collections(raw) ON DELETE CASCADE,
    PRIMARY KEY (chat_id, collection_raw)
);

CREATE TABLE IF NOT EXISTS state_by_address (
    address TEXT PRIMARY KEY,
    last_lt BIGINT NOT NULL DEFAULT 0,
    updated_at BIGINT NOT NULL DEFAULT (extract(epoch from now())::bigint)
);

CREATE TABLE IF NOT EXISTS recent_traces (
    address TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    lt BIGINT NOT NULL DEFAULT 0,
    seen_at BIGINT NOT NULL DEFAULT (extract(epoch from now())::bigint),
    PRIMARY KEY (address, trace_id)
);

CREATE TABLE IF NOT EXISTS parse_failures (
    address TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    lt BIGINT NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 1,
    last_error TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '',
    quarantined INTEGER NOT NULL DEFAULT 0,
    last_failed_at BIGINT NOT NULL DEFAULT (extract(epoch from now())::bigint),
    PRIMARY KEY (address, trace_id)
);

CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id BIGINT PRIMARY KEY REFERENCES chats(chat_id) ON DELETE CASCADE,
    min_price_ton DOUBLE PRECISION NOT NULL DEFAULT 0,
    cooldown_sec INTEGER NOT NULL DEFAULT 0,
    show_link_preview INTEGER NOT NULL DEFAULT 1,
    send_photos INTEGER NOT NULL DEFAULT 1,
    whale_threshold_ton DOUBLE PRECISION NOT NULL DEFAULT 0,
    whale_ping_admins INTEGER NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'ru',
    quiet_start TEXT NOT NULL DEFAULT '',
    quiet_end TEXT NOT NULL DEFAULT '',
    batch_window_sec INTEGER NOT NULL DEFAULT 0,
    message_template TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sale_queue (
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    sale_json TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at DOUBLE PRECISION NOT NULL,
    last_error TEXT NOT NULL DEFAULT '',
    created_at DOUBLE PRECISION NOT NULL,
    UNIQUE(chat_id, trace_id)
);

CREATE TABLE IF NOT EXISTS address_filters (
    chat_id BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    filter_type TEXT NOT NULL,
    PRIMARY KEY (chat_id, address, filter_type)
);

CREATE INDEX IF NOT EXISTS idx_chat_collections_collection ON chat_collections (collection_raw);
CREATE INDEX IF NOT EXISTS idx_parse_failures_quarantine ON parse_failures (quarantined, last_failed_at);
CREATE INDEX IF NOT EXISTS idx_sale_queue_retry ON sale_queue (next_retry_at, attempts);
CREATE INDEX IF NOT EXISTS idx_address_filters_chat ON address_filters (chat_id);
"""


class PostgresDB:
    """PostgreSQL backend using asyncpg.

    Wraps asyncpg pool to provide a similar interface to the SQLite DB class.
    """

    def __init__(self, dsn: str | None = None):
        self.dsn: str = dsn if dsn is not None else os.getenv("DATABASE_URL") or ""
        self.conn = None  # Will be set to pool
        self.write_lock = asyncio.Lock()
        self._pool = None

    async def open(self) -> None:
        try:
            import asyncpg
        except ImportError:
            raise ImportError(
                "asyncpg is required for PostgreSQL support. "
                "Install it: pip install asyncpg"
            )

        self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=10)
        self.conn = self._pool

        # Run schema
        pool = self._pool
        assert pool is not None  # just assigned above
        async with pool.acquire() as conn:
            for stmt in SCHEMA_PG.split(";"):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(stmt)

        dsn = self.dsn
        log.info("PostgreSQL connected: %s", dsn.split("@")[-1] if "@" in dsn else "***")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
            self.conn = None
