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
- Stage 5 paper trading must remain strictly simulated and local.
- Paper-trading approval or execution must never transmit a real order.
- Future web accounts must enforce server-side authorization and strict tenant isolation.
- Do not enable public registration until authentication, privacy, backup, monitoring, and security controls are validated.

## Repository notes

- `logs/` and `reports/` are generated folders and should remain ignored by Git.

## Development priorities

1. Preserve reliable daily and weekly reporting.
2. Preserve research-task and owner-review workflows.
3. Evaluate paper recommendations against SPY and QQQ.
4. Expand paper-trading attribution and risk-rule testing.
5. Do not add brokerage integration without explicit owner approval.

## Web platform direction

- Read `WEB_PLATFORM_PLAN.md` before web-platform work.
- Build the website incrementally without disrupting the research and paper-evaluation engine.
- Start with a read-only local owner dashboard.
- Use modern, responsive, accessible financial-workspace design with meaningful charts.
- Reuse stable Python research modules behind service boundaries rather than rewriting them for presentation.
- Keep web-platform maturity separate from trading authority.
- Use managed authentication and secret storage for hosted environments.
- Treat every user-owned record as tenant-scoped and test that users cannot access one another's data.

## Development guidance

- Always run `py -3.12 main.py` after meaningful changes.
- Keep the code simple and runnable locally.
- Do not add trading capability unless Joe explicitly approves it.
