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

Completed Stage 2 foundations:

- Structured security-universe configuration.
- Expanded Atlas Universe v1.3 with 56 securities across AI infrastructure, cloud/software, defense, cybersecurity, robotics, and ETFs.
- Sector, category, notes, and structured company-profile metadata.
- Atlas Scoring Engine v1 weighted rankings.
- Hybrid v3 scoring with automatically calculated Growth, Quality, and Momentum.
- Local SEC Company Facts caching in `data_cache/sec/` for faster and more resilient runs.
- Upcoming earnings tracking with local Nasdaq calendar caching in `data_cache/earnings/`.
- Auditable annual revenue and net-income Growth measurements from SEC filings.
- Auditable net-margin, operating cash-flow margin, and free-cash-flow margin Quality measurements.
- Auditable 1-month, 3-month, and 6-month Momentum measurements.
- Company Profile Highlights, Upcoming Earnings, Automated Growth, Automated Quality, and Automated Momentum report sections.
- Scoring Summary in Markdown and HTML reports.
- Structured historical research snapshots.
- Research Memory comparison in Markdown and HTML reports.
- Validation and unit tests for universe and scores.

Recommended next Stage 2 task:

Continue expanding the universe toward the 100-150 security target, then begin analyst-rating-change tracking.

## Useful Files

- `ROADMAP.md`: long-term Atlas development roadmap.
- `PROJECT_BRIEF.md`: project vision and constraints.
- `AGENTS.md`: Codex working instructions.
- `app/email_delivery.py`: optional email delivery and `.env` loading.
- `app/earnings_calendar.py`: Nasdaq earnings-calendar retrieval and local caching.
- `app/growth.py`: SEC filing measurement and automated Growth scoring.
- `data_cache/sec/`: ignored local cache for SEC ticker maps and Company Facts payloads.
- `data_cache/earnings/`: ignored local cache for Nasdaq earnings-calendar payloads.
- `app/market_data.py`: market data retrieval and fallback behavior.
- `app/momentum.py`: automated return measurement and Momentum scoring.
- `app/quality.py`: SEC filing profitability and cash-generation Quality scoring.
- `app/report_generator.py`: Markdown and HTML report generation.
- `data/security_universe.json`: company profiles and manual seed scores.
- `main.py`: daily report execution flow.
- `scripts/run_atlas_daily.ps1`: scheduled runner.
- `scripts/setup_windows_scheduled_task.ps1`: Windows Scheduled Task setup.
