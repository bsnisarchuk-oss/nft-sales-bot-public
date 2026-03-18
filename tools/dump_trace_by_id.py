import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from utils.tonapi import TonApiClient


async def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

    if len(sys.argv) < 2:
        print("Usage: py -m tools.dump_trace_by_id <TRACE_ID>")
        return

    trace_id = sys.argv[1].strip()

    client = TonApiClient(
        base_url=os.environ.get("TONAPI_BASE_URL", "https://tonapi.io"),
        api_key=os.environ.get("TONAPI_KEY", ""),
        min_interval=float(os.environ.get("TONAPI_MIN_INTERVAL", "1.1")),
    )

    try:
        trace = await client.get_trace(trace_id)
        Path("data").mkdir(exist_ok=True)
        Path("data/sample_trace.json").write_text(
            json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("Saved: data/sample_trace.json")
        print("Trace id:", trace_id)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
