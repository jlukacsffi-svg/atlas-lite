# Atlas Lite Handoff

Last updated: 2026-06-12

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
- Web Phase 2 is approximately 99% complete in `app/web_cloud.py`,
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
- Cloud Run revision `atlas-dashboard-stg-00007-r8c` serves the OAuth-enabled
  dashboard at zero minimum and one service-level maximum instance.
- Unauthenticated dashboard access redirects to Google, and `/readyz` returns
  ready without exposing private data.
- The first interactive owner login completed successfully on June 8, 2026.
  Google sign-in now establishes a signed owner session and opens the live
  dashboard at
  `https://atlas-dashboard-stg-851252682251.us-west1.run.app`.
- OAuth uses PKCE, persists the verifier only in the signed short-lived state
  cookie, and accepts only Google's equivalent basic email-scope aliases.
- The dashboard refreshes the private Cloud Storage bundle on a throttled
  interval and serves last-known data if a refresh fails.
- Automated tests cover non-owner denial, invalid state, nonce, issuer,
  audience, unverified email, session tampering, expiry, and logout.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` are deployed.
- Manual daily execution `atlas-daily-stg-zvt5n` completed successfully in
  3 minutes 42 seconds and published a new private manifest.
- Manual weekly execution `atlas-weekly-stg-wnqhc` completed successfully in
  34 seconds and published a new private manifest.
- Daily and weekly Cloud Scheduler triggers exist and remain paused pending
  separate owner approval.
- Cloud Monitoring now checks `/readyz` every ten minutes from three US
  regions and emails Joe for dashboard unavailability or a failed Atlas job.
- Schedule control is now separately guarded: resume requires explicit cost
  confirmation and recurring-execution approval, plus successful manual jobs
  and configured monitoring.
- Artifact Registry is 524.483 MB across eight recent images. Its retention
  policy is installed in dry-run mode, keeps the three newest images, and
  currently deletes nothing. The measured size is approximately 24.5 MB over
  the included 0.5 GB allowance, an estimated `$0.0025/month` storage overage.
- `scripts/gcp_staging_readiness.ps1` passed all automated cloud security,
  identity, scaling, storage, job, schedule, monitoring, and retention checks.
- Preliminary monitoring covered 21.7 hours with no Cloud Run service or job
  error logs. Regional probe noise under the original 10-second cold-start
  timeout led to a 30-second timeout at unchanged frequency and expected cost.
- The subsequent 23.89-hour validation window passed all 2,592 regional
  samples with 100% measured availability and no Cloud Run error logs.
- Cloud Run revision `atlas-dashboard-stg-00008-9qd` labels the live workspace
  `Secure owner cloud` and provides a visible sign-out link.
- Cross-device validation, manual non-owner validation, and final staging
  review remain. Recurring schedules remain paused by owner policy and are not
  required to close Web Phase 2.
- `FINAL_STAGING_REVIEW.md` and `scripts/gcp_final_staging_review.ps1`
  package the final read-only review and the remaining owner-assisted gates.
- `scripts/gcp_manual_validation.ps1` records the two observed identity checks
  locally without changing Google Cloud, OAuth, IAM, or schedule state.
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
- Authenticated redeployment, manual cloud job validation, and monitoring are
  complete. Cross-device testing, manual non-owner denial, and final staging
  sign-off remain. Schedules stay paused by owner policy.

Estimated overall Atlas program completion: 79%.

## Useful Files

- `ROADMAP.md`: long-term Atlas development roadmap.
- `STAGE4_PLAN.md`: first Stage 4 multi-agent research organization plan.
- `STAGE5_PLAN.md`: Stage 5 paper-trading policy and milestones.
- `WEB_PLATFORM_PLAN.md`: secure modern dashboard and multi-user platform plan.
- `WEB_PHASE3_PLAN.md`: local tenant-isolation foundation and release gates.
- `app/tenant_accounts.py` provides fail-closed provider-subject identity
  resolution, tenant roles and permissions, disabled-account handling, and
  tenant-scoped workspace paths.
- Web Phase 3 is approximately 25% complete. `app/tenant_store.py` adds a
  versioned local SQLite schema and tenant-aware repositories for reports,
  watchlists, portfolios, research tasks, and paper accounts. Composite
  foreign keys and active-membership checks reject cross-tenant or forged
  access. The live cloud service remains owner-only; this milestone is
  local-only and creates no cloud cost.
- Web Phase 3 is approximately 40% complete. Invite administration now uses
  expiring hashed tokens, verified identity binding, guarded role and status
  changes, owner protection, and append-only audit events. The local dashboard
  visibly reports this boundary in its Access & Security panel. No public
  registration, invitation delivery, or cloud account rollout is enabled.
- Web Phase 3 is approximately 55% complete. `app/web_tenant.py` and
  `tenant_dashboard.py` provide a separate localhost-only tenant application
  that re-resolves active membership for every request, checks session claims,
  applies role controls, and tenant-filters every private route. The dashboard
  visibly shows the resolved workspace, role, and account. The live cloud
  service remains owner-only and unchanged.
- Web Phase 3 is approximately 70% complete. `TENANT_THREAT_MODEL.md`,
  `app/tenant_backup.py`, and `tenant_backup.py` add the control matrix,
  consistent SQLite snapshots, checksum/schema/integrity validation, guarded
  isolated restoration, and an automated recovery drill. The preview Access &
  Security panel now shows the threat-model and recovery status. Archives are
  not application-encrypted and must remain in private encrypted-at-rest
  storage.
- Web Phase 3 is approximately 82% complete. Schema version 3 adds audited
  privacy requests. `tenant_privacy.py` and `TenantStore` now provide
  owner-only secret-free tenant exports plus guarded non-owner account
  deletion requests, cancellation, explicit completion confirmation,
  membership removal, and identity pseudonymization. Security audit history
  and tenant-owned records remain intact.
- Web Phase 3 is approximately 92% complete.
  `PRODUCTION_ARCHITECTURE_REVIEW.md`, `config/tenant_production_review.json`,
  and `tenant_readiness.py` select the managed PostgreSQL and identity
  direction while blocking deployment. The expected staging cost is about
  `$15/month`, so no Cloud SQL, Identity Platform, public registration,
  external invitations, or recurring schedules were activated.
- Web Phase 3 is approximately 96% complete. `app/tenant_postgres.py` adds
  native PostgreSQL migrations, a `pg8000` compatibility adapter, transaction
  handling, serialized migrations, and an automatic-IAM Cloud SQL connection
  factory. `tenant_postgres_check.py` validates the full contract offline.
  All 22 migration statements passed PostgreSQL parser validation. No database
  or cloud resource was created.
- Web Phase 3 is approximately 99% complete. Privacy, terms, retention, and
  incident-response drafts are complete, with counsel, market-data licensing,
  and independent-security review scopes assembled in
  `EXTERNAL_REVIEW_PACKET.md`. `governance_check.py` verifies the internal
  artifacts and exits blocked until every external review and owner release
  approval is recorded.
- The active product direction is now a complete owner-only workspace before
  any external account rollout. Authenticated owner controls support research
  decisions, risk-gated paper proposal decisions, and explicitly confirmed
  simulated fills. Public registration, invitations, brokerage connections,
  and real trading remain disabled. The owner controls reuse the existing
  scale-to-zero Cloud Run service and private bucket; recurring schedules
  remain paused pending separate approval.
- On June 13, 2026, owner controls were deployed to Cloud Run revision
  `atlas-dashboard-stg-00009-wlz` with 100% of service traffic. The live owner
  Google login and control-center display were validated. The dashboard
  identity has bucket-scoped `roles/storage.objectUser` access, public
  registration remains disabled, and daily and weekly schedules remain
  paused.
- The June 13 daily Cloud Run execution `atlas-daily-stg-2nppc` completed
  successfully using the current application image. It published real data for
  all 100 requested securities with no placeholders, refreshed the live
  dashboard, and generated three risk-cleared paper proposals for owner review.
  `CAPABILITY_LOG.md` now records owner-visible upgrades in plain language.
- Cloud Run revision `atlas-dashboard-stg-00010-vzq` replaced the unsupported
  paper-fill browser prompt with an in-page confirmation dialog. The owner
  completed the approved KLAC, LRCX, and ANET simulated purchases, and the
  secure dashboard now tracks all three positions alongside NVDA. Recurring
  schedules remain paused pending the separate cost-activation decision.
- Joe approved recurring Atlas research up to a $5 monthly operating target
  with the existing $10 gross-usage alert. The daily 7:00 AM Pacific and Sunday
  8:00 AM Pacific schedules are now enabled. Monitoring remains active, and
  real trading and brokerage access remain disabled.
- Corporate-action normalization is deployed. Momentum uses adjusted closes,
  research snapshots retain dated split events, and historical comparisons
  normalize pre-split prices. KLAC's June 12 10-for-1 split was validated
  against real cloud artifacts. Dashboard revision
  `atlas-dashboard-stg-00012-w55` adds an owner-visible Data Integrity panel.
- Research-task lifecycle management is deployed on dashboard revision
  `atlas-dashboard-stg-00013-ml2` and image
  `20260614-task-lifecycle`. Generated daily and weekly signals now refresh in
  place, expire after three and eight days respectively, and retain closure
  history. Controlled execution `atlas-daily-stg-xmqlx` completed
  successfully; the live agenda now has 11 current assignments instead of 16
  stale or duplicate assignments. All 277 tests pass.
- Daily and weekly schedules are enabled under the approved $5 monthly target
  and existing $10 gross-usage alert. Real trading and brokerage access remain
  disabled.
- Evidence-backed automated research is deployed on dashboard revision
  `atlas-dashboard-stg-00015-hrd` and image
  `20260614-evidence-research-v2`. Each daily run may complete up to three
  high-priority generated market tasks using measured price movement and
  company-specific Yahoo headline evidence. Results include a conservative
  recommendation and confidence rating, remain pending for owner review, and
  cannot authorize trades. Execution `atlas-daily-stg-6j2wr` produced AVAV
  and ADBE risk reviews. All 283 tests pass.
- Run the tenant preview with `py -3.12 tenant_dashboard.py`, then open
  `http://127.0.0.1:8766`. Its local SQLite state remains ignored under
  `tenant_data/`.
- `WEB_PHASE2_PLAN.md`: secure single-user cloud architecture and deployment gate.
- `GCP_STAGING_SETUP.md`: guarded Google Cloud staging setup and billing gate.
- `scripts/gcp_set_schedules_staging.ps1`: guarded schedule status, pause, and
  explicit resume workflow.
- `scripts/gcp_configure_artifact_cleanup.ps1`: plan-first image-retention
  setup that defaults to dry run.
- `scripts/gcp_staging_readiness.ps1`: read-only final-staging audit with
  explicit manual validation gates.
- `scripts/gcp_uptime_report.ps1`: repeatable read-only regional availability
  report.
- `scripts/gcp_final_staging_review.ps1`: aggregate read-only final-staging
  review command.
- `FINAL_STAGING_REVIEW.md`: operator runbook for the last Web Phase 2 gates.
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
