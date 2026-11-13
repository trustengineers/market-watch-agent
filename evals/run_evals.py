"""Score the agent's real output history.

Usage:  python evals/run_evals.py [--db data/market_watch.db] [-n 30]

Metrics, computed over the last N logged runs:
  first_pass_rate   share of runs whose first draft passed validation (attempts == 1)
  format_ok_rate    share of sent briefs with 3-6 items (or nothing_new), no em dash, <= 250 words
  repeat_urls       URLs sent on more than one day; dedup memory should keep this at 0
  avg_items         items per brief
  avg_searches      web searches per run
  avg_cost_usd      only when pricing env vars are set
Exit code 1 if any threshold fails, so CI can gate on it.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from market_watch.memory import Memory, normalize_url  # noqa: E402
from market_watch.nodes.validate import EM_DASH, MAX_WORDS, brief_text  # noqa: E402

THRESHOLDS = {"first_pass_rate": 0.7, "format_ok_rate": 1.0, "repeat_urls": 0}


def format_ok(brief: dict) -> bool:
    items = brief.get("items", [])
    if brief.get("nothing_new"):
        return not items
    text = brief_text(brief)
    return 3 <= len(items) <= 6 and EM_DASH not in text and len(text.split()) <= MAX_WORDS


def score(runs: list[dict]) -> dict:
    briefs = [json.loads(r["brief_json"] or "{}") for r in runs]
    url_days = Counter()
    for r, b in zip(runs, briefs):
        for u in {normalize_url(i["url"]) for i in b.get("items", [])}:
            url_days[u] += 1
    costs = [r["cost_usd"] for r in runs if r["cost_usd"] is not None]
    n = len(runs)
    return {
        "runs": n,
        "first_pass_rate": round(sum(r["attempts"] == 1 for r in runs) / n, 2),
        "format_ok_rate": round(sum(format_ok(b) for b in briefs) / n, 2),
        "repeat_urls": sum(1 for c in url_days.values() if c > 1),
        "avg_items": round(sum(len(b.get("items", [])) for b in briefs) / n, 1),
        "avg_searches": round(sum(r["web_searches"] or 0 for r in runs) / n, 1),
        "avg_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/market_watch.db")
    ap.add_argument("-n", type=int, default=30)
    args = ap.parse_args()

    runs = Memory(args.db).runs(args.n)
    if not runs:
        print("No runs logged yet. Run the agent first.")
        return 0
    result = score(runs)
    print(json.dumps(result, indent=2))

    failed = [
        k for k, limit in THRESHOLDS.items()
        if (result[k] > limit if k == "repeat_urls" else result[k] < limit)
    ]
    if failed:
        print(f"FAILED thresholds: {', '.join(failed)}")
        return 1
    print("All thresholds passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
