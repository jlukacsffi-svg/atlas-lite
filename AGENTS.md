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
- Read `CLOUD_COST_POLICY.md` before any cloud work.
- Read `CLOUD_COST_ESTIMATE.md` before billing or deployment work.
- Google Cloud billing is linked only to the dedicated staging project, with a
  `$10` monthly gross-usage alert budget. New billable services or materially
  higher usage require a fresh estimate and explicit owner approval.
- Never treat a cloud budget or free tier as a hard spending cap.
- Do not run cloud scripts with `-Apply` or `-ConfirmCosts` without explicit
  owner approval for that paid deployment stage.

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
- Read `WEB_PHASE2_PLAN.md` before cloud deployment work.
- Read `PRODUCTION_ARCHITECTURE_REVIEW.md` before multi-user production work.
- Run `py -3.12 tenant_readiness.py`; exit code `2` is the expected blocked
  state until Joe approves the revised cost envelope and release gates close.
- Run `py -3.12 tenant_postgres_check.py` after tenant schema changes. It must
  pass without connecting to a database or activating Cloud SQL.
- Build the website incrementally without disrupting the research and paper-evaluation engine.
- Start with a read-only local owner dashboard.
- Use modern, responsive, accessible financial-workspace design with meaningful charts.
- Reuse stable Python research modules behind service boundaries rather than rewriting them for presentation.
- Keep web-platform maturity separate from trading authority.
- Use managed authentication and secret storage for hosted environments.
- Cloud mode must fail closed when managed authentication or persistent data is not configured.
- Do not trust unsigned proxy identity headers; verify the provider's signed identity token.
- Cloud private artifacts must use the allowlisted, checksum-verified storage
  bundle; never upload `.env`, credentials, caches, or arbitrary repository files.
- Keep dashboard storage access read-only and scheduled-job storage access
  separate and least-privileged.
- Keep private backups in the ignored `backups/` folder; never commit or expose
  backup archives.
- Tenant SQLite backups are integrity-checked but not application-encrypted.
  Keep them only in private encrypted-at-rest storage and run
  `tenant_backup.py drill` before a production migration or restore.
- Tenant privacy exports belong only in the ignored `privacy_exports/` folder.
  They contain private identity and financial data, exclude invitation
  secrets, and must remain in private encrypted-at-rest storage.
- Preserve append-only security audit history when pseudonymizing a deleted
  account. Owner deletion requires a future ownership-transfer or
  tenant-closure workflow.
- Run a local `backup_restore.py drill` before the first cloud deployment and a
  cloud-backed restoration drill before production.
- Treat every user-owned record as tenant-scoped and test that users cannot access one another's data.
- After every user-visible web change, reload Atlas in the in-app browser and
  leave the updated page open for Joe to review. Show the working interface
  instead of relying only on a written description.

## Development guidance

- Always run `py -3.12 main.py` after meaningful changes.
- Keep the code simple and runnable locally.
- Do not add trading capability unless Joe explicitly approves it.
