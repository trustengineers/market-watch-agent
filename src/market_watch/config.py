"""Settings loaded from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _float_or_none(name: str) -> float | None:
    raw = os.getenv(name, "").strip()
    return float(raw) if raw else None


@dataclass(frozen=True)
class Settings:
    model: str = field(default_factory=lambda: os.getenv("MW_MODEL", "claude-opus-5-5"))
    max_searches: int = field(default_factory=lambda: int(os.getenv("MW_MAX_SEARCHES", "8")))
    window_hours: int = field(default_factory=lambda: int(os.getenv("MW_WINDOW_HOURS", "48")))
    db_path: str = field(default_factory=lambda: os.getenv("MW_DB_PATH", "data/market_watch.db"))
    telegram_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    slack_webhook: str = field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))
    price_in: float | None = field(default_factory=lambda: _float_or_none("MW_PRICE_INPUT_PER_MTOK"))
    price_out: float | None = field(default_factory=lambda: _float_or_none("MW_PRICE_OUTPUT_PER_MTOK"))
    price_search: float | None = field(default_factory=lambda: _float_or_none("MW_PRICE_SEARCH_PER_1K"))

    # Who the brief is written for. Edit this to retarget the agent.
    profile: str = (
        "Senior freelance developer based in Argentina (full-stack, AI integration, "
        "3D web: React, Next.js, TypeScript, Three.js, Python, LLM/agent work) "
        "seeking US remote jobs and long-term contracts."
    )

    queries: tuple[str, ...] = (
        "US remote jobs news today",
        "remote work hiring trends this week",
        "return to office mandate announcement",
        "tech layoffs today",
        "remote software developer job market",
        "US companies hiring Latin America developers",
        "BLS jobs report JOLTS release",
    )
