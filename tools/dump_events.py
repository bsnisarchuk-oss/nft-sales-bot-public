import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from utils.tonapi import TonApiClient


async def main() -> None:
    # Загружаем .env из корня проекта (на уровень выше tools/)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    address = os.environ.get("DUMP_ADDRESS", "").strip()
    if not address:
        raise RuntimeError("DUMP_ADDRESS не установлен. Задай в .env")

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    try:
        data = await client.get_account_events(address=address, limit=100)

        Path("data").mkdir(exist_ok=True)

        with open("data/sample_events.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("Saved: data/sample_events.json")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
