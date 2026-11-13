"""Best-effort parsing of the `page_age` strings web search returns.

Values look like "2 days ago", "5 hours ago" or "November 12, 2026".
Unknown formats return None, and the caller decides what to do with them.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta

_RELATIVE = re.compile(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", re.I)
_UNITS_HOURS = {"minute": 1 / 60, "hour": 1, "day": 24, "week": 168, "month": 720, "year": 8760}
_ABSOLUTE_FORMATS = ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d %B %Y", "%d %b %Y")


def age_hours(page_age: str | None, now: datetime) -> float | None:
    if not page_age:
        return None
    text = page_age.strip()
    if text.lower() in {"today", "just now"}:
        return 0.0
    if text.lower() == "yesterday":
        return 24.0
    m = _RELATIVE.search(text)
    if m:
        return int(m.group(1)) * _UNITS_HOURS[m.group(2).lower()]
    for fmt in _ABSOLUTE_FORMATS:
        try:
            published = datetime.strptime(text, fmt)
        except ValueError:
            continue
        # Date-only values: count from the end of that day so "today" isn't rejected.
        end_of_day = published + timedelta(days=1)
        return max(0.0, (now.replace(tzinfo=None) - end_of_day).total_seconds() / 3600)
    return None


def is_fresh(page_age: str | None, now: datetime, window_hours: int) -> bool | None:
    """True / False when the age is known, None when it can't be parsed."""
    hours = age_hours(page_age, now)
    return None if hours is None else hours <= window_hours
