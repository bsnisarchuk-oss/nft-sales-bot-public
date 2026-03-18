import sqlite3
from typing import Dict, List

from utils.db import DB


async def bind_chat(db: DB, chat_id: int, title: str, added_by: int) -> None:
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(
            "INSERT INTO chats(chat_id, title, enabled, added_by) VALUES (?,?,1,?) "
            "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title, enabled=1",
            (chat_id, title or "", added_by or 0),
        )
        await db.conn.commit()


async def unbind_chat(db: DB, chat_id: int) -> bool:
    assert db.conn
    async with db.write_lock:
        cur = await db.conn.execute("DELETE FROM chats WHERE chat_id=?", (chat_id,))
        await db.conn.commit()
        return cur.rowcount > 0


async def set_enabled(db: DB, chat_id: int, enabled: bool) -> None:
    assert db.conn
    async with db.write_lock:
        await db.conn.execute(
            "UPDATE chats SET enabled=? WHERE chat_id=?", (1 if enabled else 0, chat_id)
        )
        await db.conn.commit()


async def enabled_chats(db: DB) -> List[int]:
    assert db.conn
    cur = await db.conn.execute("SELECT chat_id FROM chats WHERE enabled=1")
    rows = await cur.fetchall()
    return [int(r[0]) for r in rows]


async def list_chats(db: DB) -> List[Dict]:
    assert db.conn
    cur = await db.conn.execute(
        "SELECT c.chat_id, c.title, c.enabled, "
        "(SELECT COUNT(*) FROM chat_collections cc WHERE cc.chat_id=c.chat_id) "
        "FROM chats c ORDER BY c.chat_id"
    )
    rows = await cur.fetchall()
    out = []
    for chat_id, title, enabled, cnt in rows:
        out.append(
            {
                "chat_id": int(chat_id),
                "title": title or "",
                "enabled": bool(enabled),
                "collections_count": int(cnt),
            }
        )
    return out


async def get_collections(db: DB, chat_id: int) -> List[dict]:
    assert db.conn
    cur = await db.conn.execute(
        "SELECT col.raw, col.b64url, col.name "
        "FROM chat_collections cc "
        "JOIN collections col ON col.raw = cc.collection_raw "
        "WHERE cc.chat_id=? ORDER BY col.raw",
        (chat_id,),
    )
    rows = await cur.fetchall()
    return [{"raw": r, "b64url": b, "name": n} for (r, b, n) in rows]


async def tracked_set(db: DB, chat_id: int) -> set[str]:
    items = await get_collections(db, chat_id)
    s = set()
    for it in items:
        if it.get("raw"):
            s.add(it["raw"])
        if it.get("b64url"):
            s.add(it["b64url"])
    return s


async def add_collection(db: DB, chat_id: int, raw: str, b64url: str, name: str = "") -> bool:
    assert db.conn
    async with db.write_lock:
        # 1) upsert коллекцию
        await db.conn.execute(
            "INSERT INTO collections(raw,b64url,name) VALUES (?,?,?) "
            "ON CONFLICT(raw) DO UPDATE SET b64url=excluded.b64url, name=CASE WHEN excluded.name<>'' THEN excluded.name ELSE collections.name END",
            (raw, b64url or "", name or ""),
        )
        # 2) привязать к чату
        try:
            await db.conn.execute(
                "INSERT INTO chat_collections(chat_id, collection_raw) VALUES (?,?)",
                (chat_id, raw),
            )
        except sqlite3.IntegrityError:
            # уже есть
            await db.conn.rollback()
            return False

        await db.conn.commit()
        return True


async def all_tracked_collections(db: DB) -> set[str]:
    """Все уникальные raw-адреса коллекций из всех enabled чатов."""
    assert db.conn
    cur = await db.conn.execute(
        "SELECT DISTINCT cc.collection_raw "
        "FROM chat_collections cc "
        "JOIN chats c ON c.chat_id = cc.chat_id "
        "WHERE c.enabled = 1"
    )
    rows = await cur.fetchall()
    return {str(r[0]) for r in rows}


async def remove_collection(db: DB, chat_id: int, raw_or_b64: str) -> bool:
    assert db.conn
    async with db.write_lock:
        # если дали b64url — найдём raw
        raw = raw_or_b64
        if raw_or_b64.startswith("EQ") or raw_or_b64.startswith("UQ"):
            cur = await db.conn.execute("SELECT raw FROM collections WHERE b64url=?", (raw_or_b64,))
            row = await cur.fetchone()
            if row:
                raw = row[0]

        cur = await db.conn.execute(
            "DELETE FROM chat_collections WHERE chat_id=? AND collection_raw=?",
            (chat_id, raw),
        )
        await db.conn.commit()
        return cur.rowcount > 0
