import asyncio
import os
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from tools.legacy_trace_sales import (
    estimate_price_buyer_seller,
    extract_raw_addresses,
    extract_ton_transfers,
)
from utils.tonapi import TonApiClient

TARGET_SALES = 100  # сколько продаж собрать
TRACE_LIMIT = 100  # сколько traces брать за запрос
MAX_PAGES_PER_ADDRESS = 30  # ограничение, чтобы не уйти в бесконечность


async def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

    getgems_addresses = [
        a.strip() for a in os.getenv("GETGEMS_ADDRESSES", "").split(",") if a.strip()
    ]
    if not getgems_addresses:
        print("GETGEMS_ADDRESSES пустой в .env")
        return

    client = TonApiClient(
        base_url=os.getenv("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.getenv("TONAPI_KEY", ""),
        min_interval=float(os.getenv("TONAPI_MIN_INTERVAL", "1.1")),
    )

    # кэши, чтобы резко ускорить (не дергать /v2/nfts/ по 100 раз на одно и то же)
    nft_cache: dict[str, dict[str, Any] | None] = {}

    # статистика
    by_sale = Counter()  # сколько продаж у коллекции
    by_item = Counter()  # сколько NFT-айтемов у коллекции (если batch)
    names: dict[str, str] = {}

    sales_found = 0
    seen_trace_ids: set[str] = set()

    async def get_nft_cached(raw_addr: str) -> dict[str, Any] | None:
        if raw_addr in nft_cache:
            return nft_cache[raw_addr]
        try:
            nft = await client.get_nft_item(raw_addr)
        except Exception:
            nft_cache[raw_addr] = None
            return None
        nft_cache[raw_addr] = nft
        return nft

    try:
        for addr in getgems_addresses:
            if sales_found >= TARGET_SALES:
                break

            print(f"\n=== Scanning address: {addr} ===", flush=True)

            before_lt = None
            pages = 0

            while sales_found < TARGET_SALES and pages < MAX_PAGES_PER_ADDRESS:
                pages += 1
                try:
                    resp = await client.get_account_traces(
                        address=addr, limit=TRACE_LIMIT, before_lt=before_lt
                    )
                except Exception as e:
                    print(f"[page {pages}] get_account_traces error: {e}", flush=True)
                    break

                traces = None
                if isinstance(resp, dict):
                    traces = resp.get("traces") or resp.get("data") or resp.get("items")
                elif isinstance(resp, list):
                    traces = resp

                if not traces:
                    print(f"[page {pages}] no traces", flush=True)
                    break

                # для пагинации берём "самый старый" lt/utime
                last = traces[-1] if isinstance(traces[-1], dict) else None
                last_lt = None
                if isinstance(last, dict):
                    last_lt = last.get("utime") or last.get("lt") or last.get("timestamp")
                before_lt = str(last_lt) if last_lt is not None else None

                print(
                    f"[page {pages}] traces={len(traces)} sales_found={sales_found}",
                    flush=True,
                )

                for t in traces:
                    if sales_found >= TARGET_SALES:
                        break
                    if not isinstance(t, dict):
                        continue
                    tid = t.get("id")
                    if not tid or tid in seen_trace_ids:
                        continue
                    seen_trace_ids.add(tid)

                    # качаем trace
                    try:
                        trace = await client.get_trace(tid)
                    except Exception:
                        # пропускаем плохой trace и идём дальше
                        continue

                    # быстрый отбор: если вообще нет raw адресов — не sale
                    raw_addrs = extract_raw_addresses(trace)
                    if not raw_addrs:
                        continue

                    # эвристика цены (можно не использовать, но пусть будет)
                    transfers = extract_ton_transfers(trace)
                    _price, _buyer, _seller = estimate_price_buyer_seller(
                        transfers, set(getgems_addresses)
                    )

                    # выцепляем NFT-айтемы через /v2/nfts/{raw}
                    sale_collections_in_this_trace: set[str] = set()

                    for raw in raw_addrs:
                        nft = await get_nft_cached(raw)
                        if not nft:
                            continue
                        col = nft.get("collection") or {}
                        col_addr = (
                            col.get("address")
                            or col.get("raw")
                            or (col.get("friendly") if isinstance(col.get("friendly"), str) else "")
                            or ""
                        )
                        if not col_addr:
                            continue

                        meta = nft.get("metadata") or {}
                        col_name = (col.get("name") or meta.get("collection") or "").strip()

                        by_item[col_addr] += 1
                        sale_collections_in_this_trace.add(col_addr)
                        if col_addr not in names:
                            names[col_addr] = col_name

                    if sale_collections_in_this_trace:
                        # считаем 1 продажу на trace (даже если 3 NFT)
                        for c in sale_collections_in_this_trace:
                            by_sale[c] += 1

                        sales_found += 1

                        if sales_found % 10 == 0:
                            print(
                                f"✅ sales_found={sales_found}/{TARGET_SALES}",
                                flush=True,
                            )

                # если before_lt не меняется — выходим, чтобы не зациклиться
                if before_lt is None:
                    break

        if not by_sale:
            print(
                "\nНе найдено ни одной продажи с коллекциями (по этим traces).",
                flush=True,
            )
            return

        print("\n=== TOP by SALES (collection | sales_count | name) ===", flush=True)
        for addr, cnt in by_sale.most_common(30):
            nm = names.get(addr, "")
            print(f"{addr} | {cnt} | {nm}", flush=True)

        print("\n=== TOP by ITEMS (collection | items_count | name) ===", flush=True)
        for addr, cnt in by_item.most_common(30):
            nm = names.get(addr, "")
            print(f"{addr} | {cnt} | {nm}", flush=True)

        # готовый JSON для вставки
        top10 = [addr for addr, _ in by_sale.most_common(10)]
        print("\n=== Suggested data/collections.json (top10 by sales) ===", flush=True)
        print("[", flush=True)
        for i, a in enumerate(top10):
            comma = "," if i < len(top10) - 1 else ""
            print(f'  "{a}"{comma}', flush=True)
        print("]", flush=True)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
