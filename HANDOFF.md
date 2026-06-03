# Atlas Lite Handoff

Last updated: 2026-06-02

## Current Roadmap Position

Stage 1: Reliable Daily Briefing is complete.

Atlas Lite now:

- Retrieves reliable market data.
- Tries yfinance first and falls back to Yahoo Finance.
- Disables yfinance for the rest of a run after repeated failures.
- Generates Markdown and HTML Morning Executive Brief reports.
- Produces a rule-based Executive Summary.
- Adds News Highlights for major movers.
- Identifies opportunities and risks.
- Supports Windows scheduled execution.
- Sends reports by email through a dedicated Gmail sender account.

Dedicated sender account:

```text
atlas.capital.reports@gmail.com
```

Recipient:

```text
jlukacsffi@gmail.com
```

Latest successful live email test:

```text
2026-06-02
[ok] Report email sent.
```

## Important Security Note

Do not paste email passwords or app passwords into chat.

The local `.env` file is ignored by Git and should stay local only.

Never commit `.env`.

## Next Development Phase

Stage 2: Research Memory And Scoring.

Recommended first Stage 2 task:

Design and implement a simple security-universe configuration that supports:

- Ticker.
- Company name.
- Sector.
- Watchlist category: Core, Watchlist, Emerging, or Avoid.
- Optional notes.

After the security universe exists, build Atlas Scoring Engine v1:

- Growth Score: 40%.
- Quality Score: 20%.
- Moat Score: 15%.
- Momentum Score: 15%.
- Risk Score: 10%.

Keep the first scoring version simple, transparent, and reviewable.

## Useful Files

- `ROADMAP.md`: long-term Atlas development roadmap.
- `PROJECT_BRIEF.md`: project vision and constraints.
- `AGENTS.md`: Codex working instructions.
- `app/email_delivery.py`: optional email delivery and `.env` loading.
- `app/market_data.py`: market data retrieval and fallback behavior.
- `app/report_generator.py`: Markdown and HTML report generation.
- `main.py`: daily report execution flow.
- `scripts/run_atlas_daily.ps1`: scheduled runner.
- `scripts/setup_windows_scheduled_task.ps1`: Windows Scheduled Task setup.

