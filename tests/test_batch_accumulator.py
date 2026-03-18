from decimal import Decimal

import pytest

from utils.batch_accumulator import add_sale, flush, pending_count, reset
from utils.models import SaleEvent, SaleItem


def _make_sale(trace_id: str = "t1") -> SaleEvent:
    return SaleEvent(
        trace_id=trace_id,
        buyer="0:buyer",
        seller="0:seller",
        price_ton=Decimal("1.0"),
        items=[
            SaleItem(
                nft_address="0:nft",
                nft_name="NFT",
                collection_address="0:col",
                collection_name="Col",
                nft_address_b64url="",
            )
        ],
    )


@pytest.fixture(autouse=True)
def _cleanup():
    reset()
    yield
    reset()


def test_add_sale_increments_count():
    add_sale(1, _make_sale("t1"), window_sec=0)
    add_sale(1, _make_sale("t2"), window_sec=0)
    assert pending_count(1) == 2


def test_different_chats_independent():
    add_sale(1, _make_sale("t1"), window_sec=0)
    add_sale(2, _make_sale("t2"), window_sec=0)
    assert pending_count(1) == 1
    assert pending_count(2) == 1


@pytest.mark.asyncio
async def test_flush_returns_sales():
    add_sale(1, _make_sale("t1"), window_sec=0)
    add_sale(1, _make_sale("t2"), window_sec=0)
    sales = await flush(1)
    assert len(sales) == 2
    assert pending_count(1) == 0


@pytest.mark.asyncio
async def test_flush_empty():
    sales = await flush(999)
    assert sales == []


@pytest.mark.asyncio
async def test_flush_calls_callback():
    called_with = {}

    async def cb(chat_id, sales):
        called_with["chat_id"] = chat_id
        called_with["count"] = len(sales)

    from utils.batch_accumulator import set_flush_callback
    set_flush_callback(cb)

    add_sale(42, _make_sale("t1"), window_sec=0)
    add_sale(42, _make_sale("t2"), window_sec=0)
    await flush(42)

    assert called_with["chat_id"] == 42
    assert called_with["count"] == 2

    # Clean up
    set_flush_callback(None)


def test_reset_clears_all():
    add_sale(1, _make_sale("t1"), window_sec=0)
    add_sale(2, _make_sale("t2"), window_sec=0)
    reset()
    assert pending_count(1) == 0
    assert pending_count(2) == 0


@pytest.mark.asyncio
async def test_add_sale_with_window_starts_timer():
    """add_sale with window_sec>0 should start a timer."""
    import asyncio
    loop = asyncio.get_event_loop()
    add_sale(99, _make_sale("t_timer"), window_sec=60, loop=loop)
    from utils.batch_accumulator import _batches
    assert 99 in _batches
    assert _batches[99].timer is not None
    # Second add does not create another timer
    add_sale(99, _make_sale("t_timer2"), window_sec=60, loop=loop)
    assert _batches[99].timer is not None


@pytest.mark.asyncio
async def test_flush_with_timer_cancels_it():
    """flush should cancel the pending timer."""
    import asyncio
    loop = asyncio.get_event_loop()
    add_sale(98, _make_sale("t_w"), window_sec=60, loop=loop)
    from utils.batch_accumulator import _batches
    timer = _batches[98].timer
    assert timer is not None
    sales = await flush(98)
    assert len(sales) == 1
    assert timer.cancelled()


@pytest.mark.asyncio
async def test_flush_callback_exception_does_not_propagate():
    """If flush callback raises, flush still returns sales."""
    from utils.batch_accumulator import set_flush_callback

    async def bad_cb(chat_id, sales):
        raise RuntimeError("oops")

    set_flush_callback(bad_cb)
    add_sale(97, _make_sale("t_ex"), window_sec=0)
    sales = await flush(97)
    assert len(sales) == 1
    set_flush_callback(None)
