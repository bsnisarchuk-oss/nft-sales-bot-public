"""Shared pytest fixtures for NFT Sales Bot tests."""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from utils.db import DB
from utils.models import SaleEvent, SaleItem


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite DB with full schema."""
    d = DB(":memory:")
    await d.open()
    yield d
    await d.close()


@pytest.fixture
def mock_bot():
    """AsyncMock aiogram Bot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_media_group = AsyncMock()
    return bot


@pytest.fixture
def sample_sale() -> SaleEvent:
    """Standard SaleEvent for tests."""
    return SaleEvent(
        trace_id="test_trace_1",
        buyer="0:buyer_addr",
        seller="0:seller_addr",
        price_ton=Decimal("5.0"),
        items=[
            SaleItem(
                nft_address="0:nft1",
                nft_name="Cool NFT #1",
                collection_address="0:col_abc",
                collection_name="Cool Collection",
                nft_address_b64url="EQnft1",
                image_url="https://example.com/img1.png",
            )
        ],
    )
