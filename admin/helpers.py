import os
import time

from aiogram.types import Message

from admin.keyboards import settings_kb
from utils.chat_settings_db import get_settings
from utils.chat_store_bridge import get_collections as get_collections_for_chat
from utils.db_instance import db_ready
from utils.i18n import t

TELEGRAM_LIMIT = 3500  # безопасно меньше 4096


def _split_chunks(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    parts = []
    buf = ""
    for line in text.splitlines(True):
        if len(buf) + len(line) > limit:
            if buf:
                parts.append(buf)
            buf = ""
        buf += line
    if buf:
        parts.append(buf)
    return parts


def _is_admin(user_id: int, admin_ids: set[int]) -> bool:
    return user_id in admin_ids


# Парсим ADMIN_IDS один раз при импорте модуля
_ADMIN_IDS: frozenset[int] = frozenset(
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
)


def _admin_ids() -> frozenset[int]:
    return _ADMIN_IDS


def _ago(ts: float, lang: str = "ru") -> str:
    if not ts:
        return t("time_never", lang)
    sec = int(time.time() - ts)
    if sec < 60:
        return t("time_sec_ago", lang, n=sec)
    mins = sec // 60
    if mins < 60:
        return t("time_min_ago", lang, n=mins)
    hrs = mins // 60
    if hrs < 48:
        return t("time_hr_ago", lang, n=hrs)
    days = hrs // 24
    return t("time_day_ago", lang, n=days)


async def _get_demo_collection_raw(chat_id: int) -> str:
    cols = await get_collections_for_chat(chat_id)
    if not cols:
        return ""
    raw = (cols[0].get("raw") or "").strip()
    return raw


async def _chat_lang(chat_id: int) -> str:
    """Get the language setting for a chat. Defaults to 'ru'."""
    db = db_ready()
    if db:
        s = await get_settings(db, chat_id)
        return s.language or "ru"
    return "ru"


async def _render_settings(message_or_query_message: Message) -> None:
    db = db_ready()
    if not db:
        await message_or_query_message.answer(t("db_not_init", "ru"))
        return

    s = await get_settings(db, message_or_query_message.chat.id)
    lang = s.language or "ru"

    text = (
        f"{t('settings_header', lang)}\n"
        f"chat_id: <code>{message_or_query_message.chat.id}</code>\n\n"
        f"🔥 min_price_ton: <b>{s.min_price_ton}</b>\n"
        f"⏱ cooldown_sec: <b>{s.cooldown_sec}</b>\n"
        f"🔗 link preview: <b>{'ON' if s.show_link_preview else 'OFF'}</b>\n"
        f"🖼 photos: <b>{'ON' if s.send_photos else 'OFF'}</b>\n"
        f"🐳 whale_threshold_ton: <b>{s.whale_threshold_ton}</b>\n"
        f"🏓 ping admins: <b>{'ON' if s.whale_ping_admins else 'OFF'}</b>\n"
        f"🌐 language: <b>{lang}</b>\n"
        f"🌙 quiet hours: <b>{s.quiet_start}-{s.quiet_end if s.quiet_start else 'OFF'}</b>\n"
        f"📦 batch_window_sec: <b>{s.batch_window_sec}</b>\n"
        f"📝 template: <b>{'custom' if s.message_template else 'default'}</b>\n"
    )

    await message_or_query_message.answer(
        text,
        reply_markup=settings_kb(
            s.show_link_preview,
            s.send_photos,
            s.whale_threshold_ton,
            s.whale_ping_admins,
            lang=lang,
        ),
        parse_mode="HTML",
    )
