"""Thin wrapper over the Anthropic client that also counts tokens and searches."""
from __future__ import annotations

from typing import Any

import anthropic

from .state import Usage


def new_usage() -> Usage:
    return {"input_tokens": 0, "output_tokens": 0, "web_searches": 0}


def add_usage(total: Usage, response: Any) -> Usage:
    u = response.usage
    total["input_tokens"] += getattr(u, "input_tokens", 0) or 0
    total["output_tokens"] += getattr(u, "output_tokens", 0) or 0
    server = getattr(u, "server_tool_use", None)
    if server is not None:
        total["web_searches"] += getattr(server, "web_search_requests", 0) or 0
    return total


def cost_usd(usage: Usage, price_in: float | None, price_out: float | None,
             price_search: float | None) -> float | None:
    if price_in is None or price_out is None:
        return None
    cost = usage["input_tokens"] / 1e6 * price_in + usage["output_tokens"] / 1e6 * price_out
    if price_search is not None:
        cost += usage["web_searches"] / 1000 * price_search
    return round(cost, 4)


_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    return _client
