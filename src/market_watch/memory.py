"""SQLite memory: which URLs were already sent, plus every brief and its cost.

This is what keeps the agent from repeating yesterday's news.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

_TRACKING_PREFIXES = ("utm_", "fbclid", "gclid", "mc_", "ref")

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    url_hash TEXT PRIMARY KEY,
    url      TEXT NOT NULL,
    title    TEXT,
    sent_on  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date      TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    candidates    INTEGER,
    fresh         INTEGER,
    attempts      INTEGER,
    brief_json    TEXT,
    rendered      TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    web_searches  INTEGER,
    cost_usd      REAL
);
"""


def normalize_url(url: str) -> str:
    """Lowercase host, drop fragment, tracking params and trailing slash."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith(_TRACKING_PREFIXES)]
    path = parts.path.rstrip("/") or "/"
    host = parts.netloc.lower().removeprefix("www.")
    return urlunsplit((parts.scheme.lower() or "https", host, path, urlencode(query), ""))


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()[:24]


class Memory:
    def __init__(self, db_path: str):
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.executescript(SCHEMA)

    def is_seen(self, url: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM seen WHERE url_hash = ?", (url_hash(url),)).fetchone()
        return row is not None

    def mark_sent(self, urls_titles: list[tuple[str, str]], run_date: str) -> None:
        self.conn.executemany(
            "INSERT OR IGNORE INTO seen (url_hash, url, title, sent_on) VALUES (?, ?, ?, ?)",
            [(url_hash(u), normalize_url(u), t, run_date) for u, t in urls_titles],
        )
        self.conn.commit()

    def log_run(self, state: dict, cost_usd: float | None) -> None:
        usage = state.get("usage", {})
        self.conn.execute(
            """INSERT INTO runs (run_date, created_at, candidates, fresh, attempts, brief_json,
               rendered, input_tokens, output_tokens, web_searches, cost_usd)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                state.get("run_date"),
                datetime.now(timezone.utc).isoformat(),
                len(state.get("candidates", [])),
                len(state.get("fresh", [])),
                state.get("attempts", 0),
                json.dumps(state.get("brief", {})),
                state.get("rendered", ""),
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("web_searches", 0),
                cost_usd,
            ),
        )
        self.conn.commit()

    def runs(self, limit: int = 30) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,))
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
