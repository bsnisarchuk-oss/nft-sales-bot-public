"""
TON/USD курс через Binance API (TONUSDT). Кэшируется на TON_USD_CACHE_TTL секунд.
"""
import asyncio
import logging
import os
from typing import Optional

import aiohttp

from utils.ttl_cache import TTLCache

log = logging.getLogger("ton_usd_rate")

_cache = TTLCache(
    ttl_seconds=int(os.getenv("TON_USD_CACHE_TTL", "60")),
    max_size=10,
)

DEFAULT_BASE = "https://data-api.binance.vision"
FALLBACK_BASE = "https://api.binance.com"

_session: Optional[aiohttp.ClientSession] = None


def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=6),
            headers={"accept": "application/json"},
        )
    return _session


async def close_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
        _session = None


async def _fetch_price(base_url: str, symbol: str) -> float:
    url = f"{base_url}/api/v3/ticker/price?symbol={symbol}"
    session = _get_session()
    async with session.get(url) as r:
        r.raise_for_status()
        data = await r.json()
    return float(data["price"])


async def get_ton_usd_rate() -> Optional[float]:
    key = "ton_usd"
    cached = _cache.get(key)
    if cached is not None:
        return float(cached)

    symbol = (os.getenv("BINANCE_SYMBOL", "TONUSDT") or "TONUSDT").strip().upper()
    base = (os.getenv("BINANCE_BASE_URL", DEFAULT_BASE) or DEFAULT_BASE).strip().rstrip("/")

    try:
        price = await _fetch_price(base, symbol)
    except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError):
        log.warning("Binance rate fetch failed on %s", base)
        try:
            price = await _fetch_price(FALLBACK_BASE, symbol)
        except (aiohttp.ClientError, asyncio.TimeoutError, KeyError, ValueError):
            log.warning("Binance fallback fetch failed")
            return None

    _cache.set(key, price)
    return price
