"""Tests for admin/demo_handlers.py — demo mode handlers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message

from admin.demo_handlers import (
    cb_demo_album,
    cb_demo_back,
    cb_demo_menu,
    cb_demo_photo,
    cb_demo_text,
    cb_demo_whale,
    cmd_demo,
    cmd_demo_mode,
)


def _msg(user_id: int = 111) -> MagicMock:
    m = MagicMock()
    m.from_user = MagicMock()
    m.from_user.id = user_id
    m.chat = MagicMock()
    m.chat.id = -100
    m.answer = AsyncMock()
    m.bot = AsyncMock()
    return m


def _cb(user_id: int = 111) -> MagicMock:
    q = MagicMock()
    q.from_user = MagicMock()
    q.from_user.id = user_id
    q.answer = AsyncMock()
    m = MagicMock(spec=Message)
    m.chat = MagicMock()
    m.chat.id = -100
    m.answer = AsyncMock()
    m.bot = AsyncMock()
    q.message = m
    return q


def _st() -> MagicMock:
    s = MagicMock()
    s.set_state = AsyncMock()
    s.clear = AsyncMock()
    return s


AP = patch("admin.demo_handlers._admin_ids", return_value=frozenset({111}))


# ---- /demo, /demo_mode ----


@pytest.mark.asyncio
async def test_demo_non_admin():
    m = _msg(user_id=999)
    with AP:
        await cmd_demo(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_demo_ok():
    m = _msg(user_id=111)
    with AP:
        await cmd_demo(m)
    assert "Demo" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_demo_mode_non_admin():
    m = _msg(user_id=999)
    with AP:
        await cmd_demo_mode(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_demo_mode_ok():
    m = _msg(user_id=111)
    with AP:
        await cmd_demo_mode(m)
    assert "Demo" in m.answer.call_args[0][0]


# ---- cb_demo_menu ----


@pytest.mark.asyncio
async def test_cb_demo_menu_non_admin():
    q = _cb(user_id=999)
    s = _st()
    with AP:
        await cb_demo_menu(q, s)
    assert "доступа" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_cb_demo_menu_ok():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_demo_menu(q, s)
    s.clear.assert_called_once()
    assert "Demo" in q.message.answer.call_args[0][0]


# ---- cb_demo_text ----


@pytest.mark.asyncio
async def test_demo_text_non_admin():
    q = _cb(user_id=999)
    with AP:
        await cb_demo_text(q)
    assert "доступа" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_demo_text_no_collections():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value=""
    ):
        await cb_demo_text(q)
    assert "нет коллекций" in q.message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_demo_text_sends_sale():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value="0:col"
    ), patch(
        "admin.demo_handlers.dispatch_sale_to_chat", new_callable=AsyncMock, return_value=True
    ) as mock_d:
        await cb_demo_text(q)
    mock_d.assert_called_once()
    sale = mock_d.call_args[0][2]
    assert sale.trace_id == "DEMO_TEXT"


# ---- cb_demo_photo ----


@pytest.mark.asyncio
async def test_demo_photo_non_admin():
    q = _cb(user_id=999)
    with AP:
        await cb_demo_photo(q)
    assert "доступа" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_demo_photo_no_collections():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value=""
    ):
        await cb_demo_photo(q)
    assert "нет коллекций" in q.message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_demo_photo_ok():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value="0:col"
    ), patch(
        "admin.demo_handlers.dispatch_sale_to_chat", new_callable=AsyncMock, return_value=True
    ) as mock_d:
        await cb_demo_photo(q)
    mock_d.assert_called_once()
    sale = mock_d.call_args[0][2]
    assert sale.trace_id == "DEMO_PHOTO"
    assert sale.items[0].image_url.startswith("http")


# ---- cb_demo_album ----


@pytest.mark.asyncio
async def test_demo_album_non_admin():
    q = _cb(user_id=999)
    with AP:
        await cb_demo_album(q)
    assert "доступа" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_demo_album_no_collections():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value=""
    ):
        await cb_demo_album(q)
    assert "нет коллекций" in q.message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_demo_album_ok():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value="0:col"
    ), patch(
        "admin.demo_handlers.dispatch_sale_to_chat", new_callable=AsyncMock, return_value=True
    ) as mock_d:
        await cb_demo_album(q)
    mock_d.assert_called_once()
    sale = mock_d.call_args[0][2]
    assert sale.trace_id == "DEMO_ALBUM"
    assert len(sale.items) == 3


# ---- cb_demo_whale ----


@pytest.mark.asyncio
async def test_demo_whale_non_admin():
    q = _cb(user_id=999)
    with AP:
        await cb_demo_whale(q)
    assert "доступа" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_demo_whale_no_collections():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value=""
    ):
        await cb_demo_whale(q)
    assert "нет коллекций" in q.message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_demo_whale_ok():
    q = _cb(user_id=111)
    with AP, patch(
        "admin.demo_handlers._get_demo_collection_raw", new_callable=AsyncMock, return_value="0:col"
    ), patch(
        "admin.demo_handlers.dispatch_sale_to_chat", new_callable=AsyncMock, return_value=True
    ) as mock_d:
        await cb_demo_whale(q)
    mock_d.assert_called_once()
    sale = mock_d.call_args[0][2]
    assert sale.price_ton == 9999
    assert sale.trace_id == "DEMO_WHALE"


# ---- cb_demo_back ----


@pytest.mark.asyncio
async def test_demo_back_non_admin():
    q = _cb(user_id=999)
    with AP:
        await cb_demo_back(q)
    assert "доступа" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_demo_back_ok():
    q = _cb(user_id=111)
    with AP:
        await cb_demo_back(q)
    assert "меню" in q.message.answer.call_args[0][0].lower()
