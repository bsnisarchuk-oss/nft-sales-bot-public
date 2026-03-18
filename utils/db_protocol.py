"""Database protocol — abstract interface for DB backends (SQLite, PostgreSQL)."""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DBConnection(Protocol):
    """Abstract async DB connection interface."""

    async def execute(self, sql: str, parameters: tuple = ()) -> Any: ...
    async def executescript(self, sql: str) -> None: ...
    async def commit(self) -> None: ...
    async def close(self) -> None: ...
    async def fetchone(self) -> Any: ...
    async def fetchall(self) -> list: ...


@runtime_checkable
class DBBackend(Protocol):
    """Abstract DB backend interface — implemented by SQLite DB and PostgreSQL."""

    conn: Any
    write_lock: asyncio.Lock

    async def open(self) -> None: ...
    async def close(self) -> None: ...
