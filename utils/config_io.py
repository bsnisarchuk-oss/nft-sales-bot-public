import time
from typing import Any, Dict, List

from utils.db_instance import db_ready


async def export_config() -> dict:
    """
    Экспортирует конфиг из SQLite.
    """
    db = db_ready()
    if not db or not db.conn:
        raise RuntimeError("DB is not initialized")

    # 1) чаты
    cur = await db.conn.execute(
        "SELECT chat_id, title, enabled, added_by, added_at FROM chats ORDER BY chat_id"
    )
    chat_rows = await cur.fetchall()

    chats: List[Dict[str, Any]] = []
    for chat_id, title, enabled, added_by, added_at in chat_rows:
        # 2) коллекции для чата
        cur2 = await db.conn.execute(
            """
            SELECT c.raw, c.b64url, c.name
            FROM chat_collections cc
            JOIN collections c ON c.raw = cc.collection_raw
            WHERE cc.chat_id=?
            ORDER BY c.raw
            """,
            (int(chat_id),),
        )
        cols = await cur2.fetchall()

        # 3) settings для чата
        cur_s = await db.conn.execute(
            "SELECT min_price_ton, cooldown_sec, show_link_preview, send_photos, whale_threshold_ton, whale_ping_admins "
            "FROM chat_settings WHERE chat_id=?",
            (int(chat_id),),
        )
        srow = await cur_s.fetchone()

        if srow:
            settings = {
                "min_price_ton": float(srow[0] or 0),
                "cooldown_sec": int(srow[1] or 0),
                "show_link_preview": bool(srow[2]),
                "send_photos": bool(srow[3]),
                "whale_threshold_ton": float(srow[4] or 0) if len(srow) > 4 else 0.0,
                "whale_ping_admins": int(srow[5] or 0) if len(srow) > 5 else 0,
            }
        else:
            settings = {
                "min_price_ton": 0.0,
                "cooldown_sec": 0,
                "show_link_preview": True,
                "send_photos": True,
                "whale_threshold_ton": 0.0,
                "whale_ping_admins": 0,
            }

        chats.append(
            {
                "chat_id": int(chat_id),
                "title": title or "",
                "enabled": bool(enabled),
                "added_by": int(added_by or 0),
                "added_at": int(added_at or 0),
                "collections": [
                    {"raw": r, "b64url": b or "", "name": n or ""} for (r, b, n) in cols
                ],
                "settings": settings,
            }
        )

    # (опционально) курсоры last_lt — полезно при переносе
    cur3 = await db.conn.execute("SELECT address, last_lt FROM state_by_address ORDER BY address")
    state_rows = await cur3.fetchall()
    state_by_address = {str(a): int(lt or 0) for (a, lt) in state_rows}

    return {
        "schema": 2,
        "exported_at": int(time.time()),
        "chats": chats,
        "state_by_address": state_by_address,
    }


async def import_config(data: dict, replace: bool = False) -> dict:
    """
    Импортирует конфиг в SQLite.
    replace=False: MERGE (upsert)
    replace=True: REPLACE (очистить и залить)
    Возвращает статистику.
    """
    db = db_ready()
    if not db:
        raise RuntimeError("DB is not initialized")

    if not isinstance(data, dict):
        raise ValueError("Invalid JSON: root is not an object")

    chats = data.get("chats", [])
    if not isinstance(chats, list):
        raise ValueError("Invalid JSON: chats must be a list")

    state_by_address = data.get("state_by_address", {})
    if state_by_address is None:
        state_by_address = {}
    if not isinstance(state_by_address, dict):
        raise ValueError("Invalid JSON: state_by_address must be an object")

    async with db.write_lock:
        result: dict = await _import_config_locked(db, data, chats, state_by_address, replace)
        return result


async def _import_config_locked(db, data, chats, state_by_address, replace):
    if not db.conn:
        raise RuntimeError("DB connection is not open")
    if replace:
        await db.conn.executescript("""
            DELETE FROM chat_collections;
            DELETE FROM collections;
            DELETE FROM chats;
            DELETE FROM recent_traces;
            DELETE FROM state_by_address;
            """)
        await db.conn.commit()

    chats_upserted = 0
    links_added = 0
    collections_upserted = 0
    settings_upserted = 0

    await db.conn.execute("BEGIN")
    try:
        for ch in chats:
            if not isinstance(ch, dict):
                continue

            chat_id = int(ch.get("chat_id") or 0)
            title = str(ch.get("title", "") or "")
            enabled = 1 if bool(ch.get("enabled", True)) else 0
            added_by = int(ch.get("added_by", 0) or 0)
            added_at = int(ch.get("added_at", 0) or 0)

            settings = ch.get("settings") or {}
            if not isinstance(settings, dict):
                settings = {}

            try:
                min_price_ton = float(settings.get("min_price_ton", 0) or 0)
            except (ValueError, TypeError):
                min_price_ton = 0.0

            try:
                cooldown_sec = int(settings.get("cooldown_sec", 0) or 0)
            except (ValueError, TypeError):
                cooldown_sec = 0

            show_link_preview = 1 if bool(settings.get("show_link_preview", True)) else 0
            send_photos = 1 if bool(settings.get("send_photos", True)) else 0

            try:
                whale_threshold_ton = float(settings.get("whale_threshold_ton", 0) or 0)
            except (ValueError, TypeError):
                whale_threshold_ton = 0.0
            try:
                whale_ping_admins = int(settings.get("whale_ping_admins", 0) or 0)
            except (ValueError, TypeError):
                whale_ping_admins = 0

            # upsert chat
            if added_at > 0:
                await db.conn.execute(
                    "INSERT INTO chats(chat_id,title,enabled,added_by,added_at) VALUES (?,?,?,?,?) "
                    "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, enabled=excluded.enabled, added_by=excluded.added_by",
                    (chat_id, title, enabled, added_by, added_at),
                )
            else:
                await db.conn.execute(
                    "INSERT INTO chats(chat_id,title,enabled,added_by) VALUES (?,?,?,?) "
                    "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, enabled=excluded.enabled, added_by=excluded.added_by",
                    (chat_id, title, enabled, added_by),
                )
            chats_upserted += 1

            cols = ch.get("collections", [])
            if not isinstance(cols, list):
                cols = []

            for c in cols:
                if not isinstance(c, dict):
                    continue
                raw = str(c.get("raw", "")).strip()
                b64url = str(c.get("b64url", "")).strip()
                name = str(c.get("name", "")).strip()
                if not raw:
                    continue

                await db.conn.execute(
                    "INSERT INTO collections(raw,b64url,name) VALUES (?,?,?) "
                    "ON CONFLICT(raw) DO UPDATE SET b64url=excluded.b64url, name=CASE WHEN excluded.name<>'' THEN excluded.name ELSE collections.name END",
                    (raw, b64url, name),
                )
                collections_upserted += 1

                # link
                await db.conn.execute(
                    "INSERT OR IGNORE INTO chat_collections(chat_id, collection_raw) VALUES (?,?)",
                    (chat_id, raw),
                )
                links_added += 1

            # upsert chat_settings
            await db.conn.execute(
                "INSERT INTO chat_settings(chat_id, min_price_ton, cooldown_sec, show_link_preview, send_photos, whale_threshold_ton, whale_ping_admins) "
                "VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(chat_id) DO UPDATE SET "
                "min_price_ton=excluded.min_price_ton, cooldown_sec=excluded.cooldown_sec, "
                "show_link_preview=excluded.show_link_preview, send_photos=excluded.send_photos, "
                "whale_threshold_ton=excluded.whale_threshold_ton, whale_ping_admins=excluded.whale_ping_admins",
                (chat_id, min_price_ton, cooldown_sec, show_link_preview, send_photos, whale_threshold_ton, whale_ping_admins),
            )
            settings_upserted += 1

        # state_by_address (курсор)
        state_upserted = 0
        for addr, lt in state_by_address.items():
            try:
                lt_i = int(lt or 0)
            except (ValueError, TypeError):
                lt_i = 0
            await db.conn.execute(
                "INSERT INTO state_by_address(address,last_lt) VALUES (?,?) "
                "ON CONFLICT(address) DO UPDATE SET last_lt=excluded.last_lt, updated_at=strftime('%s','now')",
                (str(addr), lt_i),
            )
            state_upserted += 1

        await db.conn.commit()
    except Exception:
        await db.conn.rollback()
        raise

    return {
        "replace": replace,
        "chats_upserted": chats_upserted,
        "collections_upserted": collections_upserted,
        "links_added": links_added,
        "state_upserted": state_upserted,
        "settings_upserted": settings_upserted,
    }
