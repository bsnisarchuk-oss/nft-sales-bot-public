# Дамп traces: получение traces аккаунта из TONAPI и сохранение в JSON для анализа
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from utils.tonapi import TonApiClient


def _extract_trace_ids(payload: dict) -> list[str]:
    # /v2/accounts/{account_id}/traces обычно возвращает объект со списком
    # сделаем максимально терпимо
    for key in ("traces", "data", "result", "items"):
        v = payload.get(key)
        if isinstance(v, list):
            out = []
            for x in v:
                if isinstance(x, str):
                    out.append(x)
                elif isinstance(x, dict):
                    out.append(str(x.get("id") or x.get("trace_id") or x.get("hash") or ""))
            return [s for s in out if s]

    if isinstance(payload, list):
        return [str(x) for x in payload if str(x).strip()]

    return []


async def main():
    # Загружаем .env из корня проекта (на уровень выше tools/)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    address = os.environ.get("DUMP_ADDRESS", "").strip()
    if not address:
        raise RuntimeError("Set DUMP_ADDRESS in .env")

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    try:
        data = await client.get_account_traces(address=address, limit=100)

        Path("data").mkdir(exist_ok=True)

        with open("data/sample_traces.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        ids = _extract_trace_ids(data if isinstance(data, dict) else {})

        print("Saved: data/sample_traces.json")
        print("Trace ids found:", len(ids))
        print("First 3:", ids[:3])
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
