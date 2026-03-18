"""Tests for utils/chat_collections_db.py — очистка коллекций чата."""

import pytest

from utils.chat_collections_db import clear_chat_collections
from utils.chat_store_db import add_collection, bind_chat, get_collections


@pytest.mark.asyncio
async def test_clear_removes_all_links(db):
    """clear_chat_collections удаляет все привязки коллекций к чату."""
    await bind_chat(db, -100, "G", 1)
    await add_collection(db, -100, raw="0:col1", b64url="", name="A")
    await add_collection(db, -100, raw="0:col2", b64url="", name="B")

    deleted = await clear_chat_collections(db, -100)
    assert deleted == 2

    cols = await get_collections(db, -100)
    assert cols == []


@pytest.mark.asyncio
async def test_clear_empty_chat(db):
    """clear_chat_collections для чата без коллекций возвращает 0."""
    await bind_chat(db, -100, "G", 1)
    deleted = await clear_chat_collections(db, -100)
    assert deleted == 0


@pytest.mark.asyncio
async def test_clear_does_not_affect_other_chats(db):
    """Очистка одного чата не трогает коллекции другого."""
    await bind_chat(db, -100, "G1", 1)
    await bind_chat(db, -200, "G2", 1)
    await add_collection(db, -100, raw="0:col1", b64url="", name="A")
    await add_collection(db, -200, raw="0:col1", b64url="", name="A")

    await clear_chat_collections(db, -100)

    # Чат -200 не затронут
    cols = await get_collections(db, -200)
    assert len(cols) == 1
