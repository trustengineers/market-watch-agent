"""Node 4: deterministic checks on the brief. Failures loop back to summarize once.

These same functions power the evals, so production and evaluation share one definition
of "good".
"""
from __future__ import annotations

from ..deps import Deps
from ..memory import normalize_url
from ..state import AgentState, Brief

EM_DASH = "—"
MAX_WORDS = 250
MIN_ITEMS, MAX_ITEMS = 3, 6
MAX_ATTEMPTS = 2


def brief_text(brief: Brief) -> str:
    parts = [f"{i['headline']} {i['detail']}" for i in brief.get("items", [])]
    parts += [brief.get("why_it_matters", ""), brief.get("action", "")]
    return " ".join(parts)


def validate_brief(brief: Brief, allowed_urls: list[str]) -> list[str]:
    errors: list[str] = []
    items = brief.get("items", [])
    allowed = {normalize_url(u) for u in allowed_urls}

    if brief.get("nothing_new"):
        if items:
            errors.append("nothing_new is true but items is not empty.")
        return errors

    if not MIN_ITEMS <= len(items) <= MAX_ITEMS:
        errors.append(f"Need {MIN_ITEMS} to {MAX_ITEMS} items, got {len(items)}.")
    for i, item in enumerate(items, 1):
        if normalize_url(item.get("url", "")) not in allowed:
            errors.append(f"Item {i} url is not one of the candidates: {item.get('url')}")
    urls = [normalize_url(i.get("url", "")) for i in items]
    if len(urls) != len(set(urls)):
        errors.append("Two items share the same url.")
    text = brief_text(brief)
    if EM_DASH in text:
        errors.append("Contains an em dash.")
    if len(text.split()) > MAX_WORDS:
        errors.append(f"Too long: {len(text.split())} words, limit {MAX_WORDS}.")
    if not brief.get("why_it_matters", "").strip():
        errors.append("why_it_matters is empty.")
    if not brief.get("action", "").strip():
        errors.append("action is empty.")
    return errors


def sanitize(brief: Brief, allowed_urls: list[str]) -> Brief:
    """Last resort after MAX_ATTEMPTS: keep only items with real URLs, strip em dashes."""
    allowed = {normalize_url(u) for u in allowed_urls}
    items = [i for i in brief.get("items", []) if normalize_url(i.get("url", "")) in allowed]

    def fix(s: str) -> str:
        return s.replace(f" {EM_DASH} ", ", ").replace(EM_DASH, ", ")

    items = [{**i, "headline": fix(i["headline"]), "detail": fix(i["detail"])} for i in items]
    return {
        "nothing_new": not items,
        "items": items,
        "why_it_matters": fix(brief.get("why_it_matters", "")),
        "action": fix(brief.get("action", "")),
    }


def validate(state: AgentState, deps: Deps) -> dict:
    allowed = [c["url"] for c in state.get("fresh", [])]
    errors = validate_brief(state["brief"], allowed)
    if errors and state.get("attempts", 0) >= MAX_ATTEMPTS:
        return {"brief": sanitize(state["brief"], allowed), "errors": []}
    return {"errors": errors}
