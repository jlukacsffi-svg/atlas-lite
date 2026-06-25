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

## June 22, 2026 - Catalyst Classification

New capabilities:

- Label each completed automated review with a catalyst classification such as
  `score_risk`, `company_news`, `analyst_negative`, `analyst_positive`,
  `upcoming_earnings`, `insider_activity`, or `unconfirmed`.
- Add a thesis-action line that tells the owner what kind of follow-up Atlas
  recommends before any conviction change.
- Display catalyst type and thesis action in the secure owner decision center.

Validated result:

- Cloud execution `atlas-daily-stg-2ltsk` completed successfully.
- Atlas classified AVAV as `score_risk` because the downside move coincided
  with a low Atlas score.
- Atlas classified ARM and NFLX as `company_news` because the available
  evidence was company-headline context rather than a stronger structured
  catalyst.
- Daily and weekly schedules were resumed after the controlled run.
- The full automated test suite passes with 286 tests.

Current boundaries:

- Catalyst classification is a research label, not proof of causality.
- Thesis action is a recommendation for owner review only.
- Real trading and brokerage access remain disabled.

## June 22, 2026 - Thesis-Memory Research Reviews

New capabilities:

- Compare automated research reviews against the stored Atlas thesis profile
  for each security when a profile is available.
- Add `thesis_alignment` to owner-review results, including labels such as
  `risk_to_thesis`, `supports_driver`, `pending_validation`, `neutral_context`,
  `unprofiled`, and `unconfirmed`.
- Include the stored thesis, key driver, and key risk as evidence in the owner
  decision center.
- Display thesis alignment in the secure dashboard so recommendations show
  whether new evidence supports, threatens, or merely touches the thesis.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00018-gtc` is serving 100% traffic.
- Cloud execution `atlas-daily-stg-pbbqx` completed successfully.
- Atlas produced thesis-aware owner reviews for AVAV, ARM, and MDB. AVAV was
  classified as `score_risk` with `risk_to_thesis`.
- Daily and weekly schedules were resumed after the controlled run.
- The full automated test suite passes with 287 tests.

Current boundaries:

- Thesis alignment is a conservative research label, not proof of causality.
- Older pending reviews may not have a thesis-alignment field until refreshed.
- Real trading and brokerage access remain disabled.

## June 22, 2026 - Thesis-Drift Tracking

New capabilities:

- Summarize prior owner-review history for each ticker before generating a new
  automated research review.
- Add `thesis_drift` to completed research results, including labels such as
  `new_risk`, `recurring_risk`, `new_support`, `reinforcing_support`,
  `stable_monitoring`, and `no_history`.
- Add thesis-history evidence so owner reviews can show prior thesis-risk or
  support signals.
- Display thesis drift in the secure owner decision center.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00019-627` is serving 100% traffic.
- Cloud execution `atlas-daily-stg-vgxcx` completed successfully.
- Atlas marked AVAV and ARM as `recurring_risk` because prior thesis-risk
  reviews were already recorded.
- Atlas marked NFLX as `new_risk`.
- Daily and weekly schedules were resumed after the controlled run.
- The full automated test suite passes with 288 tests.

Current boundaries:

- Thesis drift is a memory signal for owner review, not proof of causality.
- Drift labels do not authorize simulated or real trades.
- Real trading and brokerage access remain disabled.

## June 22, 2026 - Owner Review Ranking

New capabilities:

- Rank owner-review research cards by an attention score.
- Combine priority, recommendation type, catalyst type, thesis alignment,
  thesis drift, and confidence into a conservative review score.
- Display an attention badge and concise attention drivers on each owner
  decision card.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00020-dx7` is serving 100% traffic.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 289 tests.

Current boundaries:

- Attention ranking only prioritizes owner review; it does not approve,
  reject, simulate, or execute any transaction.
- Real trading and brokerage access remain disabled.

## June 23, 2026 - Daily Owner Action List

New capabilities:

- Generate a concise daily action list from the ranked owner-review queue.
- Add suggested owner dispositions such as reviewing recurring risks first,
  deferring low-confidence items for more evidence, or monitoring support
  signals for confirmation.
- Display the action list above detailed research cards in the secure Controls
  page.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00021-g9z` is serving 100% traffic.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 289 tests.

Current boundaries:

- Suggested dispositions guide owner review only.
- The action list does not approve, reject, simulate, or execute transactions.
- Real trading and brokerage access remain disabled.

## June 23, 2026 - Action Evidence Anchors

New capabilities:

- Add a concise evidence anchor to each daily owner action item.
- Prefer structured research evidence when available, with a conclusion-based
  fallback when the research item has no explicit evidence list.
- Display the evidence anchor directly under the suggested disposition in the
  secure Controls page.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00022-kdx` is serving 100% traffic.
- Dashboard image `20260623-action-evidence` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 289 tests.

Current boundaries:

- Evidence anchors are compact references for owner review, not proof of
  causality.
- Evidence anchors do not approve, reject, simulate, or execute transactions.
- Real trading and brokerage access remain disabled.

## June 23, 2026 - Action Exposure And Paper Context

New capabilities:

- Add simulated portfolio exposure context to each daily owner action item.
- Add paper-performance context to each daily owner action item, including
  account return, benchmark excess return, snapshot count, and ticker thesis
  review context when available.
- Display portfolio and paper context directly under the evidence anchor in
  the secure Controls page.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00023-dxs` is serving 100% traffic.
- Dashboard image `20260623-action-context` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 289 tests.

Current boundaries:

- Portfolio context refers to Atlas-tracked simulated exposure unless a future
  real portfolio import is explicitly configured.
- Paper-performance context is simulation-only and does not authorize trades.
- Real trading and brokerage access remain disabled.

## June 23, 2026 - Owner Outcome Learning

New capabilities:

- Summarize owner research decisions across approve, defer, and reject
  outcomes.
- Calculate the owner research approval rate from the existing audit trail.
- Summarize paper proposal outcomes across pending, approved, rejected, and
  simulated states.
- Display an Outcome Learning card in the secure Controls page with a concise
  learning signal and recent owner decisions.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00024-dqp` is serving 100% traffic.
- Dashboard image `20260623-outcome-learning` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 290 tests.

Current boundaries:

- Outcome learning summarizes historical owner decisions; it does not change
  model weights automatically yet.
- Outcome summaries do not approve, simulate, or execute transactions.
- Real trading and brokerage access remain disabled.

## June 24, 2026 - Outcome-Calibrated Attention Scoring

New capabilities:

- Use prior owner decisions to conservatively calibrate research attention
  scores.
- Lower urgency when prior owner outcomes for the same ticker or
  recommendation type show repeated caution.
- Preserve or lightly raise urgency when prior similar risk reviews were
  approved.
- Display the calibration adjustment and reason in the secure Controls page
  when owner history affects a review.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00025-8m4` is serving 100% traffic.
- Dashboard image `20260624-outcome-calibration` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 291 tests.

Current boundaries:

- Calibration only changes owner-review priority and explanation.
- Calibration does not approve, reject, simulate, or execute transactions.
- Real trading and brokerage access remain disabled.

## June 24, 2026 - Dashboard Help And Term Clarification

New capabilities:

- Add clickable information controls to major dashboard sections.
- Clarify that SPY is used as a broad S&P 500 benchmark and QQQ as a
  Nasdaq-100 growth/technology benchmark.
- Explain Atlas scores, largest watchlist moves, open simulated positions,
  research agenda, market breadth, sector tape, data integrity, controls, and
  access/security sections.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00026-qcq` is serving 100% traffic.
- Dashboard image `20260624-dashboard-help` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 292 tests.

Current boundaries:

- This is a dashboard usability improvement only.
- No research scoring, schedule, simulation, trading, or access permissions
  changed.
- Real trading and brokerage access remain disabled.

## June 24, 2026 - Dashboard Pages And Recommendation Clarity

New capabilities:

- Split the secure dashboard into page-style views for Overview,
  Recommendations, Market, Research, Paper Portfolio, Controls, and
  Access/Security.
- Add a dedicated Recommendations page that clearly separates Atlas paper
  purchase recommendations from the broader list of currently tracked
  securities.
- Add an overview preview of recommended simulated buys and the current Atlas
  list.
- Explain the owner workflow for paper ideas: approve the proposal first, then
  use Simulate fill to record the hypothetical position in the paper
  portfolio.
- Add color cues for recommendations, tracked securities, KPI cards, and the
  simulation-only workflow.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00027-8hv` is serving 100% traffic.
- Dashboard image `20260624-dashboard-pages` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 292 tests.

Current boundaries:

- This is a dashboard usability and clarity improvement only.
- Simulate fill still updates simulated paper tracking only.
- No brokerage order is sent and no real money is spent.
- Real trading and brokerage access remain disabled.

## June 24, 2026 - Paper Recommendation Feedback Loop

New capabilities:

- Compare each executed simulated buy proposal against later Atlas paper
  snapshots.
- Calculate the simulated security return from fill price to latest tracked
  price.
- Compare each simulated idea against SPY and QQQ returns over the same
  available tracking window.
- Label simulated recommendations as `working`, `lagging`, `mixed`, or
  `not_enough_time`.
- Display the result in a new Recommendation Performance panel on the Paper
  Portfolio page, including thesis, fill price, latest price, benchmark
  comparison, and snapshot count.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00028-248` is serving 100% traffic.
- Dashboard image `20260624-paper-feedback` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 293 tests.

Current boundaries:

- Feedback evaluates simulated paper outcomes only.
- Feedback does not approve, reject, simulate, or execute any transaction.
- No brokerage order is sent and no real money is spent.
- Real trading and brokerage access remain disabled.

## June 24, 2026 - Paper Proposal Why-Now Rationale

New capabilities:

- Store structured rationale bullets on new Atlas-generated paper proposals.
- Explain why a simulated buy is being proposed now, including Atlas score
  threshold, strongest score inputs, category, sector, current price move, and
  target simulated sizing.
- Display a `Why now` box on recommendation and control cards so owner review
  can see the reason before approving, rejecting, or simulating a fill.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00031-bb7` is serving 100% traffic.
- Dashboard image `20260624-why-now-v3` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 293 tests.

Current boundaries:

- Why-now rationale explains paper proposals only.
- Rationale does not approve, reject, simulate, or execute any transaction.
- No brokerage order is sent and no real money is spent.
- Real trading and brokerage access remain disabled.

## June 24, 2026 - Simulated Exit / Trim Recommendations

New capabilities:

- Surface paper sell proposals separately as `Exit / trim recommendations` on
  the Overview and Recommendations pages.
- Keep paper buy proposals and paper sell proposals visually distinct with
  separate dashboard sections, tags, and color treatment.
- Update owner controls to count active buy ideas separately from exit/trim
  ideas.
- Update the Simulate fill confirmation dialog so sell proposals are described
  as simulated exits or trims rather than purchases.
- Adjust CRO paper-risk review so a weak Atlas score can support a simulated
  sell proposal instead of automatically blocking the exit review.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00037-tcb` is serving 100% traffic.
- Dashboard image `20260624-exit-trim` is deployed.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 295 tests.

Current boundaries:

- Exit/trim recommendations update the simulated paper portfolio only after
  owner approval and explicit Simulate fill confirmation.
- No brokerage order is sent and no real money is spent.
- Real trading and brokerage access remain disabled.

## June 24, 2026 - Benchmark-Lag Paper Trim Trigger

New capabilities:

- Compare open simulated positions against executed recommendation feedback for
  SPY and QQQ benchmark lag.
- Flag a simulated holding for review when it trails both core benchmarks by at
  least 3 percentage points across multiple snapshots.
- Create a reviewable simulated half-trim sell proposal when a holding trails
  both core benchmarks by at least 8 percentage points.
- Carry the benchmark-lag explanation into the position review and sell-proposal
  rationale so owner review can see why Atlas is challenging the holding.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00038-rtz` is serving 100% traffic.
- Dashboard image `20260625-benchmark-lag-trim` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 297 tests.

Current boundaries:

- Benchmark-lag trims are simulated paper sell proposals only.
- Owner approval and explicit Simulate fill confirmation are still required
  before the paper portfolio changes.
- No brokerage order is sent and no real money is spent.
- Real trading and brokerage access remain disabled.

## June 25, 2026 - Proposal Clarity And Help Popovers

New capabilities:

- Distinguish simulated paper sell proposals as `trim` versus `exit` based on
  the current simulated holding size.
- Show owner-facing impact text that explains whether Atlas would reduce a
  position or fully close it before any simulated fill is recorded.
- Update proposal titles, confirmation copy, and success messages so the
  Controls and Recommendations pages speak in plain language about purchases,
  trims, and exits.
- Replace brittle question-mark hover behavior with popovers that open
  predictably, stay visible while the help card is being read, and close when
  the cursor or focus leaves the help control.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00039-hrs` is serving 100% traffic.
- Dashboard image `20260625-proposal-clarity` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 299 tests.

Current boundaries:

- Proposal clarity changes improve simulated paper-review understanding only.
- Owner approval and explicit Simulate fill confirmation remain required before
  the paper portfolio changes.
- No brokerage order is sent and no real money is spent.
- Real trading and brokerage access remain disabled.

## June 25, 2026 - Position Thesis Status Layer

New capabilities:

- Derive a plain-language thesis status for every open simulated paper holding:
  `healthy`, `watch`, `trim`, or `exit`.
- Use the latest thesis review and any active simulated sell proposal to decide
  the current status.
- Show a concise evidence line on each Paper Portfolio position card so the
  dashboard explains why Atlas thinks a holding is healthy, needs attention,
  should be trimmed, or should be exited.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00040-2xc` is serving 100% traffic.
- Dashboard image `20260625-thesis-status` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 300 tests.

Current boundaries:

- Thesis-status labels describe simulated paper holdings only.
- They do not execute any action by themselves and do not authorize real trades.
- Owner approval and explicit Simulate fill confirmation remain required before
  the paper portfolio changes.
- No brokerage order is sent and no real money is spent.

## June 25, 2026 - Thesis Overview Attention Layer

New capabilities:

- Add a Paper Portfolio overview panel that counts open simulated holdings by
  `healthy`, `watch`, `trim`, and `exit`.
- Rank the top holdings that need attention first, using thesis severity before
  position size so the riskiest paper names surface immediately.
- Keep the detailed per-position thesis badges underneath, while giving the
  owner a faster at-a-glance read of overall paper thesis health.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00041-xbf` is serving 100% traffic.
- Dashboard image `20260625-thesis-overview` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 301 tests.

Current boundaries:

- The thesis overview summarizes simulated paper positions only.
- It does not execute actions or grant new financial authority.
- Owner approval and explicit Simulate fill confirmation remain required before
  the paper portfolio changes.
- No brokerage order is sent and no real money is spent.

## June 25, 2026 - Recommendation Queue Clarity

New capabilities:

- Add a Recommendations-page queue summary that separates buy candidates,
  approved ideas that are ready for simulated fill, reduce or exit reviews,
  and the broader tracked universe.
- Surface an "Atlas focus right now" strip so the owner can immediately see the
  highest-priority recommendation states and the first rationale line for each.
- Make recommendation cards more explicit about their current stage, including
  "Buy candidate", "Ready to simulate", "Trim candidate", and "Exit candidate".
- Add stronger visual separation for Core, Watchlist, and tracked universe names
  so the current Atlas list is easier to scan beside active recommendations.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00042-gdg` is serving 100% traffic.
- Dashboard image `20260625-recommendation-clarity` is deployed.
- The Recommendations page now exposes the recommendation queue summary and the
  revised recommendation-stage labels.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 301 tests.

Current boundaries:

- The queue clarifies paper-only recommendations; it does not change the
  underlying research model or authorize real trades.
- Approved paper ideas still require an explicit Simulate fill before they
  appear in the paper portfolio.
- No brokerage order is sent and no real money is spent.
