"""Tests for utils/backup_db.py — автобэкап SQLite через backup API."""

import os

import pytest

from utils.backup_db import backup_now_sync, maybe_daily_backup


def test_backup_now_sync(tmp_path):
    """backup_now_sync создаёт файл бэкапа."""
    db_file = str(tmp_path / "bot.db")
    # Создаём минимальную БД
    import sqlite3

    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE test (id INTEGER)")
    con.close()

    with (
        pytest.MonkeyPatch.context() as mp,
    ):
        mp.setenv("DB_PATH", db_file)
        mp.setenv("DATA_DIR", str(tmp_path))
        path = backup_now_sync()

    assert os.path.exists(path)
    assert path.endswith(".db")


@pytest.mark.asyncio
async def test_maybe_daily_backup_creates(tmp_path):
    """maybe_daily_backup создаёт бэкап, если его ещё нет."""
    db_file = str(tmp_path / "bot.db")
    import sqlite3

    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE test (id INTEGER)")
    con.close()

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DB_PATH", db_file)
        mp.setenv("DATA_DIR", str(tmp_path))
        path = await maybe_daily_backup()

    assert path is not None
    assert os.path.exists(path)


@pytest.mark.asyncio
async def test_maybe_daily_backup_skips_existing(tmp_path):
    """maybe_daily_backup пропускает, если бэкап за сегодня уже есть."""
    db_file = str(tmp_path / "bot.db")
    import sqlite3

    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE test (id INTEGER)")
    con.close()

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("DB_PATH", db_file)
        mp.setenv("DATA_DIR", str(tmp_path))
        # Первый раз — создаёт
        await maybe_daily_backup()
        # Второй раз — пропускает
        result = await maybe_daily_backup()

    assert result is None
