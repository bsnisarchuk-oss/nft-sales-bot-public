# Сканирование недавних продаж: проверка последних traces на наличие продаж NFT
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from tools.legacy_trace_sales import extract_raw_addresses, parse_sales_from_trace
from utils.tonapi import TonApiClient


async def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

    addresses = [a.strip() for a in os.getenv("GETGEMS_ADDRESSES", "").split(",") if a.strip()]
    if not addresses:
        print("GETGEMS_ADDRESSES пустой")
        return

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    tracked = set()  # пусто = не фильтруем коллекции
    ignore = set(addresses)

    found = 0
    try:
        for addr in addresses:
            print("\n=== Address:", addr, "===")
            traces = await client.get_account_traces(addr, limit=20)
            trace_list = traces.get("traces") if isinstance(traces, dict) else traces
            if not trace_list:
                print("No traces")
                continue

            # берём последние 10 trace_id
            ids = [t["id"] for t in trace_list[:10] if isinstance(t, dict) and t.get("id")]

            for tid in ids:
                try:
                    trace = await client.get_trace(tid)
                except Exception as e:
                    print(f"trace={tid[:10]}... ❌ get_trace error: {e}")
                    continue
                raw_addrs = extract_raw_addresses(trace)
                # быстро покажем: вообще есть ли raw-адреса в trace
                print(f"trace={tid[:10]}... raw_addrs={len(raw_addrs)}", end="")

                sale = await parse_sales_from_trace(
                    trace_id=tid,
                    trace=trace,
                    tracked_collections=tracked,
                    ignore_addresses=ignore,
                    tonapi_client=client,
                )

                if sale:
                    found += 1
                    print(
                        " ✅ SALE:",
                        float(sale.price_ton),
                        "TON",
                        "items=",
                        len(sale.items),
                    )
                else:
                    print(" - no sale")

    finally:
        await client.close()

    print("\nTOTAL SALES FOUND:", found)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
