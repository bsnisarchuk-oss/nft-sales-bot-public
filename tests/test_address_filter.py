import pytest
import pytest_asyncio

from utils.address_filter_db import add_filter, check_sale_allowed, list_filters, remove_filter
from utils.db import DB


@pytest_asyncio.fixture
async def db(tmp_path):
    d = DB(str(tmp_path / "test.db"))
    await d.open()
    # Insert a chat record to satisfy FK constraints
    await d.conn.execute("INSERT INTO chats (chat_id, title) VALUES (1, 'test')")
    await d.conn.commit()
    yield d
    await d.close()


@pytest.mark.asyncio
async def test_add_and_list(db):
    ok = await add_filter(db, 1, "0:buyer_addr", "buyer_whitelist")
    assert ok is True
    filters = await list_filters(db, 1)
    assert len(filters) == 1
    assert filters[0]["address"] == "0:buyer_addr"


@pytest.mark.asyncio
async def test_add_duplicate(db):
    await add_filter(db, 1, "0:addr", "buyer_blacklist")
    ok = await add_filter(db, 1, "0:addr", "buyer_blacklist")
    assert ok is False


@pytest.mark.asyncio
async def test_remove(db):
    await add_filter(db, 1, "0:addr", "seller_whitelist")
    ok = await remove_filter(db, 1, "0:addr", "seller_whitelist")
    assert ok is True
    filters = await list_filters(db, 1)
    assert len(filters) == 0


@pytest.mark.asyncio
async def test_remove_nonexistent(db):
    ok = await remove_filter(db, 1, "0:nope", "seller_blacklist")
    assert ok is False


@pytest.mark.asyncio
async def test_no_filters_allows_all(db):
    assert await check_sale_allowed(db, 1, "0:buyer", "0:seller") is True


@pytest.mark.asyncio
async def test_buyer_whitelist_blocks(db):
    await add_filter(db, 1, "0:good_buyer", "buyer_whitelist")
    assert await check_sale_allowed(db, 1, "0:bad_buyer", "0:seller") is False
    assert await check_sale_allowed(db, 1, "0:good_buyer", "0:seller") is True


@pytest.mark.asyncio
async def test_buyer_blacklist_blocks(db):
    await add_filter(db, 1, "0:bad_buyer", "buyer_blacklist")
    assert await check_sale_allowed(db, 1, "0:bad_buyer", "0:seller") is False
    assert await check_sale_allowed(db, 1, "0:other", "0:seller") is True


@pytest.mark.asyncio
async def test_seller_whitelist_blocks(db):
    await add_filter(db, 1, "0:good_seller", "seller_whitelist")
    assert await check_sale_allowed(db, 1, "0:buyer", "0:bad_seller") is False
    assert await check_sale_allowed(db, 1, "0:buyer", "0:good_seller") is True


@pytest.mark.asyncio
async def test_seller_blacklist_blocks(db):
    await add_filter(db, 1, "0:bad_seller", "seller_blacklist")
    assert await check_sale_allowed(db, 1, "0:buyer", "0:bad_seller") is False
    assert await check_sale_allowed(db, 1, "0:buyer", "0:other") is True
