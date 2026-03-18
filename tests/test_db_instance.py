"""Tests for utils/db_instance.py — init_db, get_db, db_ready."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset module-level _db between tests."""
    import utils.db_instance as di
    original = di._db
    di._db = None
    yield
    di._db = original


@pytest.mark.asyncio
async def test_init_db_sqlite(tmp_path, monkeypatch):
    """init_db with no PostgreSQL config uses SQLite."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    # is_postgres_configured is imported inside init_db from utils.db_postgres
    with patch("utils.db_postgres.is_postgres_configured", return_value=False):
        from utils.db_instance import init_db
        db = await init_db()
    assert db is not None
    await db.close()


@pytest.mark.asyncio
async def test_init_db_returns_same_instance(tmp_path, monkeypatch):
    """Second call returns the same DB instance without re-opening."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with patch("utils.db_postgres.is_postgres_configured", return_value=False):
        from utils.db_instance import init_db
        db1 = await init_db()
        db2 = await init_db()
    assert db1 is db2
    await db1.close()


@pytest.mark.asyncio
async def test_init_db_postgres():
    """init_db with PostgreSQL configured uses PostgresDB."""
    mock_pg = AsyncMock()
    mock_pg.conn = True
    mock_pg.open = AsyncMock()
    mock_pg_cls = MagicMock(return_value=mock_pg)

    with (
        patch("utils.db_postgres.is_postgres_configured", return_value=True),
        patch("utils.db_postgres.PostgresDB", mock_pg_cls),
    ):
        from utils.db_instance import init_db
        db = await init_db()
    assert db is mock_pg


def test_get_db_none_initially():
    from utils.db_instance import get_db
    assert get_db() is None


def test_db_ready_none_when_no_db():
    from utils.db_instance import db_ready
    assert db_ready() is None


def test_db_ready_none_when_no_conn():
    import utils.db_instance as di
    mock_db = MagicMock()
    mock_db.conn = None
    di._db = mock_db
    from utils.db_instance import db_ready
    assert db_ready() is None


def test_db_ready_returns_db_when_conn_open():
    import utils.db_instance as di
    mock_db = MagicMock()
    mock_db.conn = True
    di._db = mock_db
    from utils.db_instance import db_ready
    assert db_ready() is mock_db
