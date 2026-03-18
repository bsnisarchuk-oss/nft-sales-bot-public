"""Tests for utils/notifier.py — форматирование сообщений о продажах."""

from decimal import Decimal

from utils.models import SaleEvent, SaleItem
from utils.notifier import format_sale_message, getgems_url, tonviewer_url

# --- URL helpers ---

def test_tonviewer_url_raw():
    url = tonviewer_url("0:abc123")
    assert url == "https://tonviewer.com/0%3Aabc123"


def test_tonviewer_url_empty():
    assert tonviewer_url("") == ""
    assert tonviewer_url(None) == ""


def test_getgems_url_b64():
    url = getgems_url("EQabc123")
    assert "getgems.io/nft/EQabc123" in url


def test_getgems_url_empty():
    assert getgems_url("") == ""


# --- format_sale_message ---

def test_format_basic(sample_sale):
    text = format_sale_message(sample_sale)
    assert "<b>NFT Sale</b>" in text
    assert "5.0 TON" in text
    assert "0:buyer_addr" in text
    assert "0:seller_addr" in text
    assert "Cool NFT #1" in text
    assert "Cool Collection" in text


def test_format_with_usd(sample_sale):
    text = format_sale_message(sample_sale, price_usd="15.50")
    assert "$15.50" in text


def test_format_without_usd(sample_sale):
    text = format_sale_message(sample_sale, price_usd=None)
    assert "$" not in text


def test_format_sale_message_escapes_html_fields():
    sale = SaleEvent(
        trace_id='trace<id>&"1"',
        buyer="buyer<evil>",
        seller="seller&evil",
        price_ton=Decimal("1.23"),
        items=[
            SaleItem(
                nft_address="0:nft",
                nft_name="NFT <script>alert(1)</script>",
                collection_address="0:col",
                collection_name="Cool & <b>Bad</b> Collection",
                nft_address_b64url="",
                image_url="",
            )
        ],
    )
    text = format_sale_message(sale)
    assert "<script>" not in text
    assert "buyer&lt;evil&gt;" in text
    assert "seller&amp;evil" in text
    assert "Cool &amp; &lt;b&gt;Bad&lt;/b&gt; Collection" in text


def test_format_multiple_items_truncated():
    """Больше 10 items — выводятся первые 10, остальные в '...and N more'."""
    sale = SaleEvent(
        trace_id="multi",
        buyer="0:b",
        seller="0:s",
        price_ton=Decimal("10"),
        items=[
            SaleItem(
                nft_address=f"0:nft{i}",
                nft_name=f"NFT #{i}",
                collection_address="0:col",
                collection_name="Col",
            )
            for i in range(15)
        ],
    )
    text = format_sale_message(sale)
    assert "Items:</b> 15" in text
    assert "NFT #9" in text
    assert "and 5 more" in text


def test_format_no_seller():
    """Если seller пустой, строка Seller не выводится."""
    sale = SaleEvent(
        trace_id="t",
        buyer="0:b",
        seller="",
        price_ton=Decimal("1"),
        items=[
            SaleItem(
                nft_address="0:n",
                nft_name="N",
                collection_address="0:c",
                collection_name="C",
            )
        ],
    )
    text = format_sale_message(sale)
    assert "Seller" not in text


def test_format_links_with_b64url():
    """Если есть nft_address_b64url — появляются ссылки Tonviewer и GetGems."""
    sale = SaleEvent(
        trace_id="t",
        buyer="0:b",
        seller="",
        price_ton=Decimal("1"),
        items=[
            SaleItem(
                nft_address="0:nft",
                nft_name="N",
                collection_address="0:c",
                collection_name="C",
                nft_address_b64url="EQtest123",
            )
        ],
    )
    text = format_sale_message(sale)
    assert "Tonviewer" in text
    assert "GetGems" in text


# --- render_custom_template ---

def test_render_custom_template_basic(sample_sale):
    from utils.notifier import render_custom_template
    result = render_custom_template(
        "Sold {nft_name} for {price_ton} TON to {buyer}", sample_sale
    )
    assert result == "Sold Cool NFT #1 for 5.0 TON to 0:buyer_addr"


def test_render_custom_template_with_usd(sample_sale):
    from utils.notifier import render_custom_template
    result = render_custom_template("{price_ton} TON (${price_usd})", sample_sale, price_usd="17.50")
    assert result == "5.0 TON ($17.50)"


def test_render_custom_template_empty_returns_none(sample_sale):
    from utils.notifier import render_custom_template
    assert render_custom_template("", sample_sale) is None
    assert render_custom_template("   ", sample_sale) is None


def test_render_custom_template_invalid_key_returns_none(sample_sale):
    from utils.notifier import render_custom_template
    result = render_custom_template("{nonexistent_key}", sample_sale)
    assert result is None


def test_render_custom_template_no_items():
    from utils.notifier import render_custom_template
    sale = SaleEvent(
        trace_id="t1", buyer="0:b", seller="0:s",
        price_ton=Decimal("1.0"), items=[],
    )
    result = render_custom_template("{nft_name} - {collection_name}", sale)
    assert result == " - "


def test_format_sale_message_uses_custom_template(sample_sale):
    text = format_sale_message(sample_sale, custom_template="🔥 {price_ton} TON")
    assert text == "🔥 5.0 TON"


def test_format_sale_message_invalid_template_falls_back(sample_sale):
    """Невалидный шаблон → стандартный формат."""
    text = format_sale_message(sample_sale, custom_template="{bad_key_xyz}")
    assert "NFT Sale" in text


def test_format_sale_message_english(sample_sale):
    text = format_sale_message(sample_sale, lang="en")
    assert "NFT Sale" in text
    assert "Price:" in text
