# Atlas Lite Agent Instructions

Atlas Lite is the first working prototype of Atlas Capital Research.

It generates Morning Executive Brief markdown reports for a growth-focused stock watchlist.

For broader project context, long-term vision, future autonomy levels, scoring plans, and environment notes, read `PROJECT_BRIEF.md`.

## Current status

- v1.0 works locally.
- Run command: `py -3.12 main.py`

## Data source behavior

- Try `yfinance` first.
- If `yfinance` returns no data, use raw Yahoo Finance chart API fallback.
- Always preserve fallback market-data behavior.

## Current watchlist

- NVDA
- AMD
- AVGO
- TSM
- ARM
- MSFT
- AMZN
- GOOGL
- META
- PLTR
- LMT
- NOC
- RTX
- CRWD
- PANW
- SPY
- QQQ

## Safety rules

- No real trading.
- No brokerage APIs.
- No financial commitments.
- No customer outreach.

## Repository notes

- `logs/` and `reports/` are generated folders and should remain ignored by Git.

## Development priorities

1. Add news headlines explaining major price moves.
2. Add AI-generated executive summary.
3. Add HTML report output.
4. Add scheduled daily execution.
5. Add email delivery.

## Development guidance

- Always run `py -3.12 main.py` after meaningful changes.
- Keep the code simple and runnable locally.
- Do not add trading capability unless Joe explicitly approves it.
