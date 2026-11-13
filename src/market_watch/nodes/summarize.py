"""Node 3: pick what matters and write the brief, as structured output.

A forced tool call gives us JSON we can validate instead of free text we'd have to parse.
"""
from __future__ import annotations

import json

from ..deps import Deps
from ..llm import add_usage, client
from ..state import AgentState, Brief

BRIEF_TOOL = {
    "name": "submit_brief",
    "description": "Submit the daily market brief.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nothing_new": {"type": "boolean", "description": "True if no candidate is genuinely new and meaningful."},
            "items": {
                "type": "array",
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "headline": {"type": "string", "description": "Short bold lead, under 10 words."},
                        "detail": {"type": "string", "description": "One or two plain-language sentences."},
                        "url": {"type": "string", "description": "Exactly one URL copied from the candidates."},
                    },
                    "required": ["headline", "detail", "url"],
                },
            },
            "why_it_matters": {"type": "string"},
            "action": {"type": "string"},
        },
        "required": ["nothing_new", "items", "why_it_matters", "action"],
    },
}

PROMPT = """Today is {date} (US Eastern). Below are search results from the last {hours} hours.
Write a brief for this reader: {profile}

Rules:
- Pick 3 to 6 items that are genuinely new and matter for the reader. Fewer good items beat padding.
- If none qualify, set nothing_new to true and leave items empty.
- Each item's url must be copied exactly from the candidates. Never invent a link.
- Ignore results whose page_age shows they are older than the window, and evergreen guides.
- Paraphrase. No quotes longer than 15 words.
- why_it_matters: 1 to 2 sentences, specific to the reader.
- action: one concrete step they can take today.
- Whole brief under 250 words. Never use the em dash character.
{feedback}
Candidates (JSON):
{candidates}"""


def summarize(state: AgentState, deps: Deps) -> dict:
    attempts = state.get("attempts", 0) + 1
    fresh = state.get("fresh", [])

    if state.get("dry_run"):
        return {"brief": _dry_brief(fresh), "attempts": attempts}

    s = deps.settings
    errors = state.get("errors") or []
    feedback = ""
    if errors:
        feedback = "\nYour previous draft failed these checks; fix them:\n" + "\n".join(f"- {e}" for e in errors) + "\n"

    resp = client().messages.create(
        model=s.model,
        max_tokens=2048,
        tools=[BRIEF_TOOL],
        tool_choice={"type": "tool", "name": "submit_brief"},
        messages=[{"role": "user", "content": PROMPT.format(
            date=state["run_date"], hours=s.window_hours, profile=s.profile,
            feedback=feedback, candidates=json.dumps(fresh, indent=1),
        )}],
    )
    usage = add_usage(dict(state["usage"]), resp)
    brief: Brief = next(b.input for b in resp.content if b.type == "tool_use")
    return {"brief": brief, "attempts": attempts, "usage": usage}


def _dry_brief(fresh: list) -> Brief:
    """Deterministic brief for --dry-run, so the pipeline runs with no API key."""
    items = [{"headline": c["title"][:60], "detail": "Fixture item for a dry run.", "url": c["url"]}
             for c in fresh[:3]]
    return {
        "nothing_new": not items,
        "items": items,
        "why_it_matters": "Dry run: this text is a placeholder.",
        "action": "Set ANTHROPIC_API_KEY and run without --dry-run.",
    }
