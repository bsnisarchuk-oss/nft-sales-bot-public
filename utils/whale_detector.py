"""Sweep detection — detect when a buyer purchases multiple NFTs in a short window."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class SweepEvent:
    buyer: str
    count: int
    window_sec: float


# buyer -> list of (timestamp, trace_id)
_buyer_history: dict[str, list[tuple[float, str]]] = {}

# Default: 5 min window, 3+ purchases = sweep
SWEEP_WINDOW_SEC = 300
SWEEP_MIN_COUNT = 3


def record_purchase(buyer: str, trace_id: str) -> SweepEvent | None:
    """Record a purchase and return SweepEvent if sweep threshold is reached.

    Returns SweepEvent only on the exact threshold crossing (not on every subsequent purchase).
    """
    now = time.monotonic()
    cutoff = now - SWEEP_WINDOW_SEC

    history = _buyer_history.setdefault(buyer, [])
    # Prune old entries
    history[:] = [(ts, tid) for ts, tid in history if ts > cutoff]
    history.append((now, trace_id))

    if len(history) == SWEEP_MIN_COUNT:
        return SweepEvent(buyer=buyer, count=len(history), window_sec=SWEEP_WINDOW_SEC)
    return None


def reset() -> None:
    """Clear all buyer history (for testing)."""
    _buyer_history.clear()
