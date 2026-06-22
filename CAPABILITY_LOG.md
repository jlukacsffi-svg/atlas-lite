# Atlas Capability Log

This log records owner-visible capabilities as they become available. Each
entry states what Atlas can do now and which safety boundaries remain.

## June 13, 2026 - Active Owner Research

New capabilities:

- Run the Atlas daily research cycle on demand in Google Cloud without relying
  on the owner's laptop.
- Retrieve real public market data for the 100-security Atlas universe.
- Produce current market breadth, movers, sector trends, hybrid scores, news
  explanations, analyst actions, insider transactions, and research prompts.
- Display the refreshed results in the secure owner dashboard.
- Generate risk-reviewed paper-trade proposals for explicit owner approval or
  rejection.
- Persist owner decisions and simulated portfolio changes in private cloud
  storage.

Current boundaries:

- Real trading is disabled.
- Brokerage access is disabled.
- Public registration and external accounts are disabled.
- Daily and weekly schedules remain paused until separately approved.
- Market information and model outputs require owner judgment and are not
  personalized financial advice.

## June 13, 2026 - Active Paper Portfolio

New capabilities:

- Confirm approved simulated purchases through an accessible in-page dialog
  that works in the secure Atlas application.
- Track approved paper positions using the latest available market price,
  including shares, average cost, market value, unrealized gain or loss, cash
  reserve, total equity, and benchmark-relative history.
- Persist the simulated fills in private cloud storage so later research runs
  can revalue the positions and review their theses.
- Display completed paper purchases immediately in the owner dashboard.

Activated owner positions:

- KLAC: 19 simulated shares.
- LRCX: 13 simulated shares.
- ANET: 30 simulated shares.
- NVDA remains an existing simulated position with 24 shares.

Current boundaries:

- Simulation approval and simulation fill remain separate owner actions.
- All positions use simulated capital only.
- Real trading and brokerage access remain disabled.

## June 13, 2026 - Corporate-Action Normalization

New capabilities:

- Use split-adjusted Yahoo historical prices for momentum calculations.
- Detect dated stock-split events and retain their source, ratio, and effective
  date in the research archive.
- Normalize pre-split snapshot prices before calculating historical changes.
- Disclose applied adjustments in executive reports and display recent
  corporate actions in the dashboard Data Integrity panel.

Validated result:

- Atlas detected KLAC's June 12, 2026 10-for-1 split.
- The June 8 KLAC comparison price is normalized from $1,929.20 to $192.92.
- The resulting June 8-to-June 13 comparison is +31.94%, replacing the false
  unadjusted decline of approximately 86.8%.

Current boundaries:

- Split data depends on published Yahoo corporate-action events.
- Other corporate actions such as spin-offs and symbol changes need future
  normalization work.
- Recommendations remain research outputs requiring owner judgment.
- Recurring daily and weekly cloud schedules remain paused pending separate
  cost approval.

## June 13, 2026 - Recurring Owner Research

New capabilities:

- Run the daily Atlas research cycle automatically at 7:00 AM Pacific.
- Run the weekly Atlas strategy cycle automatically at 8:00 AM Pacific each
  Sunday.
- Refresh private dashboard research and paper-position valuations without the
  owner's laptop being online.
- Monitor dashboard availability and failed cloud jobs through Google Cloud
  alert policies.

Approved cost boundary:

- Target recurring Atlas usage is no more than $5 per month.
- The existing $10 monthly gross-usage budget remains active with alerts at
  25%, 50%, 80%, and 100%.
- Promotional credits do not replace the budget controls.

Current boundaries:

- Automatic research and reporting are enabled.
- Investment decisions and paper fills still require owner review.
- Real trading and brokerage access remain disabled.

## June 13, 2026 - Current Research Agenda

New capabilities:

- Refresh recurring daily and weekly research signals in place instead of
  adding duplicate assignments after every run.
- Automatically close daily signals after three days and weekly signals after
  eight days when they are no longer refreshed.
- Preserve closed assignments, timestamps, and close reasons for audit history.
- Leave manual, in-progress, and owner-review tasks untouched by automatic
  maintenance.

Validated result:

- The live queue was reduced from 16 stale or duplicate open assignments to 11
  current assignments after the June 13 daily run.
- The current queue contains eight fresh daily signals and three still-valid
  weekly signals.
- The secure owner dashboard displays 11 open assignments, including three
  high-priority risk reviews.

Current boundaries:

- Atlas organizes and prioritizes research; it does not independently complete
  every research assignment.
- Owner decisions remain required for paper fills and all financial actions.
- Real trading and brokerage access remain disabled.

## June 14, 2026 - Evidence-Backed Research Reviews

New capabilities:

- Complete up to three fresh high-priority generated market assignments during
  each daily research run.
- Combine the measured market move with company-specific public headlines.
- Produce a conservative conclusion, recommendation, and confidence rating.
- Route completed work to the secure owner decision center with expandable,
  clickable evidence.
- Preserve a pending owner review when the same signal appears again instead
  of creating a duplicate task.

Validated result:

- Cloud execution `atlas-daily-stg-6j2wr` completed successfully.
- Atlas produced medium-confidence risk reviews for AVAV and ADBE.
- The AVAV review displays the measured 7.14% decline and one
  company-specific headline; unrelated broad-search results are excluded.
- The ADBE review includes three company-specific headlines.
- The full automated test suite passes with 283 tests.

Current boundaries:

- Headline evidence provides research context and does not prove causality.
- Atlas limits automatic completion to a small number of high-priority
  generated assignments.
- Every conclusion still requires an owner approve, defer, or reject decision.
- Real trading and brokerage access remain disabled.

## June 22, 2026 - Monitoring Alert Tuning

Operational update:

- Verified the live dashboard readiness endpoint returns `200 {"status":"ready"}`.
- Confirmed Cloud Run revision `atlas-dashboard-stg-00015-hrd` is healthy and
  serving traffic.
- Identified noisy dashboard-unavailable email alerts caused by a strict
  perfect-uptime threshold on a low-cost scale-to-zero staging service.
- Tuned the dashboard availability alert to require sustained multi-region
  readiness failure below a 0.67 pass fraction for 600 seconds.
- Left daily and weekly Cloud Run job-failure alerts immediate.

Current boundaries:

- The dashboard still scales to zero to preserve the low-cost staging target.
- A brief cold start should no longer produce unnecessary dashboard-down
  emails.
- Sustained multi-region readiness failure should still alert the owner.

## June 22, 2026 - Context-Aware Research Reviews

New capabilities:

- Enrich automated owner-review research with Atlas score, watchlist category,
  and sector context.
- Add upcoming earnings, analyst-action headlines, insider Form 4 activity,
  and tracked portfolio exposure to research evidence when available.
- Include these context signals in the conclusion so owner reviews read more
  like a compact analyst memo than a headline-only note.

Validated result:

- Cloud execution `atlas-daily-stg-wpcqs` completed successfully.
- Atlas produced context-aware risk reviews for AVAV, ARM, and MDB.
- Each review includes the measured move, Atlas score/category/sector evidence,
  and company-specific public headlines.
- Daily and weekly schedules were resumed after the controlled run.
- The full automated test suite passes with 284 tests.

Current boundaries:

- Context signals improve research quality but do not prove causality.
- Completed research remains pending for owner approval, deferral, or rejection.
- Real trading and brokerage access remain disabled.
