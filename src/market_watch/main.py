"""CLI entry point: `market-watch run [--dry-run]` and `market-watch history`."""
from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Settings
from .deps import Deps
from .graph import build_graph
from .memory import Memory


def _load_dotenv(path: str = ".env") -> None:
    """Tiny .env loader so there is no extra dependency."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def run(dry_run: bool = False) -> dict:
    settings = Settings()
    memory = Memory(":memory:" if dry_run else settings.db_path)
    graph = build_graph(Deps(settings=settings, memory=memory))
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    return graph.invoke({"run_date": today, "dry_run": dry_run, "attempts": 0})


def history(limit: int) -> None:
    for r in Memory(Settings().db_path).runs(limit):
        cost = f"${r['cost_usd']:.4f}" if r["cost_usd"] is not None else "n/a"
        print(f"{r['run_date']}  candidates={r['candidates']:>3}  fresh={r['fresh']:>3}  "
              f"attempts={r['attempts']}  searches={r['web_searches']}  "
              f"tokens={r['input_tokens']}/{r['output_tokens']}  cost={cost}")


def cli() -> None:
    _load_dotenv()
    parser = argparse.ArgumentParser(prog="market-watch")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_run = sub.add_parser("run", help="Run the agent once")
    p_run.add_argument("--dry-run", action="store_true", help="Use fixtures, no API calls, no memory writes")
    p_hist = sub.add_parser("history", help="Show recent runs and their cost")
    p_hist.add_argument("-n", type=int, default=14)
    args = parser.parse_args()

    if args.cmd == "run":
        state = run(dry_run=args.dry_run)
        u = state.get("usage", {})
        print(f"\n[run] fresh={len(state.get('fresh', []))} attempts={state.get('attempts')} "
              f"searches={u.get('web_searches', 0)} delivered_to={state.get('delivered_to')}")
    else:
        history(args.n)


if __name__ == "__main__":
    cli()
