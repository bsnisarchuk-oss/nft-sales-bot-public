# Резолв NFT из trace: получение метаданных NFT по адресам, найденным в trace
import asyncio
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from utils.tonapi import TonApiClient

# Friendly TON-адреса: EQ/UQ + 46 символов
RE_FRIENDLY = re.compile(r"(?:EQ|UQ)[A-Za-z0-9_-]{46}")

# Raw TON-адреса: 0: + 64 hex символа
RE_RAW = re.compile(r"0:[0-9a-fA-F]{64}")


def extract_addresses(text: str) -> list[str]:
    # сначала friendly, потом raw
    friendly = RE_FRIENDLY.findall(text)
    raw = RE_RAW.findall(text)
    return list(dict.fromkeys(friendly + raw))


async def main():
    # Загружаем .env из корня проекта (на уровень выше tools/)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    trace_path = Path("data/sample_trace.json")
    if not trace_path.exists():
        raise RuntimeError("No data/sample_trace.json. Run: py -m tools.dump_trace")

    text = trace_path.read_text(encoding="utf-8")
    addresses = extract_addresses(text)

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    try:
        print("Candidate addresses:", len(addresses))
        shown = 0

        for addr in addresses:
            # пробуем трактовать как NFT item
            try:
                nft = await client.get_nft_item(addr)
            except Exception:
                continue

            # если это реально NFT item — обычно есть metadata/name или что-то подобное
            meta = nft.get("metadata") or {}
            name = meta.get("name") or nft.get("name") or "(no name)"
            collection = nft.get("collection") or {}
            col_addr = collection.get("address") or ""
            col_name = collection.get("name") or ""
            owner = (nft.get("owner") or {}).get("address") or ""

            print("\nNFT ITEM:", addr)
            print(" name:", name)
            print(" owner:", owner)
            print(" collection:", col_name, col_addr)

            shown += 1
            if shown >= 10:
                break

        if shown == 0:
            print("\nNo NFT items resolved from this trace.")
            print("Это может означать, что адреса в trace только raw и TonAPI не принимает raw без")
            print("или этот trace не содержит NFT item адреса в явном виде. Тогда будем доставать")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
