# Тест парсера продаж из trace: проверка работы parse_sales_from_trace на sample_trace.json
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from tools.legacy_trace_sales import parse_sales_from_trace
from utils.storage import load_json
from utils.tonapi import TonApiClient


async def main():
    # Загружаем .env из корня проекта (на уровень выше tools/)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    trace_path = Path("data/sample_trace.json")
    if not trace_path.exists():
        raise RuntimeError("No data/sample_trace.json. Run: py -m tools.dump_trace")

    trace = json.loads(trace_path.read_text(encoding="utf-8"))

    # trace_id можно взять из файла, но для теста ок любой
    trace_id = trace.get("id") or trace.get("trace_id") or "sample_trace"

    tracked = set(load_json("data/collections.json", default=[]))

    # адреса, которые лучше исключить при выборе buyer/seller (комиссии/маркет)
    ignore = set(a.strip() for a in os.getenv("GETGEMS_ADDRESSES", "").split(",") if a.strip())

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    try:
        sale = await parse_sales_from_trace(
            trace_id=trace_id,
            trace=trace,
            tracked_collections=tracked,
            ignore_addresses=ignore,
            tonapi_client=client,
        )

        if not sale:
            print("No sale parsed from this trace (or not in tracked collections).")
            return

        print("TRACE:", sale.trace_id)
        print("PRICE:", sale.price_ton, "TON")
        print("BUYER:", sale.buyer)
        print("SELLER:", sale.seller)
        print("ITEMS:", len(sale.items))
        for it in sale.items:
            print("-", it.collection_name, "|", it.nft_name, "|", it.nft_address)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
