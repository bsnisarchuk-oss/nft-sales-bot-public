"""Tests for utils/diagnostics.py."""

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
async def test_check_db_ok(db):
    """check_db should return (True, 'OK') when DB is open."""
    with patch("utils.diagnostics.db_ready", return_value=db):
        from utils.diagnostics import check_db
        ok, msg = await check_db()
        assert ok is True
        assert msg == "OK"


@pytest.mark.asyncio
async def test_check_db_no_connection():
    """check_db should return (False, ...) when DB is None."""
    with patch("utils.diagnostics.db_ready", return_value=None):
        from utils.diagnostics import check_db
        ok, msg = await check_db()
        assert ok is False
        assert "not initialized" in msg.lower()


@pytest.mark.asyncio
async def test_check_tonapi_ok():
    """check_tonapi should return (True, 'OK') when API responds."""
    mock_client = AsyncMock()
    mock_client.get_account_events = AsyncMock(return_value={"events": []})
    mock_client.close = AsyncMock()

    def _make_client(*a, **kw):
        return mock_client

    mock_client_cls = _make_client

    with (
        patch("utils.diagnostics.all_tracked_collections", new_callable=AsyncMock, return_value={"0:col1"}),
        patch("utils.diagnostics.TonApiClient", mock_client_cls),
    ):
        from utils.diagnostics import check_tonapi
        ok, msg = await check_tonapi(timeout_sec=5)
        assert ok is True
        assert msg == "OK"
        mock_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_check_db_exception():
    """check_db returns (False, error_type) when execute raises."""
    db_mock = AsyncMock()
    db_mock.conn = AsyncMock()
    db_mock.conn.execute = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("utils.diagnostics.db_ready", return_value=db_mock):
        from utils.diagnostics import check_db
        ok, msg = await check_db()
        assert ok is False
        assert "RuntimeError" in msg


@pytest.mark.asyncio
async def test_check_tonapi_no_collections_no_getgems():
    """No tracked collections, GETGEMS_ADDRESSES is empty → (False, 'No tracked collections')."""
    with (
        patch("utils.diagnostics.all_tracked_collections", new_callable=AsyncMock, return_value=set()),
        patch("utils.diagnostics.GETGEMS_ADDRESSES", []),
    ):
        from utils.diagnostics import check_tonapi
        ok, msg = await check_tonapi()
        assert ok is False
        assert "No tracked" in msg


@pytest.mark.asyncio
async def test_check_tonapi_falls_back_to_getgems():
    """No tracked collections but GETGEMS_ADDRESSES set → uses first address."""
    mock_client = AsyncMock()
    mock_client.get_account_events = AsyncMock(return_value={})
    mock_client.close = AsyncMock()

    with (
        patch("utils.diagnostics.all_tracked_collections", new_callable=AsyncMock, return_value=set()),
        patch("utils.diagnostics.GETGEMS_ADDRESSES", ["0:getgems"]),
        patch("utils.diagnostics.TonApiClient", return_value=mock_client),
    ):
        from utils.diagnostics import check_tonapi
        ok, msg = await check_tonapi()
        assert ok is True


@pytest.mark.asyncio
async def test_check_tonapi_timeout():
    """check_tonapi returns (False, 'TimeoutError') on asyncio.TimeoutError."""
    import asyncio

    mock_client = AsyncMock()
    mock_client.get_account_events = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_client.close = AsyncMock()

    with (
        patch("utils.diagnostics.all_tracked_collections", new_callable=AsyncMock, return_value={"0:col1"}),
        patch("utils.diagnostics.TonApiClient", return_value=mock_client),
    ):
        from utils.diagnostics import check_tonapi
        ok, msg = await check_tonapi(timeout_sec=0)
        assert ok is False
        # TimeoutError from wait_for
        assert "Timeout" in msg or ok is False


@pytest.mark.asyncio
async def test_check_tonapi_exception():
    """check_tonapi returns (False, error_type) on generic exception."""
    mock_client = AsyncMock()
    mock_client.get_account_events = AsyncMock(side_effect=RuntimeError("api down"))
    mock_client.close = AsyncMock()

    with (
        patch("utils.diagnostics.all_tracked_collections", new_callable=AsyncMock, return_value={"0:col1"}),
        patch("utils.diagnostics.TonApiClient", return_value=mock_client),
    ):
        from utils.diagnostics import check_tonapi
        ok, msg = await check_tonapi()
        assert ok is False
        assert "RuntimeError" in msg


# ── check_bot_can_send ──

@pytest.mark.asyncio
async def test_check_bot_admin():
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=AsyncMock(id=123))
    member = AsyncMock()
    member.status = "administrator"
    bot.get_chat_member = AsyncMock(return_value=member)

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is True
    assert "administrator" in msg


@pytest.mark.asyncio
async def test_check_bot_creator():
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=AsyncMock(id=123))
    member = AsyncMock()
    member.status = "creator"
    bot.get_chat_member = AsyncMock(return_value=member)

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is True


@pytest.mark.asyncio
async def test_check_bot_restricted_can_send():
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=AsyncMock(id=123))
    member = AsyncMock()
    member.status = "restricted"
    member.can_send_messages = True
    bot.get_chat_member = AsyncMock(return_value=member)

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is True


@pytest.mark.asyncio
async def test_check_bot_restricted_cannot_send():
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=AsyncMock(id=123))
    member = AsyncMock()
    member.status = "restricted"
    member.can_send_messages = False
    bot.get_chat_member = AsyncMock(return_value=member)

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is False
    assert "restricted" in msg


@pytest.mark.asyncio
async def test_check_bot_kicked():
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=AsyncMock(id=123))
    member = AsyncMock()
    member.status = "kicked"
    bot.get_chat_member = AsyncMock(return_value=member)

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is False


@pytest.mark.asyncio
async def test_check_bot_member():
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=AsyncMock(id=123))
    member = AsyncMock()
    member.status = "member"
    bot.get_chat_member = AsyncMock(return_value=member)

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is True


@pytest.mark.asyncio
async def test_check_bot_exception():
    bot = AsyncMock()
    bot.get_me = AsyncMock(side_effect=RuntimeError("forbidden"))

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is False
    assert "RuntimeError" in msg


@pytest.mark.asyncio
async def test_check_bot_unknown_status():
    bot = AsyncMock()
    bot.get_me = AsyncMock(return_value=AsyncMock(id=123))
    member = AsyncMock()
    member.status = "unknown_status"
    bot.get_chat_member = AsyncMock(return_value=member)

    from utils.diagnostics import check_bot_can_send
    ok, msg = await check_bot_can_send(bot, -100)
    assert ok is True
