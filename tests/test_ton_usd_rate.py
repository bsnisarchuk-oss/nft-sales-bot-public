"""Tests for utils/ton_usd_rate.py — получение курса TON/USD с Binance."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from utils.ton_usd_rate import _cache, get_ton_usd_rate


@pytest.fixture(autouse=True)
def clear_cache():
    """Очищаем кэш перед каждым тестом."""
    _cache._data.clear()
    yield
    _cache._data.clear()


@pytest.mark.asyncio
async def test_returns_cached_value():
    """Если значение в кэше — HTTP-запрос не делается."""
    _cache.set("ton_usd", 3.45)
    rate = await get_ton_usd_rate()
    assert rate == 3.45


@pytest.mark.asyncio
async def test_fetches_from_binance():
    """При пустом кэше делает запрос к Binance и кэширует."""
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = AsyncMock(return_value={"price": "3.50"})
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)

    with patch("utils.ton_usd_rate._get_session", return_value=mock_session):
        rate = await get_ton_usd_rate()

    assert rate == 3.50
    assert _cache.get("ton_usd") == 3.50


@pytest.mark.asyncio
async def test_fallback_on_primary_failure():
    """Если primary Binance URL падает, пробуем fallback."""
    call_count = 0

    mock_resp_fail = AsyncMock()
    mock_resp_fail.raise_for_status = MagicMock(side_effect=aiohttp.ClientError("fail"))
    mock_resp_fail.__aenter__ = AsyncMock(return_value=mock_resp_fail)
    mock_resp_fail.__aexit__ = AsyncMock(return_value=False)

    mock_resp_ok = AsyncMock()
    mock_resp_ok.raise_for_status = MagicMock()
    mock_resp_ok.json = AsyncMock(return_value={"price": "4.00"})
    mock_resp_ok.__aenter__ = AsyncMock(return_value=mock_resp_ok)
    mock_resp_ok.__aexit__ = AsyncMock(return_value=False)

    def side_effect(url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_resp_fail
        return mock_resp_ok

    mock_session = MagicMock()
    mock_session.get = MagicMock(side_effect=side_effect)

    with patch("utils.ton_usd_rate._get_session", return_value=mock_session):
        rate = await get_ton_usd_rate()

    assert rate == 4.00


@pytest.mark.asyncio
async def test_returns_none_on_total_failure():
    """Если и primary и fallback падают, возвращает None."""
    mock_resp = AsyncMock()
    mock_resp.raise_for_status = MagicMock(side_effect=aiohttp.ClientError("fail"))
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)

    with patch("utils.ton_usd_rate._get_session", return_value=mock_session):
        rate = await get_ton_usd_rate()

    assert rate is None
