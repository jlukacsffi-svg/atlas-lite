# Atlas Lite Handoff

Last updated: 2026-06-07

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
- Local ignored `research_tasks/` queue started before autonomous agents.
- `research_tasks.py generate` creates reviewable task suggestions from latest archive signals.
- Morning Executive Brief includes a Research Agenda section with open local tasks.
- `research_tasks.py summary` summarizes local tasks by status, role, and priority.
- `research_tasks.py agenda` writes a local Markdown research agenda.
- `research_tasks.py brief --role ROLE` writes a focused CEO, CIO, CRO, or Reporting brief.
- The daily run now creates deduplicated research tasks directly from current market signals.
- The weekly summary creates deduplicated CIO and CRO tasks from multi-run trends.
- Configured portfolio risk alerts create CRO or Reporting tasks.
- Daily and weekly runs refresh the shared agenda and all role briefs.
- Task status updates can append review notes.
- Completed research records a conclusion, recommendation, confidence, and evidence.
- Completed findings enter a separate owner-review queue.
- Owner decisions are recorded without authorizing or executing trades.
- Sector-trend assignments route to a dedicated Sector Analyst role.

Stage 5 paper-trading foundation:

- `STAGE5_PLAN.md` defines the simulated-account safety policy.
- `app/paper_trading.py` manages local simulated cash, positions, and accounting.
- `paper_trading.py` provides initialization, preview, simulated order, status, and ledger commands.
- `paper_trading/` is ignored by Git.
- The append-only JSONL ledger records account initialization and every simulated fill.
- Initial rules prohibit margin, short selling, options, and leverage; enforce cash reserve, position size, and daily trade limits; and require a thesis.
- No brokerage integration or real-order transmission exists.
- Paper recommendations have immutable IDs and can be linked to simulated fills.
- Performance snapshots compare simulated equity with SPY and QQQ.
- Decision audit tracks recommendations, linked fills, realized wins/losses, and win rate.
- `paper_trading.py report` writes a local Markdown evaluation report.
- Daily reports include paper performance after a simulated account is intentionally initialized.
- The local paper account was initialized with $100,000 simulated cash.
- Every simulated fill now requires a separately approved, single-use paper proposal.
- Owner-approved research can create a pending paper proposal, but never an automatic fill.
- `paper_risk_v1` records CRO-style reviews for every pending proposal.
- Hard-hold proposals are automatically rejected by paper policy; caution proposals remain pending.
- The strategy enforces a maximum of three active buy proposals.
- `paper_monitor_v1` records one thesis review per open position per day.
- Weak-score or Avoid holdings create pending exit proposals, never automatic sells.
- Strategy proposals now create and link immutable recommendation records first.
- The daily run refreshes `paper_trading/performance.md`.
- Stage 5 software is complete; the live paper evaluation period is in progress.

Secure web-platform direction:

- `WEB_PLATFORM_PLAN.md` defines the modern dashboard, secure cloud, and multi-user product track.
- The website should become the primary Atlas experience; email remains a notification and report-delivery channel.
- Web Phase 1 is complete: `dashboard.py` serves a read-only local owner dashboard over stable Atlas outputs.
- The dashboard displays market breadth, paper performance, benchmark context, score leaders, movers, sector movement, positions, and research tasks.
- Run it with `py -3.12 dashboard.py`, then open `http://127.0.0.1:8765`.
- The current dashboard is localhost-only and has no public authentication or cloud exposure.
- Later phases add secure cloud hosting, invite-only user accounts, strict tenant isolation, and eventually a controlled customer product.
- Web development must not weaken the research engine or grant additional trading authority.
- Public account creation is prohibited until authentication, authorization, tenant isolation, privacy, backups, monitoring, and incident-response controls are validated.
- Web Phase 2 is approximately 90% complete in `app/web_cloud.py`,
  `cloud_dashboard.py`, `Dockerfile`, and `WEB_PHASE2_PLAN.md`.
- Cloud mode is fail-closed. The personal-project deployment uses Google OpenID
  Connect, an owner-email allowlist, signed short-lived sessions, and explicit
  persistent data storage. Legacy IAP verification remains available for a
  future Google Cloud organization.
- Durable single-owner storage is implemented in `app/cloud_storage.py` using
  an allowlisted Cloud Storage bundle, versioned manifest, SHA-256 checks, atomic
  downloads, and generation-match upload preconditions.
- `ATLAS_DATA_ROOT` now controls all writable runtime state, and a seeded
  disposable-root daily run completed successfully.
- `cloud_daily.py` and `cloud_weekly.py` pull durable state before running and
  push it only after success.
- Google Cloud CLI 571.0.0, user login, and Application Default Credentials
  are configured locally.
- The dedicated `atlas-capital-research-stg` project is linked to
  `My Billing Account` with a `$10` monthly gross-usage budget.
- The private bucket, least-privilege service accounts, Artifact Registry,
  first dashboard image, and scale-to-zero Cloud Run service exist.
- The initial private bundle contains 197 files and passed a checksum-verified
  isolated cloud pull restoration test.
- The Cloud Run container loaded the private bundle and passed its startup
  probe.
- Direct Cloud Run IAP was disabled after official documentation and live
  testing confirmed that personal projects outside a Google Cloud organization
  cannot use it for this owner identity.
- Before the owner OAuth deployment, the service was safely dark and returned
  `403`; no jobs or schedules were active.
- Guarded plan-first scripts cover staging bootstrap, dashboard deployment,
  Cloud Run jobs, schedules, and read-only status.
- Application-level Google OAuth is implemented with signed state, nonce,
  verified ID tokens, verified email, exact owner matching, one-hour signed
  sessions, secure cookies, and logout.
- `scripts/gcp_configure_oauth_secrets.ps1` securely transfers a downloaded
  OAuth web-client JSON to Secret Manager without printing values.
- `scripts/gcp_deploy_staging.ps1` now references Secret Manager and exposes
  only the application-controlled login boundary.
- Google Auth Platform is configured in testing mode with
  `jlukacsffi@gmail.com` as the only test user.
- The `Atlas Owner Dashboard` OAuth web client uses the exact Cloud Run
  callback URI.
- OAuth client credentials and the generated session key are stored in Secret
  Manager; temporary local credential material was deleted.
- Cloud Run revision `atlas-dashboard-stg-00002-bwj` serves the OAuth-enabled
  dashboard at zero minimum and one service-level maximum instance.
- Unauthenticated dashboard access redirects to Google, and `/readyz` returns
  ready without exposing private data.
- The first interactive owner-login completion, monitoring, jobs, schedules,
  and final staging validation remain.
- `scripts/gcp_zero_cost_audit.ps1` preserves the historical pre-activation
  gate and now fails by design. Use `gcp_staging_status.ps1` for active staging.
- Joe reported approximately `$300` of Google Cloud promotional credit and
  approved a minimal-cost direction. The operating target is `$0-$5` per month
  with a `$10` monthly gross-usage alert budget. The credit is believed to
  expire around September 3-4, 2026; the console date remains to be confirmed.
- `CLOUD_COST_ESTIMATE.md` records the expected service costs and review steps.
- Local disaster-recovery tooling now creates private ZIP backups containing
  only the cloud allowlist, verifies all paths, sizes, and SHA-256 checksums,
  and refuses unapproved overwrites.
- A local restoration drill passed, followed by a cloud pull restoration test
  of 197 files and 10,532,703 local bytes.
- Authenticated redeployment, monitoring, scheduled jobs, and final staging
  validation remain.

## Useful Files

- `ROADMAP.md`: long-term Atlas development roadmap.
- `STAGE4_PLAN.md`: first Stage 4 multi-agent research organization plan.
- `STAGE5_PLAN.md`: Stage 5 paper-trading policy and milestones.
- `WEB_PLATFORM_PLAN.md`: secure modern dashboard and multi-user platform plan.
- `WEB_PHASE2_PLAN.md`: secure single-user cloud architecture and deployment gate.
- `GCP_STAGING_SETUP.md`: guarded Google Cloud staging setup and billing gate.
- `app/cloud_storage.py`: private durable artifact synchronization.
- `app/backup_restore.py`: private backup creation, inspection, validation, and
  guarded restoration.
- `backup_restore.py`: backup and restoration-drill command-line entry point.
- `cloud_sync.py`: manual private artifact pull/push command.
- `cloud_daily.py`: cloud daily job wrapper.
- `cloud_weekly.py`: cloud weekly job wrapper.
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
- `app/paper_trading.py`: strictly simulated account and risk-rule engine.
- `paper_trading.py`: Stage 5 paper-account command-line entry point.
- `app/research_tasks.py`: local Stage 4 research task queue.
- `research_tasks.py`: command-line entry point for listing and adding research tasks.
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
