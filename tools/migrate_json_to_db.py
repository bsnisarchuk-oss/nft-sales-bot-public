import asyncio
import os

from utils.db import DB
from utils.storage import load_json


def _data_path(filename: str) -> str:
    return os.path.join(os.getenv("DATA_DIR", "data"), filename)


async def main():
    db = DB()
    await db.open()
    assert db.conn

    # 1) chats + collections из chats_config.json
    chats_cfg = load_json(_data_path("chats_config.json"), default={"chats": {}})
    chats = chats_cfg.get("chats", {})
    if not isinstance(chats, dict):
        chats = {}

    migrated_chats = 0
    migrated_links = 0

    for chat_id_str, meta in chats.items():
        try:
            chat_id = int(chat_id_str)
        except Exception:
            continue
        if not isinstance(meta, dict):
            meta = {}

        title = str(meta.get("title", "") or "")
        enabled = 1 if bool(meta.get("enabled", True)) else 0
        added_by = int(meta.get("added_by", 0) or 0)
        added_at = int(meta.get("added_at", 0) or 0)

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

        migrated_chats += 1

        cols = meta.get("collections", [])
        if not isinstance(cols, list):
            cols = []

        for c in cols:
            # поддержим и старый формат строк
            if isinstance(c, str):
                raw = c.strip()
                b64url = ""
                name = ""
            elif isinstance(c, dict):
                raw = str(c.get("raw", "")).strip()
                b64url = str(c.get("b64url", "")).strip()
                name = str(c.get("name", "")).strip()
            else:
                continue

            if not raw:
                continue

            # upsert collection
            await db.conn.execute(
                "INSERT INTO collections(raw,b64url,name) VALUES (?,?,?) "
                "ON CONFLICT(raw) DO UPDATE SET b64url=excluded.b64url, name=CASE WHEN excluded.name<>'' THEN excluded.name ELSE collections.name END",
                (raw, b64url, name),
            )

            # link collection to chat
            await db.conn.execute(
                "INSERT OR IGNORE INTO chat_collections(chat_id, collection_raw) VALUES (?,?)",
                (chat_id, raw),
            )
            migrated_links += 1

    # 2) last_lt_by_address из processed_events.json → state_by_address
    processed = load_json(_data_path("processed_events.json"), default={})
    last_lt = processed.get("last_lt_by_address") or processed.get("last_ts_by_address") or {}
    if not isinstance(last_lt, dict):
        last_lt = {}

    migrated_state = 0
    for addr, lt in last_lt.items():
        try:
            lt_i = int(lt or 0)
        except Exception:
            lt_i = 0
        await db.conn.execute(
            "INSERT INTO state_by_address(address,last_lt) VALUES (?,?) "
            "ON CONFLICT(address) DO UPDATE SET last_lt=excluded.last_lt, updated_at=strftime('%s','now')",
            (str(addr), lt_i),
        )
        migrated_state += 1

    await db.conn.commit()
    await db.close()

    print(f"OK: chats={migrated_chats}, links={migrated_links}, state_by_address={migrated_state}")


if __name__ == "__main__":
    asyncio.run(main())
