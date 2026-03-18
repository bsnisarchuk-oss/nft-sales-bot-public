"""Digest mode — accumulate sale stats and produce periodic summaries.

Records sale events and generates digest text (total sales, volume, top buyers).
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from html import escape as h


@dataclass
class DigestStats:
    total_sales: int = 0
    total_volume_ton: Decimal = Decimal(0)
    top_buyers: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    top_collections: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    first_sale_at: float = 0.0
    last_sale_at: float = 0.0


# chat_id -> DigestStats
_digests: dict[int, DigestStats] = {}


def record_sale(chat_id: int, buyer: str, price_ton: Decimal, collection_name: str) -> None:
    """Record a sale for digest accumulation."""
    now = time.time()
    d = _digests.setdefault(chat_id, DigestStats())
    d.total_sales += 1
    d.total_volume_ton += price_ton
    if buyer:
        d.top_buyers[buyer] += 1
    if collection_name:
        d.top_collections[collection_name] += 1
    if not d.first_sale_at:
        d.first_sale_at = now
    d.last_sale_at = now


def format_digest(chat_id: int, lang: str = "ru") -> str | None:
    """Format and reset the digest for a chat. Returns None if no sales."""
    d = _digests.pop(chat_id, None)
    if not d or d.total_sales == 0:
        return None

    lines = ["<b>📊 Digest</b>"]
    lines.append(f"Sales: <b>{d.total_sales}</b>")
    lines.append(f"Volume: <b>{d.total_volume_ton} TON</b>")

    # Top 3 buyers
    if d.top_buyers:
        sorted_buyers = sorted(d.top_buyers.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append("")
        lines.append("<b>Top buyers:</b>")
        for addr, count in sorted_buyers:
            short = addr[:16] + "..." if len(addr) > 16 else addr
            lines.append(f"  <code>{h(short)}</code> — {count}")

    # Top 3 collections
    if d.top_collections:
        sorted_cols = sorted(d.top_collections.items(), key=lambda x: x[1], reverse=True)[:3]
        lines.append("")
        lines.append("<b>Top collections:</b>")
        for name, count in sorted_cols:
            lines.append(f"  {h(name)} — {count}")

    return "\n".join(lines)


def has_data(chat_id: int) -> bool:
    """Check if there's digest data for a chat."""
    d = _digests.get(chat_id)
    return d is not None and d.total_sales > 0


def reset(chat_id: int | None = None) -> None:
    """Clear digest data. If chat_id is None, clear all."""
    if chat_id is None:
        _digests.clear()
    else:
        _digests.pop(chat_id, None)
