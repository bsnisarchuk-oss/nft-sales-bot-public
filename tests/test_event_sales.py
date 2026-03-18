"""Tests for utils/event_sales.py — парсинг NftPurchase, TelemintDeployV2, AuctionBid."""

from decimal import Decimal
from unittest.mock import AsyncMock

import aiohttp
import pytest

from utils.event_sales import (
    _get_addr,
    _nano_to_ton,
    _normalized_raw,
    parse_sale_from_event,
)


class _FakeTonApi:
    """Mock TonAPI — normalize_address возвращает адрес как есть."""

    async def normalize_address(self, addr: str) -> tuple[str, str]:
        return addr, ""

    async def get_nft_item(self, addr: str) -> dict:
        return {
            "metadata": {"name": f"NFT {addr[:8]}"},
            "collection": {"address": "0:col", "name": "TestCol"},
        }


# --- _get_addr ---

def test_get_addr_from_string():
    assert _get_addr("0:abc") == "0:abc"


def test_get_addr_from_dict():
    assert _get_addr({"address": "0:abc", "raw": "0:xyz"}) == "0:abc"


def test_get_addr_from_dict_raw_fallback():
    assert _get_addr({"raw": "0:xyz"}) == "0:xyz"


def test_get_addr_from_none():
    assert _get_addr(None) == ""


def test_get_addr_from_int():
    assert _get_addr(42) == ""


# --- _nano_to_ton ---

def test_nano_to_ton_normal():
    assert _nano_to_ton("1000000000") == Decimal("1")


def test_nano_to_ton_none():
    assert _nano_to_ton(None) == Decimal("0")


def test_nano_to_ton_invalid():
    assert _nano_to_ton("not_a_number") == Decimal("0")


def test_nano_to_ton_int():
    assert _nano_to_ton(5000000000) == Decimal("5")


# --- parse_sale_from_event: NftPurchase ---

@pytest.mark.asyncio
async def test_nft_purchase_basic():
    event = {
        "event_id": "ev1",
        "actions": [
            {
                "type": "NftPurchase",
                "status": "ok",
                "NftPurchase": {
                    "buyer": {"address": "0:buyer"},
                    "seller": {"address": "0:seller"},
                    "amount": {"value": "2000000000"},
                    "nft": {
                        "address": "0:nft1",
                        "metadata": {"name": "NFT #1"},
                        "collection": {"address": "0:col_abc", "name": "TestCol"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col_abc", tonapi_client=_FakeTonApi())
    assert sale is not None
    assert sale.price_ton == Decimal("2")
    assert sale.buyer == "0:buyer"
    assert sale.seller == "0:seller"
    assert len(sale.items) == 1
    assert sale.items[0].nft_name == "NFT #1"


@pytest.mark.asyncio
async def test_nft_purchase_wrong_collection():
    event = {
        "event_id": "ev2",
        "actions": [
            {
                "type": "NftPurchase",
                "status": "ok",
                "NftPurchase": {
                    "buyer": {"address": "0:buyer"},
                    "seller": {"address": "0:seller"},
                    "amount": "1000000000",
                    "nft": {
                        "address": "0:nft1",
                        "metadata": {"name": "NFT"},
                        "collection": {"address": "0:other_col", "name": "Other"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:target_col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_nft_purchase_failed_status_ignored():
    event = {
        "event_id": "ev3",
        "actions": [
            {
                "type": "NftPurchase",
                "status": "failed",
                "NftPurchase": {
                    "buyer": {"address": "0:buyer"},
                    "seller": {"address": "0:seller"},
                    "amount": "1000000000",
                    "nft": {
                        "address": "0:nft1",
                        "collection": {"address": "0:col", "name": "C"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


# --- parse_sale_from_event: AuctionBid ---

@pytest.mark.asyncio
async def test_auction_bid_matching():
    event = {
        "event_id": "ev_bid",
        "actions": [
            {
                "type": "AuctionBid",
                "status": "ok",
                "AuctionBid": {
                    "bidder": {"address": "0:bidder"},
                    "amount": {"value": "3000000000"},
                    "nft": {
                        "address": "0:nft_bid",
                        "metadata": {"name": "Bid NFT"},
                        "collection": {"address": "0:col_bid", "name": "BidCol"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col_bid", tonapi_client=_FakeTonApi())
    assert sale is not None
    assert sale.price_ton == Decimal("3")
    assert sale.buyer == "0:bidder"


@pytest.mark.asyncio
async def test_auction_bid_mismatched_collection():
    event = {
        "event_id": "ev_bid2",
        "actions": [
            {
                "type": "AuctionBid",
                "status": "ok",
                "AuctionBid": {
                    "bidder": {"address": "0:bidder"},
                    "amount": {"value": "1000000000"},
                    "nft": {
                        "address": "0:nft",
                        "metadata": {"name": "NFT"},
                        "collection": {"address": "0:real", "name": "Real"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:other", tonapi_client=_FakeTonApi())
    assert sale is None


# --- parse_sale_from_event: edge cases ---

@pytest.mark.asyncio
async def test_empty_event_id():
    event = {"event_id": "", "actions": []}
    assert await parse_sale_from_event(event, "0:col") is None


@pytest.mark.asyncio
async def test_no_actions():
    event = {"event_id": "ev", "actions": None}
    assert await parse_sale_from_event(event, "0:col") is None


@pytest.mark.asyncio
async def test_no_tonapi_client():
    """Without tonapi_client, addresses are compared as-is."""
    event = {
        "event_id": "ev_no_api",
        "actions": [
            {
                "type": "NftPurchase",
                "status": "ok",
                "NftPurchase": {
                    "buyer": "0:buyer",
                    "seller": "0:seller",
                    "amount": "500000000",
                    "nft": {
                        "address": "0:nft",
                        "metadata": {"name": "N"},
                        "collection": {"address": "0:col_x", "name": "X"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col_x", tonapi_client=None)
    assert sale is not None
    assert sale.price_ton == Decimal("0.5")


# --- _normalized_raw ---

@pytest.mark.asyncio
async def test_normalized_raw_empty_addr():
    from utils.event_sales import _normalized_raw
    result = await _normalized_raw("", None)
    assert result == ""


@pytest.mark.asyncio
async def test_normalized_raw_no_client():
    result = await _normalized_raw("0:abc", None)
    assert result == "0:abc"


@pytest.mark.asyncio
async def test_normalized_raw_client_exception():
    """When normalize_address raises ClientError, return the original addr."""
    client = AsyncMock()
    client.normalize_address = AsyncMock(side_effect=aiohttp.ClientError())
    result = await _normalized_raw("0:abc", client)
    assert result == "0:abc"


# --- NftPurchase edge cases ---

@pytest.mark.asyncio
async def test_nft_purchase_non_dict_action_skipped():
    """Non-dict actions in list should be skipped without error."""
    event = {
        "event_id": "ev_nondict",
        "actions": ["not_a_dict", None, 42],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_nft_purchase_non_dict_purchase_skipped():
    event = {
        "event_id": "ev_bad_purchase",
        "actions": [{"type": "NftPurchase", "status": "ok", "NftPurchase": "not_a_dict"}],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_nft_purchase_non_dict_nft_skipped():
    event = {
        "event_id": "ev_bad_nft",
        "actions": [
            {
                "type": "NftPurchase",
                "status": "ok",
                "NftPurchase": {
                    "buyer": "0:b",
                    "seller": "0:s",
                    "amount": "1000000000",
                    "nft": "not_a_dict",
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_nft_purchase_non_dict_collection_skipped():
    event = {
        "event_id": "ev_bad_col",
        "actions": [
            {
                "type": "NftPurchase",
                "status": "ok",
                "NftPurchase": {
                    "buyer": "0:b",
                    "seller": "0:s",
                    "amount": "1000000000",
                    "nft": {
                        "address": "0:nft",
                        "metadata": {"name": "N"},
                        "collection": "not_a_dict",
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_nft_purchase_zero_price_skipped():
    """NftPurchase with price_ton == 0 should be filtered out."""
    event = {
        "event_id": "ev_zero",
        "actions": [
            {
                "type": "NftPurchase",
                "status": "ok",
                "NftPurchase": {
                    "buyer": {"address": "0:buyer"},
                    "seller": {"address": "0:seller"},
                    "amount": {"value": "0"},
                    "nft": {
                        "address": "0:nft1",
                        "metadata": {"name": "NFT #1"},
                        "collection": {"address": "0:col", "name": "TestCol"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


# --- TelemintDeployV2 ---

@pytest.mark.asyncio
async def test_telemint_basic():
    """TelemintDeployV2: SmartContractExec + NftItemTransfer → SaleEvent."""
    class _TonApiWithNft:
        async def normalize_address(self, addr):
            return addr, ""

        async def get_nft_item(self, addr):
            return {
                "metadata": {"name": "Fragment NFT"},
                "name": "Fragment NFT",
                "collection": {"address": "0:frag_col", "name": "FragCol"},
            }

    event = {
        "event_id": "ev_telemint",
        "actions": [
            {
                "type": "SmartContractExec",
                "status": "ok",
                "SmartContractExec": {
                    "operation": "TelemintDeployV2",
                    "executor": {"address": "0:buyer"},
                    "ton_attached": "5000000000",
                },
            },
            {
                "type": "NftItemTransfer",
                "status": "ok",
                "NftItemTransfer": {"nft": "0:nft_frag"},
            },
        ],
    }
    sale = await parse_sale_from_event(event, "0:frag_col", tonapi_client=_TonApiWithNft())
    assert sale is not None
    assert sale.price_ton == Decimal("5")
    assert sale.buyer == "0:buyer"
    assert len(sale.items) == 1


@pytest.mark.asyncio
async def test_telemint_no_sc_exec_returns_none():
    """Without SmartContractExec TelemintDeployV2, returns None."""
    event = {
        "event_id": "ev_no_sc",
        "actions": [
            {
                "type": "NftItemTransfer",
                "status": "ok",
                "NftItemTransfer": {"nft": "0:nft"},
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_telemint_wrong_operation_returns_none():
    """SmartContractExec with different operation → no TelemintDeployV2 path."""
    event = {
        "event_id": "ev_wrong_op",
        "actions": [
            {
                "type": "SmartContractExec",
                "status": "ok",
                "SmartContractExec": {
                    "operation": "SomeOtherOp",
                    "executor": "0:buyer",
                    "ton_attached": "1000000000",
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_telemint_no_nft_transfer_returns_none():
    """TelemintDeployV2 without NftItemTransfer → None (no nft_addr)."""
    event = {
        "event_id": "ev_no_transfer",
        "actions": [
            {
                "type": "SmartContractExec",
                "status": "ok",
                "SmartContractExec": {
                    "operation": "TelemintDeployV2",
                    "executor": "0:buyer",
                    "ton_attached": "1000000000",
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_telemint_zero_price_skipped():
    """TelemintDeployV2 with price 0 → filtered out."""
    event = {
        "event_id": "ev_tel_zero",
        "actions": [
            {
                "type": "SmartContractExec",
                "status": "ok",
                "SmartContractExec": {
                    "operation": "TelemintDeployV2",
                    "executor": "0:buyer",
                    "ton_attached": "0",
                },
            },
            {
                "type": "NftItemTransfer",
                "status": "ok",
                "NftItemTransfer": {"nft": "0:nft"},
            },
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


# --- AuctionBid edge cases ---

@pytest.mark.asyncio
async def test_auction_bid_non_dict_action_skipped():
    event = {
        "event_id": "ev_bid_nondict",
        "actions": ["not_a_dict"],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_auction_bid_non_dict_bid_skipped():
    event = {
        "event_id": "ev_bid_bad",
        "actions": [{"type": "AuctionBid", "status": "ok", "AuctionBid": "not_a_dict"}],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_auction_bid_non_dict_nft_skipped():
    event = {
        "event_id": "ev_bid_bad_nft",
        "actions": [
            {
                "type": "AuctionBid",
                "status": "ok",
                "AuctionBid": {
                    "bidder": "0:bidder",
                    "amount": {"value": "1000000000"},
                    "nft": "not_a_dict",
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col", tonapi_client=_FakeTonApi())
    assert sale is None


@pytest.mark.asyncio
async def test_auction_bid_zero_price_skipped():
    """AuctionBid with price 0 → filtered out."""
    event = {
        "event_id": "ev_bid_zero",
        "actions": [
            {
                "type": "AuctionBid",
                "status": "ok",
                "AuctionBid": {
                    "bidder": {"address": "0:bidder"},
                    "amount": {"value": "0"},
                    "nft": {
                        "address": "0:nft_bid",
                        "metadata": {"name": "Bid NFT"},
                        "collection": {"address": "0:col_bid", "name": "BidCol"},
                    },
                },
            }
        ],
    }
    sale = await parse_sale_from_event(event, "0:col_bid", tonapi_client=_FakeTonApi())
    assert sale is None
