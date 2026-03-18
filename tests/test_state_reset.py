"""Tests for utils/state_reset.py."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from utils.db import DB


@pytest_asyncio.fixture
async def db():
    d = DB(":memory:")
    await d.open()
    yield d
    await d.close()


@pytest.mark.asyncio
async def test_reset_no_db_raises():
    with patch("utils.state_reset.db_ready", return_value=None):
        from utils.state_reset import reset_state_last_30_min
        with pytest.raises(RuntimeError, match="not initialized"):
            await reset_state_last_30_min()


@pytest.mark.asyncio
async def test_reset_empty_addresses_returns_zero(db):
    with patch("utils.state_reset.db_ready", return_value=db):
        from utils.state_reset import reset_state_last_30_min
        result = await reset_state_last_30_min(addresses=[])
    assert result["changed"] == 0
    assert result["target_ts"] == 0


@pytest.mark.asyncio
async def test_reset_with_addresses_no_rows(db):
    with patch("utils.state_reset.db_ready", return_value=db):
        from utils.state_reset import reset_state_last_30_min
        result = await reset_state_last_30_min(addresses=["0:abc", "0:def"])
    assert "changed" in result
    assert "target_ts" in result
    assert result["changed"] == 0


@pytest.mark.asyncio
async def test_reset_auto_detect_from_tracked(db):
    with (
        patch("utils.state_reset.db_ready", return_value=db),
        patch(
            "utils.chat_store_bridge.all_tracked_collections",
            new_callable=AsyncMock,
            return_value={"0:col1"},
        ),
    ):
        from utils.state_reset import reset_state_last_30_min
        result = await reset_state_last_30_min(addresses=None)
    assert "changed" in result


@pytest.mark.asyncio
async def test_reset_addresses_whitespace_stripped(db):
    with patch("utils.state_reset.db_ready", return_value=db):
        from utils.state_reset import reset_state_last_30_min
        # Should not raise even with spaces
        result = await reset_state_last_30_min(addresses=["  0:abc  ", "", "  "])
    # Only "0:abc" is valid — no rows to update
    assert result["changed"] == 0
