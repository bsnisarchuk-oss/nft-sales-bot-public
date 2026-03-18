"""Tests for admin/helpers.py — pure utility functions."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from admin.helpers import _admin_ids, _ago, _get_demo_collection_raw, _is_admin, _split_chunks
from admin.keyboards import admin_main_kb, demo_kb, settings_kb

# ---- _split_chunks ----


def test_split_chunks_short():
    text = "Hello, world!"
    assert _split_chunks(text, limit=3500) == [text]


def test_split_chunks_long():
    lines = [f"Line {i:03d}: {'x' * 40}\n" for i in range(100)]
    text = "".join(lines)
    chunks = _split_chunks(text, limit=2000)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 2100


def test_split_chunks_empty():
    assert _split_chunks("") == []


# ---- _is_admin ----


def test_is_admin_true():
    assert _is_admin(111, {111, 222}) is True


def test_is_admin_false():
    assert _is_admin(999, {111, 222}) is False


# ---- _admin_ids ----


def test_admin_ids_from_env():
    ids = _admin_ids()
    assert isinstance(ids, frozenset)
    for i in ids:
        assert isinstance(i, int)


# ---- _ago ----


def test_ago_never():
    assert _ago(0) == "никогда"


def test_ago_seconds():
    assert "сек назад" in _ago(time.time() - 30)


def test_ago_minutes():
    assert "мин назад" in _ago(time.time() - 300)


def test_ago_hours():
    assert "ч назад" in _ago(time.time() - 7200)


def test_ago_days():
    assert "дн назад" in _ago(time.time() - 200000)


# ---- _get_demo_collection_raw ----


@pytest.mark.asyncio
async def test_get_demo_collection_raw_empty():
    with patch(
        "admin.helpers.get_collections_for_chat",
        new_callable=AsyncMock,
        return_value=[],
    ):
        result = await _get_demo_collection_raw(123)
        assert result == ""


@pytest.mark.asyncio
async def test_get_demo_collection_raw_found():
    with patch(
        "admin.helpers.get_collections_for_chat",
        new_callable=AsyncMock,
        return_value=[{"raw": "0:col1", "b64url": "EQcol1"}],
    ):
        result = await _get_demo_collection_raw(123)
        assert result == "0:col1"


# ---- _render_settings ----


@pytest.mark.asyncio
async def test_render_settings_no_db():
    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.chat.id = -100
    with patch("admin.helpers.db_ready", return_value=None):
        from admin.helpers import _render_settings
        await _render_settings(msg)
    text = msg.answer.call_args[0][0]
    assert "DB" in text


@pytest.mark.asyncio
async def test_render_settings_ok():
    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.chat = MagicMock()
    msg.chat.id = -100
    settings = MagicMock()
    settings.min_price_ton = 1.0
    settings.cooldown_sec = 5
    settings.show_link_preview = True
    settings.send_photos = False
    settings.whale_threshold_ton = 10.0
    settings.whale_ping_admins = True
    with patch("admin.helpers.db_ready", return_value=MagicMock()), patch(
        "admin.helpers.get_settings", new_callable=AsyncMock, return_value=settings
    ):
        from admin.helpers import _render_settings
        await _render_settings(msg)
    text = msg.answer.call_args[0][0]
    assert "Settings" in text
    assert "1.0" in text


# ---- keyboards (для coverage admin/keyboards.py) ----


def test_admin_main_kb():
    kb = admin_main_kb()
    assert kb is not None


def test_settings_kb():
    kb = settings_kb(show_preview=True, send_photos=False, whale_threshold_ton=5.0, whale_ping=True)
    assert kb is not None


def test_demo_kb():
    kb = demo_kb()
    assert kb is not None
