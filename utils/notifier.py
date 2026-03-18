# Уведомления: форматирование сообщений о продажах NFT для отправки в Telegram

import logging
from html import escape as h
from typing import Optional
from urllib.parse import quote

from utils.i18n import t
from utils.models import SaleEvent

log = logging.getLogger("notifier")


def tonviewer_url(addr: str) -> str:
    """Ссылка на Tonviewer (принимает и raw, и b64url)."""
    a = (addr or "").strip()
    return f"https://tonviewer.com/{quote(a)}" if a else ""


def getgems_url(addr_b64: str) -> str:
    """Ссылка на GetGems (только b64url)."""
    a = (addr_b64 or "").strip()
    return f"https://getgems.io/nft/{quote(a)}" if a else ""


def render_custom_template(template: str, sale: SaleEvent, price_usd: Optional[str] = None) -> str | None:
    """Render a user-defined template with sale variables.

    Available variables: {price_ton}, {price_usd}, {buyer}, {seller},
    {trace_id}, {items_count}, {nft_name}, {collection_name}

    Returns None if template is empty or rendering fails.
    """
    if not template or not template.strip():
        return None

    first_item = sale.items[0] if sale.items else None
    try:
        return template.format(
            price_ton=sale.price_ton,
            price_usd=price_usd or "",
            buyer=sale.buyer or "",
            seller=sale.seller or "",
            trace_id=sale.trace_id,
            items_count=len(sale.items),
            nft_name=first_item.nft_name if first_item else "",
            collection_name=first_item.collection_name if first_item else "",
        )
    except (KeyError, IndexError, ValueError):
        log.warning("Failed to render custom template: %s", template[:100])
        return None


def format_sale_message(
    sale: SaleEvent,
    price_usd: Optional[str] = None,
    lang: str = "ru",
    custom_template: str = "",
) -> str:
    # Try custom template first
    if custom_template:
        rendered = render_custom_template(custom_template, sale, price_usd)
        if rendered is not None:
            return rendered

    # Default format
    lines = []
    lines.append(t("sale_header", lang))
    price_line = t("price_label", lang, price_ton=sale.price_ton)
    if price_usd:
        price_line += " " + t("price_usd", lang, price_usd=price_usd)
    lines.append(price_line)
    if sale.buyer:
        lines.append(t("buyer_label", lang, buyer=f"<code>{h(sale.buyer)}</code>"))
    if sale.seller:
        lines.append(t("seller_label", lang, seller=f"<code>{h(sale.seller)}</code>"))
    lines.append(t("trace_label", lang, trace_id=f"<code>{h(sale.trace_id)}</code>"))
    lines.append("")
    lines.append(t("items_label", lang, count=len(sale.items)))
    for it in sale.items[:10]:
        lines.append(f"• <b>{h(it.collection_name)}</b> - {h(it.nft_name)}")
        tv = tonviewer_url(it.nft_address_b64url or it.nft_address)
        links = f'<a href="{tv}">Tonviewer</a>' if tv else ""
        if it.nft_address_b64url:
            gg = getgems_url(it.nft_address_b64url)
            links += f' | <a href="{gg}">GetGems</a>' if links else f'<a href="{gg}">GetGems</a>'
        if links:
            lines.append(f"  {links}")
    if len(sale.items) > 10:
        lines.append(t("and_more", lang, n=len(sale.items) - 10))
    return "\n".join(lines)
