
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from admin.helpers import _admin_ids, _chat_lang, _render_settings
from admin.keyboards import admin_main_kb, language_kb
from admin.states import CollectionStates, SettingsStates
from config import TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL
from utils.chat_collections_db import clear_chat_collections
from utils.chat_settings_db import (
    copy_settings,
    get_settings,
    reset_settings,
    set_cooldown,
    set_language,
    set_min_price,
    upsert_settings,
)
from utils.chat_store_bridge import (
    add_collection as add_collection_for_chat,
)
from utils.chat_store_bridge import (
    remove_collection as remove_collection_for_chat,
)
from utils.db_instance import db_ready
from utils.i18n import t
from utils.state_reset import reset_state_last_30_min
from utils.tonapi import TonApiClient

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return
    await _render_settings(message)


@router.message(Command("set_min_price"))
async def cmd_set_min_price(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(t("min_price_example", lang))
        return

    try:
        val = float(parts[1].replace(",", "."))
        if val < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(t("min_price_error", lang))
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        return

    await set_min_price(db, message.chat.id, val)
    await message.answer(t("min_price_set", lang, val=val))


@router.message(Command("set_cooldown"))
async def cmd_set_cooldown(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(t("cooldown_example", lang))
        return

    try:
        sec = int(parts[1])
        if sec < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(t("cooldown_error", lang))
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        return

    await set_cooldown(db, message.chat.id, sec)
    await message.answer(t("cooldown_set", lang, val=sec))


@router.callback_query(F.data == "settings_menu")
async def cb_settings_menu(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    await state.clear()
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return
    await _render_settings(msg)
    await query.answer()


@router.callback_query(F.data == "add_collection")
async def cb_add_collection(query: CallbackQuery, state: FSMContext):
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return
    lang = await _chat_lang(msg.chat.id)
    await state.set_state(CollectionStates.waiting_add_address)
    await msg.answer(t("add_collection_prompt", lang))
    await query.answer()


@router.callback_query(F.data == "remove_collection")
async def cb_remove_collection(query: CallbackQuery, state: FSMContext):
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return
    lang = await _chat_lang(msg.chat.id)
    await state.set_state(CollectionStates.waiting_remove_address)
    await msg.answer(t("remove_collection_prompt", lang))
    await query.answer()


@router.callback_query(F.data == "settings_back")
async def cb_settings_back(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.clear()
    await msg.answer(t("cmd_back", lang), reply_markup=admin_main_kb(lang))
    await query.answer()


@router.callback_query(F.data == "settings_min_price")
async def cb_settings_min_price(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_min_price)
    await msg.answer(t("min_price_prompt", lang))
    await query.answer()


@router.message(SettingsStates.waiting_min_price)
async def st_wait_min_price(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip().replace(",", ".")
    try:
        val = float(txt)
        if val < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(t("min_price_error", lang))
        await state.clear()
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    s = await get_settings(db, message.chat.id)
    s.min_price_ton = val
    await upsert_settings(db, message.chat.id, s)

    await message.answer(t("min_price_set", lang, val=val))
    await state.clear()
    await _render_settings(message)


@router.callback_query(F.data == "settings_cooldown")
async def cb_settings_cooldown(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_cooldown)
    await msg.answer(t("cooldown_prompt", lang))
    await query.answer()


@router.message(SettingsStates.waiting_cooldown)
async def st_wait_cooldown(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip()
    try:
        sec = int(txt)
        if sec < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(t("cooldown_error", lang))
        await state.clear()
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    s = await get_settings(db, message.chat.id)
    s.cooldown_sec = sec
    await upsert_settings(db, message.chat.id, s)

    await message.answer(t("cooldown_set", lang, val=sec))
    await state.clear()
    await _render_settings(message)


@router.callback_query(F.data == "settings_toggle_preview")
async def cb_toggle_preview(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    db = db_ready()
    if not db:
        await query.answer(t("db_not_init"), show_alert=True)
        return

    s = await get_settings(db, msg.chat.id)
    lang = s.language or "ru"
    s.show_link_preview = not s.show_link_preview
    await upsert_settings(db, msg.chat.id, s)

    await msg.answer(t("preview_toggled", lang, state="ON" if s.show_link_preview else "OFF"))
    await _render_settings(msg)
    await query.answer()


@router.callback_query(F.data == "settings_toggle_photos")
async def cb_toggle_photos(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return
    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    db = db_ready()
    if not db:
        await query.answer(t("db_not_init"), show_alert=True)
        return

    s = await get_settings(db, msg.chat.id)
    lang = s.language or "ru"
    s.send_photos = not s.send_photos
    await upsert_settings(db, msg.chat.id, s)

    await msg.answer(t("photos_toggled", lang, state="ON" if s.send_photos else "OFF"))
    await _render_settings(msg)
    await query.answer()


@router.callback_query(F.data == "settings_whale_threshold")
async def cb_settings_whale_threshold(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_whale_threshold)
    await msg.answer(t("whale_prompt", lang))
    await query.answer()


@router.message(SettingsStates.waiting_whale_threshold)
async def st_wait_whale_threshold(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip().replace(",", ".")
    try:
        val = float(txt)
        if val < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(t("whale_error", lang))
        await state.clear()
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    s = await get_settings(db, message.chat.id)
    s.whale_threshold_ton = val
    await upsert_settings(db, message.chat.id, s)

    await message.answer(t("whale_set", lang, val=val))
    await state.clear()
    await _render_settings(message)


@router.callback_query(F.data == "settings_toggle_whale_ping")
async def cb_toggle_whale_ping(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    db = db_ready()
    if not db:
        await query.answer(t("db_not_init"), show_alert=True)
        return

    s = await get_settings(db, msg.chat.id)
    lang = s.language or "ru"
    s.whale_ping_admins = not s.whale_ping_admins
    await upsert_settings(db, msg.chat.id, s)

    await msg.answer(t("whale_ping_toggled", lang, state="ON" if s.whale_ping_admins else "OFF"))
    await _render_settings(msg)
    await query.answer()


@router.callback_query(F.data == "settings_reset")
async def cb_settings_reset(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    db = db_ready()
    if not db:
        await msg.answer(t("db_not_init"))
        await query.answer()
        return

    lang = await _chat_lang(msg.chat.id)
    await reset_settings(db, msg.chat.id)
    await state.clear()
    await msg.answer(t("settings_reset_done", lang))
    await _render_settings(msg)
    await query.answer()


@router.callback_query(F.data == "settings_copy")
async def cb_settings_copy(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_copy_from_chat_id)
    await msg.answer(t("copy_prompt", lang))
    await query.answer()


# ── Language selection ──

@router.callback_query(F.data == "settings_language")
async def cb_settings_language(query: CallbackQuery) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await msg.answer(t("language_prompt", lang), reply_markup=language_kb())
    await query.answer()


@router.callback_query(F.data.startswith("set_lang_"))
async def cb_set_language(query: CallbackQuery) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    new_lang = (query.data or "").replace("set_lang_", "")
    if new_lang not in ("ru", "en"):
        new_lang = "ru"

    db = db_ready()
    if not db:
        await query.answer(t("db_not_init"), show_alert=True)
        return

    await set_language(db, msg.chat.id, new_lang)
    await msg.answer(t("language_set", new_lang))
    await _render_settings(msg)
    await query.answer()


# ── Quiet hours ──

@router.callback_query(F.data == "settings_quiet_hours")
async def cb_settings_quiet_hours(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_quiet_hours)
    await msg.answer(t("quiet_hours_prompt", lang))
    await query.answer()


@router.message(SettingsStates.waiting_quiet_hours)
async def st_wait_quiet_hours(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip()

    # "0" disables quiet hours
    if txt == "0":
        db = db_ready()
        if not db:
            await message.answer(t("db_not_init", lang))
            await state.clear()
            return
        s = await get_settings(db, message.chat.id)
        s.quiet_start = ""
        s.quiet_end = ""
        await upsert_settings(db, message.chat.id, s)
        await message.answer(t("quiet_hours_off", lang))
        await state.clear()
        await _render_settings(message)
        return

    # Parse "HH:MM-HH:MM"
    parts = txt.split("-")
    if len(parts) != 2:
        await message.answer(t("quiet_hours_error", lang))
        await state.clear()
        return

    from utils.quiet_hours import parse_time
    start = parse_time(parts[0])
    end = parse_time(parts[1])
    if start is None or end is None:
        await message.answer(t("quiet_hours_error", lang))
        await state.clear()
        return

    start_str = parts[0].strip()
    end_str = parts[1].strip()

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    s = await get_settings(db, message.chat.id)
    s.quiet_start = start_str
    s.quiet_end = end_str
    await upsert_settings(db, message.chat.id, s)

    await message.answer(t("quiet_hours_set", lang, start=start_str, end=end_str))
    await state.clear()
    await _render_settings(message)


# ── Batch window ──

@router.callback_query(F.data == "settings_batch_window")
async def cb_settings_batch_window(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_batch_window)
    await msg.answer(t("batch_prompt", lang))
    await query.answer()


@router.message(SettingsStates.waiting_batch_window)
async def st_wait_batch_window(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip()
    try:
        val = int(txt)
        if val < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(t("batch_error", lang))
        await state.clear()
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    s = await get_settings(db, message.chat.id)
    s.batch_window_sec = val
    await upsert_settings(db, message.chat.id, s)

    await message.answer(t("batch_set", lang, val=val))
    await state.clear()
    await _render_settings(message)


# ── Custom template ──

@router.callback_query(F.data == "settings_template")
async def cb_settings_template(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_template)
    await msg.answer(t("template_prompt", lang), parse_mode="HTML")
    await query.answer()


@router.message(SettingsStates.waiting_template)
async def st_wait_template(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip()

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    s = await get_settings(db, message.chat.id)

    if txt == "0":
        s.message_template = ""
        await upsert_settings(db, message.chat.id, s)
        await message.answer(t("template_reset", lang))
    else:
        s.message_template = txt
        await upsert_settings(db, message.chat.id, s)
        await message.answer(t("template_set", lang))

    await state.clear()
    await _render_settings(message)


# ── Collections reset ──

@router.callback_query(F.data == "collections_reset_confirm")
async def cb_collections_reset_confirm(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    lang = await _chat_lang(msg.chat.id)
    await state.set_state(SettingsStates.waiting_reset_collections_confirm)

    await msg.answer(t("reset_collections_confirm", lang), parse_mode="HTML")
    await query.answer()


@router.callback_query(F.data == "state_reset_30m")
async def cb_state_reset_30m(query: CallbackQuery, state: FSMContext) -> None:
    if not query.from_user or query.from_user.id not in _admin_ids():
        await query.answer(t("no_access"), show_alert=True)
        return

    msg = query.message
    if not isinstance(msg, Message):
        await query.answer(t("error"), show_alert=True)
        return

    await msg.answer("⏳ Reset state (~30 min)...")

    try:
        result = await reset_state_last_30_min()
    except Exception:
        await msg.answer("❌ Error resetting state.")
        await query.answer()
        return

    await msg.answer(
        f"✅ Reset state done.\n"
        f"Target time: {result['target_ts']}\n"
        f"Changed: {result['changed']}"
    )
    await query.answer()


@router.message(SettingsStates.waiting_copy_from_chat_id)
async def st_copy_from_chat(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip()
    try:
        from_chat_id = int(txt)
    except (ValueError, TypeError):
        await message.answer(t("copy_error", lang))
        await state.clear()
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    ok = await copy_settings(db, from_chat_id=from_chat_id, to_chat_id=message.chat.id)
    if not ok:
        await message.answer(t("copy_no_source", lang))
        await state.clear()
        return

    await message.answer(t("copy_done", lang, chat_id=from_chat_id), parse_mode="HTML")
    await state.clear()
    await _render_settings(message)


@router.message(SettingsStates.waiting_reset_collections_confirm)
async def st_reset_collections_confirm(message: Message, state: FSMContext):
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    txt = (message.text or "").strip().upper()

    if txt == "NO":
        await message.answer(t("cancelled", lang))
        await state.clear()
        return

    if txt != "YES":
        await message.answer(t("write_yes_or_no", lang), parse_mode="HTML")
        return

    db = db_ready()
    if not db:
        await message.answer(t("db_not_init", lang))
        await state.clear()
        return

    deleted = await clear_chat_collections(db, message.chat.id)
    await message.answer(t("reset_collections_done", lang, count=deleted))

    await state.clear()
    # синхронизируем и JSON-конфиг (fallback-хранилище)
    try:
        from utils import chat_config_store

        chat_config_store.clear_chat_collections(message.chat.id)
    except Exception:
        pass

    await message.answer(t("reset_collections_empty", lang))


@router.message(CollectionStates.waiting_add_address)
async def st_add_collection(message: Message, state: FSMContext):
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    addr = (message.text or "").strip()
    client = TonApiClient(TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL)

    try:
        raw, b64url = await client.normalize_address(addr)
        name = ""
        try:
            col = await client.get_nft_collection(raw)
            meta = col.get("metadata") or {}
            name = (meta.get("name") or col.get("name") or "").strip()
        except Exception:
            name = ""
    except Exception:
        await message.answer(t("add_collection_error", lang))
        await state.clear()
        return
    finally:
        await client.close()

    added = await add_collection_for_chat(message.chat.id, raw=raw, b64url=b64url, name=name)

    if added:
        await message.answer(
            t("add_collection_ok", lang, raw=raw, b64url=b64url),
            parse_mode="HTML",
        )
    else:
        await message.answer(t("add_collection_exists", lang))

    await state.clear()


@router.message(CollectionStates.waiting_remove_address)
async def st_remove_collection(message: Message, state: FSMContext):
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        await state.clear()
        return

    lang = await _chat_lang(message.chat.id)
    addr = (message.text or "").strip()
    removed = await remove_collection_for_chat(message.chat.id, raw_or_b64=addr)

    if removed:
        await message.answer(t("remove_collection_ok", lang))
    else:
        await message.answer(t("remove_collection_not_found", lang))

    await state.clear()
