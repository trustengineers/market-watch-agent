"""Node 1: run web searches and collect raw results as candidates.

Claude decides the exact queries (seeded by Settings.queries) and runs them with the
server-side web search tool. We keep the structured results, not Claude's prose, so
every later step works from real URLs.
"""
from __future__ import annotations

import json

from ..deps import FIXTURES, Deps
from ..llm import add_usage, client, new_usage
from ..state import AgentState, Candidate

MAX_CONTINUATIONS = 3

PROMPT = """Today is {date} (US Eastern). Find news published in the last {hours} hours
about the US remote job market. Run separate searches; start from these and adapt:
{queries}

Prefer original sources (company announcements, BLS, major outlets) over listicles.
Skip evergreen "how to find a remote job" content. When you are done searching,
reply with the single word DONE."""


def search(state: AgentState, deps: Deps) -> dict:
    if state.get("dry_run"):
        data = json.loads((FIXTURES / "candidates.json").read_text())
        return {"candidates": data, "usage": new_usage()}

    s = deps.settings
    usage = new_usage()
    messages: list[dict] = [{
        "role": "user",
        "content": PROMPT.format(
            date=state["run_date"], hours=s.window_hours,
            queries="\n".join(f"- {q}" for q in s.queries),
        ),
    }]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": s.max_searches}]

    candidates: list[Candidate] = []
    for _ in range(MAX_CONTINUATIONS):
        resp = client().messages.create(model=s.model, max_tokens=2048, messages=messages, tools=tools)
        add_usage(usage, resp)
        for block in resp.content:
            if block.type != "web_search_tool_result" or not isinstance(block.content, list):
                continue  # error results arrive as a single object, not a list
            for r in block.content:
                candidates.append({"url": r.url, "title": r.title, "page_age": getattr(r, "page_age", None)})
        # Long server-tool turns can pause; hand the turn back so Claude can finish.
        if resp.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})

    return {"candidates": candidates, "usage": usage}
