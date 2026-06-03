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
- Sector, category, notes, and structured company-profile metadata.
- Atlas Scoring Engine v1 weighted rankings.
- Hybrid v2 scoring with automatically calculated Growth and Momentum.
- Auditable annual revenue and net-income Growth measurements from SEC filings.
- Auditable 1-month, 3-month, and 6-month Momentum measurements.
- Company Profile Highlights, Automated Growth, and Automated Momentum report sections.
- Scoring Summary in Markdown and HTML reports.
- Structured historical research snapshots.
- Research Memory comparison in Markdown and HTML reports.
- Validation and unit tests for universe and scores.

Recommended next Stage 2 task:

Begin automating Quality with measurable financial data, then expand the security universe.

## Useful Files

- `ROADMAP.md`: long-term Atlas development roadmap.
- `PROJECT_BRIEF.md`: project vision and constraints.
- `AGENTS.md`: Codex working instructions.
- `app/email_delivery.py`: optional email delivery and `.env` loading.
- `app/growth.py`: SEC filing measurement and automated Growth scoring.
- `app/market_data.py`: market data retrieval and fallback behavior.
- `app/momentum.py`: automated return measurement and Momentum scoring.
- `app/report_generator.py`: Markdown and HTML report generation.
- `data/security_universe.json`: company profiles and manual seed scores.
- `main.py`: daily report execution flow.
- `scripts/run_atlas_daily.ps1`: scheduled runner.
- `scripts/setup_windows_scheduled_task.ps1`: Windows Scheduled Task setup.
