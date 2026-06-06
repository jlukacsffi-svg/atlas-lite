# Atlas Lite Handoff

Last updated: 2026-06-02

## Current Roadmap Position

Stage 1: Reliable Daily Briefing is complete.

Atlas Lite now:

- Retrieves reliable market data.
- Tries yfinance first and falls back to Yahoo Finance.
- Disables yfinance for the rest of a run after repeated failures.
- Generates Markdown and HTML Morning Executive Brief reports.
- Produces a rule-based Executive Summary that interprets market tone, sector strength, priority names, catalysts, risks, and volatility.
- Adds News Highlights for major movers.
- Identifies opportunities and risks.
- Supports Windows scheduled execution.
- Sends reports by email through a dedicated Gmail sender account.
- Sends weekly research summaries by email when email delivery is enabled.

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

## Current Development Phase

Stage 3: Portfolio Intelligence.

Stage 2: Research Memory And Scoring is complete at the foundation level.

Completed Stage 2 foundations:

- Structured security-universe configuration.
- Expanded Atlas Universe v1.5 with 100 securities across AI infrastructure, AI power, cloud/software, defense, cybersecurity, robotics, healthcare, financials, consumer platforms, and ETFs.
- Sector, category, notes, and structured company-profile metadata.
- Atlas Scoring Engine v1 weighted rankings.
- Sector Scorecard and catalyst-aware Atlas Priority Ranking.
- Conservative Watchlist Change Recommendations for category review.
- Executive Summary integrates sector scores, priority rankings, earnings, analyst actions, insider activity, and major price moves.
- Hybrid v3 scoring with automatically calculated Growth, Quality, and Momentum.
- Local SEC Company Facts caching in `data_cache/sec/` for faster and more resilient runs.
- Upcoming earnings tracking with local Nasdaq calendar caching in `data_cache/earnings/`.
- Analyst-action headline tracking with local cache in `data_cache/analyst_actions/`.
- Insider-transaction tracking from SEC Form 4 filings with local cache in `data_cache/insider_transactions/`.
- Auditable annual revenue and net-income Growth measurements from SEC filings.
- Auditable net-margin, operating cash-flow margin, and free-cash-flow margin Quality measurements.
- Auditable 1-month, 3-month, and 6-month Momentum measurements.
- Sector Scorecard, Atlas Priority Ranking, Watchlist Change Recommendations, Company Profile Highlights, Upcoming Earnings, Analyst Actions, Insider Transactions, Automated Growth, Automated Quality, and Automated Momentum report sections.
- Scoring Summary in Markdown and HTML reports.
- Structured historical research snapshots.
- Local research archive index in `research_archive/archive_index.json` and `research_archive/archive_index.md`.
- Weekly research summary generator powered by the local archive index.
- Weekly summary email delivery and Windows weekly scheduled-task helpers.
- Weekly summary Key Changes and Sector Trend Shifts sections.
- Weekly "What Changed This Week" narrative section.
- Weekly Research Action Prompts section for research-only follow-up tasks.
- Research Memory comparison in Markdown and HTML reports.
- Validation and unit tests for universe and scores.

Stage 3 portfolio-intelligence foundations completed:

- Optional local `data/portfolio.json` support.
- Safe committed template at `data/portfolio.example.json`.
- Portfolio market value, estimated daily change, benchmark context, position exposure, sector exposure, and risk-alert reporting.
- `portfolio_check.py` validates local portfolio structure before daily use.
- Local portfolio history snapshots in ignored `portfolio_history/`.
- Real portfolio file is ignored by Git.

Recommended next Stage 3 task:

Create the local `data/portfolio.json` file when Joe is ready to add real holdings. After that, run `py -3.12 portfolio_check.py`, then run `py -3.12 main.py` to generate the first portfolio-aware brief. If Joe wants to wait on real holdings, the next software step is Stage 4 planning for a lightweight research task queue and agent-role boundaries.

Stage 4 planning artifact:

- `STAGE4_PLAN.md` defines the first lightweight multi-agent research organization path.
- Recommended first Stage 4 build: local ignored `research_tasks/` queue before autonomous agents.

## Useful Files

- `ROADMAP.md`: long-term Atlas development roadmap.
- `STAGE4_PLAN.md`: first Stage 4 multi-agent research organization plan.
- `PROJECT_BRIEF.md`: project vision and constraints.
- `AGENTS.md`: Codex working instructions.
- `app/analyst_actions.py`: analyst-action headline retrieval and local caching.
- `app/email_delivery.py`: optional email delivery and `.env` loading.
- `app/earnings_calendar.py`: Nasdaq earnings-calendar retrieval and local caching.
- `app/growth.py`: SEC filing measurement and automated Growth scoring.
- `app/insider_transactions.py`: SEC Form 4 retrieval, XML parsing, and local caching.
- `data_cache/analyst_actions/`: ignored local cache for analyst-action headline payloads.
- `data_cache/sec/`: ignored local cache for SEC ticker maps and Company Facts payloads.
- `data_cache/earnings/`: ignored local cache for Nasdaq earnings-calendar payloads.
- `data_cache/insider_transactions/`: ignored local cache for SEC submissions and Form 4 XML.
- `app/market_data.py`: market data retrieval and fallback behavior.
- `app/momentum.py`: automated return measurement and Momentum scoring.
- `app/portfolio.py`: optional local portfolio loading and exposure analysis.
- `portfolio_check.py`: local portfolio validation command.
- `app/quality.py`: SEC filing profitability and cash-generation Quality scoring.
- `app/report_generator.py`: Markdown and HTML report generation.
- `app/weekly_summary.py`: weekly summary generation from the local research archive index.
- `data/security_universe.json`: company profiles and manual seed scores.
- `main.py`: daily report execution flow.
- `weekly_summary.py`: command-line entry point for weekly summaries.
- `scripts/run_atlas_daily.ps1`: scheduled runner.
- `scripts/run_atlas_weekly.ps1`: weekly summary scheduled runner.
- `scripts/setup_windows_scheduled_task.ps1`: Windows Scheduled Task setup.
- `scripts/setup_windows_weekly_summary_task.ps1`: Windows Weekly Summary Scheduled Task setup.
