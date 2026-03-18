"""Batch accumulator — group multiple sales into one message per chat.

When batch_window_sec > 0 for a chat, sales are accumulated and sent
as a single summary message after the window expires.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Coroutine

from utils.models import SaleEvent

log = logging.getLogger("batch_accumulator")


@dataclass
class _Batch:
    sales: list[SaleEvent] = field(default_factory=list)
    timer: asyncio.TimerHandle | None = None


# chat_id -> _Batch
_batches: dict[int, _Batch] = {}

# Callback: (bot, chat_id, sales_list) -> None
_flush_callback: Callable[..., Coroutine] | None = None


def set_flush_callback(cb: Callable[..., Coroutine]) -> None:
    """Register the function that sends batched sales."""
    global _flush_callback
    _flush_callback = cb


def add_sale(chat_id: int, sale: SaleEvent, window_sec: int, loop: asyncio.AbstractEventLoop | None = None) -> None:
    """Add a sale to the batch for a chat. Starts a timer if not already running."""
    batch = _batches.setdefault(chat_id, _Batch())
    batch.sales.append(sale)

    if batch.timer is None and window_sec > 0:
        if loop is None:
            loop = asyncio.get_event_loop()
        batch.timer = loop.call_later(window_sec, lambda: _schedule_flush(chat_id, loop))
        log.debug("Batch timer started for chat %s (%ds window, %d sales)", chat_id, window_sec, len(batch.sales))


def _schedule_flush(chat_id: int, loop: asyncio.AbstractEventLoop) -> None:
    """Schedule the async flush in the event loop."""
    asyncio.ensure_future(flush(chat_id), loop=loop)


async def flush(chat_id: int) -> list[SaleEvent]:
    """Flush accumulated sales for a chat. Returns the flushed sales."""
    batch = _batches.pop(chat_id, None)
    if not batch or not batch.sales:
        return []

    if batch.timer is not None:
        batch.timer.cancel()

    sales = batch.sales
    log.info("Flushing batch for chat %s: %d sales", chat_id, len(sales))

    if _flush_callback:
        try:
            await _flush_callback(chat_id, sales)
        except Exception:
            log.exception("Batch flush callback failed for chat %s", chat_id)

    return sales


def pending_count(chat_id: int) -> int:
    """Number of pending sales in the batch for a chat."""
    batch = _batches.get(chat_id)
    return len(batch.sales) if batch else 0


def reset() -> None:
    """Clear all batches (for testing)."""
    for batch in _batches.values():
        if batch.timer:
            batch.timer.cancel()
    _batches.clear()
