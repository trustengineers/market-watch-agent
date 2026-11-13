from datetime import datetime, timezone

from market_watch.config import Settings
from market_watch.deps import Deps
from market_watch.freshness import age_hours
from market_watch.memory import Memory, normalize_url
from market_watch.nodes.dedupe import dedupe
from market_watch.nodes.deliver import render
from market_watch.nodes.validate import sanitize, validate_brief
from market_watch.main import run

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
URLS = ["https://a.com/1", "https://b.com/2", "https://c.com/3"]


def good_brief():
    return {
        "nothing_new": False,
        "items": [{"headline": f"H{i}", "detail": "Plain detail.", "url": u} for i, u in enumerate(URLS)],
        "why_it_matters": "It matters.",
        "action": "Do one thing.",
    }


def deps():
    return Deps(settings=Settings(), memory=Memory(":memory:"))


# --- memory ------------------------------------------------------------------

def test_normalize_url_strips_tracking_www_slash_fragment():
    assert normalize_url("https://WWW.Site.com/a/?utm_source=x&id=7#top") == "https://site.com/a?id=7"


def test_seen_urls_are_filtered_on_the_next_run():
    d = deps()
    d.memory.mark_sent([("https://site.com/story?utm_medium=email", "Story")], "2026-11-12")
    out = dedupe({"candidates": [{"url": "https://www.site.com/story/", "title": "Story", "page_age": "2 hours ago"}]}, d, NOW)
    assert out["fresh"] == []


# --- freshness ---------------------------------------------------------------

def test_age_parsing():
    assert age_hours("5 hours ago", NOW) == 5
    assert age_hours("2 days ago", NOW) == 48
    assert age_hours("Today", NOW) == 0
    assert age_hours("November 13, 2026", NOW) == 0
    assert age_hours("someday", NOW) is None


def test_dedupe_drops_stale_and_duplicates_keeps_unknown_age():
    import json
    from market_watch.deps import FIXTURES
    cands = json.loads((FIXTURES / "candidates.json").read_text())
    fresh = dedupe({"candidates": cands}, deps(), NOW)["fresh"]
    titles = [c["title"] for c in fresh]
    assert len(fresh) == 4
    assert not any("duplicate" in t for t in titles)
    assert not any("2025" in t for t in titles)
    assert any(c["page_age"] is None for c in fresh)


# --- validation --------------------------------------------------------------

def test_good_brief_passes():
    assert validate_brief(good_brief(), URLS) == []


def test_invented_url_fails():
    b = good_brief()
    b["items"][0]["url"] = "https://made-up.com/x"
    assert any("not one of the candidates" in e for e in validate_brief(b, URLS))


def test_em_dash_and_item_count_fail():
    b = good_brief()
    b["action"] = "Do this — now."
    b["items"] = b["items"][:2]
    errors = validate_brief(b, URLS)
    assert any("em dash" in e for e in errors)
    assert any("Need 3 to 6" in e for e in errors)


def test_sanitize_removes_bad_urls_and_dashes():
    b = good_brief()
    b["items"][0]["url"] = "https://made-up.com/x"
    b["why_it_matters"] = "A — B"
    s = sanitize(b, URLS)
    assert len(s["items"]) == 2 and "—" not in s["why_it_matters"]


def test_render_nothing_new():
    assert "Nothing meaningful" in render({"nothing_new": True, "items": []}, "2026-11-13")


# --- end to end --------------------------------------------------------------

def test_dry_run_end_to_end():
    state = run(dry_run=True)
    assert state["delivered_to"] == ["stdout"]
    assert state["rendered"].startswith("Remote Job Market |")
    assert state["errors"] == []
