"""Tests for utils/config_io.py — экспорт/импорт конфигурации в SQLite."""


from unittest.mock import patch

import pytest

from utils.chat_settings_db import get_settings
from utils.chat_store_db import add_collection, bind_chat
from utils.config_io import _import_config_locked


@pytest.mark.asyncio
async def test_import_merge_creates_chat(db):
    """Импорт в режиме merge создаёт чат и коллекции."""
    data = {
        "chats": [
            {
                "chat_id": -100,
                "title": "Imported",
                "enabled": True,
                "added_by": 1,
                "added_at": 0,
                "collections": [
                    {"raw": "0:col1", "b64url": "EQcol1", "name": "Col One"}
                ],
                "settings": {"min_price_ton": 5.0},
            }
        ],
        "state_by_address": {"0:col1": 999},
    }
    chats = data["chats"]
    state = data["state_by_address"]

    result = await _import_config_locked(db, data, chats, state, replace=False)
    assert result["chats_upserted"] == 1
    assert result["collections_upserted"] == 1
    assert result["state_upserted"] == 1

    # Проверяем настройки
    s = await get_settings(db, -100)
    assert s.min_price_ton == 5.0


@pytest.mark.asyncio
async def test_import_replace_clears_existing(db):
    """Импорт в режиме replace очищает старые данные."""
    # Создаём существующий чат
    await bind_chat(db, -100, "Old", 1)
    await add_collection(db, -100, raw="0:old_col", b64url="", name="Old")

    data = {
        "chats": [
            {
                "chat_id": -200,
                "title": "New",
                "enabled": True,
                "added_by": 2,
                "added_at": 0,
                "collections": [],
                "settings": {},
            }
        ],
        "state_by_address": {},
    }
    chats = data["chats"]
    state = data["state_by_address"]

    result = await _import_config_locked(db, data, chats, state, replace=True)
    assert result["chats_upserted"] == 1

    # Старый чат удалён
    cur = await db.conn.execute("SELECT 1 FROM chats WHERE chat_id=?", (-100,))
    assert await cur.fetchone() is None


@pytest.mark.asyncio
async def test_import_with_settings(db):
    """Все поля settings корректно импортируются."""
    data = {
        "chats": [
            {
                "chat_id": -100,
                "title": "G",
                "enabled": True,
                "added_by": 1,
                "added_at": 0,
                "collections": [],
                "settings": {
                    "min_price_ton": 1.5,
                    "cooldown_sec": 30,
                    "show_link_preview": False,
                    "send_photos": False,
                    "whale_threshold_ton": 100.0,
                    "whale_ping_admins": 1,
                },
            }
        ],
        "state_by_address": {},
    }
    chats = data["chats"]
    state = data["state_by_address"]

    await _import_config_locked(db, data, chats, state, replace=False)

    s = await get_settings(db, -100)
    assert s.min_price_ton == 1.5
    assert s.cooldown_sec == 30
    assert s.show_link_preview is False
    assert s.send_photos is False
    assert s.whale_threshold_ton == 100.0


@pytest.mark.asyncio
async def test_import_empty_chats(db):
    """Пустой список чатов — ничего не ломается."""
    result = await _import_config_locked(db, {}, [], {}, replace=False)
    assert result["chats_upserted"] == 0
    assert result["collections_upserted"] == 0


@pytest.mark.asyncio
async def test_import_skip_invalid_chat(db):
    """Невалидный элемент в списке чатов пропускается."""
    result = await _import_config_locked(db, {}, ["not_a_dict", 42], {}, replace=False)
    assert result["chats_upserted"] == 0


# --- export_config ---

@pytest.mark.asyncio
async def test_export_config_no_db():
    """export_config raises RuntimeError when DB not initialized."""
    from utils.config_io import export_config
    with patch("utils.config_io.db_ready", return_value=None):
        with pytest.raises(RuntimeError, match="not initialized"):
            await export_config()


@pytest.mark.asyncio
async def test_export_config_empty_db(db):
    """export_config on empty DB returns valid structure."""
    from utils.config_io import export_config
    with patch("utils.config_io.db_ready", return_value=db):
        result = await export_config()
    assert result["schema"] == 2
    assert "exported_at" in result
    assert result["chats"] == []
    assert result["state_by_address"] == {}


@pytest.mark.asyncio
async def test_export_config_with_chat(db):
    """export_config exports chat + collection + settings."""
    from utils.chat_settings_db import ChatSettings, upsert_settings
    from utils.chat_store_db import add_collection, bind_chat
    from utils.config_io import export_config

    await bind_chat(db, -100, "Test Chat", 1)
    await add_collection(db, -100, "0:col1", "EQcol1", "My Col")
    s = ChatSettings(min_price_ton=2.5, cooldown_sec=30)
    await upsert_settings(db, -100, s)

    with patch("utils.config_io.db_ready", return_value=db):
        result = await export_config()

    assert len(result["chats"]) == 1
    chat = result["chats"][0]
    assert chat["chat_id"] == -100
    assert chat["title"] == "Test Chat"
    assert len(chat["collections"]) == 1
    assert chat["collections"][0]["raw"] == "0:col1"
    assert chat["settings"]["min_price_ton"] == 2.5
    assert chat["settings"]["cooldown_sec"] == 30


@pytest.mark.asyncio
async def test_export_config_includes_state(db):
    """export_config includes state_by_address cursor positions."""
    from utils.config_io import export_config

    await db.conn.execute(
        "INSERT INTO state_by_address(address, last_lt) VALUES (?, ?)", ("0:col1", 999)
    )
    await db.conn.commit()

    with patch("utils.config_io.db_ready", return_value=db):
        result = await export_config()

    assert result["state_by_address"].get("0:col1") == 999


@pytest.mark.asyncio
async def test_export_chat_no_settings(db):
    """Chat without settings row gets default settings dict."""
    from utils.chat_store_db import bind_chat
    from utils.config_io import export_config

    await bind_chat(db, -200, "No Settings Chat", 1)

    with patch("utils.config_io.db_ready", return_value=db):
        result = await export_config()

    chat = next(c for c in result["chats"] if c["chat_id"] == -200)
    assert chat["settings"]["min_price_ton"] == 0.0
    assert chat["settings"]["show_link_preview"] is True


# --- import_config (top-level validation) ---

@pytest.mark.asyncio
async def test_import_config_no_db():
    """import_config raises RuntimeError when DB not initialized."""
    from utils.config_io import import_config
    with patch("utils.config_io.db_ready", return_value=None):
        with pytest.raises(RuntimeError, match="not initialized"):
            await import_config({"chats": []})


@pytest.mark.asyncio
async def test_import_config_invalid_root(db):
    """import_config raises ValueError when root is not a dict."""
    from utils.config_io import import_config
    with patch("utils.config_io.db_ready", return_value=db):
        with pytest.raises(ValueError, match="not an object"):
            await import_config("not a dict")


@pytest.mark.asyncio
async def test_import_config_chats_not_list(db):
    """import_config raises ValueError when chats is not a list."""
    from utils.config_io import import_config
    with patch("utils.config_io.db_ready", return_value=db):
        with pytest.raises(ValueError, match="must be a list"):
            await import_config({"chats": "wrong"})


@pytest.mark.asyncio
async def test_import_config_state_not_dict(db):
    """import_config raises ValueError when state_by_address is not a dict."""
    from utils.config_io import import_config
    with patch("utils.config_io.db_ready", return_value=db):
        with pytest.raises(ValueError, match="must be an object"):
            await import_config({"chats": [], "state_by_address": "bad"})


@pytest.mark.asyncio
async def test_import_config_success(db):
    """import_config merge mode works end-to-end."""
    from utils.config_io import import_config
    data = {
        "chats": [{"chat_id": -300, "title": "T", "enabled": True, "added_by": 1,
                   "added_at": 1700000000, "collections": [], "settings": {}}],
        "state_by_address": {},
    }
    with patch("utils.config_io.db_ready", return_value=db):
        result = await import_config(data)
    assert result["chats_upserted"] == 1


# --- _import_config_locked edge cases ---

@pytest.mark.asyncio
async def test_import_chat_with_added_at(db):
    """Chat with added_at > 0 uses the WITH added_at SQL branch."""
    data = {"chats": [
        {"chat_id": -400, "title": "T", "enabled": True, "added_by": 1,
         "added_at": 1700000000, "collections": [], "settings": {}}
    ], "state_by_address": {}}
    result = await _import_config_locked(db, data, data["chats"], {}, replace=False)
    assert result["chats_upserted"] == 1
    cur = await db.conn.execute("SELECT added_at FROM chats WHERE chat_id=?", (-400,))
    row = await cur.fetchone()
    assert row[0] == 1700000000


@pytest.mark.asyncio
async def test_import_collection_empty_raw_skipped(db):
    """Collection with empty raw field is skipped."""
    chat = {"chat_id": -500, "title": "T", "enabled": True, "added_by": 1,
            "added_at": 0, "collections": [{"raw": "", "b64url": "EQ", "name": "X"}],
            "settings": {}}
    result = await _import_config_locked(db, {}, [chat], {}, replace=False)
    assert result["collections_upserted"] == 0


@pytest.mark.asyncio
async def test_import_non_dict_collection_skipped(db):
    """Non-dict item in collections list is skipped."""
    chat = {"chat_id": -600, "title": "T", "enabled": True, "added_by": 1,
            "added_at": 0, "collections": ["not_a_dict", None, 42],
            "settings": {}}
    result = await _import_config_locked(db, {}, [chat], {}, replace=False)
    assert result["collections_upserted"] == 0


@pytest.mark.asyncio
async def test_import_settings_bad_values(db):
    """Bad settings values (non-numeric) fall back to defaults."""
    chat = {"chat_id": -700, "title": "T", "enabled": True, "added_by": 1,
            "added_at": 0, "collections": [],
            "settings": {"min_price_ton": "bad", "cooldown_sec": "also_bad",
                         "whale_threshold_ton": "x", "whale_ping_admins": "y"}}
    result = await _import_config_locked(db, {}, [chat], {}, replace=False)
    assert result["chats_upserted"] == 1

    from utils.chat_settings_db import get_settings
    s = await get_settings(db, -700)
    assert s.min_price_ton == 0.0
    assert s.cooldown_sec == 0


@pytest.mark.asyncio
async def test_import_state_bad_lt_defaults_to_zero(db):
    """Bad lt value in state_by_address defaults to 0."""
    result = await _import_config_locked(
        db, {}, [], {"0:col_bad": "not_an_int"}, replace=False
    )
    assert result["state_upserted"] == 1
    cur = await db.conn.execute(
        "SELECT last_lt FROM state_by_address WHERE address=?", ("0:col_bad",)
    )
    row = await cur.fetchone()
    assert row[0] == 0
