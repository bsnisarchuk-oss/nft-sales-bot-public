"""Tests for utils/tonapi.py — TonApiClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from utils.circuit_breaker import CircuitOpenError
from utils.tonapi import TonApiClient

# Patch asyncio.sleep globally to avoid real waits in retry logic
pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _no_sleep():
    with patch("utils.tonapi.asyncio.sleep", new_callable=AsyncMock):
        yield


def _mock_response(status=200, json_data=None, headers=None):
    """Create a mock aiohttp response as async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data or {})
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status >= 400:
        from aiohttp import ClientResponseError, RequestInfo
        from yarl import URL

        ri = RequestInfo(url=URL("http://test"), method="GET", headers={}, real_url=URL("http://test"))
        resp.raise_for_status.side_effect = ClientResponseError(
            request_info=ri, history=(), status=status
        )
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def client():
    with patch("aiohttp.ClientSession"):
        c = TonApiClient("https://tonapi.io", "test-key", min_interval=0)
    c._session = MagicMock()
    c._last_request_ts = 0
    return c


@pytest.mark.asyncio
async def test_get_success(client):
    mock_cm = _mock_response(200, {"ok": True})
    with patch.object(client._session, "get", return_value=mock_cm):
        result = await client._get("/v2/test")
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_get_4xx_raises(client):
    mock_cm = _mock_response(404)
    with patch.object(client._session, "get", return_value=mock_cm):
        from aiohttp import ClientResponseError

        with pytest.raises(ClientResponseError):
            await client._get("/v2/missing")


@pytest.mark.asyncio
async def test_circuit_breaker_open(client):
    client._cb._state = "open"
    client._cb._opened_at = 999999999999.0
    with pytest.raises(CircuitOpenError):
        await client._get("/v2/test")


@pytest.mark.asyncio
async def test_get_account_events(client):
    data = {"events": [{"id": "1"}]}
    mock_cm = _mock_response(200, data)
    with patch.object(client._session, "get", return_value=mock_cm):
        result = await client.get_account_events("0:abc", limit=5)
    assert result == data


@pytest.mark.asyncio
async def test_get_nft_item_caching(client):
    data = {"address": "0:nft", "name": "test"}
    mock_cm1 = _mock_response(200, data)
    mock_cm2 = _mock_response(200, {"should": "not be called"})

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_cm1
        return mock_cm2

    with patch.object(client._session, "get", side_effect=side_effect):
        r1 = await client.get_nft_item("0:nft")
        r2 = await client.get_nft_item("0:nft")

    assert r1 == data
    assert r2 == data
    assert call_count == 1  # second call served from cache


@pytest.mark.asyncio
async def test_get_nft_collection_caching(client):
    data = {"address": "0:col", "metadata": {"name": "MyCol"}}
    mock_cm = _mock_response(200, data)

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_cm

    with patch.object(client._session, "get", side_effect=side_effect):
        r1 = await client.get_nft_collection("0:col")
        await client.get_nft_collection("0:col")  # cached, no API call

    assert r1 == data
    assert call_count == 1


@pytest.mark.asyncio
async def test_address_parse_caching(client):
    data = {"raw_form": "0:abc", "bounceable": {"b64url": "EQabc"}}
    mock_cm = _mock_response(200, data)

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_cm

    with patch.object(client._session, "get", side_effect=side_effect):
        r1 = await client.address_parse("EQabc")
        await client.address_parse("EQabc")  # cached, no API call

    assert r1 == data
    assert call_count == 1


@pytest.mark.asyncio
async def test_normalize_address(client):
    data = {"raw_form": "0:abc123", "bounceable": {"b64url": "EQabc123"}}
    mock_cm = _mock_response(200, data)
    with patch.object(client._session, "get", return_value=mock_cm):
        raw, b64 = await client.normalize_address("EQabc123")
    assert raw == "0:abc123"
    assert b64 == "EQabc123"


@pytest.mark.asyncio
async def test_to_b64url(client):
    data = {"raw_form": "0:abc", "bounceable": {"b64url": "EQxyz"}}
    mock_cm = _mock_response(200, data)
    with patch.object(client._session, "get", return_value=mock_cm):
        result = await client.to_b64url("0:abc")
    assert result == "EQxyz"


@pytest.mark.asyncio
async def test_parse_address_alias(client):
    data = {"raw_form": "0:abc", "bounceable": {"b64url": "EQabc"}}
    mock_cm = _mock_response(200, data)
    with patch.object(client._session, "get", return_value=mock_cm):
        result = await client.parse_address("0:abc")
    assert result == data


@pytest.mark.asyncio
async def test_close(client):
    client._session = AsyncMock()
    await client.close()
    client._session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_5xx_records_cb_failure(client):
    """5xx response records circuit breaker failure."""
    mock_cm = _mock_response(500)
    with patch.object(client._session, "get", return_value=mock_cm):
        from aiohttp import ClientResponseError

        with pytest.raises(ClientResponseError):
            await client._get("/v2/fail")
    # CB should have recorded failures
    assert client._cb._failure_count > 0
