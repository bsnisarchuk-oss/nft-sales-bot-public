"""Tests for admin/commands.py — Telegram command handlers."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from admin.commands import (
    cmd_backup_now,
    cmd_bind,
    cmd_chats,
    cmd_collections,
    cmd_health,
    cmd_help,
    cmd_pause,
    cmd_refresh_names,
    cmd_resume,
    cmd_start,
    cmd_status,
    cmd_unbind,
    st_unbind_confirm,
)


def _make_message(user_id: int = 111, chat_id: int = -100, text: str = "") -> MagicMock:
    msg = MagicMock()
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.chat = MagicMock()
    msg.chat.id = chat_id
    msg.chat.title = "Test Chat"
    msg.chat.username = "testchat"
    msg.text = text
    msg.answer = AsyncMock()
    msg.bot = AsyncMock()
    return msg


def _make_state() -> MagicMock:
    state = MagicMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.update_data = AsyncMock()
    return state


ADMIN_PATCH = patch("admin.commands._admin_ids", return_value=frozenset({111}))


# ---- /start ----


@pytest.mark.asyncio
async def test_start_non_admin_denied():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_start(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_start_admin_ok():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH:
        await cmd_start(msg)
    assert msg.answer.call_args.kwargs.get("reply_markup") is not None


# ---- /help ----


@pytest.mark.asyncio
async def test_help_non_admin_denied():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_help(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_help_returns_commands_list():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH:
        await cmd_help(msg)
    text = msg.answer.call_args[0][0]
    assert "/start" in text and "/bind" in text and "/settings" in text


# ---- /collections ----


@pytest.mark.asyncio
async def test_collections_non_admin_denied():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=[]
    ):
        await cmd_collections(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_collections_no_user():
    msg = _make_message(user_id=111)
    msg.from_user = None
    with ADMIN_PATCH:
        await cmd_collections(msg)
    assert "доступ" in msg.answer.call_args[0][0].lower() or "access" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_collections_empty():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=[]
    ):
        await cmd_collections(msg)
    assert "📭" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_collections_with_items():
    items = [
        {"name": "Cool NFTs", "raw": "0:abc123", "b64url": "EQabc"},
        {"name": "", "raw": "0:def456", "b64url": ""},
    ]
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=items
    ):
        await cmd_collections(msg)
    text = msg.answer.call_args[0][0]
    assert "0:abc123" in text and "Cool NFTs" in text


# ---- /refresh_names ----


@pytest.mark.asyncio
async def test_refresh_names_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_refresh_names(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_refresh_names_no_collections():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=[]
    ):
        await cmd_refresh_names(msg)
    assert "не добавлены" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_refresh_names_all_have_names():
    items = [{"name": "Already Named", "raw": "0:abc"}]
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=items
    ):
        await cmd_refresh_names(msg)
    assert "уже есть названия" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_refresh_names_updates_name():
    items = [{"name": "", "raw": "0:abc"}]
    msg = _make_message(user_id=111)
    mock_client = AsyncMock()
    mock_client.get_nft_collection = AsyncMock(
        return_value={"metadata": {"name": "New Name"}}
    )
    mock_client.close = AsyncMock()

    def _make_client(*a, **kw):
        return mock_client

    mock_db = MagicMock()
    mock_db.conn = AsyncMock()
    mock_db.conn.execute = AsyncMock()
    mock_db.conn.commit = AsyncMock()

    with ADMIN_PATCH, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=items
    ), patch("admin.commands.TonApiClient", _make_client), patch(
        "admin.commands.db_ready", return_value=mock_db
    ):
        await cmd_refresh_names(msg)
    # Should report "Обновлено: 1"
    texts = [call[0][0] for call in msg.answer.call_args_list]
    full = " ".join(texts)
    assert "1" in full and "New Name" in full


# ---- /health ----


@pytest.mark.asyncio
async def test_health_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_health(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_health_all_ok():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.check_db", new_callable=AsyncMock, return_value=(True, "OK")
    ), patch(
        "admin.commands.check_tonapi", new_callable=AsyncMock, return_value=(True, "OK")
    ), patch(
        "admin.commands.check_bot_can_send", new_callable=AsyncMock, return_value=(True, "OK (admin)")
    ):
        await cmd_health(msg)
    text = msg.answer.call_args[0][0]
    assert "HEALTH" in text and "OK" in text


@pytest.mark.asyncio
async def test_health_all_fail():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.check_db", new_callable=AsyncMock, return_value=(False, "no conn")
    ), patch(
        "admin.commands.check_tonapi", new_callable=AsyncMock, return_value=(False, "timeout")
    ), patch(
        "admin.commands.check_bot_can_send", new_callable=AsyncMock, return_value=(False, "restricted")
    ):
        await cmd_health(msg)
    text = msg.answer.call_args[0][0]
    assert "FAIL" in text and "Fix" in text


# ---- /status ----


@pytest.mark.asyncio
async def test_status_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_status(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_status_ok():
    msg = _make_message(user_id=111)
    snap = {
        "started_at": time.time() - 600,
        "last_tick_at": time.time() - 5,
        "last_tick_addr": "0:abc",
        "last_tick_trace": "tr_1",
        "total_traces": 42,
        "total_sales": 7,
        "last_sale_at": time.time() - 60,
        "last_sale_trace": "sale_1",
        "errors_last_hour": 0,
        "last_error": "",
    }
    with ADMIN_PATCH, patch(
        "admin.commands.rt_snapshot", return_value=snap
    ), patch("admin.commands.db_ready", return_value=None):
        await cmd_status(msg)
    text = msg.answer.call_args[0][0]
    assert "Status" in text and "42" in text and "7" in text


@pytest.mark.asyncio
async def test_status_with_queue_stats():
    msg = _make_message(user_id=111)
    snap = {
        "started_at": time.time() - 600,
        "last_tick_at": time.time() - 5,
        "last_tick_addr": "0:abc",
        "last_tick_trace": "tr_1",
        "total_traces": 0,
        "total_sales": 0,
        "last_sale_at": 0,
        "last_sale_trace": "",
        "errors_last_hour": 0,
        "last_error": "",
    }
    mock_db = MagicMock()
    with ADMIN_PATCH, patch(
        "admin.commands.rt_snapshot", return_value=snap
    ), patch("admin.commands.db_ready", return_value=mock_db), patch(
        "utils.sale_queue.queue_stats",
        new_callable=AsyncMock,
        return_value={"pending": 3, "stale": 1},
    ):
        await cmd_status(msg)
    text = msg.answer.call_args[0][0]
    assert "Queue pending" in text and "3" in text


# ---- /bind ----


@pytest.mark.asyncio
async def test_bind_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_bind(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_bind_success():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.check_bot_can_send", new_callable=AsyncMock, return_value=(True, "OK")
    ), patch("admin.commands.bind_chat", new_callable=AsyncMock) as mock_bind, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=[]
    ):
        await cmd_bind(msg)
    mock_bind.assert_called_once()
    assert "привязан" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_bind_cant_send():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.check_bot_can_send",
        new_callable=AsyncMock,
        return_value=(False, "NO (restricted)"),
    ):
        await cmd_bind(msg)
    assert "Send messages" in msg.answer.call_args[0][0]


# ---- /unbind FSM ----


@pytest.mark.asyncio
async def test_unbind_non_admin():
    msg = _make_message(user_id=999)
    state = _make_state()
    with ADMIN_PATCH:
        await cmd_unbind(msg, state)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_unbind_starts_fsm():
    msg = _make_message(user_id=111)
    state = _make_state()
    with ADMIN_PATCH, patch(
        "admin.commands.get_collections_for_chat", new_callable=AsyncMock, return_value=[]
    ):
        await cmd_unbind(msg, state)
    state.set_state.assert_called_once()
    assert "YES" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_unbind_confirm_yes():
    msg = _make_message(user_id=111, text="YES")
    state = _make_state()
    with ADMIN_PATCH, patch("admin.commands.unbind_chat", new_callable=AsyncMock) as mock_unbind:
        await st_unbind_confirm(msg, state)
    mock_unbind.assert_called_once_with(msg.chat.id)
    state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_unbind_confirm_no():
    msg = _make_message(user_id=111, text="NO")
    state = _make_state()
    with ADMIN_PATCH:
        await st_unbind_confirm(msg, state)
    assert "отменено" in msg.answer.call_args[0][0].lower()
    state.clear.assert_called_once()


@pytest.mark.asyncio
async def test_unbind_confirm_garbage():
    msg = _make_message(user_id=111, text="maybe")
    state = _make_state()
    with ADMIN_PATCH:
        await st_unbind_confirm(msg, state)
    assert "YES" in msg.answer.call_args[0][0]
    state.clear.assert_not_called()


@pytest.mark.asyncio
async def test_unbind_confirm_non_admin():
    msg = _make_message(user_id=999, text="YES")
    state = _make_state()
    with ADMIN_PATCH:
        await st_unbind_confirm(msg, state)
    assert "доступа" in msg.answer.call_args[0][0].lower()
    state.clear.assert_called_once()


# ---- /pause + /resume ----


@pytest.mark.asyncio
async def test_pause_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_pause(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_pause_sets_disabled():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch("admin.commands.set_enabled", new_callable=AsyncMock) as mock_set:
        await cmd_pause(msg)
    mock_set.assert_called_once_with(msg.chat.id, False)


@pytest.mark.asyncio
async def test_resume_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_resume(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_resume_sets_enabled():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch("admin.commands.set_enabled", new_callable=AsyncMock) as mock_set:
        await cmd_resume(msg)
    mock_set.assert_called_once_with(msg.chat.id, True)


# ---- /chats ----


@pytest.mark.asyncio
async def test_chats_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_chats(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_chats_empty():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch("admin.commands.list_chats", new_callable=AsyncMock, return_value=[]):
        await cmd_chats(msg)
    assert "/bind" in msg.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_chats_with_data():
    rows = [
        {"chat_id": -100, "title": "Group A", "enabled": True, "collections_count": 3},
        {"chat_id": -200, "title": "", "enabled": False, "collections_count": 0},
    ]
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch("admin.commands.list_chats", new_callable=AsyncMock, return_value=rows):
        await cmd_chats(msg)
    text = msg.answer.call_args[0][0]
    assert "Group A" in text and "ON" in text and "OFF" in text


# ---- /backup_now ----


@pytest.mark.asyncio
async def test_backup_non_admin():
    msg = _make_message(user_id=999)
    with ADMIN_PATCH:
        await cmd_backup_now(msg)
    assert "доступа" in msg.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_backup_now_success():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.backup_now", new_callable=AsyncMock, return_value="data/backup_2026.db"
    ):
        await cmd_backup_now(msg)
    text = msg.answer.call_args[0][0]
    assert "✅" in text and "backup" in text.lower()


@pytest.mark.asyncio
async def test_backup_now_os_error():
    msg = _make_message(user_id=111)
    with ADMIN_PATCH, patch(
        "admin.commands.backup_now", new_callable=AsyncMock, side_effect=OSError("disk full")
    ):
        await cmd_backup_now(msg)
    assert "❌" in msg.answer.call_args[0][0]
