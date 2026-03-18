"""Tests for utils/state_store_db.py — курсор last_lt, дедупликация трейсов, parse failures."""

import pytest

from utils.state_store_db import (
    clear_parse_failure,
    get_last_lt,
    is_trace_seen,
    mark_trace_seen,
    quarantine_parse_failure,
    register_parse_failure,
    seen_trace,
    set_last_lt,
)


@pytest.mark.asyncio
async def test_last_lt_default(db):
    """Для нового адреса last_lt = 0."""
    lt = await get_last_lt(db, "0:addr")
    assert lt == 0


@pytest.mark.asyncio
async def test_set_and_get_last_lt(db):
    await set_last_lt(db, "0:addr", 12345)
    lt = await get_last_lt(db, "0:addr")
    assert lt == 12345


@pytest.mark.asyncio
async def test_update_last_lt(db):
    """Повторный set обновляет значение."""
    await set_last_lt(db, "0:addr", 100)
    await set_last_lt(db, "0:addr", 200)
    lt = await get_last_lt(db, "0:addr")
    assert lt == 200


@pytest.mark.asyncio
async def test_trace_not_seen(db):
    assert await is_trace_seen(db, "0:addr", "trace1") is False


@pytest.mark.asyncio
async def test_mark_and_check_trace(db):
    await mark_trace_seen(db, "0:addr", "trace1", lt=100)
    assert await is_trace_seen(db, "0:addr", "trace1") is True


@pytest.mark.asyncio
async def test_seen_trace_returns_false_for_new(db):
    """seen_trace возвращает False для нового трейса и записывает его."""
    is_dup = await seen_trace(db, "0:addr", "trace_new", lt=50)
    assert is_dup is False
    # Теперь он уже записан
    is_dup = await seen_trace(db, "0:addr", "trace_new", lt=50)
    assert is_dup is True


@pytest.mark.asyncio
async def test_register_parse_failure(db):
    """register_parse_failure инкрементирует attempts при повторных вызовах."""
    attempts = await register_parse_failure(
        db, "0:addr", "trace_fail", lt=10, error_name="ValueError", payload={"key": "val"}
    )
    assert attempts == 1

    attempts = await register_parse_failure(
        db, "0:addr", "trace_fail", lt=10, error_name="ValueError", payload={"key": "val"}
    )
    assert attempts == 2


@pytest.mark.asyncio
async def test_quarantine_and_clear_parse_failure(db):
    """quarantine помечает запись, clear удаляет."""
    await register_parse_failure(
        db, "0:addr", "trace_q", lt=5, error_name="Err", payload={}
    )
    await quarantine_parse_failure(db, "0:addr", "trace_q")

    # Проверяем, что запись помечена как quarantined
    cur = await db.conn.execute(
        "SELECT quarantined FROM parse_failures WHERE address=? AND trace_id=?",
        ("0:addr", "trace_q"),
    )
    row = await cur.fetchone()
    assert row[0] == 1

    # clear удаляет полностью
    await clear_parse_failure(db, "0:addr", "trace_q")
    cur = await db.conn.execute(
        "SELECT 1 FROM parse_failures WHERE address=? AND trace_id=?",
        ("0:addr", "trace_q"),
    )
    assert await cur.fetchone() is None
