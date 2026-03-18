"""Tests for utils/chat_settings_db.py — настройки чатов (min_price, cooldown, whale)."""

import pytest

from utils.chat_settings_db import (
    ChatSettings,
    copy_settings,
    get_settings,
    reset_settings,
    set_cooldown,
    set_min_price,
    upsert_settings,
)
from utils.chat_store_db import bind_chat


@pytest.mark.asyncio
async def test_default_settings(db):
    """Для нового чата возвращаются дефолтные настройки."""
    s = await get_settings(db, -100)
    assert s.min_price_ton == 0.0
    assert s.cooldown_sec == 0
    assert s.show_link_preview is True
    assert s.send_photos is True
    assert s.whale_threshold_ton == 0.0
    assert s.whale_ping_admins is False


@pytest.mark.asyncio
async def test_upsert_and_get(db):
    """upsert_settings сохраняет, get_settings читает."""
    await bind_chat(db, -100, "G", 1)
    s = ChatSettings(min_price_ton=2.5, cooldown_sec=30, send_photos=False)
    await upsert_settings(db, -100, s)

    loaded = await get_settings(db, -100)
    assert loaded.min_price_ton == 2.5
    assert loaded.cooldown_sec == 30
    assert loaded.send_photos is False


@pytest.mark.asyncio
async def test_set_min_price(db):
    await bind_chat(db, -100, "G", 1)
    await set_min_price(db, -100, 5.0)
    s = await get_settings(db, -100)
    assert s.min_price_ton == 5.0


@pytest.mark.asyncio
async def test_set_cooldown(db):
    await bind_chat(db, -100, "G", 1)
    await set_cooldown(db, -100, 60)
    s = await get_settings(db, -100)
    assert s.cooldown_sec == 60


@pytest.mark.asyncio
async def test_reset_settings(db):
    """reset_settings возвращает все поля к дефолтам."""
    await bind_chat(db, -100, "G", 1)
    await upsert_settings(db, -100, ChatSettings(min_price_ton=10, cooldown_sec=99))
    await reset_settings(db, -100)

    s = await get_settings(db, -100)
    assert s.min_price_ton == 0.0
    assert s.cooldown_sec == 0


@pytest.mark.asyncio
async def test_copy_settings(db):
    """copy_settings копирует настройки из одного чата в другой."""
    await bind_chat(db, -100, "Src", 1)
    await bind_chat(db, -200, "Dst", 1)
    await upsert_settings(db, -100, ChatSettings(min_price_ton=3.0, whale_threshold_ton=50.0))

    ok = await copy_settings(db, from_chat_id=-100, to_chat_id=-200)
    assert ok is True

    s = await get_settings(db, -200)
    assert s.min_price_ton == 3.0
    assert s.whale_threshold_ton == 50.0


@pytest.mark.asyncio
async def test_copy_settings_nonexistent_source(db):
    """copy_settings из несуществующего чата возвращает False."""
    await bind_chat(db, -200, "Dst", 1)
    ok = await copy_settings(db, from_chat_id=-999, to_chat_id=-200)
    assert ok is False


@pytest.mark.asyncio
async def test_whale_settings(db):
    """Whale threshold и ping admins сохраняются корректно."""
    await bind_chat(db, -100, "G", 1)
    s = ChatSettings(whale_threshold_ton=100.0, whale_ping_admins=True)
    await upsert_settings(db, -100, s)

    loaded = await get_settings(db, -100)
    assert loaded.whale_threshold_ton == 100.0
    assert loaded.whale_ping_admins is True
