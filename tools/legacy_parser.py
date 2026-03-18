# Парсер событий NFT: извлечение информации о покупках NFT из событий TONAPI
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List

NANO = Decimal("1000000000")


def nano_to_ton(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    # TonAPI часто отдаёт amount как int/str в nanoTON
    return Decimal(str(value)) / NANO


@dataclass
class SaleItem:
    nft_address: str
    nft_name: str
    collection_address: str
    collection_name: str
    buyer: str
    seller: str
    price_ton: Decimal


@dataclass
class SaleEvent:
    event_id: str
    utime: int
    tx_hash: str
    items: List[SaleItem]

    @property
    def total_price_ton(self) -> Decimal:
        return sum((i.price_ton for i in self.items), Decimal("0"))


def _extract_events(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("events", "data", "result"):
        v = payload.get(key)
        if isinstance(v, list):
            return v
    return []


def _looks_like_nft_purchase(action: Dict[str, Any]) -> bool:
    t = (action.get("type") or action.get("action") or "").lower()
    # делаем максимально терпимо к форматам
    if "nft" in t and ("purchase" in t or "sale" in t or "buy" in t):
        return True
    # иногда data лежит прямо внутри action без type
    if "nft" in action and ("amount" in action or "price" in action):
        return True
    return False


def _pick_purchase_payload(action: Dict[str, Any]) -> Dict[str, Any]:
    # возможные варианты расположения полезной нагрузки
    for key in ("nft_purchase", "nftPurchase", "payload", "data"):
        v = action.get(key)
        if isinstance(v, dict):
            return v
    return action


def _get_addr(obj: Any) -> str:
    if isinstance(obj, dict):
        return obj.get("address") or obj.get("raw") or obj.get("friendly") or ""
    if isinstance(obj, str):
        return obj
    return ""


def parse_sales_from_events(payload: Any, tracked_collections: set[str]) -> List[SaleEvent]:
    events = _extract_events(payload)
    out: List[SaleEvent] = []

    for ev in events:
        actions = ev.get("actions") or ev.get("event_actions") or []
        if not isinstance(actions, list):
            continue

        items: List[SaleItem] = []

        for act in actions:
            if not isinstance(act, dict):
                continue
            if not _looks_like_nft_purchase(act):
                continue

            data = _pick_purchase_payload(act)

            nft = data.get("nft") or act.get("nft") or {}
            if not isinstance(nft, dict):
                nft = {}

            nft_address = _get_addr(nft) or _get_addr(data.get("nft_address"))
            nft_name = (
                (nft.get("metadata") or {}).get("name")
                or nft.get("name")
                or data.get("nft_name")
                or nft_address
                or "NFT"
            )

            collection = nft.get("collection") or data.get("collection") or {}
            if not isinstance(collection, dict):
                collection = {}

            collection_address = _get_addr(collection) or _get_addr(data.get("collection_address"))
            collection_name = (
                collection.get("name")
                or data.get("collection_name")
                or collection_address
                or "Collection"
            )

            # фильтрация по tracked collections (сравниваем адрес)
            if tracked_collections and collection_address not in tracked_collections:
                continue

            buyer = _get_addr(data.get("buyer")) or _get_addr(act.get("buyer")) or ""
            seller = _get_addr(data.get("seller")) or _get_addr(act.get("seller")) or ""

            amount = data.get("amount")
            if amount is None:
                amount = data.get("price")
            if amount is None:
                amount = act.get("amount") or act.get("price")

            price_ton = nano_to_ton(amount)

            if not nft_address:
                # если не нашли адрес NFT — пропускаем, чтобы не слать мусор
                continue

            items.append(
                SaleItem(
                    nft_address=nft_address,
                    nft_name=nft_name,
                    collection_address=collection_address,
                    collection_name=collection_name,
                    buyer=buyer,
                    seller=seller,
                    price_ton=price_ton,
                )
            )

        if items:
            event_id = str(ev.get("event_id") or ev.get("id") or "")
            utime = int(ev.get("timestamp") or ev.get("utime") or 0)
            tx_hash = str(ev.get("tx_hash") or ev.get("hash") or ev.get("transaction_hash") or "")

            out.append(SaleEvent(event_id=event_id, utime=utime, tx_hash=tx_hash, items=items))

    return out
