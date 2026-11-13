"""Node 2: drop anything already sent, anything clearly stale, and duplicates."""
from __future__ import annotations

from datetime import datetime, timezone

from ..deps import Deps
from ..freshness import is_fresh
from ..memory import url_hash
from ..state import AgentState, Candidate

MAX_FRESH = 40  # keeps the summarize prompt small and cheap


def dedupe(state: AgentState, deps: Deps, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    window = deps.settings.window_hours
    seen_in_batch: set[str] = set()
    fresh: list[Candidate] = []

    for c in state.get("candidates", []):
        h = url_hash(c["url"])
        if h in seen_in_batch or deps.memory.is_seen(c["url"]):
            continue
        # Unknown age stays in; the summarizer is told to judge it. Known-stale goes.
        if is_fresh(c.get("page_age"), now, window) is False:
            continue
        seen_in_batch.add(h)
        fresh.append(c)

    return {"fresh": fresh[:MAX_FRESH]}
