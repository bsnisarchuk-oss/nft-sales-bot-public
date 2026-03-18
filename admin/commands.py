import asyncio
import time
from html import escape as h

import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from admin.helpers import _admin_ids, _ago, _chat_lang, _split_chunks
from admin.keyboards import admin_main_kb
from admin.states import ChatStates
from config import TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL
from utils.backup_db import backup_now
from utils.chat_store_bridge import (
    bind_chat,
    list_chats,
    set_enabled,
    unbind_chat,
)
from utils.chat_store_bridge import (
    get_collections as get_collections_for_chat,
)
from utils.db_instance import db_ready
from utils.diagnostics import check_bot_can_send, check_db, check_tonapi
from utils.i18n import t
from utils.runtime_state import snapshot as rt_snapshot
from utils.tonapi import TonApiClient

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return
    lang = await _chat_lang(message.chat.id)
    await message.answer(
        t("cmd_start", lang),
        reply_markup=admin_main_kb(lang),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    await message.answer(t("cmd_help", lang), parse_mode="HTML")


@router.message(Command("collections"))
async def cmd_collections(message: Message) -> None:
    if not message.from_user:
        await message.answer(t("no_access"))
        return

    if message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    items = await get_collections_for_chat(message.chat.id)

    if not items:
        await message.answer(t("no_collections", lang))
        return

    lines = [t("collections_header", lang, count=len(items))]
    for i, it in enumerate(items, 1):
        name = (it.get("name") or "").strip()
        raw = (it.get("raw") or "").strip()
        eq = (it.get("b64url") or "").strip()
        title = f"{i}. {name}" if name else f"{i}."
        lines.append(title)
        lines.append(f"raw: <code>{raw}</code>")
        if eq:
            lines.append(f"EQ: <code>{eq}</code>")
        lines.append("")

    text = "\n".join(lines).strip()

    for chunk in _split_chunks(text):
        await message.answer(chunk, parse_mode="HTML")


@router.message(Command("refresh_names"))
async def cmd_refresh_names(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    items = await get_collections_for_chat(message.chat.id)
    if not items:
        await message.answer(t("refresh_no_collections", lang))
        return

    todo = [it for it in items if not (it.get("name") or "").strip()]
    if not todo:
        await message.answer(t("refresh_all_named", lang))
        return

    await message.answer(t("refresh_progress", lang, count=len(todo)))

    db = db_ready()
    client = TonApiClient(TONAPI_BASE_URL, TONAPI_KEY, TONAPI_MIN_INTERVAL)
    updated: list[tuple[str, str]] = []
    skipped = 0

    try:
        for it in todo:
            raw = (it.get("raw") or "").strip()
            if not raw:
                skipped += 1
                continue
            try:
                col = await client.get_nft_collection(raw)
                meta = col.get("metadata") or {}
                name = (meta.get("name") or col.get("name") or "").strip()
            except (aiohttp.ClientError, asyncio.TimeoutError, KeyError):
                name = ""
            if not name:
                skipped += 1
                continue
            if db and db.conn:
                await db.conn.execute(
                    "UPDATE collections SET name=? WHERE raw=?",
                    (name, raw),
                )
            updated.append((raw, name))

        if db and db.conn:
            await db.conn.commit()

        # синхронизация в JSON fallback (chat_config_store)
        if updated:
            try:
                from utils import chat_config_store

                cfg = chat_config_store.load_cfg()
                name_by_raw = dict(updated)
                for chat_data in (cfg.get("chats") or {}).values():
                    if not isinstance(chat_data, dict):
                        continue
                    for col_item in chat_data.get("collections") or []:
                        if isinstance(col_item, dict):
                            r = col_item.get("raw")
                            if r and r in name_by_raw:
                                col_item["name"] = name_by_raw[r]
                    chat_config_store.save_cfg(cfg)
            except Exception:
                pass
    finally:
        await client.close()

    report = [
        t("refresh_done", lang, updated=len(updated), total=len(todo)),
    ]
    if skipped:
        report.append(t("refresh_skipped", lang, count=skipped))
    if updated:
        lines = [f"{i}. {name}" for i, (_, name) in enumerate(updated[:30], 1)]
        report.append("\n".join(lines))
        if len(updated) > 30:
            report.append(f"...+{len(updated) - 30}")
    text = "\n".join(report)
    for chunk in _split_chunks(text):
        await message.answer(chunk)


@router.message(Command("health"))
async def cmd_health(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    db_ok, db_msg = await check_db()
    api_ok, api_msg = await check_tonapi()
    send_ok, send_msg = await check_bot_can_send(message.bot, message.chat.id)

    tips = []
    if not send_ok:
        tips.append(t("health_fix_send", lang))
    if not api_ok:
        tips.append(t("health_fix_tonapi", lang))
    if not db_ok:
        tips.append(t("health_fix_db", lang))

    text = (
        t("health_header", lang)
        + f"DB: <b>{'OK' if db_ok else 'FAIL'}</b> - <code>{h(db_msg)}</code>\n"
        f"TonAPI: <b>{'OK' if api_ok else 'FAIL'}</b> - <code>{h(api_msg)}</code>\n"
        f"Can send here: <b>{'YES' if send_ok else 'NO'}</b> - <code>{h(send_msg)}</code>\n"
    )
    if tips:
        text += "\n" + t("health_fix_header", lang) + "\n".join(tips)

    await message.answer(text, parse_mode="HTML")


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    s = rt_snapshot()
    uptime_sec = int(time.time() - s["started_at"])
    uptime_min = uptime_sec // 60

    text = (
        f"{t('status_header', lang)}\n"
        f"{t('status_uptime', lang)}: <b>{uptime_min} {t('status_min', lang)}</b>\n"
        f"{t('status_last_tick', lang)}: <b>{_ago(s['last_tick_at'], lang)}</b>\n"
        f"{t('status_last_addr', lang)}: <code>{s['last_tick_addr']}</code>\n"
        f"{t('status_last_trace', lang)}: <code>{s['last_tick_trace']}</code>\n\n"
        f"{t('status_traces', lang)}: <b>{s['total_traces']}</b>\n"
        f"{t('status_sales', lang)}: <b>{s['total_sales']}</b>\n"
        f"{t('status_last_sale', lang)}: <b>{_ago(s['last_sale_at'], lang)}</b>\n"
        f"{t('status_last_sale_trace', lang)}: <code>{s['last_sale_trace']}</code>\n\n"
        f"{t('status_errors', lang)}: <b>{s['errors_last_hour']}</b>\n"
        f"{t('status_last_error', lang)}: <code>{s['last_error']}</code>\n"
    )

    # Queue stats
    try:
        from utils.sale_queue import queue_stats
        db = db_ready()
        if db:
            qs = await queue_stats(db)
            if qs["pending"] or qs["stale"]:
                text += f"\nQueue pending: <b>{qs['pending']}</b>"
                if qs["stale"]:
                    text += f" | stale: {qs['stale']}"
                text += "\n"
    except Exception:
        pass

    await message.answer(text, parse_mode="HTML")


@router.message(Command("bind"))
async def cmd_bind(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    ok, msg = await check_bot_can_send(message.bot, message.chat.id)
    if not ok:
        await message.answer(
            t("bind_no_perms", lang) + f"\nDetails: <code>{h(msg)}</code>",
            parse_mode="HTML",
        )
        return

    await bind_chat(
        chat_id=message.chat.id,
        title=getattr(message.chat, "title", "") or getattr(message.chat, "username", "") or "",
        added_by=message.from_user.id if message.from_user else 0,
    )

    cols = await get_collections_for_chat(message.chat.id)
    count = len(cols) if isinstance(cols, list) else 0
    title = getattr(message.chat, "title", "") or getattr(message.chat, "username", "") or ""
    await message.answer(
        t("bind_ok", lang, title=h(title or "-"), chat_id=message.chat.id, count=count),
        parse_mode="HTML",
        reply_markup=admin_main_kb(lang),
    )


@router.message(Command("unbind"))
async def cmd_unbind(message: Message, state: FSMContext) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    cols = await get_collections_for_chat(message.chat.id)
    count = len(cols) if isinstance(cols, list) else 0

    await state.set_state(ChatStates.waiting_unbind_confirm)
    await message.answer(
        t("unbind_confirm", lang, count=count),
        parse_mode="HTML",
    )


@router.message(ChatStates.waiting_unbind_confirm)
async def st_unbind_confirm(message: Message, state: FSMContext) -> None:
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

    await unbind_chat(message.chat.id)
    await message.answer(t("unbind_done", lang))
    await state.clear()


@router.message(Command("pause"))
async def cmd_pause(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    await set_enabled(message.chat.id, False)
    await message.answer(t("paused", lang))


@router.message(Command("resume"))
async def cmd_resume(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    await set_enabled(message.chat.id, True)
    await message.answer(t("resumed", lang))


@router.message(Command("chats"))
async def cmd_chats(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    rows = await list_chats()
    if not rows:
        await message.answer(t("no_chats", lang))
        return

    lines = [t("chats_header", lang)]
    for r in rows:
        st = "ON" if r["enabled"] else "OFF"
        title = r["title"] or "(no title)"
        lines.append(
            f"- <b>{st}</b> {title}\n  id: <code>{r['chat_id']}</code> | collections: {r['collections_count']}"
        )
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("backup_now"))
async def cmd_backup_now(message: Message) -> None:
    if not message.from_user or message.from_user.id not in _admin_ids():
        await message.answer(t("no_access"))
        return

    lang = await _chat_lang(message.chat.id)
    try:
        path = await backup_now()
        await message.answer(t("backup_ok", lang, path=path), parse_mode="HTML")
    except OSError:
        await message.answer(t("backup_fail", lang))
