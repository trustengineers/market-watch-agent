"""Node 5: render the brief, send it, and record what was sent."""
from __future__ import annotations

import httpx

from ..deps import Deps
from ..llm import cost_usd
from ..state import AgentState, Brief


def render(brief: Brief, run_date: str) -> str:
    title = f"Remote Job Market | {run_date}"
    if brief.get("nothing_new") or not brief.get("items"):
        return f"{title}\n\nNothing meaningful is new today."
    lines = [title, "", "What's new"]
    for i in brief["items"]:
        lines.append(f"- {i['headline']}: {i['detail']} {i['url']}")
    lines += ["", "Why it matters for you", brief["why_it_matters"], "", "One action", brief["action"]]
    return "\n".join(lines)


def _send_telegram(token: str, chat_id: str, text: str) -> None:
    # Plain text: no parse_mode, so URLs and punctuation never need escaping.
    r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage",
                   json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=20)
    r.raise_for_status()


def _send_slack(webhook: str, text: str) -> None:
    httpx.post(webhook, json={"text": text}, timeout=20).raise_for_status()


def deliver(state: AgentState, deps: Deps) -> dict:
    s = deps.settings
    text = render(state.get("brief") or {"nothing_new": True}, state["run_date"])
    delivered = ["stdout"]
    print(text)

    if not state.get("dry_run"):
        if s.telegram_token and s.telegram_chat_id:
            _send_telegram(s.telegram_token, s.telegram_chat_id, text)
            delivered.append("telegram")
        if s.slack_webhook:
            _send_slack(s.slack_webhook, text)
            delivered.append("slack")
    return {"rendered": text, "delivered_to": delivered}


def record(state: AgentState, deps: Deps) -> dict:
    """Mark sent URLs as seen and log the run. Dry runs change nothing."""
    if state.get("dry_run"):
        return {}
    brief = state.get("brief") or {}
    sent = [(i["url"], i["headline"]) for i in brief.get("items", [])]
    deps.memory.mark_sent(sent, state["run_date"])
    s = deps.settings
    deps.memory.log_run(state, cost_usd(state["usage"], s.price_in, s.price_out, s.price_search))
    return {}
