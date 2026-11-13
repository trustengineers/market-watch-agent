"""Exercise the real (non dry-run) code paths with a fake Anthropic client."""
from types import SimpleNamespace as NS

import market_watch.nodes.search as search_mod
import market_watch.nodes.summarize as summarize_mod
from market_watch.config import Settings
from market_watch.deps import Deps
from market_watch.graph import build_graph
from market_watch.memory import Memory

URLS = ["https://a.com/1", "https://b.com/2", "https://c.com/3"]


def usage(searches=0):
    return NS(input_tokens=100, output_tokens=20, server_tool_use=NS(web_search_requests=searches))


def block(type_, **kw):
    return NS(type=type_, model_dump=lambda: {"type": type_}, **kw)


class FakeClient:
    """First search call pauses, second finishes; summarize first returns a bad brief."""

    def __init__(self):
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if "tool_choice" in kw:  # summarize
            bad = len([c for c in self.calls if "tool_choice" in c]) == 1
            urls = ["https://invented.com/x", *URLS[1:]] if bad else URLS
            brief = {"nothing_new": False, "why_it_matters": "W.", "action": "A.",
                     "items": [{"headline": "H", "detail": "D.", "url": u} for u in urls]}
            return NS(content=[block("tool_use", input=brief)], usage=usage(), stop_reason="tool_use")
        first = len(self.calls) == 1
        results = [NS(url=u, title=f"T{i}", page_age="3 hours ago") for i, u in enumerate(URLS)]
        content = [
            block("server_tool_use"),
            block("web_search_tool_result", content=results[:2] if first else results[2:]),
            block("web_search_tool_result", content=NS(error_code="too_many_requests")),
        ]
        return NS(content=content, usage=usage(searches=2), stop_reason="pause_turn" if first else "end_turn")


def test_live_graph_with_retry(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(search_mod, "client", lambda: fake)
    monkeypatch.setattr(summarize_mod, "client", lambda: fake)

    memory = Memory(":memory:")
    graph = build_graph(Deps(settings=Settings(), memory=memory))
    state = graph.invoke({"run_date": "2026-11-13", "dry_run": False, "attempts": 0})

    assert len(state["candidates"]) == 3            # pause_turn continued, error block skipped
    assert state["attempts"] == 2                   # invented URL triggered one retry
    assert state["errors"] == []
    assert state["usage"]["web_searches"] == 4
    assert "Your previous draft failed" in fake.calls[-1]["messages"][0]["content"]
    assert all(memory.is_seen(u) for u in URLS)     # recorded for tomorrow's dedup
    assert memory.runs()[0]["attempts"] == 2
