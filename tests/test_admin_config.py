"""Tests for admin/config_handlers.py — export/import config."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from admin.config_handlers import (
    cmd_export_config,
    cmd_import_config,
    cmd_import_config_replace,
    st_import_file,
)


def _msg(user_id: int = 111, text: str = "") -> MagicMock:
    m = MagicMock()
    m.from_user = MagicMock()
    m.from_user.id = user_id
    m.chat = MagicMock()
    m.chat.id = -100
    m.text = text
    m.answer = AsyncMock()
    m.answer_document = AsyncMock()
    m.bot = AsyncMock()
    m.document = None
    return m


def _st() -> MagicMock:
    s = MagicMock()
    s.set_state = AsyncMock()
    s.clear = AsyncMock()
    s.get_data = AsyncMock(return_value={})
    s.update_data = AsyncMock()
    return s


AP = patch("admin.config_handlers._admin_ids", return_value=frozenset({111}))


# ---- /export_config ----


@pytest.mark.asyncio
async def test_export_non_admin():
    m = _msg(user_id=999)
    with AP:
        await cmd_export_config(m)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_export_sends_json_document():
    m = _msg(user_id=111)
    with AP, patch(
        "admin.config_handlers.export_config",
        new_callable=AsyncMock,
        return_value={"chats": {}, "state": {}},
    ):
        await cmd_export_config(m)
    m.answer_document.assert_called_once()


# ---- /import_config ----


@pytest.mark.asyncio
async def test_import_non_admin():
    m = _msg(user_id=999)
    s = _st()
    with AP:
        await cmd_import_config(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_import_sets_merge_mode():
    m = _msg(user_id=111)
    s = _st()
    with AP:
        await cmd_import_config(m, s)
    s.update_data.assert_called_once_with(import_replace=False)
    assert "MERGE" in m.answer.call_args[0][0]


# ---- /import_config_replace ----


@pytest.mark.asyncio
async def test_import_replace_non_admin():
    m = _msg(user_id=999)
    s = _st()
    with AP:
        await cmd_import_config_replace(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_import_sets_replace_mode():
    m = _msg(user_id=111)
    s = _st()
    with AP:
        await cmd_import_config_replace(m, s)
    s.update_data.assert_called_once_with(import_replace=True)
    assert "REPLACE" in m.answer.call_args[0][0]


# ---- st_import_file ----


def _msg_with_doc(user_id: int = 111, content: bytes = b"{}") -> MagicMock:
    m = _msg(user_id=user_id)
    doc = MagicMock()
    doc.file_id = "file123"
    doc.file_size = len(content)
    m.document = doc

    mock_file = MagicMock()
    mock_file.file_path = "/tmp/f.json"
    m.bot.get_file = AsyncMock(return_value=mock_file)

    async def fake_download(path, buf):
        buf.write(content)

    m.bot.download_file = AsyncMock(side_effect=fake_download)
    return m


@pytest.mark.asyncio
async def test_import_file_non_admin():
    m = _msg_with_doc(user_id=999)
    s = _st()
    with AP:
        await st_import_file(m, s)
    assert "доступа" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_import_file_no_document():
    m = _msg(user_id=111)
    m.document = None
    s = _st()
    with AP:
        await st_import_file(m, s)
    assert "нет файла" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_import_file_too_large():
    m = _msg(user_id=111)
    doc = MagicMock()
    doc.file_size = 5_000_000
    m.document = doc
    s = _st()
    with AP:
        await st_import_file(m, s)
    assert "слишком" in m.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_import_file_invalid_json():
    m = _msg_with_doc(content=b"not valid {{{")
    s = _st()
    with AP:
        await st_import_file(m, s)
    assert "JSON" in m.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_import_file_success_merge():
    m = _msg_with_doc(content=b'{"chats": []}')
    s = _st()
    s.get_data = AsyncMock(return_value={"import_replace": False})
    result = {"chats_upserted": 1, "collections_upserted": 2, "links_added": 3, "state_upserted": 0}
    with AP, patch(
        "admin.config_handlers.import_config", new_callable=AsyncMock, return_value=result
    ):
        await st_import_file(m, s)
    text = m.answer.call_args[0][0]
    assert "MERGE" in text and "1" in text


@pytest.mark.asyncio
async def test_import_file_success_replace():
    m = _msg_with_doc(content=b'{"chats": []}')
    s = _st()
    s.get_data = AsyncMock(return_value={"import_replace": True})
    result = {"chats_upserted": 2, "collections_upserted": 5, "links_added": 5, "state_upserted": 1}
    with AP, patch(
        "admin.config_handlers.import_config", new_callable=AsyncMock, return_value=result
    ):
        await st_import_file(m, s)
    text = m.answer.call_args[0][0]
    assert "REPLACE" in text


@pytest.mark.asyncio
async def test_import_file_import_error():
    m = _msg_with_doc(content=b'{"chats": []}')
    s = _st()
    with AP, patch(
        "admin.config_handlers.import_config",
        new_callable=AsyncMock,
        side_effect=ValueError("bad format"),
    ):
        await st_import_file(m, s)
    assert "❌" in m.answer.call_args[0][0]
