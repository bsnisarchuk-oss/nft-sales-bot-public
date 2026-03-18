"""Tests for persistent sale queue (utils/sale_queue.py)."""

import time
from decimal import Decimal

import pytest
import pytest_asyncio

from utils.db import DB
from utils.models import SaleEvent, SaleItem
from utils.sale_queue import (
    cleanup_stale,
    dequeue_batch,
    enqueue,
    mark_failed,
    mark_sent,
    queue_stats,
)


def _sale(trace_id: str = "tr_1", price: str = "5.0") -> SaleEvent:
    return SaleEvent(
        trace_id=trace_id,
        buyer="0:buyer",
        seller="0:seller",
        price_ton=Decimal(price),
        items=[
            SaleItem(
                nft_address="0:nft1",
                nft_name="NFT #1",
                collection_address="0:col1",
                collection_name="Collection",
            )
        ],
    )


@pytest_asyncio.fixture
async def db():
    d = DB(":memory:")
    await d.open()
    yield d
    await d.close()


@pytest.mark.asyncio
async def test_enqueue_and_dequeue(db):
    """Enqueued sale should be dequeued."""
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    batch = await dequeue_batch(db, limit=10)
    assert len(batch) == 1
    qid, chat_id, sale = batch[0]
    assert chat_id == 100
    assert sale.trace_id == "tr_1"
    assert sale.price_ton == Decimal("5.0")
    assert len(sale.items) == 1


@pytest.mark.asyncio
async def test_duplicate_ignored(db):
    """Same (chat_id, trace_id) should not be duplicated."""
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    batch = await dequeue_batch(db, limit=10)
    assert len(batch) == 1


@pytest.mark.asyncio
async def test_dequeue_respects_next_retry_at(db):
    """Items with future next_retry_at should not be dequeued."""
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    # Push next_retry_at into the future
    async with db.write_lock:
        await db.conn.execute(
            "UPDATE sale_queue SET next_retry_at = ?", (time.time() + 9999,)
        )
        await db.conn.commit()
    batch = await dequeue_batch(db, limit=10)
    assert len(batch) == 0


@pytest.mark.asyncio
async def test_mark_sent_deletes(db):
    """mark_sent should remove the record."""
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    batch = await dequeue_batch(db, limit=10)
    assert len(batch) == 1
    await mark_sent(db, batch[0][0])
    batch2 = await dequeue_batch(db, limit=10)
    assert len(batch2) == 0


@pytest.mark.asyncio
async def test_mark_failed_increments_attempts(db):
    """mark_failed should increment attempts and postpone retry."""
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    batch = await dequeue_batch(db, limit=10)
    qid = batch[0][0]
    await mark_failed(db, qid, "some error")
    # Check attempts increased
    cur = await db.conn.execute("SELECT attempts FROM sale_queue WHERE id=?", (qid,))
    row = await cur.fetchone()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_cleanup_stale(db):
    """cleanup_stale should remove records with attempts >= MAX_ATTEMPTS."""
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    # Set attempts to MAX
    async with db.write_lock:
        await db.conn.execute("UPDATE sale_queue SET attempts = 5")
        await db.conn.commit()
    cleaned = await cleanup_stale(db)
    assert cleaned == 1
    batch = await dequeue_batch(db, limit=10)
    assert len(batch) == 0


@pytest.mark.asyncio
async def test_queue_stats(db):
    """queue_stats should report pending and stale counts."""
    await enqueue(db, chat_id=100, sale=_sale("tr_1"))
    await enqueue(db, chat_id=100, sale=_sale("tr_2"))
    # Make one stale
    async with db.write_lock:
        await db.conn.execute(
            "UPDATE sale_queue SET attempts = 5 WHERE trace_id = 'tr_2'"
        )
        await db.conn.commit()
    stats = await queue_stats(db)
    assert stats["pending"] == 1
    assert stats["stale"] == 1
