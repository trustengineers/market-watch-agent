# Market Watch Agent

An autonomous research agent that sends a daily brief on the US remote job market.
It searches the web, remembers what it already sent, writes a short brief for a
specific reader, checks its own output, and delivers it to Telegram or Slack.

Built with **LangGraph** and the **Claude API** (server-side web search, structured output via forced tool calls).

## How it works

```
START -> search -> dedupe --(nothing new)--> deliver -> record -> END
                     |
                     v
                 summarize <-> validate   (one retry with the failed checks as feedback)
                                  |
                                  v
                               deliver
```

| Node | What it does | Why it matters |
|---|---|---|
| `search` | Claude runs several web searches; we keep the raw results (URL, title, age), not its prose | Every later step works from real URLs |
| `dedupe` | Drops URLs already sent (SQLite memory), stale results and duplicates | No repeated news day to day |
| `summarize` | Claude picks 3 to 6 items and writes the brief through a forced `submit_brief` tool call | Output is JSON we can check, not free text |
| `validate` | Deterministic checks: every link came from the search results, 3 to 6 items, under 250 words, no em dashes | Catches invented links before they reach you |
| `deliver` | Renders plain text, sends to Telegram and/or Slack, always prints to stdout | |
| `record` | Marks sent URLs as seen, logs tokens, searches and cost | Feeds dedup and evals |

If validation still fails after the retry, the brief is sanitized (bad links removed) instead of failing the run.

## Quick start

```bash
pip install -e ".[dev]"
market-watch run --dry-run      # fixtures only: no API key, no memory writes
pytest -q                       # 11 tests, including the live path with a mocked client

cp .env.example .env            # add ANTHROPIC_API_KEY, optionally Telegram/Slack
market-watch run                # real run
market-watch history            # recent runs: candidates, retries, searches, tokens, cost
python evals/run_evals.py       # score the run history
```

## Evals

`evals/run_evals.py` scores the last N real runs and exits non-zero when a threshold fails:

| Metric | Threshold | Meaning |
|---|---|---|
| `first_pass_rate` | >= 0.7 | Share of first drafts that passed validation |
| `format_ok_rate` | 1.0 | Every sent brief meets the format rules |
| `repeat_urls` | 0 | No URL sent on two different days |

Also reported: average items, searches and cost per run.

## Scheduling

`.github/workflows/daily.yml` runs the agent every day at 12:37 UTC and keeps the SQLite memory
between runs with the Actions cache. Add these repository secrets: `ANTHROPIC_API_KEY`, and
`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` and/or `SLACK_WEBHOOK_URL`.

The cache can be evicted after 7 days without use. For memory that never resets, run it on a small
VPS with cron, or point `MW_DB_PATH` at a persistent volume.

## Customizing

Edit `src/market_watch/config.py`:
- `profile`: who the brief is written for.
- `queries`: the starting searches.
- `MW_WINDOW_HOURS`, `MW_MAX_SEARCHES`, `MW_MODEL` in `.env`.

Cost tracking: set the `MW_PRICE_*` variables from the current Anthropic pricing page; otherwise only token and search counts are logged.

## Project layout

```
src/market_watch/
  graph.py         LangGraph wiring
  nodes/           search, dedupe, summarize, validate, deliver
  memory.py        SQLite: seen URLs + run log
  freshness.py     parses "5 hours ago" / "November 12, 2026"
  llm.py           client, usage and cost accounting
  config.py        settings, reader profile, seed queries
evals/run_evals.py
tests/
fixtures/candidates.json
```

## Roadmap

- [ ] Next.js dashboard reading the run log (history, cost chart, sent items)
- [ ] MCP server exposing `get_latest_brief` and `search_history` so other agents can use it
- [ ] LLM-as-judge eval for relevance to the reader profile
- [ ] Per-reader profiles (multiple subscribers)
