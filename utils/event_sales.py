# Парсер продаж NFT из TonAPI events (NftPurchase, TelemintDeployV2, AuctionBid)
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import aiohttp

from utils.models import SaleEvent, SaleItem
from utils.nft_media import extract_image_url

log = logging.getLogger("event_sales")

NANO = Decimal("1000000000")


def _get_addr(obj: Any) -> str:
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return obj.get("address") or obj.get("raw") or ""
    return ""


def _nano_to_ton(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value)) / NANO
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


async def _normalized_raw(addr: str, tonapi_client: Any) -> str:
    if not addr:
        return ""
    if tonapi_client:
        try:
            raw, _ = await tonapi_client.normalize_address(addr)
            return raw or addr
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError):
            return addr
    return addr


async def _try_nft_purchase(
    actions: List[Dict],
    event_id: str,
    collection_address: str,
    tonapi_client: Any,
) -> Optional[SaleEvent]:
    """Handle NftPurchase actions (GetGems and standard marketplaces)."""
    items: List[SaleItem] = []
    buyer = ""
    seller = ""
    price_ton = Decimal("0")

    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("type") != "NftPurchase" or action.get("status") != "ok":
            continue

        purchase = action.get("NftPurchase")
        if not isinstance(purchase, dict):
            continue

        nft = purchase.get("nft")
        if not isinstance(nft, dict):
            continue

        col = nft.get("collection")
        if not isinstance(col, dict):
            continue
        col_addr = _get_addr(col)

        # Normalize and compare collection addresses
        col_addr_raw = await _normalized_raw(col_addr, tonapi_client)
        target_raw = await _normalized_raw(collection_address, tonapi_client)

        if col_addr_raw != target_raw:
            continue

        col_name = col.get("name") or col_addr or "Collection"
        nft_addr = _get_addr(nft)
        if not nft_addr:
            continue

        meta = nft.get("metadata") or {}
        nft_name = meta.get("name") or nft.get("name") or nft_addr
        image_url = extract_image_url(nft)

        action_buyer = _get_addr(purchase.get("buyer"))
        action_seller = _get_addr(purchase.get("seller"))

        amount = purchase.get("amount")
        action_price = Decimal("0")
        if isinstance(amount, dict):
            val = amount.get("value")
            if val is not None:
                action_price = _nano_to_ton(val)
        elif amount is not None:
            action_price = _nano_to_ton(amount)

        if action_price > price_ton:
            price_ton = action_price
            buyer = action_buyer
            seller = action_seller

        items.append(
            SaleItem(
                nft_address=nft_addr,
                nft_name=nft_name,
                collection_address=col_addr_raw or collection_address,
                collection_name=col_name,
                nft_address_b64url="",
                image_url=image_url,
            )
        )

    if not items:
        return None
    return SaleEvent(trace_id=event_id, buyer=buyer, seller=seller, price_ton=price_ton, items=items)


async def _try_telemint(
    actions: List[Dict],
    event_id: str,
    collection_address: str,
    tonapi_client: Any,
) -> Optional[SaleEvent]:
    """Handle Fragment TelemintDeployV2 (SmartContractExec + NftItemTransfer)."""
    # Find SmartContractExec with TelemintDeployV2 operation
    sc_action = None
    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("type") != "SmartContractExec" or action.get("status") != "ok":
            continue
        sc = action.get("SmartContractExec")
        if not isinstance(sc, dict):
            continue
        if sc.get("operation") == "TelemintDeployV2":
            sc_action = sc
            break

    if sc_action is None:
        return None

    buyer = _get_addr(sc_action.get("executor"))
    price_ton = _nano_to_ton(sc_action.get("ton_attached"))

    # Find paired NftItemTransfer to get NFT address
    nft_addr = ""
    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("type") != "NftItemTransfer" or action.get("status") != "ok":
            continue
        transfer = action.get("NftItemTransfer")
        if isinstance(transfer, dict):
            nft_addr = transfer.get("nft") or ""
            if isinstance(nft_addr, dict):
                nft_addr = _get_addr(nft_addr)
            break

    if not nft_addr:
        return None

    # Fetch NFT metadata for name/image
    nft_name = nft_addr
    col_name = "Collection"
    image_url = ""
    nft_b64url = ""
    target_raw = await _normalized_raw(collection_address, tonapi_client)
    nft_collection_raw = ""
    if tonapi_client:
        try:
            nft_data = await tonapi_client.get_nft_item(nft_addr)
            meta = nft_data.get("metadata") or {}
            nft_name = meta.get("name") or nft_data.get("name") or nft_addr
            col = nft_data.get("collection") or {}
            col_name = col.get("name") or col_name
            nft_collection_raw = await _normalized_raw(_get_addr(col), tonapi_client)
            image_url = extract_image_url(nft_data)
        except (KeyError, AttributeError, IndexError):
            pass
        try:
            _, nft_b64url = await tonapi_client.normalize_address(nft_addr)
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError):
            pass

    # Страхуемся от неверной маршрутизации: коллекция в событии должна совпадать с таргетом.
    if target_raw and nft_collection_raw and nft_collection_raw != target_raw:
        return None

    item_collection = nft_collection_raw or target_raw or collection_address
    items = [
        SaleItem(
            nft_address=nft_addr,
            nft_name=nft_name,
            collection_address=item_collection,
            collection_name=col_name,
            nft_address_b64url=nft_b64url,
            image_url=image_url,
        )
    ]
    return SaleEvent(trace_id=event_id, buyer=buyer, seller="", price_ton=price_ton, items=items)


async def _try_auction_bid(
    actions: List[Dict],
    event_id: str,
    collection_address: str,
    tonapi_client: Any,
) -> Optional[SaleEvent]:
    """Handle Fragment AuctionBid events."""
    for action in actions:
        if not isinstance(action, dict):
            continue
        if action.get("type") != "AuctionBid" or action.get("status") != "ok":
            continue

        bid = action.get("AuctionBid")
        if not isinstance(bid, dict):
            continue

        # Bidder = buyer
        buyer = _get_addr(bid.get("bidder"))

        # Price from amount
        amount = bid.get("amount")
        price_ton = Decimal("0")
        if isinstance(amount, dict):
            price_ton = _nano_to_ton(amount.get("value"))

        # NFT data (rich — includes metadata)
        nft = bid.get("nft")
        if not isinstance(nft, dict):
            continue

        nft_addr = _get_addr(nft)
        if not nft_addr:
            continue

        meta = nft.get("metadata") or {}
        nft_name = meta.get("name") or nft.get("name") or nft_addr
        image_url = extract_image_url(nft)

        col = nft.get("collection") or {}
        col_name = col.get("name") or "Collection"
        col_addr = _get_addr(col)
        col_addr_raw = await _normalized_raw(col_addr, tonapi_client)
        target_raw = await _normalized_raw(collection_address, tonapi_client)

        if target_raw and col_addr_raw and col_addr_raw != target_raw:
            continue

        items = [
            SaleItem(
                nft_address=nft_addr,
                nft_name=nft_name,
                collection_address=col_addr_raw or target_raw or collection_address,
                collection_name=col_name,
                nft_address_b64url="",
                image_url=image_url,
            )
        ]
        return SaleEvent(trace_id=event_id, buyer=buyer, seller="", price_ton=price_ton, items=items)

    return None


async def parse_sale_from_event(
    event: Dict[str, Any],
    collection_address: str,
    tonapi_client=None,
) -> Optional[SaleEvent]:
    """
    Парсит один event из /v2/accounts/{collection_addr}/events.
    Поддерживает: NftPurchase, TelemintDeployV2, AuctionBid.
    Возвращает None если подходящее действие не найдено.
    """
    event_id = event.get("event_id") or ""
    if not event_id:
        return None

    actions = event.get("actions")
    if not isinstance(actions, list):
        return None

    # 1) NftPurchase (GetGems, standard marketplaces)
    result = await _try_nft_purchase(actions, event_id, collection_address, tonapi_client)
    if result:
        if result.price_ton <= 0:
            log.debug("Skipping event %s: price_ton=%s <= 0", event_id, result.price_ton)
            return None
        return result

    # 2) TelemintDeployV2 (Fragment mints/purchases)
    result = await _try_telemint(actions, event_id, collection_address, tonapi_client)
    if result:
        if result.price_ton <= 0:
            log.debug("Skipping event %s: price_ton=%s <= 0", event_id, result.price_ton)
            return None
        return result

    # 3) AuctionBid (Fragment auctions)
    result = await _try_auction_bid(actions, event_id, collection_address, tonapi_client)
    if result:
        if result.price_ton <= 0:
            log.debug("Skipping event %s: price_ton=%s <= 0", event_id, result.price_ton)
            return None
        return result

    return None
