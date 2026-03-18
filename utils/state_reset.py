import time
from typing import Iterable, Optional

from utils.db_instance import db_ready


async def reset_state_last_30_min(
    addresses: Optional[Iterable[str]] = None, traces_limit: int = 200
) -> dict:
    """
    Откатывает состояние в таблице state_by_address для указанных адресов,
    если они обновлялись за последние 30 минут.

    Если addresses=None, автоматически берёт все tracked коллекции.

    Возвращает словарь:
    - target_ts: целевая метка времени (int)
    - changed: количество обновлённых строк (int)
    """
    db = db_ready()
    if not db:
        raise RuntimeError("DB is not initialized")

    if addresses is None:
        from utils.chat_store_bridge import all_tracked_collections

        addrs = list(await all_tracked_collections())
    else:
        addrs = [a.strip() for a in addresses if a and a.strip()]
    if not addrs:
        return {"target_ts": 0, "changed": 0}

    now = int(time.time())
    target_ts = now - 30 * 60

    placeholders = ",".join(["?"] * len(addrs))
    sql = (
        f"UPDATE state_by_address "
        f"SET last_lt=0, updated_at=? "
        f"WHERE address IN ({placeholders}) AND updated_at >= ?"
    )

    if not db.conn:
        raise RuntimeError("DB connection is not open")
    cur = await db.conn.execute(sql, (now, *addrs, target_ts))
    await db.conn.commit()
    changed = int(cur.rowcount or 0)

    return {"target_ts": target_ts, "changed": changed}
