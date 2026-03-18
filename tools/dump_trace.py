# Дамп одного trace: получение полного trace по ID из TONAPI для детального анализа
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from utils.tonapi import TonApiClient


def _extract_first_trace_id(payload: dict) -> str:
    for key in ("traces", "data", "result", "items"):
        v = payload.get(key)
        if isinstance(v, list) and v:
            x = v[0]
            if isinstance(x, str):
                return x
            if isinstance(x, dict):
                return str(x.get("id") or x.get("trace_id") or x.get("hash") or "")

    if isinstance(payload, list) and payload:
        return str(payload[0])

    return ""


async def main() -> None:
    # Загружаем .env из корня проекта (на уровень выше tools/)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    traces_path = Path("data/sample_traces.json")
    if not traces_path.exists():
        raise RuntimeError("No data/sample_traces.json. Run: py -m tools.dump_traces")

    with open(traces_path, "r", encoding="utf-8") as f:
        traces_payload = json.load(f)

    if not isinstance(traces_payload, dict):
        raise RuntimeError(f"Unexpected format in {traces_path}")

    trace_id = _extract_first_trace_id(traces_payload)
    if not trace_id:
        raise RuntimeError("No trace_id found in sample_traces.json")

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    try:
        trace = await client.get_trace(trace_id)

        Path("data").mkdir(exist_ok=True)

        with open("data/sample_trace.json", "w", encoding="utf-8") as f:
            json.dump(trace, f, ensure_ascii=False, indent=2)

        print("Saved: data/sample_trace.json")
        print("Trace id:", trace_id)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
