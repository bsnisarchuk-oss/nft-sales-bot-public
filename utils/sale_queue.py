"""
Persistent queue для продаж, которые не удалось отправить в Telegram.
При сбое send — sale попадает в очередь и будет отправлена позже.
"""
import json
import logging
import time
from dataclasses import asdict
from decimal import Decimal
from typing import List, Tuple

from utils.db import DB
from utils.models import SaleEvent, SaleItem

log = logging.getLogger("sale_queue")

QUEUE_BACKOFFS = [10, 30, 60, 300, 900]  # 10s, 30s, 1m, 5m, 15m
MAX_ATTEMPTS = 5


async def enqueue(db: DB, chat_id: int, sale: SaleEvent) -> bool:
    """Добавить sale в очередь для конкретного чата. Дубликаты игнорируются."""
    if not db.conn:
        return False
    sale_dict = asdict(sale)
    # Decimal не сериализуется в JSON напрямую
    sale_dict["price_ton"] = str(sale.price_ton)
    sale_json = json.dumps(sale_dict, ensure_ascii=False)
    now = time.time()
    async with db.write_lock:
        await db.conn.execute(
            "INSERT OR IGNORE INTO sale_queue "
            "(chat_id, sale_json, trace_id, attempts, next_retry_at, created_at) "
            "VALUES (?, ?, ?, 0, ?, ?)",
            (chat_id, sale_json, sale.trace_id, now, now),
        )
        await db.conn.commit()
    return True


def _deserialize_sale(sale_json: str) -> SaleEvent:
    """Восстановить SaleEvent из JSON."""
    d = json.loads(sale_json)
    items = [SaleItem(**it) for it in d.pop("items", [])]
    d["price_ton"] = Decimal(d["price_ton"])
    return SaleEvent(**d, items=items)


async def dequeue_batch(
    db: DB, limit: int = 10
) -> List[Tuple[int, int, SaleEvent]]:
    """Достать batch записей, готовых к повторной отправке.
    Возвращает список (queue_id, chat_id, SaleEvent)."""
    if not db.conn:
        return []
    now = time.time()
    cur = await db.conn.execute(
        "SELECT id, chat_id, sale_json FROM sale_queue "
        "WHERE next_retry_at <= ? AND attempts < ? "
        "ORDER BY next_retry_at LIMIT ?",
        (now, MAX_ATTEMPTS, limit),
    )
    rows = await cur.fetchall()
    result = []
    for qid, chat_id, sale_json in rows:
        try:
            sale = _deserialize_sale(sale_json)
            result.append((qid, chat_id, sale))
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("Failed to deserialize queued sale id=%s: %s", qid, e)
            # Удаляем битую запись
            async with db.write_lock:
                await db.conn.execute("DELETE FROM sale_queue WHERE id=?", (qid,))
                await db.conn.commit()
    return result


async def mark_sent(db: DB, queue_id: int) -> None:
    """Удалить успешно отправленную запись из очереди."""
    if not db.conn:
        return
    async with db.write_lock:
        await db.conn.execute("DELETE FROM sale_queue WHERE id=?", (queue_id,))
        await db.conn.commit()


async def mark_failed(db: DB, queue_id: int, error: str) -> None:
    """Увеличить attempts и отложить next_retry_at."""
    if not db.conn:
        return
    async with db.write_lock:
        cur = await db.conn.execute(
            "SELECT attempts FROM sale_queue WHERE id=?", (queue_id,)
        )
        row = await cur.fetchone()
        if not row:
            return
        attempts = row[0] + 1
        backoff_idx = min(attempts - 1, len(QUEUE_BACKOFFS) - 1)
        next_retry = time.time() + QUEUE_BACKOFFS[backoff_idx]
        await db.conn.execute(
            "UPDATE sale_queue SET attempts=?, next_retry_at=?, last_error=? WHERE id=?",
            (attempts, next_retry, error[:200], queue_id),
        )
        await db.conn.commit()


async def cleanup_stale(db: DB) -> int:
    """Удалить записи, превысившие MAX_ATTEMPTS. Возвращает кол-во удалённых."""
    if not db.conn:
        return 0
    async with db.write_lock:
        cur = await db.conn.execute(
            "DELETE FROM sale_queue WHERE attempts >= ?", (MAX_ATTEMPTS,)
        )
        await db.conn.commit()
        return cur.rowcount or 0


async def queue_stats(db: DB) -> dict:
    """Статистика очереди: pending, stale, oldest_sec."""
    if not db.conn:
        return {"pending": 0, "stale": 0}
    cur = await db.conn.execute(
        "SELECT "
        "  COUNT(CASE WHEN attempts < ? THEN 1 END), "
        "  COUNT(CASE WHEN attempts >= ? THEN 1 END), "
        "  MIN(created_at) "
        "FROM sale_queue",
        (MAX_ATTEMPTS, MAX_ATTEMPTS),
    )
    row = await cur.fetchone()
    if not row:
        return {"pending": 0, "stale": 0}
    oldest = int(time.time() - row[2]) if row[2] else 0
    return {"pending": row[0] or 0, "stale": row[1] or 0, "oldest_sec": oldest}
