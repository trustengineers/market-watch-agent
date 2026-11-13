"""Shared graph state. Every node reads from and writes to this dict."""
from __future__ import annotations

from typing import TypedDict


class Candidate(TypedDict):
    url: str
    title: str
    page_age: str | None


class BriefItem(TypedDict):
    headline: str
    detail: str
    url: str


class Brief(TypedDict, total=False):
    nothing_new: bool
    items: list[BriefItem]
    why_it_matters: str
    action: str


class Usage(TypedDict):
    input_tokens: int
    output_tokens: int
    web_searches: int


class AgentState(TypedDict, total=False):
    run_date: str              # YYYY-MM-DD, US Eastern
    dry_run: bool
    candidates: list[Candidate]  # raw search results
    fresh: list[Candidate]       # after dedup + freshness filter
    brief: Brief
    errors: list[str]            # validation errors from the last attempt
    attempts: int
    rendered: str                # final message text
    delivered_to: list[str]
    usage: Usage
