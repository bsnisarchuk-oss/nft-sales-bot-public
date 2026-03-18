from dataclasses import dataclass

from utils.db import DB


@dataclass
class ChatSettings:
    min_price_ton: float = 0.0
    cooldown_sec: int = 0
    show_link_preview: bool = True
    send_photos: bool = True
    whale_threshold_ton: float = 0.0
    whale_ping_admins: bool = False
    language: str = "ru"
    quiet_start: str = ""
    quiet_end: str = ""
    batch_window_sec: int = 0
    message_template: str = ""


_COLS = (
    "min_price_ton, cooldown_sec, show_link_preview, send_photos, "
    "whale_threshold_ton, whale_ping_admins, language, quiet_start, quiet_end, "
    "batch_window_sec, message_template"
)


async def get_settings(db: DB, chat_id: int) -> ChatSettings:
    assert db.conn
    cur = await db.conn.execute(
        f"SELECT {_COLS} FROM chat_settings WHERE chat_id=?",
        (int(chat_id),),
    )
    row = await cur.fetchone()
    if not row:
        return ChatSettings()
    return ChatSettings(
        min_price_ton=float(row[0] or 0),
        cooldown_sec=int(row[1] or 0),
        show_link_preview=bool(row[2]),
        send_photos=bool(row[3]),
        whale_threshold_ton=float(row[4] or 0),
        whale_ping_admins=bool(row[5]),
        language=str(row[6] or "ru"),
        quiet_start=str(row[7] or ""),
        quiet_end=str(row[8] or ""),
        batch_window_sec=int(row[9] or 0),
        message_template=str(row[10] or ""),
    )


def _settings_values(chat_id: int, s: ChatSettings) -> tuple:
    return (
        int(chat_id),
        float(s.min_price_ton),
        int(s.cooldown_sec),
        1 if s.show_link_preview else 0,
        1 if s.send_photos else 0,
        float(s.whale_threshold_ton),
        1 if s.whale_ping_admins else 0,
        s.language,
        s.quiet_start,
        s.quiet_end,
        int(s.batch_window_sec),
        s.message_template,
    )


_UPSERT_SQL = (
    "INSERT INTO chat_settings(chat_id, min_price_ton, cooldown_sec, show_link_preview, "
    "send_photos, whale_threshold_ton, whale_ping_admins, language, quiet_start, quiet_end, "
    "batch_window_sec, message_template) "
    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?) "
    "ON CONFLICT(chat_id) DO UPDATE SET "
    "min_price_ton=excluded.min_price_ton, cooldown_sec=excluded.cooldown_sec, "
    "show_link_preview=excluded.show_link_preview, send_photos=excluded.send_photos, "
    "whale_threshold_ton=excluded.whale_threshold_ton, whale_ping_admins=excluded.whale_ping_admins, "
    "language=excluded.language, quiet_start=excluded.quiet_start, quiet_end=excluded.quiet_end, "
    "batch_window_sec=excluded.batch_window_sec, message_template=excluded.message_template"
)


async def upsert_settings(db: DB, chat_id: int, s: ChatSettings) -> None:
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(_UPSERT_SQL, _settings_values(chat_id, s))
        await db.conn.commit()


async def set_min_price(db: DB, chat_id: int, min_price_ton: float) -> None:
    s = await get_settings(db, chat_id)
    s.min_price_ton = float(min_price_ton)
    await upsert_settings(db, chat_id, s)


async def set_cooldown(db: DB, chat_id: int, cooldown_sec: int) -> None:
    s = await get_settings(db, chat_id)
    s.cooldown_sec = int(cooldown_sec)
    await upsert_settings(db, chat_id, s)


async def set_language(db: DB, chat_id: int, language: str) -> None:
    s = await get_settings(db, chat_id)
    s.language = language
    await upsert_settings(db, chat_id, s)


async def reset_settings(db: DB, chat_id: int) -> None:
    await upsert_settings(db, chat_id, ChatSettings())


async def copy_settings(db: DB, from_chat_id: int, to_chat_id: int) -> bool:
    assert db.conn
    s = await get_settings(db, from_chat_id)
    # Check if source has any custom settings (not all defaults)
    if s == ChatSettings():
        cur = await db.conn.execute(
            "SELECT 1 FROM chat_settings WHERE chat_id=?", (int(from_chat_id),)
        )
        if not await cur.fetchone():
            return False
    await upsert_settings(db, to_chat_id, s)
    return True
