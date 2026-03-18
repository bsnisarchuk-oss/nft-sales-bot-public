# Legacy: парсер продаж NFT из trace (не используется в production).
# Модели SaleEvent/SaleItem импортируются из utils.models.
from __future__ import annotations

import json
import re
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import aiohttp

from utils.models import SaleEvent, SaleItem  # noqa: F401 — re-export
from utils.nft_media import extract_image_url

RAW_ADDR_RE = re.compile(r"0:[0-9a-fA-F]{64}")
NANO = Decimal("1000000000")


def nano_to_ton(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value)) / NANO


def _json_text(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def extract_raw_addresses(trace: Dict[str, Any]) -> List[str]:
    text = _json_text(trace)
    return sorted(set(RAW_ADDR_RE.findall(text)))


def _iter_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from _iter_dicts(x)


def _get_addr(x: Any) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return x.get("address") or x.get("raw") or x.get("friendly") or ""
    return ""


def extract_ton_transfers(trace: Dict[str, Any]) -> List[Tuple[str, str, int]]:
    """
    Возвращает список (src, dst, value_nano) по всем сообщениям в trace.
    Делаем максимально терпимо к структуре.
    """
    transfers: List[Tuple[str, str, int]] = []

    for d in _iter_dicts(trace):
        # TonAPI trace обычно содержит in_msg/out_msgs у transaction-нод
        if "in_msg" in d and isinstance(d["in_msg"], dict):
            m = d["in_msg"]
            src = _get_addr(m.get("source") or m.get("src"))
            dst = _get_addr(m.get("destination") or m.get("dst"))
            val = m.get("value") or m.get("amount")
            if val is not None:
                try:
                    transfers.append((src, dst, int(val)))
                except Exception:
                    pass

        if "out_msgs" in d and isinstance(d["out_msgs"], list):
            for m in d["out_msgs"]:
                if not isinstance(m, dict):
                    continue
                src = _get_addr(m.get("source") or m.get("src"))
                dst = _get_addr(m.get("destination") or m.get("dst"))
                val = m.get("value") or m.get("amount")
                if val is not None:
                    try:
                        transfers.append((src, dst, int(val)))
                    except Exception:
                        pass

    # оставляем только реальные переводы (value > 0)
    return [(s, t, v) for (s, t, v) in transfers if isinstance(v, int) and v > 0]


def estimate_price_buyer_seller(
    transfers: List[Tuple[str, str, int]],
    ignore_addresses: Set[str],
) -> Tuple[Decimal, str, str]:
    """
    Эвристика: берём самый большой TON перевод в trace.
    buyer = src, seller = dst, price = value
    Исключаем ignore_addresses (наши fee/market адреса), чтобы не выбрать комиссию.
    """
    best = None
    for src, dst, val in transfers:
        if src in ignore_addresses or dst in ignore_addresses:
            continue
        if best is None or val > best[2]:
            best = (src, dst, val)

    if not best:
        return Decimal("0"), "", ""

    src, dst, val = best
    return nano_to_ton(val), src, dst


async def parse_sales_from_trace(
    trace_id: str,
    trace: Dict[str, Any],
    tracked_collections: Set[str],
    ignore_addresses: Set[str],
    tonapi_client,
) -> Optional[SaleEvent]:
    """
    Возвращает одну "продажу" на trace (с batch NFT в items).
    Если nft в trace нет или не попали в tracked_collections — вернёт None.
    """
    nft_addrs = extract_raw_addresses(trace)
    if not nft_addrs:
        return None

    # оцениваем цену и стороны
    transfers = extract_ton_transfers(trace)
    price_ton, buyer, seller = estimate_price_buyer_seller(transfers, ignore_addresses)

    items: List[SaleItem] = []
    for nft_addr in nft_addrs:
        try:
            nft = await tonapi_client.get_nft_item(nft_addr)
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                # это не NFT — просто пропускаем
                continue
            # другие ошибки TonAPI не скрываем
            raise
        except Exception:
            continue

        # нормализация NFT-адреса через TonAPI
        try:
            raw, b64url = await tonapi_client.normalize_address(nft_addr)
        except Exception:
            raw, b64url = nft_addr, ""

        meta = nft.get("metadata") or {}
        nft_name = meta.get("name") or nft.get("name") or nft_addr

        col = nft.get("collection") or {}
        col_addr = _get_addr(col) or ""
        col_name = col.get("name") or col_addr or "Collection"
        # Нормализуем адрес коллекции через API, чтобы совпадал с форматом в чатах (raw)
        if col_addr and tonapi_client:
            try:
                col_raw, col_b64 = await tonapi_client.normalize_address(col_addr)
                col_addr = col_raw or col_addr
            except Exception:
                pass

        # фильтр по коллекциям
        if tracked_collections and col_addr not in tracked_collections:
            continue

        image_url = extract_image_url(nft)

        items.append(
            SaleItem(
                nft_address=raw,
                nft_name=nft_name,
                collection_address=col_addr,
                collection_name=col_name,
                nft_address_b64url=b64url,
                image_url=image_url,
            )
        )

    if not items:
        return None

    return SaleEvent(
        trace_id=trace_id,
        buyer=buyer,
        seller=seller,
        price_ton=price_ton,
        items=items,
    )
