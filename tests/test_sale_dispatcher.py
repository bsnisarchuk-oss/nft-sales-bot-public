"""Tests for sale_dispatcher module."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from utils.models import SaleEvent, SaleItem


def _make_sale(
    price: str = "5.0",
    collection: str = "0:col_abc",
    trace_id: str = "tr_1",
    image_url: str = "",
) -> SaleEvent:
    return SaleEvent(
        trace_id=trace_id,
        buyer="0:buyer",
        seller="0:seller",
        price_ton=Decimal(price),
        items=[
            SaleItem(
                nft_address="0:nft1",
                nft_name="NFT #1",
                collection_address=collection,
                collection_name="Col",
                nft_address_b64url="EQnft1",
                image_url=image_url,
            )
        ],
    )


# --------------- helpers for mocking ---------------

def _mock_settings(
    min_price: float = 0,
    cooldown: int = 0,
    show_preview: bool = True,
    send_photos: bool = True,
    whale_threshold: float = 0,
    whale_ping: bool = False,
):
    """Return an object that quacks like ChatSettings row."""
    class S:
        min_price_ton = min_price
        cooldown_sec = cooldown
        show_link_preview = show_preview
        send_photos_attr = send_photos
        whale_threshold_ton = whale_threshold
        whale_ping_admins = whale_ping
        language = "ru"
        quiet_start = ""
        quiet_end = ""
        message_template = ""
    s = S()
    s.send_photos = send_photos
    return s


@pytest.fixture(autouse=True)
def _reset_cooldown():
    """Reset module-level cooldown dict between tests."""
    import utils.sale_dispatcher as sd
    sd._last_sent_at.clear()
    yield
    sd._last_sent_at.clear()


# --------------- _send_sale_to_chat tests ---------------


@pytest.mark.asyncio
async def test_sale_sent_to_matching_chat(mock_bot):
    """Sale should be sent when collection matches tracked set."""
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=None),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is True
        mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_sale_filtered_wrong_collection(mock_bot):
    """Sale should NOT be sent if collection is not in tracked set."""
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:other_col"}),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is False
        mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_no_tracked_returns_false(mock_bot):
    """Empty tracked set → False."""
    with patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value=set()):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is False


@pytest.mark.asyncio
async def test_min_price_filters_cheap_sale(mock_bot):
    """Sales below min_price should be filtered out."""
    settings = _mock_settings(min_price=10.0)
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale(price="5.0"))
        assert result is False


@pytest.mark.asyncio
async def test_min_price_zero_passes(mock_bot):
    """min_price=0 should let all sales through."""
    settings = _mock_settings(min_price=0)
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is True


@pytest.mark.asyncio
async def test_single_photo_sent(mock_bot):
    """If NFT has image_url, send_photo should be called."""
    settings = _mock_settings(send_photos=True)
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        sale = _make_sale(image_url="https://example.com/img.png")
        result = await _send_sale_to_chat(mock_bot, 123, sale)
        assert result is True
        mock_bot.send_photo.assert_called_once()
        # send_message should NOT be called when photo succeeds
        mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_photo_fail_fallback_text(mock_bot):
    """If send_photo fails, should fallback to send_message."""
    settings = _mock_settings(send_photos=True)
    mock_bot.send_photo.side_effect = Exception("photo error")
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        sale = _make_sale(image_url="https://example.com/img.png")
        result = await _send_sale_to_chat(mock_bot, 123, sale)
        assert result is True
        mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_usd_price_in_message(mock_bot):
    """USD price should appear in the message when rate is available."""
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=None),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale(price="10.0"))
        assert result is True
        call_kwargs = mock_bot.send_message.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text", "")
        assert "$" in text or "USD" in text or "35" in text


@pytest.mark.asyncio
async def test_no_usd_when_rate_none(mock_bot):
    """When rate is None, message should still be sent without USD."""
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=None),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=None),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale(price="10.0"))
        assert result is True
        mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_retry_on_telegram_error(mock_bot):
    """Should retry on first failure, succeed on second."""
    mock_bot.send_message.side_effect = [Exception("TelegramError"), None]
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=None),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
        patch("utils.sale_dispatcher.asyncio.sleep", new_callable=AsyncMock),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is True
        assert mock_bot.send_message.call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausted_enqueues(mock_bot):
    """After SEND_MAX_RETRIES failures, should enqueue and return False."""
    mock_bot.send_message.side_effect = Exception("fail")
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=None),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
        patch("utils.sale_dispatcher.asyncio.sleep", new_callable=AsyncMock),
        patch("utils.sale_dispatcher._enqueue_failed", new_callable=AsyncMock) as mock_enq,
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is False
        mock_enq.assert_called_once()


# --------------- dispatch_sale_to_chats tests ---------------


@pytest.mark.asyncio
async def test_no_enabled_chats_returns_empty(mock_bot):
    """No enabled chats → empty list."""
    with patch("utils.sale_dispatcher.enabled_chats", new_callable=AsyncMock, return_value=[]):
        from utils.sale_dispatcher import dispatch_sale_to_chats
        result = await dispatch_sale_to_chats(mock_bot, _make_sale())
        assert result == []


@pytest.mark.asyncio
async def test_dispatch_routes_to_matching_chat(mock_bot):
    """dispatch_sale_to_chats should send to matching chats."""
    with (
        patch("utils.sale_dispatcher.enabled_chats", new_callable=AsyncMock, return_value=[111]),
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=None),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import dispatch_sale_to_chats
        result = await dispatch_sale_to_chats(mock_bot, _make_sale())
        assert 111 in result


@pytest.mark.asyncio
async def test_whale_header_added(mock_bot):
    """Whale threshold sale should include whale header."""
    settings = _mock_settings(whale_threshold=3.0, whale_ping=False)
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale(price="5.0"))
        assert result is True
        call_kwargs = mock_bot.send_message.call_args
        text = call_kwargs.kwargs.get("text") or call_kwargs[1].get("text", "")
        assert "WHALE" in text


@pytest.mark.asyncio
async def test_whale_ping_admins(mock_bot):
    """Whale + ping_admins should add admin mention to text."""
    settings = _mock_settings(whale_threshold=3.0, whale_ping=True)
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
        patch.dict("os.environ", {"ADMIN_IDS": "123456"}),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale(price="5.0"))
        assert result is True
        text = mock_bot.send_message.call_args.kwargs.get("text") or \
               mock_bot.send_message.call_args[1].get("text", "")
        assert "123456" in text


@pytest.mark.asyncio
async def test_quiet_hours_skips_sale(mock_bot):
    """During quiet hours, sale should be skipped (return False)."""
    settings = _mock_settings()
    settings.quiet_start = "00:00"
    settings.quiet_end = "23:59"  # always quiet

    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
        patch("utils.sale_dispatcher.is_quiet_now", return_value=True),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is False
        mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_cooldown_wait(mock_bot):
    """When cooldown active, should sleep before sending."""
    import time

    import utils.sale_dispatcher as sd

    settings = _mock_settings(cooldown=10)
    sd._last_sent_at[123] = time.time() - 2  # 2 sec ago, need 8 more

    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
        patch("utils.sale_dispatcher.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_sale())
        assert result is True
        mock_sleep.assert_called_once()  # cooldown sleep happened
        slept = mock_sleep.call_args[0][0]
        assert slept > 0


@pytest.mark.asyncio
async def test_apply_cooldown_updates_last_sent():
    """_apply_cooldown should update _last_sent_at when ignore=False."""
    import utils.sale_dispatcher as sd
    sd._last_sent_at.clear()
    sd._apply_cooldown(999, cooldown_sec=10, ignore_cooldown=False)
    assert 999 in sd._last_sent_at


@pytest.mark.asyncio
async def test_apply_cooldown_ignores_when_flag():
    """_apply_cooldown should NOT update when ignore_cooldown=True."""
    import utils.sale_dispatcher as sd
    sd._last_sent_at.clear()
    sd._apply_cooldown(999, cooldown_sec=10, ignore_cooldown=True)
    assert 999 not in sd._last_sent_at


@pytest.mark.asyncio
async def test_multiple_photos_send_media_group(mock_bot):
    """Multiple images → send_media_group + send_message (caption)."""
    settings = _mock_settings(send_photos=True)

    def _make_multi_photo_sale():
        return SaleEvent(
            trace_id="t_multi",
            buyer="0:buyer",
            seller="0:seller",
            price_ton=Decimal("5.0"),
            items=[
                SaleItem(
                    nft_address=f"0:nft{i}",
                    nft_name=f"NFT #{i}",
                    collection_address="0:col_abc",
                    collection_name="Col",
                    nft_address_b64url=f"EQnft{i}",
                    image_url=f"https://example.com/img{i}.png",
                )
                for i in range(3)
            ],
        )

    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=settings),
        patch("utils.sale_dispatcher.db_ready", return_value=AsyncMock()),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import _send_sale_to_chat
        result = await _send_sale_to_chat(mock_bot, 123, _make_multi_photo_sale())
        assert result is True
        mock_bot.send_media_group.assert_called_once()
        mock_bot.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_enqueue_failed_calls_enqueue(mock_bot):
    """_enqueue_failed should call sale_queue.enqueue when DB available."""
    sale = _make_sale()
    mock_db = AsyncMock()

    with (
        patch("utils.sale_dispatcher.db_ready", return_value=mock_db),
        patch("utils.sale_queue.enqueue", new_callable=AsyncMock) as mock_enqueue,
    ):
        from utils.sale_dispatcher import _enqueue_failed
        await _enqueue_failed(123, sale)
        mock_enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_sale_to_chat_public_api(mock_bot):
    """dispatch_sale_to_chat is the public single-chat API."""
    with (
        patch("utils.sale_dispatcher.tracked_set", new_callable=AsyncMock, return_value={"0:col_abc"}),
        patch("utils.sale_dispatcher.get_settings", new_callable=AsyncMock, return_value=None),
        patch("utils.sale_dispatcher.db_ready", return_value=None),
        patch("utils.sale_dispatcher.get_ton_usd_rate", new_callable=AsyncMock, return_value=3.5),
    ):
        from utils.sale_dispatcher import dispatch_sale_to_chat
        result = await dispatch_sale_to_chat(mock_bot, 999, _make_sale())
        assert result is True
