"""Tests for admin/settings_handlers.py — settings commands and FSM flows."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message

from admin.settings_handlers import (
    cb_add_collection,
    cb_collections_reset_confirm,
    cb_remove_collection,
    cb_settings_back,
    cb_settings_cooldown,
    cb_settings_copy,
    cb_settings_menu,
    cb_settings_min_price,
    cb_settings_reset,
    cb_settings_whale_threshold,
    cb_state_reset_30m,
    cb_toggle_photos,
    cb_toggle_preview,
    cb_toggle_whale_ping,
    cmd_set_cooldown,
    cmd_set_min_price,
    cmd_settings,
    st_add_collection,
    st_copy_from_chat,
    st_remove_collection,
    st_reset_collections_confirm,
    st_wait_cooldown,
    st_wait_min_price,
    st_wait_whale_threshold,
)


def _msg(user_id: int = 111, chat_id: int = -100, text: str = "") -> MagicMock:
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.chat = MagicMock()
    msg.chat.id = chat_id
    msg.text = text
    msg.answer = AsyncMock()
    msg.bot = AsyncMock()
    return msg


def _cb(user_id: int = 111, chat_id: int = -100) -> MagicMock:
    query = MagicMock()
    query.from_user = MagicMock()
    query.from_user.id = user_id
    query.answer = AsyncMock()
    m = MagicMock(spec=Message)
    m.chat = MagicMock()
    m.chat.id = chat_id
    m.answer = AsyncMock()
    m.bot = AsyncMock()
    query.message = m
    return query


def _st() -> MagicMock:
    s = MagicMock()
    s.set_state = AsyncMock()
    s.clear = AsyncMock()
    s.get_data = AsyncMock(return_value={})
    s.update_data = AsyncMock()
    return s


def _settings(**kw):
    s = MagicMock()
    s.min_price_ton = kw.get("min_price", 0.0)
    s.cooldown_sec = kw.get("cooldown", 0)
    s.show_link_preview = kw.get("preview", True)
    s.send_photos = kw.get("photos", True)
    s.whale_threshold_ton = kw.get("whale", 0.0)
    s.whale_ping_admins = kw.get("ping", False)
    return s


AP = patch("admin.settings_handlers._admin_ids", return_value=frozenset({111}))


# ---- /settings ----


@pytest.mark.asyncio
async def test_cmd_settings_non_admin():
    m = _msg(user_id=999)
    with AP:
        await cmd_settings(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_settings_ok():
    m = _msg(user_id=111)
    with AP, patch("admin.settings_handlers._render_settings", new_callable=AsyncMock) as mock_r:
        await cmd_settings(m)
    mock_r.assert_called_once_with(m)


# ---- /set_min_price ----


@pytest.mark.asyncio
async def test_set_min_price_valid():
    m = _msg(user_id=111, text="/set_min_price 2.5")
    db = MagicMock()
    with AP, patch("admin.settings_handlers.db_ready", return_value=db), patch(
        "admin.settings_handlers.set_min_price", new_callable=AsyncMock
    ) as mock_set:
        await cmd_set_min_price(m)
    mock_set.assert_called_once_with(db, m.chat.id, 2.5)


@pytest.mark.asyncio
async def test_set_min_price_negative():
    m = _msg(user_id=111, text="/set_min_price -1")
    with AP:
        await cmd_set_min_price(m)
    assert "❌" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_set_min_price_no_arg():
    m = _msg(user_id=111, text="/set_min_price")
    with AP:
        await cmd_set_min_price(m)
    assert "пример" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_set_min_price_garbage():
    m = _msg(user_id=111, text="/set_min_price abc")
    with AP:
        await cmd_set_min_price(m)
    assert "❌" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_set_min_price_no_db():
    m = _msg(user_id=111, text="/set_min_price 5")
    with AP, patch("admin.settings_handlers.db_ready", return_value=None):
        await cmd_set_min_price(m)
    assert "DB" in m.answer.call_args[0][0]


# ---- /set_cooldown ----


@pytest.mark.asyncio
async def test_set_cooldown_valid():
    m = _msg(user_id=111, text="/set_cooldown 10")
    db = MagicMock()
    with AP, patch("admin.settings_handlers.db_ready", return_value=db), patch(
        "admin.settings_handlers.set_cooldown", new_callable=AsyncMock
    ) as mock_set:
        await cmd_set_cooldown(m)
    mock_set.assert_called_once_with(db, m.chat.id, 10)


@pytest.mark.asyncio
async def test_set_cooldown_negative():
    m = _msg(user_id=111, text="/set_cooldown -5")
    with AP:
        await cmd_set_cooldown(m)
    assert "❌" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_set_cooldown_no_arg():
    m = _msg(user_id=111, text="/set_cooldown")
    with AP:
        await cmd_set_cooldown(m)
    assert "пример" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_set_cooldown_no_db():
    m = _msg(user_id=111, text="/set_cooldown 10")
    with AP, patch("admin.settings_handlers.db_ready", return_value=None):
        await cmd_set_cooldown(m)
    assert "DB" in m.answer.call_args[0][0]


# ---- Callbacks: simple navigations ----


@pytest.mark.asyncio
async def test_cb_settings_menu():
    q = _cb(user_id=111)
    s = _st()
    with AP, patch("admin.settings_handlers._render_settings", new_callable=AsyncMock):
        await cb_settings_menu(q, s)
    s.clear.assert_called_once()
    q.answer.assert_called()


@pytest.mark.asyncio
async def test_cb_settings_menu_non_admin():
    q = _cb(user_id=999)
    s = _st()
    with AP:
        await cb_settings_menu(q, s)
    q.answer.assert_called_once()
    assert "доступа" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_cb_settings_back():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_settings_back(q, s)
    s.clear.assert_called_once()
    q.answer.assert_called()


@pytest.mark.asyncio
async def test_cb_add_collection():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_add_collection(q, s)
    s.set_state.assert_called_once()
    q.answer.assert_called()


@pytest.mark.asyncio
async def test_cb_remove_collection():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_remove_collection(q, s)
    s.set_state.assert_called_once()
    q.answer.assert_called()


# ---- Callbacks: FSM entry points ----


@pytest.mark.asyncio
async def test_cb_settings_min_price():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_settings_min_price(q, s)
    s.set_state.assert_called_once()


@pytest.mark.asyncio
async def test_cb_settings_cooldown():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_settings_cooldown(q, s)
    s.set_state.assert_called_once()


@pytest.mark.asyncio
async def test_cb_settings_whale_threshold():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_settings_whale_threshold(q, s)
    s.set_state.assert_called_once()


@pytest.mark.asyncio
async def test_cb_settings_copy():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_settings_copy(q, s)
    s.set_state.assert_called_once()


@pytest.mark.asyncio
async def test_cb_collections_reset_confirm():
    q = _cb(user_id=111)
    s = _st()
    with AP:
        await cb_collections_reset_confirm(q, s)
    s.set_state.assert_called_once()


# ---- Callbacks: toggles ----


@pytest.mark.asyncio
async def test_toggle_preview():
    q = _cb(user_id=111)
    s = _st()
    settings = _settings(preview=True)
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.get_settings", new_callable=AsyncMock, return_value=settings
    ), patch("admin.settings_handlers.upsert_settings", new_callable=AsyncMock), patch(
        "admin.settings_handlers._render_settings", new_callable=AsyncMock
    ):
        await cb_toggle_preview(q, s)
    assert settings.show_link_preview is False


@pytest.mark.asyncio
async def test_toggle_preview_no_db():
    q = _cb(user_id=111)
    s = _st()
    with AP, patch("admin.settings_handlers.db_ready", return_value=None):
        await cb_toggle_preview(q, s)
    assert "DB" in str(q.answer.call_args)


@pytest.mark.asyncio
async def test_toggle_photos():
    q = _cb(user_id=111)
    s = _st()
    settings = _settings(photos=True)
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.get_settings", new_callable=AsyncMock, return_value=settings
    ), patch("admin.settings_handlers.upsert_settings", new_callable=AsyncMock), patch(
        "admin.settings_handlers._render_settings", new_callable=AsyncMock
    ):
        await cb_toggle_photos(q, s)
    assert settings.send_photos is False


@pytest.mark.asyncio
async def test_toggle_whale_ping():
    q = _cb(user_id=111)
    s = _st()
    settings = _settings(ping=False)
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.get_settings", new_callable=AsyncMock, return_value=settings
    ), patch("admin.settings_handlers.upsert_settings", new_callable=AsyncMock), patch(
        "admin.settings_handlers._render_settings", new_callable=AsyncMock
    ):
        await cb_toggle_whale_ping(q, s)
    assert settings.whale_ping_admins is True


# ---- Callback: settings_reset ----


@pytest.mark.asyncio
async def test_cb_settings_reset():
    q = _cb(user_id=111)
    s = _st()
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.reset_settings", new_callable=AsyncMock
    ) as mock_reset, patch("admin.settings_handlers._render_settings", new_callable=AsyncMock):
        await cb_settings_reset(q, s)
    mock_reset.assert_called_once()
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_cb_settings_reset_no_db():
    q = _cb(user_id=111)
    s = _st()
    with AP, patch("admin.settings_handlers.db_ready", return_value=None):
        await cb_settings_reset(q, s)
    msg = q.message
    assert "DB" in msg.answer.call_args[0][0]


# ---- Callback: state_reset_30m ----


@pytest.mark.asyncio
async def test_cb_state_reset_30m_ok():
    q = _cb(user_id=111)
    s = _st()
    with AP, patch(
        "admin.settings_handlers.reset_state_last_30_min",
        new_callable=AsyncMock,
        return_value={"target_ts": 12345, "changed": 2},
    ):
        await cb_state_reset_30m(q, s)
    msg = q.message
    texts = [c[0][0] for c in msg.answer.call_args_list]
    full = " ".join(texts)
    assert "2" in full


@pytest.mark.asyncio
async def test_cb_state_reset_30m_error():
    q = _cb(user_id=111)
    s = _st()
    with AP, patch(
        "admin.settings_handlers.reset_state_last_30_min",
        new_callable=AsyncMock,
        side_effect=RuntimeError("fail"),
    ):
        await cb_state_reset_30m(q, s)
    msg = q.message
    texts = [c[0][0] for c in msg.answer.call_args_list]
    full = " ".join(texts)
    assert "ошибка" in full.lower() or "error" in full.lower()


# ---- FSM: waiting_min_price ----


@pytest.mark.asyncio
async def test_fsm_min_price_flow():
    m = _msg(user_id=111, text="3.5")
    s = _st()
    settings = _settings()
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.get_settings", new_callable=AsyncMock, return_value=settings
    ), patch("admin.settings_handlers.upsert_settings", new_callable=AsyncMock) as mock_up, patch(
        "admin.settings_handlers._render_settings", new_callable=AsyncMock
    ):
        await st_wait_min_price(m, s)
    assert settings.min_price_ton == 3.5
    mock_up.assert_called_once()
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_fsm_min_price_invalid():
    m = _msg(user_id=111, text="abc")
    s = _st()
    with AP:
        await st_wait_min_price(m, s)
    assert "❌" in m.answer.call_args[0][0]
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_fsm_min_price_no_db():
    m = _msg(user_id=111, text="5")
    s = _st()
    with AP, patch("admin.settings_handlers.db_ready", return_value=None):
        await st_wait_min_price(m, s)
    assert "DB" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_fsm_min_price_non_admin():
    m = _msg(user_id=999, text="5")
    s = _st()
    with AP:
        await st_wait_min_price(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


# ---- FSM: waiting_cooldown ----


@pytest.mark.asyncio
async def test_fsm_cooldown_flow():
    m = _msg(user_id=111, text="15")
    s = _st()
    settings = _settings()
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.get_settings", new_callable=AsyncMock, return_value=settings
    ), patch("admin.settings_handlers.upsert_settings", new_callable=AsyncMock), patch(
        "admin.settings_handlers._render_settings", new_callable=AsyncMock
    ):
        await st_wait_cooldown(m, s)
    assert settings.cooldown_sec == 15
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_fsm_cooldown_invalid():
    m = _msg(user_id=111, text="abc")
    s = _st()
    with AP:
        await st_wait_cooldown(m, s)
    assert "❌" in m.answer.call_args[0][0]


# ---- FSM: waiting_whale_threshold ----


@pytest.mark.asyncio
async def test_fsm_whale_threshold_flow():
    m = _msg(user_id=111, text="50")
    s = _st()
    settings = _settings()
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.get_settings", new_callable=AsyncMock, return_value=settings
    ), patch("admin.settings_handlers.upsert_settings", new_callable=AsyncMock), patch(
        "admin.settings_handlers._render_settings", new_callable=AsyncMock
    ):
        await st_wait_whale_threshold(m, s)
    assert settings.whale_threshold_ton == 50.0
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_fsm_whale_threshold_invalid():
    m = _msg(user_id=111, text="xyz")
    s = _st()
    with AP:
        await st_wait_whale_threshold(m, s)
    assert "❌" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_fsm_whale_threshold_non_admin():
    m = _msg(user_id=999, text="50")
    s = _st()
    with AP:
        await st_wait_whale_threshold(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


# ---- FSM: copy_from_chat ----


@pytest.mark.asyncio
async def test_fsm_copy_from_chat_ok():
    m = _msg(user_id=111, text="-200")
    s = _st()
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.copy_settings", new_callable=AsyncMock, return_value=True
    ), patch("admin.settings_handlers._render_settings", new_callable=AsyncMock):
        await st_copy_from_chat(m, s)
    texts = [c[0][0] for c in m.answer.call_args_list]
    full = " ".join(texts)
    assert "скопированы" in full.lower()
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_fsm_copy_from_chat_not_found():
    m = _msg(user_id=111, text="-200")
    s = _st()
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.copy_settings", new_callable=AsyncMock, return_value=False
    ):
        await st_copy_from_chat(m, s)
    assert "нет сохранённых" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_fsm_copy_from_chat_invalid():
    m = _msg(user_id=111, text="not_a_number")
    s = _st()
    with AP:
        await st_copy_from_chat(m, s)
    assert "❌" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_fsm_copy_from_chat_non_admin():
    m = _msg(user_id=999, text="-200")
    s = _st()
    with AP:
        await st_copy_from_chat(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


# ---- FSM: reset_collections_confirm ----


@pytest.mark.asyncio
async def test_fsm_reset_collections_yes():
    m = _msg(user_id=111, text="YES")
    s = _st()
    with AP, patch("admin.settings_handlers.db_ready", return_value=MagicMock()), patch(
        "admin.settings_handlers.clear_chat_collections", new_callable=AsyncMock, return_value=3
    ):
        await st_reset_collections_confirm(m, s)
    texts = [c[0][0] for c in m.answer.call_args_list]
    full = " ".join(texts)
    assert "3" in full
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_fsm_reset_collections_no():
    m = _msg(user_id=111, text="NO")
    s = _st()
    with AP:
        await st_reset_collections_confirm(m, s)
    assert "отменено" in m.answer.call_args[0][0].lower()
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_fsm_reset_collections_garbage():
    m = _msg(user_id=111, text="maybe")
    s = _st()
    with AP:
        await st_reset_collections_confirm(m, s)
    assert "YES" in m.answer.call_args[0][0]
    s.clear.assert_not_called()


@pytest.mark.asyncio
async def test_fsm_reset_collections_non_admin():
    m = _msg(user_id=999, text="YES")
    s = _st()
    with AP:
        await st_reset_collections_confirm(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


# ---- FSM: add/remove collection ----


@pytest.mark.asyncio
async def test_add_collection_success():
    m = _msg(user_id=111, text="0:abc123")
    s = _st()
    mock_client = AsyncMock()
    mock_client.normalize_address = AsyncMock(return_value=("0:abc123", "EQabc"))
    mock_client.get_nft_collection = AsyncMock(return_value={"metadata": {"name": "Cool"}})
    mock_client.close = AsyncMock()

    with AP, patch("admin.settings_handlers.TonApiClient", lambda *a, **kw: mock_client), patch(
        "admin.settings_handlers.add_collection_for_chat", new_callable=AsyncMock, return_value=True
    ):
        await st_add_collection(m, s)
    assert "✅" in m.answer.call_args_list[0][0][0]
    s.clear.assert_called_once()


@pytest.mark.asyncio
async def test_add_collection_duplicate():
    m = _msg(user_id=111, text="0:abc123")
    s = _st()
    mock_client = AsyncMock()
    mock_client.normalize_address = AsyncMock(return_value=("0:abc123", "EQabc"))
    mock_client.get_nft_collection = AsyncMock(return_value={})
    mock_client.close = AsyncMock()

    with AP, patch("admin.settings_handlers.TonApiClient", lambda *a, **kw: mock_client), patch(
        "admin.settings_handlers.add_collection_for_chat", new_callable=AsyncMock, return_value=False
    ):
        await st_add_collection(m, s)
    assert "уже есть" in m.answer.call_args_list[0][0][0].lower()


@pytest.mark.asyncio
async def test_add_collection_bad_address():
    m = _msg(user_id=111, text="garbage")
    s = _st()
    mock_client = AsyncMock()
    mock_client.normalize_address = AsyncMock(side_effect=ValueError("bad addr"))
    mock_client.close = AsyncMock()

    with AP, patch("admin.settings_handlers.TonApiClient", lambda *a, **kw: mock_client):
        await st_add_collection(m, s)
    assert "не смог" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_add_collection_non_admin():
    m = _msg(user_id=999, text="0:abc")
    s = _st()
    with AP:
        await st_add_collection(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_remove_collection_ok():
    m = _msg(user_id=111, text="0:abc")
    s = _st()
    with AP, patch(
        "admin.settings_handlers.remove_collection_for_chat", new_callable=AsyncMock, return_value=True
    ):
        await st_remove_collection(m, s)
    assert "✅" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_remove_collection_not_found():
    m = _msg(user_id=111, text="0:unknown")
    s = _st()
    with AP, patch(
        "admin.settings_handlers.remove_collection_for_chat", new_callable=AsyncMock, return_value=False
    ):
        await st_remove_collection(m, s)
    assert "не нашёл" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_remove_collection_non_admin():
    m = _msg(user_id=999, text="0:abc")
    s = _st()
    with AP:
        await st_remove_collection(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()
