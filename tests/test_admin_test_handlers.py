"""Tests for admin/test_handlers.py — test commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from admin.test_handlers import cmd_test, cmd_test_photo, cmd_test_route, cmd_test_sale


def _msg(user_id: int = 111, text: str = "") -> MagicMock:
    m = MagicMock()
    m.from_user = MagicMock()
    m.from_user.id = user_id
    m.chat = MagicMock()
    m.chat.id = -100
    m.text = text
    m.answer = AsyncMock()
    m.bot = AsyncMock()
    return m


AP = patch("admin.test_handlers._admin_ids", return_value=frozenset({111}))


# ---- /test ----


@pytest.mark.asyncio
async def test_cmd_test_non_admin():
    m = _msg(user_id=999)
    with AP:
        await cmd_test(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_test_ok():
    m = _msg(user_id=111)
    with AP:
        await cmd_test(m)
    m.answer.assert_called_once()
    text = m.answer.call_args[0][0]
    assert "TEST_TRACE" in text or "1.23" in text


# ---- /test_photo ----


@pytest.mark.asyncio
async def test_cmd_test_photo_non_admin():
    m = _msg(user_id=999)
    with AP:
        await cmd_test_photo(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_test_photo_ok():
    m = _msg(user_id=111)
    with AP:
        await cmd_test_photo(m)
    m.bot.send_photo.assert_called_once()
    call_kw = m.bot.send_photo.call_args
    assert call_kw.kwargs.get("chat_id") == -100 or call_kw[1].get("chat_id") == -100


@pytest.mark.asyncio
async def test_cmd_test_photo_no_bot():
    m = _msg(user_id=111)
    m.bot = None
    with AP:
        await cmd_test_photo(m)
    # Should return gracefully without error


# ---- /test_sale ----


@pytest.mark.asyncio
async def test_cmd_test_sale_non_admin():
    m = _msg(user_id=999)
    with AP:
        await cmd_test_sale(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_test_sale_ok():
    m = _msg(user_id=111)
    with AP:
        await cmd_test_sale(m)
    m.answer.assert_called_once()
    text = m.answer.call_args[0][0]
    assert "TEST_TRACE_MULTI" in text or "2.50" in text or "2.5" in text


# ---- /test_route ----


@pytest.mark.asyncio
async def test_cmd_test_route_non_admin():
    m = _msg(user_id=999, text="/test_route")
    with AP:
        await cmd_test_route(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_test_route_with_addr():
    m = _msg(user_id=111, text="/test_route 0:abc123")
    mock_client = MagicMock()
    mock_client.normalize_address = AsyncMock(return_value=("0:abc123", "EQabc"))
    mock_client.close = AsyncMock()
    with AP, patch(
        "admin.test_handlers.TonApiClient", return_value=mock_client
    ), patch(
        "admin.test_handlers.dispatch_sale_to_chats",
        new_callable=AsyncMock,
        return_value=[-100],
    ) as mock_d:
        await cmd_test_route(m)
    mock_d.assert_called_once()
    sale = mock_d.call_args[0][1]
    assert sale.items[0].collection_address == "0:abc123"
    text = m.answer.call_args[0][0]
    assert "test_route" in text


@pytest.mark.asyncio
async def test_cmd_test_route_no_addr_no_collections():
    m = _msg(user_id=111, text="/test_route")
    with AP, patch(
        "admin.test_handlers.get_collections_for_chat",
        new_callable=AsyncMock,
        return_value=[],
    ):
        await cmd_test_route(m)
    assert "коллекци" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_test_route_no_addr_uses_first_collection():
    m = _msg(user_id=111, text="/test_route")
    mock_client = MagicMock()
    mock_client.normalize_address = AsyncMock(return_value=("0:col1", "EQcol1"))
    mock_client.close = AsyncMock()
    with AP, patch(
        "admin.test_handlers.get_collections_for_chat",
        new_callable=AsyncMock,
        return_value=[{"raw": "0:col1", "b64url": "EQcol1"}],
    ), patch(
        "admin.test_handlers.TonApiClient", return_value=mock_client
    ), patch(
        "admin.test_handlers.dispatch_sale_to_chats",
        new_callable=AsyncMock,
        return_value=[-100],
    ) as mock_d:
        await cmd_test_route(m)
    sale = mock_d.call_args[0][1]
    assert sale.items[0].collection_address == "0:col1"


@pytest.mark.asyncio
async def test_cmd_test_route_normalize_fails():
    m = _msg(user_id=111, text="/test_route 0:bad")
    mock_client = MagicMock()
    mock_client.normalize_address = AsyncMock(side_effect=Exception("API error"))
    mock_client.close = AsyncMock()
    with AP, patch(
        "admin.test_handlers.TonApiClient", return_value=mock_client
    ), patch(
        "admin.test_handlers.dispatch_sale_to_chats",
        new_callable=AsyncMock,
        return_value=[],
    ):
        await cmd_test_route(m)
    # Should still work, using original address
    text = m.answer.call_args[0][0]
    assert "test_route" in text


@pytest.mark.asyncio
async def test_cmd_test_no_from_user():
    m = _msg(user_id=111)
    m.from_user = None
    with AP:
        await cmd_test(m)
    assert "доступа" in m.answer.call_args[0][0].lower()
