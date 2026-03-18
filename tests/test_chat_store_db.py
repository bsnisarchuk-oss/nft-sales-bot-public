"""Tests for utils/chat_store_db.py — CRUD чатов и коллекций в SQLite."""

import pytest

from utils.chat_store_db import (
    add_collection,
    all_tracked_collections,
    bind_chat,
    enabled_chats,
    get_collections,
    list_chats,
    remove_collection,
    set_enabled,
    tracked_set,
    unbind_chat,
)


@pytest.mark.asyncio
async def test_bind_and_list(db):
    """bind_chat создаёт чат, list_chats его показывает."""
    await bind_chat(db, chat_id=-100, title="Test Group", added_by=111)
    chats = await list_chats(db)
    assert len(chats) == 1
    assert chats[0]["chat_id"] == -100
    assert chats[0]["title"] == "Test Group"
    assert chats[0]["enabled"] is True


@pytest.mark.asyncio
async def test_bind_idempotent(db):
    """Повторный bind обновляет title, не дублирует."""
    await bind_chat(db, chat_id=-100, title="Old", added_by=1)
    await bind_chat(db, chat_id=-100, title="New", added_by=1)
    chats = await list_chats(db)
    assert len(chats) == 1
    assert chats[0]["title"] == "New"


@pytest.mark.asyncio
async def test_unbind(db):
    await bind_chat(db, chat_id=-100, title="G", added_by=1)
    removed = await unbind_chat(db, -100)
    assert removed is True
    chats = await list_chats(db)
    assert len(chats) == 0


@pytest.mark.asyncio
async def test_unbind_nonexistent(db):
    removed = await unbind_chat(db, -999)
    assert removed is False


@pytest.mark.asyncio
async def test_set_enabled(db):
    await bind_chat(db, chat_id=-100, title="G", added_by=1)
    await set_enabled(db, -100, False)
    ids = await enabled_chats(db)
    assert -100 not in ids

    await set_enabled(db, -100, True)
    ids = await enabled_chats(db)
    assert -100 in ids


@pytest.mark.asyncio
async def test_add_and_get_collections(db):
    """Добавляем коллекцию в чат, проверяем get_collections."""
    await bind_chat(db, chat_id=-100, title="G", added_by=1)
    added = await add_collection(db, -100, raw="0:col1", b64url="EQcol1", name="Col One")
    assert added is True

    cols = await get_collections(db, -100)
    assert len(cols) == 1
    assert cols[0]["raw"] == "0:col1"
    assert cols[0]["name"] == "Col One"


@pytest.mark.asyncio
async def test_add_collection_duplicate(db):
    """Повторное добавление той же коллекции возвращает False."""
    await bind_chat(db, chat_id=-100, title="G", added_by=1)
    await add_collection(db, -100, raw="0:col1", b64url="", name="")
    added_again = await add_collection(db, -100, raw="0:col1", b64url="", name="")
    assert added_again is False


@pytest.mark.asyncio
async def test_remove_collection_by_raw(db):
    await bind_chat(db, chat_id=-100, title="G", added_by=1)
    await add_collection(db, -100, raw="0:col1", b64url="EQcol1", name="C")
    removed = await remove_collection(db, -100, raw_or_b64="0:col1")
    assert removed is True
    assert await get_collections(db, -100) == []


@pytest.mark.asyncio
async def test_remove_collection_by_b64url(db):
    """Удаление по EQ-адресу тоже работает."""
    await bind_chat(db, chat_id=-100, title="G", added_by=1)
    await add_collection(db, -100, raw="0:col1", b64url="EQcol1", name="C")
    removed = await remove_collection(db, -100, raw_or_b64="EQcol1")
    assert removed is True


@pytest.mark.asyncio
async def test_tracked_set(db):
    await bind_chat(db, chat_id=-100, title="G", added_by=1)
    await add_collection(db, -100, raw="0:col1", b64url="EQcol1", name="")
    ts = await tracked_set(db, -100)
    assert "0:col1" in ts
    assert "EQcol1" in ts


@pytest.mark.asyncio
async def test_all_tracked_collections(db):
    """all_tracked_collections возвращает raw коллекций из enabled чатов."""
    await bind_chat(db, chat_id=-100, title="G1", added_by=1)
    await bind_chat(db, chat_id=-200, title="G2", added_by=1)
    await add_collection(db, -100, raw="0:col1", b64url="", name="")
    await add_collection(db, -200, raw="0:col2", b64url="", name="")

    all_cols = await all_tracked_collections(db)
    assert "0:col1" in all_cols
    assert "0:col2" in all_cols

    # Отключаем чат — его коллекции не возвращаются
    await set_enabled(db, -200, False)
    all_cols = await all_tracked_collections(db)
    assert "0:col1" in all_cols
    assert "0:col2" not in all_cols
