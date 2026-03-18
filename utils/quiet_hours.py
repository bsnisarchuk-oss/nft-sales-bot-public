"""Quiet hours — suppress notifications during specified time range."""

from __future__ import annotations

import re
from datetime import datetime, time

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_time(s: str) -> time | None:
    """Parse 'HH:MM' string into a time object. Returns None on invalid input."""
    m = _TIME_RE.match(s.strip())
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        return None
    return time(h, mi)


def is_quiet_now(quiet_start: str, quiet_end: str, now: datetime | None = None) -> bool:
    """Check if current time falls within the quiet hours range.

    Supports cross-midnight ranges like 23:00-07:00.
    Returns False if quiet hours are not configured or invalid.
    """
    if not quiet_start or not quiet_end:
        return False

    start = parse_time(quiet_start)
    end = parse_time(quiet_end)
    if start is None or end is None:
        return False

    if now is None:
        now = datetime.now()
    current = now.time()

    if start <= end:
        # Same day range: e.g. 09:00-17:00
        return start <= current < end
    else:
        # Cross-midnight range: e.g. 23:00-07:00
        return current >= start or current < end
