"""Tests for utils/chat_store_bridge.py — DB/JSON bridge."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Patch db_ready at module level for all tests
@pytest.fixture
def mock_db():
    """Return a mock DB object."""
    db = MagicMock()
    db.conn = True
    return db


@pytest.fixture
def mock_db_ready(mock_db):
    with patch("utils.chat_store_bridge.db_ready", return_value=mock_db) as m:
        m._db = mock_db
        yield mock_db


@pytest.fixture
def mock_db_none():
    with patch("utils.chat_store_bridge.db_ready", return_value=None):
        yield


# ── READ functions: DB path ──


@pytest.mark.asyncio
async def test_enabled_chats_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store:
        mock_store.enabled_chats = AsyncMock(return_value=[1, 2, 3])
        from utils.chat_store_bridge import enabled_chats

        result = await enabled_chats()
    assert result == [1, 2, 3]
    mock_store.enabled_chats.assert_awaited_once()


@pytest.mark.asyncio
async def test_tracked_set_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store:
        mock_store.tracked_set = AsyncMock(return_value={"0:a", "0:b"})
        from utils.chat_store_bridge import tracked_set

        result = await tracked_set(1)
    assert result == {"0:a", "0:b"}


@pytest.mark.asyncio
async def test_all_tracked_collections_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store:
        mock_store.all_tracked_collections = AsyncMock(return_value={"0:x"})
        from utils.chat_store_bridge import all_tracked_collections

        result = await all_tracked_collections()
    assert result == {"0:x"}


@pytest.mark.asyncio
async def test_get_collections_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store:
        mock_store.get_collections = AsyncMock(return_value=[{"raw": "0:a"}])
        from utils.chat_store_bridge import get_collections

        result = await get_collections(1)
    assert result == [{"raw": "0:a"}]


@pytest.mark.asyncio
async def test_list_chats_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store:
        mock_store.list_chats = AsyncMock(return_value=[{"chat_id": 1}])
        from utils.chat_store_bridge import list_chats

        result = await list_chats()
    assert result == [{"chat_id": 1}]


# ── READ functions: JSON fallback ──


@pytest.mark.asyncio
async def test_enabled_chats_json(mock_db_none):
    with patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_json.enabled_chats = MagicMock(return_value=[10])
        from utils.chat_store_bridge import enabled_chats

        result = await enabled_chats()
    assert result == [10]


@pytest.mark.asyncio
async def test_tracked_set_json(mock_db_none):
    with patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_json.tracked_set = MagicMock(return_value={"0:z"})
        from utils.chat_store_bridge import tracked_set

        result = await tracked_set(1)
    assert result == {"0:z"}


# ── WRITE functions: DB + JSON backup ──


@pytest.mark.asyncio
async def test_bind_chat_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store, \
         patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_store.bind_chat = AsyncMock()
        mock_json.bind_chat = MagicMock()
        from utils.chat_store_bridge import bind_chat

        await bind_chat(1, "Test", 100)
    mock_store.bind_chat.assert_awaited_once()
    mock_json.bind_chat.assert_called_once()


@pytest.mark.asyncio
async def test_bind_chat_json_failure_ignored(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store, \
         patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_store.bind_chat = AsyncMock()
        mock_json.bind_chat = MagicMock(side_effect=RuntimeError("JSON fail"))
        from utils.chat_store_bridge import bind_chat

        # Should not raise
        await bind_chat(1, "Test", 100)
    mock_store.bind_chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_enabled_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store, \
         patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_store.set_enabled = AsyncMock()
        mock_json.set_enabled = MagicMock()
        from utils.chat_store_bridge import set_enabled

        await set_enabled(1, False)
    mock_store.set_enabled.assert_awaited_once()
    mock_json.set_enabled.assert_called_once()


@pytest.mark.asyncio
async def test_unbind_chat_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store, \
         patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_store.unbind_chat = AsyncMock(return_value=True)
        mock_json.unbind_chat = MagicMock()
        from utils.chat_store_bridge import unbind_chat

        result = await unbind_chat(1)
    assert result is True


@pytest.mark.asyncio
async def test_unbind_chat_json_fallback(mock_db_none):
    with patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_json.unbind_chat = MagicMock(return_value=True)
        from utils.chat_store_bridge import unbind_chat

        result = await unbind_chat(1)
    assert result is True


@pytest.mark.asyncio
async def test_add_collection_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store, \
         patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_store.add_collection = AsyncMock(return_value=True)
        mock_json.add_collection = MagicMock()
        from utils.chat_store_bridge import add_collection

        result = await add_collection(1, "0:a", "EQa", "MyNFT")
    assert result is True
    mock_json.add_collection.assert_called_once()


@pytest.mark.asyncio
async def test_remove_collection_db(mock_db_ready):
    with patch("utils.chat_store_bridge.chat_store_db") as mock_store, \
         patch("utils.chat_store_bridge.chat_config_store") as mock_json:
        mock_store.remove_collection = AsyncMock(return_value=True)
        mock_json.remove_collection = MagicMock()
        from utils.chat_store_bridge import remove_collection

        result = await remove_collection(1, "0:a")
    assert result is True
