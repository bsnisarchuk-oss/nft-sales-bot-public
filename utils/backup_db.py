"""
Автобэкап SQLite: раз в день + ручной /backup_now.
Безопасно через sqlite backup API.
"""

import asyncio
import os
import sqlite3
import time


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _db_path() -> str:
    data_dir = os.getenv("DATA_DIR", "data")
    db_path = os.getenv("DB_PATH", os.path.join(data_dir, "bot.db"))
    return db_path


def _backup_dir() -> str:
    data_dir = os.getenv("DATA_DIR", "data")
    return os.path.join(data_dir, "backups")


def _today_name() -> str:
    return time.strftime("%Y-%m-%d")


def _backup_file_path() -> str:
    return os.path.join(_backup_dir(), f"bot-{_today_name()}.db")


def backup_now_sync() -> str:
    src = _db_path()
    dst = _backup_file_path()
    _ensure_dir(_backup_dir())
    con = sqlite3.connect(src)
    bck = sqlite3.connect(dst)
    try:
        con.backup(bck)
    finally:
        bck.close()
        con.close()
    return dst


async def backup_now() -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, backup_now_sync)


async def maybe_daily_backup() -> str | None:
    dst = _backup_file_path()
    if os.path.exists(dst):
        return None
    return await backup_now()
