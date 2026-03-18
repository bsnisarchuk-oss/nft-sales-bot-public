import asyncio
import os
import re

import aiosqlite


def db_path() -> str:
    data_dir = os.getenv("DATA_DIR", "data")
    db_path_env = os.getenv("DB_PATH")
    if db_path_env:
        return db_path_env
    return os.path.join(data_dir, "bot.db")


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 1,
    added_by INTEGER NOT NULL DEFAULT 0,
    added_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS collections (
    raw TEXT PRIMARY KEY,
    b64url TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS chat_collections (
    chat_id INTEGER NOT NULL,
    collection_raw TEXT NOT NULL,
    PRIMARY KEY (chat_id, collection_raw),
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
    FOREIGN KEY (collection_raw) REFERENCES collections(raw) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS state_by_address (
    address TEXT PRIMARY KEY,
    last_lt INTEGER NOT NULL DEFAULT 0,
    updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS recent_traces (
    address TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    lt INTEGER NOT NULL DEFAULT 0,
    seen_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (address, trace_id)
);

CREATE TABLE IF NOT EXISTS parse_failures (
    address TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    lt INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 1,
    last_error TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '',
    quarantined INTEGER NOT NULL DEFAULT 0,
    last_failed_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    PRIMARY KEY (address, trace_id)
);

CREATE TABLE IF NOT EXISTS chat_settings (
    chat_id INTEGER PRIMARY KEY,
    min_price_ton REAL NOT NULL DEFAULT 0,
    cooldown_sec INTEGER NOT NULL DEFAULT 0,
    show_link_preview INTEGER NOT NULL DEFAULT 1,
    send_photos INTEGER NOT NULL DEFAULT 1,
    whale_threshold_ton REAL NOT NULL DEFAULT 0,
    whale_ping_admins INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sale_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    sale_json TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_retry_at REAL NOT NULL,
    last_error TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    UNIQUE(chat_id, trace_id)
);

CREATE TABLE IF NOT EXISTS address_filters (
    chat_id INTEGER NOT NULL,
    address TEXT NOT NULL,
    filter_type TEXT NOT NULL,
    PRIMARY KEY (chat_id, address, filter_type),
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chat_collections_collection ON chat_collections (collection_raw);
CREATE INDEX IF NOT EXISTS idx_parse_failures_quarantine ON parse_failures (quarantined, last_failed_at);
CREATE INDEX IF NOT EXISTS idx_sale_queue_retry ON sale_queue (next_retry_at, attempts);
CREATE INDEX IF NOT EXISTS idx_address_filters_chat ON address_filters (chat_id);
"""


class DB:
    def __init__(self, path: str | None = None):
        self.path = path or db_path()
        self.conn: aiosqlite.Connection | None = None
        self.write_lock = asyncio.Lock()

    async def open(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        # WAL снижает риск повреждения при сбоях и разгружает конкурентный доступ
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA synchronous=NORMAL")
        await self.conn.execute("PRAGMA busy_timeout=5000")
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()
        await self._ensure_column("chat_settings", "whale_threshold_ton", "whale_threshold_ton REAL NOT NULL DEFAULT 0")
        await self._ensure_column("chat_settings", "whale_ping_admins", "whale_ping_admins INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("chat_settings", "language", "language TEXT NOT NULL DEFAULT 'ru'")
        await self._ensure_column("chat_settings", "quiet_start", "quiet_start TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("chat_settings", "quiet_end", "quiet_end TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("chat_settings", "batch_window_sec", "batch_window_sec INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("chat_settings", "message_template", "message_template TEXT NOT NULL DEFAULT ''")
        await self.conn.commit()

    _VALID_SQL_NAME = re.compile(r'^[a-z_][a-z0-9_]*$')

    async def _ensure_column(self, table: str, col: str, ddl: str) -> None:
        assert self.conn
        if not self._VALID_SQL_NAME.match(table) or not self._VALID_SQL_NAME.match(col):
            raise ValueError(f"Invalid SQL identifier: {table}.{col}")
        cur = await self.conn.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in await cur.fetchall()]
        if col not in cols:
            await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None
