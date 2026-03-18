# TonAPI клиент: асинхронный HTTP-клиент для работы с TONAPI с rate limiting
import asyncio
import logging
import os
import random
import time
from typing import Any, Dict, Optional, cast

import aiohttp
from aiohttp import ClientError

from utils.circuit_breaker import CircuitBreaker, CircuitOpenError
from utils.ttl_cache import TTLCache

log = logging.getLogger(__name__)


class TonApiClient:
    def __init__(self, base_url: str, api_key: str, min_interval: float = 1.1) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.min_interval = min_interval
        self._session = aiohttp.ClientSession()
        self._lock = asyncio.Lock()
        self._last_request_ts = 0.0
        self._cb = CircuitBreaker(
            failure_threshold=int(os.getenv("CB_FAILURE_THRESHOLD", "5")),
            recovery_timeout=float(os.getenv("CB_RECOVERY_TIMEOUT", "60")),
        )
        self._nft_cache = TTLCache(
            ttl_seconds=int(os.getenv("NFT_CACHE_TTL", "3600")),
            max_size=5000,
        )
        # Кэш для address_parse / normalize_address — 1–6 ч, меньше нагрузка на API
        self._addr_cache = TTLCache(
            ttl_seconds=int(os.getenv("ADDR_CACHE_TTL", "21600")),  # 6 ч по умолчанию
            max_size=2000,
        )

    async def close(self) -> None:
        await self._session.close()

    async def _rate_limit(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self.min_interval - (now - self._last_request_ts)
            if wait > 0:
                try:
                    await asyncio.sleep(wait)
                except asyncio.CancelledError:
                    # Ctrl+C: пробрасываем сразу, не ждём
                    raise
            self._last_request_ts = time.monotonic()

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}{path}"
        max_retries = 5

        for attempt in range(1, max_retries + 1):
            if not self._cb.allow_request():
                log.warning("Circuit breaker OPEN — skipping request to %s", url)
                raise CircuitOpenError(f"Circuit breaker open for {url}")

            await self._rate_limit()

            try:
                async with self._session.get(
                    url, params=params or {}, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as r:
                    # 429: Too Many Requests
                    if r.status == 429:
                        retry_after = r.headers.get("Retry-After")
                        wait = None
                        if retry_after:
                            try:
                                wait = float(retry_after)
                            except (ValueError, TypeError):
                                pass
                        # если Retry-After нет, делаем экспоненциальную паузу
                        if wait is None:
                            wait = min(20.0, 2.0**attempt)
                        # небольшой "джиттер", чтобы не биться в лимит синхронно
                        wait += random.uniform(0.0, 0.5)

                        if attempt == max_retries:
                            r.raise_for_status()
                        try:
                            await asyncio.sleep(wait)
                        except asyncio.CancelledError:
                            raise
                        continue

                    # 5хх: временные проблемы TonAPI
                    if 500 <= r.status < 600:
                        self._cb.record_failure()
                        wait = min(20.0, 2.0**attempt) + random.uniform(0.0, 0.5)
                        if attempt == max_retries:
                            r.raise_for_status()
                        try:
                            await asyncio.sleep(wait)
                        except asyncio.CancelledError:
                            raise
                        continue

                    # 404 и другие 4xx: не ретраим, сразу пробрасываем
                    if 400 <= r.status < 500:
                        r.raise_for_status()

                    r.raise_for_status()
                    self._cb.record_success()
                    result: Dict[str, Any] = cast(Dict[str, Any], await r.json())
                    return result

            except asyncio.CancelledError:
                # Ctrl+C: пробрасываем сразу, не ретраим
                raise
            except aiohttp.ClientResponseError:
                # 4xx ошибки (404, 400 и т.д.) - не ретраим, сразу пробрасываем
                # 5xx ошибки тоже пробрасываем (они обрабатываются выше в try блоке)
                raise
            except (asyncio.TimeoutError, ClientError):
                # сеть/таймаут: тоже ретраим
                self._cb.record_failure()
                wait = min(20.0, 2.0**attempt) + random.uniform(0.0, 0.5)
                if attempt == max_retries:
                    raise
                try:
                    await asyncio.sleep(wait)
                except asyncio.CancelledError:
                    raise

        raise RuntimeError(f"TonAPI request failed after {max_retries} retries: {url}")

    async def get_account_events(
        self, address: str, limit: int = 20, before_lt: str | None = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if before_lt:
            params["before_lt"] = before_lt

        # А если у твоего TonAPI другой путь — покажет sample_events.json, подстроим.
        result = await self._get(f"/v2/accounts/{address}/events", params)
        return cast(Dict[str, Any], result)

    async def get_account_traces(
        self, address: str, limit: int = 100, before_lt: str | None = None
    ) -> dict:
        params: Dict[str, Any] = {"limit": limit}
        if before_lt:
            params["before_lt"] = before_lt
        return cast(dict, await self._get(f"/v2/accounts/{address}/traces", params=params))

    async def get_trace(self, trace_id: str) -> dict:
        return cast(dict, await self._get(f"/v2/traces/{trace_id}", params=None))

    async def get_nft_item(self, address: str) -> dict:
        cache_key = f"nft:{address}"
        cached = self._nft_cache.get(cache_key)
        if cached is not None:
            result: dict = cast(dict, cached)
            return result

        data = await self._get(f"/v2/nfts/{address}", params=None)
        self._nft_cache.set(cache_key, data)
        return cast(dict, data)

    async def get_nft_collection(self, address: str) -> dict:
        """Информация о NFT-коллекции по адресу. Кэшируется так же, как get_nft_item."""
        cache_key = f"col:{address}"
        cached = self._nft_cache.get(cache_key)
        if cached is not None:
            result: dict = cast(dict, cached)
            return result

        data = await self._get(f"/v2/nfts/collections/{address}", params=None)
        self._nft_cache.set(cache_key, data)
        return cast(dict, data)

    async def address_parse(self, account_id: str) -> dict:
        """
        Обёртка над /v2/address/{account_id}/parse.
        Возвращает разобранный адрес (bounceable/b64url и т.п.).
        Кэш 1–6 ч (ADDRESS_CACHE_TTL), чтобы не бить лимиты API.
        """
        cache_key = f"addr:{account_id}"
        cached = self._addr_cache.get(cache_key)
        if cached is not None:
            result: dict = cast(dict, cached)
            return result

        data = await self._get(f"/v2/address/{account_id}/parse", params=None)
        self._addr_cache.set(cache_key, data)
        return cast(dict, data)

    # совместимый алиас под название из инструкций (parse_address)
    async def parse_address(self, account_id: str) -> dict:
        return await self.address_parse(account_id)

    async def normalize_address(self, account_id: str) -> tuple[str, str]:
        """
        Возвращает (raw_form, bounceable_b64url).
        Нормализует адрес через TonAPI для валидации пользовательского ввода.
        """
        data = await self.address_parse(account_id)
        raw_form = data.get("raw_form") or ""
        b64url = (data.get("bounceable") or {}).get("b64url") or ""
        return raw_form, b64url

    async def to_b64url(self, account_id: str) -> str:
        """
        Утилита для получения bounceable.b64url адреса по account_id.
        """
        data = await self.address_parse(account_id)
        b64: str = cast(str, data["bounceable"]["b64url"])
        return b64
