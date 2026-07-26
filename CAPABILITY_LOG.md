# Atlas Capability Log

This log records owner-visible capabilities as they become available. Each
entry states what Atlas can do now and which safety boundaries remain.

## July 15, 2026 - Atlas now audits sector-gate effects

New capabilities:

- Add an owner-visible `Sector gate audit` to the paper-learning dashboard.
- Count active sector-gated candidates by cleared, tightened, boosted, and
  currently eligible status.
- Count accepted simulated buy recommendations that carried a sector-gate
  rationale, including how many cleared stronger confirmation, were tightened,
  or benefited from constructive sector evidence.
- Align strategy gate telemetry with the same 3-snapshot sector-learning
  checkpoint shown in the sector-learning bridge.
- Extend the token-protected staging verification contract with a
  `sector_gate_audit` check.

Validated result:

- Focused `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` coverage passes with 185 tests.
- Cloud Run revision `atlas-dashboard-stg-00128-n86` is live on image
  `20260715-sector-gate-audit`.
- The deployed image digest is
  `sha256:e97cd40d025c39696a6cab8e018d97af17a24093419c15be137a7eaf7f25db37`.
- The token-protected dashboard verification endpoint passes on the deployed
  revision and includes the sector gate audit check.
- The daily and weekly Cloud Run jobs were updated to the same image, manual
  executions `atlas-daily-stg-9znm9` and `atlas-weekly-stg-8r55h` completed
  successfully, and recurring schedules are enabled again.
- The in-app browser controller still cannot be used because the bundled
  browser runtime fails while redefining a protected Node `process` global;
  live dashboard verification and staging readiness passed.

Current boundaries:

- This remains simulated paper-entry management only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now audit how sector gates affect simulated decisions, but it
  still does not place real orders or change any real-money account.

## July 15, 2026 - Atlas now explains sector-learning gates in paper decisions

New capabilities:

- Use sector-learning cautions as a stronger simulated paper-entry gate, not
  just a ranking adjustment.
- Require stronger benchmark excess, sector-relative strength, sector breadth,
  trend quality, persistence, and follow-through before Atlas opens another
  simulated buy in a sector where recent judged buys are lagging.
- Keep positive sector learning conservative: a working sector can still earn a
  small `+1.5` strategy tilt, but it does not bypass trend, benchmark, news, or
  risk filters.
- Carry sector-learning gate status into accepted simulated buy rationales, so
  Atlas can say when a lagging-sector setup cleared the stronger confirmation
  bar and how many checks passed.
- Update the sector-learning bridge language so owner-facing summaries explain
  the `Sector learning gate` checkpoint rather than only showing a generic
  tilt.
- Use a lightweight dashboard verification read model that bypasses the refresh
  wrapper and full dashboard build while preserving the Stage 5 contract fields
  needed for smoke checks.

Validated result:

- Focused `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` coverage passes with 184 tests.
- Cloud Run revision `atlas-dashboard-stg-00127-88b` is live on image
  `20260715-sector-gate-telemetry-lightverify2`.
- The deployed image digest is
  `sha256:363bdd77ba297591b3074f83270bdc95dd5507021a6e589393852b4649ef0969`.
- The token-protected dashboard verification endpoint passes on the deployed
  revision and includes the sector-learning bridge, benchmark scorecard,
  benchmark exit tuning, benchmark entry pacing, autonomous queue, and
  accountability-report checks.
- The daily and weekly Cloud Run jobs were updated to the same image, manual
  executions `atlas-daily-stg-5n4vl` and `atlas-weekly-stg-rcmgx` completed
  successfully, and recurring schedules are enabled again.
- The in-app browser controller still cannot be used because the bundled
  browser runtime fails while redefining a protected Node `process` global;
  live dashboard verification and staging readiness passed.

Current boundaries:

- This remains simulated paper-entry management only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now tighten paper-only entry gates based on sector learning, but it
  still does not place real orders or change any real-money account.

## July 15, 2026 - Atlas now exposes the sector-learning bridge

New capabilities:

- Add an owner-facing `Sector learning bridge` card to the Stage 5
  paper-learning dashboard.
- Summarize 3-snapshot sector buy evidence using the same small paper-strategy
  tilt rules Atlas already applies during simulated entry ranking.
- Show whether each sector is in a `boost`, `caution`, or `watch` posture,
  including judged buy count, working/mixed/lagging outcomes, working rate, and
  visible `Strategy tilt` amount.
- Extend the token-protected staging verification contract with a
  `sector_learning_bridge` check.
- Speed up the dashboard verification endpoint by checking the already-built
  paper payload instead of invoking the full owner-control model during
  read-only smoke checks.

Validated result:

- Focused `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` coverage passes with 180 tests.
- Cloud Run revision `atlas-dashboard-stg-00122-2vz` is live on image
  `20260715-sector-learning-bridge-verification-fast`.
- The deployed image digest is
  `sha256:d2a4aab7827d7cda17341deecf67b742102f9ea22e02e6ea75666d9ef9fe9b41`.
- The token-protected dashboard verification endpoint passes on the deployed
  revision and includes the new `sector_learning_bridge` check.
- The daily and weekly Cloud Run jobs were updated to the same optimized image,
  manual executions `atlas-daily-stg-tchkh` and `atlas-weekly-stg-kb9jf`
  completed successfully, and recurring schedules are enabled again.
- The in-app browser controller could not be used on this pass because the
  bundled browser runtime failed while redefining a protected Node `process`
  global; live dashboard verification and staging readiness still passed.

Current boundaries:

- This remains simulated paper-entry management only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The sector bridge currently exposes and explains Atlas's existing small
  sector tilts; it does not yet add stronger sector-level paper-entry gating.

## July 13, 2026 - Atlas now shows sector-level capital rotation accountability

New capabilities:

- Add an owner-facing capital-rotation scoreboard to the Stage 5 paper-learning
  dashboard.
- Group simulated capital by sector, including open exposure, open weight,
  gross buys, gross sells, net committed capital, realized and unrealized P/L,
  judged buy counts, buy working rate, and average benchmark-relative edge.
- Label each sector with a compact posture such as `press`, `watch`,
  `diversify`, or `review`, making it clearer where Atlas believes simulated
  capital is being earned versus where concentration or weak follow-through
  needs more scrutiny.
- Extend the token-protected staging verification contract with a
  `capital_rotation_scoreboard` check.
- Optimize the dashboard read model so the scoreboard reuses already-scored
  paper feedback rows instead of adding another expensive feedback pass.

Validated result:

- Focused `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` coverage passes with 178 tests.
- Cloud Run revision `atlas-dashboard-stg-00120-lmh` is live on image
  `20260713-capital-rotation-scoreboard-fast`.
- The deployed image digest is
  `sha256:8dffd994b555e381d49735107eff613ee9236e756516a4e0c22d7368dee1942f`.
- The token-protected dashboard verification endpoint passes on the deployed
  revision and includes the new `capital_rotation_scoreboard` check.
- The daily and weekly Cloud Run jobs were updated to the same optimized
  image, manual executions `atlas-daily-stg-7pcmh` and
  `atlas-weekly-stg-v8nm5` completed successfully, and recurring schedules are
  enabled again.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.

Current boundaries:

- This is read-only owner visibility for the simulated paper portfolio.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The scoreboard informs future sector-level tuning, but this change does not
  add new real-money trading authority or brokerage execution.

## July 12, 2026 - Atlas now uses benchmark scorecards to tune entry pacing

New capabilities:

- Extend benchmark-specific scorecards with buy-only judged counts, working
  rate, and average decision edge for each tracked benchmark.
- Let benchmark-specific buy evidence gently retune autonomous paper target
  entry size, new-idea capacity, and sector-repeat pressure when broader
  buy/persistence learning has not already made an adjustment.
- Show the new adaptive entry-pacing profile in the dashboard learning panel
  and Controls strategy adaptive cards.
- Add `benchmark_rotation_stats` to the entry strategy profile so the staging
  verification contract can confirm the evidence path exists.

Validated result:

- Focused `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` coverage passes with 177 tests.
- Cloud Run revision `atlas-dashboard-stg-00118-f7x` is live on image
  `20260712-benchmark-entry-pacing`.
- The deployed image digest is
  `sha256:e469493715c0b890ca323166ac20fe32003ad2d589b604fe35cdc09a07f8851b`.
- The token-protected dashboard verification endpoint passes on the deployed
  revision and includes the new `benchmark_entry_pacing` check.
- The daily and weekly Cloud Run jobs were updated to the same image, manual
  executions `atlas-daily-stg-xdnhd` and `atlas-weekly-stg-n2lwj` completed
  successfully, and recurring schedules are enabled again.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.

Current boundaries:

- This remains simulated paper-entry management only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now let benchmark-specific paper evidence tune sector and capital
  pacing, but it still does not place real orders or change any real-money
  account.

## July 12, 2026 - Atlas now uses benchmark scorecards to tune paper exit strictness

New capabilities:

- Extend benchmark-specific scorecards with sell-only judged counts, working
  rate, and average decision edge for each tracked benchmark.
- Let benchmark-specific sell evidence gently retune autonomous paper monitor
  review and trim thresholds when stronger projection-driver or sell-trigger
  learning has not already made an adjustment.
- Move paper exits slightly earlier when trims/exits are helping versus the
  relevant benchmark scorecard, and slightly slower when trims/exits are
  lagging versus that scorecard.
- Add `benchmark_exit_stats` to the adaptive projection-tuning profile so the
  live dashboard verification contract can confirm the evidence path exists.

Validated result:

- Focused `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` coverage passes with 175 tests.
- Cloud Run revision `atlas-dashboard-stg-00117-5vw` is live on image
  `20260712-benchmark-exit-tuning`.
- The deployed image digest is
  `sha256:bdac74ccd5c83fadcae8c40344b02afd87985286dfa550d3115e0cec76f3fb4e`.
- The token-protected dashboard verification endpoint passes on the deployed
  revision and includes the new `benchmark_exit_tuning` check.
- The daily and weekly Cloud Run jobs were updated to the same image, manual
  executions `atlas-daily-stg-q684b` and `atlas-weekly-stg-dwdfh` completed
  successfully, and recurring schedules are enabled again.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.

Current boundaries:

- This remains simulated paper-position management only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now let benchmark-specific paper evidence tune exit strictness,
  but it still does not place real orders or change any real-money account.

## July 12, 2026 - Atlas now shows benchmark-specific decision scorecards

New capabilities:

- Add a benchmark-specific paper learning scorecard for `SPY` and `QQQ`.
- Score simulated buys by whether the owned stock beat each benchmark, and
  score simulated trims/exits by whether selling avoided later weakness versus
  each benchmark.
- Show the new scorecard in the dashboard paper-learning panel with judged
  comparisons, working/mixed/lagging counts, working rate, and average decision
  edge.
- Add the same benchmark-specific scorecard to the saved paper-performance
  report and to the staging dashboard verification contract.

Validated result:

- Focused `tests.test_paper_trading`, `tests.test_web_dashboard`, and
  `tests.test_web_cloud` coverage passes with 89 tests.
- Broader focused coverage for `tests.test_paper_strategy`,
  `tests.test_paper_trading`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` passes with 159 tests.
- Cloud Run revision `atlas-dashboard-stg-00116-zv8` is live on image
  `20260712-benchmark-scorecards`.
- The deployed image digest is
  `sha256:80698bcfe94bc080935df38d11b84e8e4d7c921102960593ce18d43dc1285db3`.
- The token-protected dashboard verification endpoint passes on the deployed
  revision and includes the new `benchmark_scorecard` check.
- The daily and weekly Cloud Run jobs were updated to the same image, manual
  executions `atlas-daily-stg-5jshm` and `atlas-weekly-stg-qhfzc` completed
  successfully, and recurring schedules are enabled again.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.

Current boundaries:

- This remains simulated paper-trading attribution only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now measures benchmark-specific decision quality more clearly, but it
  has not yet used those scorecards to retune exit strictness or sector pacing.

## July 12, 2026 - Atlas now explains simulated trim and exit triggers more clearly

New capabilities:

- Add an explicit `Trim trigger` or `Exit trigger` explanation to simulated
  sell recommendations so the owner no longer has to infer why Atlas wants to
  reduce versus fully close a paper position.
- Summarize the sell decision in plain language and list the main supporting
  reasons, including thesis-risk alignment, CRO-style risk-review flags, weak
  current score posture, adverse recent price movement, and cautionary paper-
  learning evidence when present.
- Show the same trigger explanation directly in both the Controls proposal
  cards and the recommendation surfaces, keeping the sell case auditable in
  the main places where Atlas asks for attention.
- Preserve the simpler `trim` versus `exit` action labeling while adding the
  missing decision context needed to understand how Atlas is interpreting
  simulated deterioration.

Validated result:

- Focused `tests.test_owner_controls` and `tests.test_web_dashboard` coverage
  passes for the new sell-trigger explanation layer.
- The broader local owner-controls and dashboard suites pass with 41 tests.

Current boundaries:

- This is a paper-trading explanation improvement only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now explains why it wants to trim or exit, but it does not yet score
  which specific trigger combinations are outperforming or underperforming
  over time for autonomous retuning.

## July 12, 2026 - Atlas now measures which sell-trigger patterns are working

New capabilities:

- Extend the paper-feedback learning layer beyond buy/sell direction and
  projection-driver labels into explicit trim/exit trigger families.
- Classify judged simulated trims and exits into compact trigger patterns such
  as `Confirmation weakness`, `Risk flags`, `Score pressure`, or mixed
  combinations when Atlas is acting from more than one sell pressure at once.
- Rank those sell-trigger patterns by judged working rate so Atlas can see
  which kinds of simulated de-risking are helping most often after the fact.
- Show those trigger-pattern learning cards directly in the dashboard learning
  panel beside the existing buy/sell calibration and projection-driver reads.

Validated result:

- Focused `tests.test_paper_trading` and `tests.test_web_dashboard` coverage
  passes for sell-trigger learning.
- The broader local `tests.test_paper_trading` and `tests.test_web_dashboard`
  suites pass with 48 tests.

Current boundaries:

- This remains simulated paper-learning only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now measure which sell-trigger patterns appear most helpful, but
  it does not yet automatically retune trim or exit aggressiveness from that
  signal.

## July 12, 2026 - Atlas now retunes paper trim timing from judged sell-trigger evidence

New capabilities:

- Feed the new sell-trigger learning back into the existing adaptive paper
  monitor rather than leaving it as dashboard-only insight.
- Let strong judged `Confirmation weakness` trim/exit patterns make Atlas
  escalate review and de-risk a little earlier inside autonomous paper mode.
- Let weak judged `Confirmation weakness` patterns slow those same trim/review
  triggers so Atlas waits for a clearer breakdown before reducing exposure.
- Reuse the existing projection-threshold override path, so both projection-
  driver learning and sell-trigger learning shape one coherent paper monitor.

Validated result:

- Focused `tests.test_paper_trading`, `tests.test_paper_monitor`, and broader
  `tests.test_web_dashboard` coverage pass for the new retuning path.
- The broader local `tests.test_paper_trading`, `tests.test_paper_monitor`,
  and `tests.test_web_dashboard` suites pass with 63 tests.

Current boundaries:

- This remains simulated paper-management only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now retunes paper trim timing from judged sell-trigger evidence, but
  it is still not yet changing real-money behavior or adapting sector-level
  selection logic from this signal.

## July 12, 2026 - Atlas now retunes paper entry selectivity and sizing from judged buy outcomes

New capabilities:

- Add an adaptive entry profile beside the adaptive paper monitor so Atlas can
  change how selective it is on new paper buys from judged buy evidence.
- Let consistently constructive judged buys slightly lower the paper buy-score
  threshold and slightly increase target entry size.
- Let lagging judged buys raise the paper buy-score threshold, reduce target
  entry size, and put more weight on benchmark outperformance and trend
  quality before opening a fresh paper position.
- Feed those overrides through `PaperStrategy.from_account_policy()` so every
  normal strategy run automatically inherits the latest judged buy learning.

Validated result:

- Focused `tests.test_paper_trading` and `tests.test_paper_strategy` coverage
  pass for the adaptive entry profile.
- The broader local `tests.test_paper_trading` and `tests.test_paper_strategy`
  suites pass with 58 tests.

Current boundaries:

- This remains simulated paper-strategy tuning only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now retunes entry selectivity and sizing from judged buy outcomes, but
  it is not yet adapting the maximum new-proposal count or sector-diversity
  pressure from that same learning signal.

## July 12, 2026 - Atlas now retunes paper idea capacity and sector concentration pressure

New capabilities:

- Extend the adaptive entry profile beyond score threshold and sizing into
  portfolio-construction pressure for new paper ideas.
- Let constructive judged buys slightly increase the maximum number of fresh
  paper proposals and slightly loosen the sector-repeat penalty so Atlas can
  press healthy leadership a bit harder.
- Let lagging judged buys reduce concurrent new-idea capacity and strengthen
  the sector-repeat penalty so Atlas spreads risk more carefully when entry
  quality is underperforming.
- Feed those construction overrides through `PaperStrategy.from_account_policy()`
  so normal strategy generation automatically inherits the latest judged buy
  evidence.

Validated result:

- Focused `tests.test_paper_trading` and `tests.test_paper_strategy` coverage
  pass for the construction-pressure overrides.
- The broader local `tests.test_paper_trading` and `tests.test_paper_strategy`
  suites pass with 58 tests.

Current boundaries:

- This remains simulated paper-construction tuning only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now retunes idea capacity and sector concentration pressure from
  judged buy outcomes, but it is not yet adapting daily trade-count limits or
  benchmark selection from that same learning signal.

## July 12, 2026 - Atlas now retunes daily paper trade pressure and benchmark trust

New capabilities:

- Extend the adaptive paper-learning layer beyond entry selectivity and idea
  capacity into daily execution pacing, letting strong judged outcomes lift
  the paper trade cap slightly and lagging outcomes slow the book down.
- Learn which benchmark bar, `SPY` or `QQQ`, best matches recent judged buy
  outcomes rather than always trusting whichever benchmark is strongest on the
  day.
- Feed that adaptive benchmark preference through `PaperStrategy.from_account_policy()`
  so borderline paper entries are judged against the benchmark bar Atlas has
  recently found more informative.
- Keep the benchmark choice auditable through a dedicated benchmark-preference
  profile instead of hiding the change inside opaque strategy heuristics.

Validated result:

- Focused `tests.test_paper_trading` and `tests.test_paper_strategy` coverage
  passes for adaptive daily trade pressure and benchmark preference.
- The broader local `tests.test_paper_trading` and `tests.test_paper_strategy`
  suites pass with 64 tests.

Current boundaries:

- This remains simulated paper-strategy tuning only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now retunes daily trade pressure and benchmark trust from judged paper
  outcomes, with dashboard and report visibility now captured in the next
  capability-log entry.

## July 12, 2026 - Atlas now carries adaptive paper context into dashboard decisions and basis exports

New capabilities:

- Surface adaptive daily trade pressure and benchmark trust directly in the
  owner Controls summary, strategy panel, and proposal cards.
- Add the same adaptive context to holding lifecycle drilldowns so a position
  view explains the current paper pacing and benchmark-trust regime behind
  Atlas's projection.
- Carry the adaptive regime into accountant-style basis-report transaction rows
  and the exported basis CSV beside driver, news event, shares, fill price,
  basis, proceeds, and realized result.
- Preserve weighted-average basis math while adding the adaptive context as
  explanatory metadata for review and auditability.

Validated result:

- Focused `tests.test_paper_trading`, `tests.test_owner_controls`, and
  `tests.test_web_dashboard` coverage passes for the new adaptive visibility
  and export fields.
- The broader local `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_owner_controls`, and `tests.test_web_dashboard` suites pass with
  105 tests.
- Cloud Run revision `atlas-dashboard-stg-00115-xqh` is live on image
  `20260712-adaptive-audit-context`, and the token-protected dashboard
  verification endpoint passes on that revision.
- The final automated staging review passes with fresh successful daily and
  weekly Cloud Run job executions and recurring schedules enabled.

Current boundaries:

- This remains simulated paper-trading visibility and auditability only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now shows and exports the adaptive context in live staging, but final
  owner browser review still depends on the two remaining manual identity
  gates: cross-device owner login and non-owner Google account denial.

## July 10, 2026 - Atlas now uses projection posture inside autonomous paper position management

New capabilities:

- Push the newer `Projection watch` intelligence beyond dashboard explanation
- into the live paper-monitor decision layer locally.
- Combine post-entry benchmark excess, sector breadth, trend regime, trend
  quality, and current news tone into a compact internal projection posture.
- Let Atlas escalate a holding from maintain to review when that projection
  posture is no longer clearly supportive, even before older hard-stop rules
  alone would force the issue.
- Let Atlas trigger a projection-driven trim when benchmark lag since entry,
  weak sector participation, and damaged trend posture all align together.
- Tighten winner-add behavior so Atlas adds to an existing leader only when
  the projection posture is still supportive, sector breadth is healthier, and
  trend quality remains strong enough to justify more exposure.

Validated result:

- Focused `tests.test_paper_monitor`, `tests.test_web_dashboard`, and
  `tests.test_paper_strategy` pass with the new monitor behavior.
- The full local automated test suite now passes with 361 tests.
- Cloud Run service revision `atlas-dashboard-stg-00101-rg4` is live on image
  `20260710-projection-monitor`.
- Manual cloud daily execution `atlas-daily-stg-6fckm` completed successfully
  at `2026-07-11T02:33:53Z`.
- Manual cloud weekly execution `atlas-weekly-stg-4vw4k` completed
  successfully at `2026-07-11T02:29:23Z`.
- The latest archived cloud snapshot
  `research_archive/snapshot_20260711_023331.json` is present after the
  projection-monitor rollout, and the private manifest now reports
  `generated_at` of `2026-07-11T02:33:48+00:00`.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` schedulers are
  enabled again after verification.

Current boundaries:

- This remains simulated paper-position intelligence only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now act on projection posture inside its paper monitor, but the
  dashboard does not yet explicitly label which live review, trim, or add
  decision came from this new projection layer versus an older score, lag, or
  news rule.

## July 10, 2026 - Atlas now labels projection-driven paper actions in the owner dashboard

New capabilities:

- Show a compact decision-driver badge on live Controls cards whenever Atlas
  is acting from the new projection layer rather than only older score, lag,
  or news logic.
- Label projection-driven actions in plain language as `Projection de-risk`,
  `Projection caution`, `Projection leadership`, or
  `Projection-supported add`.
- Prefer the exact projection trigger line as the visible evidence anchor so
  the owner can see whether the decision came from benchmark lag, weaker
  sector breadth, damaged trend posture, or still-supportive continuation.
- Extend this visibility to both ranked `Portfolio action queue` items and
  `Hold-steady holdings`, so projection-led continuation is auditable as well
  as projection-led caution.

Validated result:

- Focused `tests.test_owner_controls` and `tests.test_web_dashboard` pass.
- The full local automated test suite now passes with 363 tests.
- Cloud Run service revision `atlas-dashboard-stg-00102-5gw` is live on image
  `20260710-projection-driver-ui`.
- The deployed image digest is
  `sha256:a7747bc40911b86a768d63afd61d50c5a89382fe74b9f87f02844164e03ea15e`.
- Direct service verification confirms `atlas-dashboard-stg-00102-5gw` as the
  latest ready revision, and `/readyz` returns `{"status":"ready"}`.

Current boundaries:

- This is an owner-visibility and auditability improvement only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The explicit projection-driver labels are live in Controls, but the same
  labels are not yet carried through the Overview portfolio summary, paper
  holding detail dialog, or exported reports.

## July 10, 2026 - Atlas now carries projection-driver labels through paper drilldowns and basis exports

New capabilities:

- Extend the same projection-driver language from Controls into the Overview
  portfolio-focus summary, open holding rows, and the per-position lifecycle
  drilldown.
- Show the autonomous reason consistently as a compact tag such as
  `Projection caution`, `Projection de-risk`, or
  `Projection-supported add` wherever the owner reviews a holding.
- Carry that same driver into the accountant-style accountability report so
  each simulated trade row can name not only the news-event context but also
  the forward-looking projection reason that shaped the decision.
- Export the same driver metadata in the basis CSV through new `Driver` and
  `Driver Detail` columns for outside review.
- Infer the driver labels directly from stored thesis and rationale text so
  Atlas keeps one explanation trail instead of parallel manual annotations.

Validated result:

- Focused `tests.test_web_dashboard`, `tests.test_paper_trading`, and
  `tests.test_owner_controls` pass.
- The full local automated test suite still passes with 363 tests.
- Cloud Run service revision `atlas-dashboard-stg-00103-ppw` is live on image
  `20260710-projection-driver-workflow`.
- The deployed image digest is
  `sha256:c4c98578bd1fe8613d96942a53b7eaa4adf9c85572c6eea824cbaa8ed970effb`.
- Direct service verification confirms `atlas-dashboard-stg-00103-ppw` as the
  latest ready revision, and `/readyz` returns `{"status":"ready"}`.

Current boundaries:

- This remains an owner-visibility and auditability improvement only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Projection-driver labels are now visible through Overview, holding
  drilldowns, and basis export surfaces, but trade-history cards and saved
  paper-performance artifacts still have room to carry the same labels more
  explicitly.

## July 10, 2026 - Atlas now preserves projection-driver labels in recent activity and saved paper reports

New capabilities:

- Extend the same projection-driver badges into the live recent-activity feed
  and grouped trade-history workflow, so historical simulated buys, trims, and
  exits keep the same autonomous explanation visible.
- Carry the same driver labels into the saved `performance.md` artifact by
  adding a `Driver` column to the `Recent Execution Context` table.
- Keep the durable performance report aligned with the live dashboard instead
  of forcing the owner to infer whether an execution came from projection-led
  caution, de-risking, or supportive continuation.
- Reuse the same shared inference helper, so recent activity, grouped trade
  history, accountability exports, and saved reports all read from one
  consistent explanation model.

Validated result:

- Focused `tests.test_paper_trading` and `tests.test_web_dashboard` pass.
- The full local automated test suite still passes with 363 tests.
- Cloud Run service revision `atlas-dashboard-stg-00104-nzq` is live on image
  `20260710-projection-driver-history`.
- The deployed image digest is
  `sha256:6e2ba3a01ee62d82bb4becc706390b01c9b16fbd83d01bd7285c94ec6fff58f2`.
- Direct service verification confirms `atlas-dashboard-stg-00104-nzq` as the
  latest ready revision, and `/readyz` returns `{"status":"ready"}`.

Current boundaries:

- This remains an owner-visibility and auditability improvement only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas now preserves projection-driver labels through most live and saved
  paper-review surfaces, but the post-trade learning summaries still do not
  yet break out which projection-led decisions are outperforming or lagging
  over time.

## July 11, 2026 - Atlas now measures which projection-driven paper decisions are working

New capabilities:

- Extend the paper-feedback learning layer so Atlas can compare judged
  simulated outcomes by projection driver rather than only by buy versus sell.
- Track working, mixed, and lagging judged trades for projection-led patterns
  such as `Projection-supported add` and `Projection caution`.
- Show compact working-rate cards for recent projection drivers directly in the
  owner dashboard's learning panel.
- Add learning takeaways that explicitly name the strongest and weaker recent
  projection reads instead of leaving that comparison implicit.
- Carry the same projection-driver badge into executed feedback rows so the
  detailed learning view matches the learning-summary breakdown.

Validated result:

- Focused `tests.test_paper_trading` and `tests.test_web_dashboard` pass.
- The full local automated test suite still passes with 363 tests.
- Cloud Run service revision `atlas-dashboard-stg-00105-xdg` is live on image
  `20260711-projection-learning`.
- The deployed image digest is
  `sha256:0c09091ad011f782afb8bb009d449b8997353b6dd9be26abe6da853801305253`.
- Direct service verification confirms `atlas-dashboard-stg-00105-xdg` as the
  latest ready revision, and `/readyz` returns `{"status":"ready"}`.

Current boundaries:

- This remains an owner-visibility and learning-readout improvement only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now tell which recent projection-driven patterns appear to be
  working best, but it does not yet automatically retune autonomous thresholds
  or execution aggressiveness from that learning signal.

## July 6, 2026 - Atlas now projects what each open holding needs to do next

New capabilities:

- Add a `Projection watch` block to each open paper holding drilldown so Atlas
  can move beyond retrospective explanation into a first owner-visible
  predictive posture.
- Combine trend posture, benchmark-relative return since entry, same-day
  confirmation, sector breadth, and company-news tone into a near-term
  forward read.
- Tell the owner whether Atlas currently favors continued leadership, wants
  more proof before trusting upside, or sees elevated stall, trim, or exit
  risk.
- Surface concrete watchpoints such as holding the 50-day trend cushion,
  keeping benchmark confirmation positive, monitoring thinning sector breadth,
  or reacting quickly to an adverse company-news shift.

Validated result:

- Focused `tests.test_web_dashboard` coverage passes for the new projection
  layer.
- The full local automated test suite passes with 359 tests.
- Cloud Run service revision `atlas-dashboard-stg-00100-xrb` is live on image
  `20260706-position-projection-watch`.
- Manual cloud daily execution `atlas-daily-stg-wnp4r` completed successfully
  at `2026-07-07T02:57:55Z`.
- Manual cloud weekly execution `atlas-weekly-stg-8nhdp` completed
  successfully at `2026-07-07T02:54:01Z`.
- The latest archived cloud snapshot
  `research_archive/snapshot_20260707_025733.json` is present after the
  projection-watch rollout, and the private manifest now reports
  `generated_at` of `2026-07-07T02:57:51+00:00`.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` schedulers are
  enabled again after verification.

Current boundaries:

- This remains simulated paper-position intelligence only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas can now describe what it wants to see next, but those projection
  watchpoints are not yet directly wired into new autonomous add, trim, or
  de-risk thresholds.

## July 6, 2026 - Atlas now distinguishes genuine leadership from simple market lift in holding drilldowns

New capabilities:

- Add an `Outcome framing` layer to each open paper holding so Atlas can judge
  whether a name is outperforming because it is truly leading or simply rising
  with a strong market tape.
- Compare each holding's return since its latest open buy fill with the
  stronger of `SPY` or `QQQ` over the same post-entry window.
- Label the result in plain language such as `genuine leader`, `modestly ahead
  of the market`, or `rising less than the market since entry`.
- Carry current sector-average context and same-day benchmark confirmation into
  that explanation so the owner can see both the holding's lifecycle result
  and whether today's tape is still supporting it.

Validated result:

- Focused `tests.test_web_dashboard` coverage passes for the new
  benchmark-relative holding-outcome language.
- The full local automated test suite passes with 359 tests.
- Cloud Run service revision `atlas-dashboard-stg-00099-nhl` is live on image
  `20260706-position-outcome-framing`.
- Manual cloud daily execution `atlas-daily-stg-68f94` completed successfully
  at `2026-07-07T02:41:03Z`.
- Manual cloud weekly execution `atlas-weekly-stg-6w5gh` completed
  successfully at `2026-07-07T02:43:07Z`.
- The latest archived cloud snapshot
  `research_archive/snapshot_20260707_024041.json` is present after the
  outcome-framing rollout, and the private manifest now reports
  `generated_at` of `2026-07-07T02:41:00+00:00`.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` schedulers are
  enabled again after verification.

Current boundaries:

- This improves simulated holding explainability and benchmark accountability
  only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Atlas is now better at naming true leadership versus market lift, but it is
  still not yet making an explicit forward projection about what needs to
  happen next for a holding to keep working.

## July 6, 2026 - Atlas now carries news-event context, trend diagnostics, and confirmation context through drilldowns and exports

New capabilities:

- Move beyond simple positive/negative headline matching across the live Atlas
  research, dashboard, decision, and reporting flow.
- Classify company-news headlines into more informative event types including
  `earnings_beat`, `earnings_miss`, `guidance_raise`, `guidance_cut`,
  `analyst_upgrade`, `analyst_downgrade`, `product_launch`, `contract_win`,
  `approval`, `legal_risk`, and `offering_or_dilution`.
- Weight headlines modestly by source so Atlas treats a Reuters or Bloomberg
  event as more informative than a lighter secondary source.
- Preserve richer `news_signal` fields such as weighted positive/negative
  totals, high-impact event counts, a dominant event type, and a compact
  headline-event summary list.
- Let the paper strategy block an otherwise strong simulated buy when a single
  high-impact negative event, such as legal risk or a guidance cut, is already
  present.
- Let the open-position monitor escalate that same high-impact news risk into
  a review or trim without waiting for multiple negative headlines to stack up.
- Show the dominant event class directly in dashboard and controls news
  summaries so Atlas explains whether the tone is being driven by a product
  launch, analyst action, guidance change, legal risk, or something routine.
- Carry inferred event summaries into the saved paper performance report and
  accountability report so exported artifacts stay aligned with the live owner
  experience and autonomous paper-decision trail.
- Extend the same event context into the paper position-detail drilldown and
  basis-report workflow, including a `News event` field on transaction-level
  execution rows.
- Add a trend-diagnostics block to each holding lifecycle drilldown so Atlas
  can expose trend quality, regime, moving-average posture, RSI, EMA slope,
  and distance from the 52-week high beside the execution journal.
- Add a sector-and-benchmark confirmation block to the same holding drilldown
  so Atlas can show whether a move is being confirmed by the holding's sector
  and the broader benchmark tape.

Validated result:

- Focused tests pass for `tests.test_news_data`,
  `tests.test_paper_strategy`, `tests.test_paper_monitor`,
  `tests.test_web_dashboard`, `tests.test_owner_controls`,
  `tests.test_paper_trading`, and `tests.test_paper_trading_cli`.
- The full local automated test suite passes with 359 tests.

Current boundaries:

- Cloud Run service revision `atlas-dashboard-stg-00098-q8h` is live on image
  `20260706-position-confirmation-drilldown`.
- Manual cloud daily execution `atlas-daily-stg-7lxgs` completed successfully
  at `2026-07-07T02:24:53Z`.
- Manual cloud weekly execution `atlas-weekly-stg-gkmw6` completed
  successfully at `2026-07-07T02:26:24Z`.
- The latest archived cloud snapshot
  `research_archive/snapshot_20260707_022430.json` is present after the latest
  confirmation-drilldown rollout, and the private manifest now reports
  `generated_at` of `2026-07-07T02:24:49+00:00`.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` schedulers are
  enabled again after verification.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The news model is still intentionally lightweight keyword classification; it
  is more informative than before, but it is not a full NLP event-severity or
  credibility model.

## July 6, 2026 - Atlas now shows company-news tone in the owner dashboard

New capabilities:

- Surface the persisted `news_signal` directly in the Overview paper-focus
  panel, open paper-position rows, ranked Controls queue, hold-steady holdings,
  and paper proposal cards.
- Explain whether recent company-specific news is supportive, constructive,
  neutral, cautious, or adverse without forcing the owner to infer it from the
  raw research snapshot.
- Keep the same news-summary wording consistent across the dashboard and
  Controls surfaces so Atlas tells the same story whether the owner is looking
  at a holding, a trim/exit queue item, or a new paper proposal.

Validated result:

- Focused tests for `tests.test_web_dashboard` and `tests.test_owner_controls`
  pass.
- The full local automated test suite passes with 355 tests.
- Cloud Run service revision `atlas-dashboard-stg-00091-bmz` is live on image
  `20260706-dashboard-news-tone`.
- `/readyz` returns `{"status":"ready"}` after deployment verification.

Current boundaries:

- This is an owner-visibility and explainability improvement only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The displayed news layer is still based on lightweight headline
  classification rather than deeper event severity or source weighting.

## July 5, 2026 - Atlas now monitors company news as an input to paper decisions

New capabilities:

- Refresh cached company-news headlines for held names, large movers, and top
  ranked candidates during the daily Atlas run.
- Classify recent company-news tone into a compact `news_signal` with positive
  and negative counts, a normalized score, and supportive, constructive,
  cautious, neutral, or adverse labels.
- Let the paper strategy use this signal to slightly improve candidate ranking,
  block new simulated buys when company-specific news is clearly adverse, and
  strengthen simulated sell logic when weak benchmark-relative performance is
  confirmed by negative headlines.
- Let the open-position monitor escalate review or trim behavior when multiple
  recent company-specific negative headlines reinforce a weakening thesis.
- Preserve `news_signal` inside structured research snapshots so future cloud
  runs can expose this layer through the archive and dashboard instead of using
  it only transiently during execution.

Validated result:

- Focused tests pass for `tests.test_news_data`,
  `tests.test_paper_strategy`, `tests.test_paper_monitor`, and
  `tests.test_research_memory`.
- The full local automated test suite passes with 354 tests.
- Cloud Run service revision `atlas-dashboard-stg-00090-rv7` is live on image
  `20260705-news-audit`.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` both point to image
  `20260705-news-audit`.
- Manual cloud daily execution `atlas-daily-stg-4pfbw` completed successfully
  on July 5, 2026 and published a new private manifest at
  `2026-07-06T02:40:59Z`.
- The latest archived cloud snapshot `snapshot_20260706_024044.json` now
  preserves `news_signal` for live tracked names, confirming that news-aware
  paper decisions are audit-visible in cloud artifacts and not only used
  transiently during execution.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` schedulers are
  enabled again after verification.

Current boundaries:

- This remains simulation-only paper trading logic.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The current signal is intentionally lightweight headline classification; it
  improves context and gating, but it is not yet a full event-severity or
  source-weighting model.

## July 5, 2026 - Atlas now manages open paper positions more proactively

New capabilities:

- Add a first position-management layer on top of Atlas entry and exit logic.
- Escalate repeated review-level weakness into an automatic simulated trim
  proposal instead of waiting only for a full hard-exit trigger.
- Add a winner-add rule so Atlas can open a follow-on simulated buy proposal
  for a held name that continues to outperform after entry with enough
  post-entry confirmation.
- Keep this logic inside the normal risk-review and proposal pipeline so Atlas
  still records review, risk, approval, and execution steps before changing
  simulated exposure.

Validated result:

- The full local automated test suite passes with 350 tests, including new
  coverage for winner-add proposals and repeated-review trim escalation.
- Cloud Run service revision `atlas-dashboard-stg-00088-z5f` is live on image
  `20260705-position-management`.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image.
- Manual daily execution `atlas-daily-stg-p8zdn` completed successfully on
  July 6, 2026.
- That live run used the new position-management logic to trim `KLAC` from 19
  simulated shares to 9.5 shares after repeated review-level weakness and
  benchmark lag, increasing cash to `$57,354.78` and bringing realized gain or
  loss to `-$426.88`.
- `/readyz` remained healthy after deployment, and both recurring schedulers
  are enabled again.

Current boundaries:

- This remains simulation-only paper trading logic.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The new winner-add path is available, but whether Atlas actually adds to a
  position still depends on strong live post-entry leadership rather than a
  forced activity target.

## July 5, 2026 - Live paper performance now stays in sync after autonomous trades

New capabilities:

- Refresh the paper-performance snapshot and saved `performance.md` report
  after the autonomous paper-management cycle runs, so the dashboard no longer
  shows a stale pre-trade book after Atlas executes its own simulated buys or
  sells.
- Keep the paper account, performance report, and cloud bundle aligned when
  autonomous exits happen during the same daily run.

Validated result:

- The full local automated test suite still passes with 348 tests.
- Cloud Run service revision `atlas-dashboard-stg-00087-q79` is live on image
  `20260705-posttrade-sync`.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image.
- Manual daily execution `atlas-daily-stg-hzqxn` completed successfully on
  July 5, 2026.
- The latest private bundle now shows the autonomous `NVDA` exit consistently
  across `paper_trading/account.json` and `paper_trading/performance.md`,
  including realized loss, updated cash, and removal of `NVDA` from open
  position attribution.
- Both recurring schedulers are enabled again after manual verification.

Current boundaries:

- This remains simulation-only paper trading logic.
- Real trading remains disabled.
- Brokerage access remains disabled.
- Thesis-review rows may still include same-run review context for a name that
  was exited later in that run, which is acceptable but can be refined later.

## July 5, 2026 - Autonomous paper selection now uses persistence and breadth confirmation

New capabilities:

- Add benchmark-breadth confirmation across `SPY`, `QQQ`, `IWM`, and `RSP`
  so Atlas can tell the difference between broad market strength, broad
  weakness, and mixed tape.
- Add sector-breadth scoring so each candidate now measures how many names in
  its sector are participating, not just the sector's average move.
- Add a multi-day `persistence_score` built from 1-month, 3-month, and
  6-month returns, EMA slope, price versus moving averages, and short-drawdown
  context.
- Use breadth and persistence in autonomous paper-buy ranking, cautious-market
  buy gating, and exit escalation so Atlas prefers leadership that is holding
  up across more than one day and cuts weaker names faster when participation
  breaks down.
- Preserve more rationale detail in stored paper recommendations and proposals
  so the dashboard can show the added sector-breadth, persistence, and
  follow-through explanation directly.

Validated result:

- The full local automated test suite passes with 348 tests, including updated
  paper-strategy coverage for persistence preference, thin-sector blocking,
  and breadth-aware exit escalation.
- Cloud Run service revision `atlas-dashboard-stg-00086-cfh` is live on image
  `20260705-persistence-breadth`.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image.
- Manual daily execution `atlas-daily-stg-wcw9d` completed successfully in
  4 minutes 34.23 seconds on July 5, 2026.
- Manual weekly execution `atlas-weekly-stg-dddr7` also completed
  successfully after the job update.
- `/readyz` returned `{"status":"ready"}` after deployment verification, and
  both recurring schedulers are enabled again.

Current boundaries:

- This remains simulation-only paper trading logic.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The new confirmation layer should improve autonomous trade quality, but live
  trade count still depends on actual market conditions rather than forced
  activity.

## July 5, 2026 - Autonomous paper selection now uses sector rotation and follow-through

New capabilities:

- Add sector-rotation context to Atlas paper selection so each candidate now
  measures how its sector is performing relative to the active benchmark.
- Add a `follow_through_score` that blends Atlas score, daily move,
  benchmark-relative strength, sector-relative strength, trend quality, and
  trend regime confirmation.
- Use these new signals in paper-buy ranking, buy gating, and exit escalation
  so Atlas prefers stronger leadership and cuts weaker laggards faster.
- Explain sector rotation and follow-through directly in paper-buy rationale
  and sell thesis text so autonomous decisions are easier to audit.

Validated result:

- Local automated tests now pass with 345 checks, including new coverage for
  sector-leader preference, weak follow-through blocking, and sector/follow-
  through exit escalation.
- Cloud Run service revision `atlas-dashboard-stg-00085-l78` is live on image
  `20260705-rotation-followthrough`.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image.
- Manual daily execution `atlas-daily-stg-vz7ld` completed successfully on
  July 5, 2026 after the job update.

Current boundaries:

- This remains simulation-only paper trading logic.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The new signals should make Atlas more selective and more responsive, but
  actual buy and sell counts still depend on live market conditions.

## July 5, 2026 - Paper Portfolio now exposes accountant-style basis reporting

New capabilities:

- Add an `Open basis report` workflow to the Paper Portfolio page so Atlas can
  show every simulated buy, trim, and sell with timestamp, shares, fill price,
  gross amount, basis per share, basis amount, proceeds, realized gain or
  loss, and remaining position size.
- Summarize each ticker with total bought shares, sold shares, open shares,
  weighted-average cost, open basis, and realized gain or loss so the owner
  can review the paper ledger like a tax-lot accountability report.
- Export the same drill-down detail to `atlas-paper-basis-report.csv` for
  outside review by an accountant or anyone who needs purchase-date and cost-
  basis support.

Validated result:

- Focused automated tests pass for `tests.test_paper_trading` and
  `tests.test_web_dashboard`, covering weighted-average basis math plus the
  dashboard payload and UI strings.
- Cloud Run service revision `atlas-dashboard-stg-00083-hmn` is live on image
  `20260705-basis-report`.
- The staging readiness endpoint returned `{"status":"ready"}` on July 5,
  2026 after deployment verification.

Current boundaries:

- This report covers the Atlas simulated paper ledger only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The report uses weighted-average cost accounting for the paper account rather
  than broker-specific tax-lot election logic.

## July 5, 2026 - Regime-Aware Autonomous Paper Selection

New capabilities:

- Add richer trend-regime measurements to Atlas momentum analysis, including
  price distance versus key moving averages, shorter drawdown context, and a
  derived `trend_regime_score`.
- Classify each name into clearer internal posture states such as
  `leadership`, `constructive`, `repair`, `fragile`, or `breakdown`.
- Make the autonomous paper strategy react to broad benchmark regime, not just
  raw score and one-day relative strength.
- Tighten paper-buy entry standards during mixed or weak benchmark conditions
  and escalate exit candidates faster when a held name breaks down against the
  benchmark backdrop.

Validated result:

- Local tests now pass with 340 automated checks.
- Cloud Run service revision `atlas-dashboard-stg-00082-cd4` is live on image
  `20260705-regime-strategy`.
- Cloud job execution `atlas-daily-stg-ng595` completed successfully on the
  same image digest after deployment.
- The latest private snapshot `snapshot_20260705_180651.json` reports
  `universe_version=1.7`, `tracked=140`, and `available=140`.
- Live benchmark ETF artifacts now include regime-aware trend fields, for
  example `SPY`, `IWM`, and `RSP` showing `trend_regime=leadership` in the
  latest cloud snapshot.
- Daily and weekly schedulers remain enabled after deployment.

Current boundaries:

- Real trading remains disabled.
- Brokerage access remains disabled.
- This stage improves autonomous decision quality and benchmark awareness, but
  the latest live run still found no new simulated buy or exit strong enough to
  act on.
- The next likely lever is to increase signal breadth further with more
  relative-strength, rotation, or follow-through context instead of simply
  forcing trades.

## July 5, 2026 - Autonomous Scheduling And Broader Market Rotation Coverage

New capabilities:

- Expand Atlas from 125 to 140 tracked securities in `Atlas Universe v1.7`.
- Add broad-market, style, and sector ETFs so Atlas can compare leadership
  shifts across financials, energy, healthcare, industrials, staples,
  utilities, materials, real estate, communications, small caps, equal-weight,
  value, growth, and dividend quality.
- Keep the secure owner dashboard autonomous by enabling the paused daily and
  weekly Cloud Scheduler jobs again after the owner explicitly approved
  unattended operation.

Validated result:

- `data/security_universe.json` now reports version `1.7`.
- The full automated test suite still passes locally with 336 tests.
- Cloud Run service revision `atlas-dashboard-stg-00081-qp9` is live on image
  tag `20260705-universe-v17`.
- Cloud Run job execution `atlas-daily-stg-fmtsj` completed successfully on
  July 5, 2026 and published a fresh private snapshot with
  `universe_version=1.7`, `tracked=140`, and `available=140`.
- The persisted paper-account policy remains in aggressive autonomous mode:
  auto-manage enabled, 5 buy slots, 6% target size, 84 buy threshold, 58 exit
  threshold, 2.4 benchmark weight, 0.35 trend weight, 1.5 sector-repeat
  penalty, and a -6% daily downside filter.
- `atlas-daily-stg` and `atlas-weekly-stg` schedulers are now `ENABLED`
  again in `America/Los_Angeles`.

Current boundaries:

- Real trading remains disabled.
- Brokerage access remains disabled.
- The broader universe and autonomous scheduling increase Atlas activity
  potential, but the latest live cycle still did not generate new paper buy or
  exit proposals.
- The next practical lever is better signal sensitivity, especially stronger
  trend and regime detection rather than lowering quality thresholds too far.

## July 4, 2026 - Owner-Editable Autonomous Paper Strategy

New capabilities:

- Adjust Atlas paper-autonomy settings directly from the secure owner dashboard
  without editing local files or redeploying code.
- Enable or disable autonomous paper management from the Controls page.
- Tune buy-slot count, target position size, buy threshold, exit threshold,
  benchmark weighting, trend weighting, sector-repeat pressure, and the daily
  downside filter in one owner-only form.
- Apply a more aggressive paper preset that is explicitly designed to pursue
  more autonomous buy and sell activity while staying simulation-only.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00079-6k7` is serving the live
  strategy editor.
- The owner workspace policy was updated live to an aggressive autonomous
  paper preset: auto-manage on, 5 buy slots, 6% target size, 84 buy
  threshold, 58 exit threshold, 2.4 benchmark weight, 0.35 trend weight,
  1.5 sector-repeat penalty, and a -6% daily downside filter.
- Cloud execution `atlas-daily-stg-284c4` completed successfully after the
  strategy change and refreshed the live workspace at 5:38 PM Pacific.

Current boundaries:

- Real trading remains disabled.
- Brokerage access remains disabled.
- Strategy tuning changes Atlas paper behavior only.
- The latest aggressive run still produced no new paper proposals, so broader
  universe expansion is the next likely path to more autonomous activity.

## July 5, 2026 - Cross-Sector Universe Expansion

New capabilities:

- Expand Atlas from 100 to 125 tracked securities in `Atlas Universe v1.6`.
- Add more liquid leaders across industrials, infrastructure, energy majors,
  consumer staples, healthcare, data-center and wireless infrastructure, and
  materials.
- Give the autonomous paper engine a broader opportunity set outside its
  original AI- and IT-heavy concentration while keeping the focus on large,
  liquid, benchmark-comparable names.

Validated result:

- `data/security_universe.json` now reports version `1.6`.
- The expanded universe contains 125 unique tickers and passed duplicate and
  structural validation.
- The full automated test suite passes locally with 336 tests.

Current boundaries:

- This is still a research and paper-simulation coverage expansion only.
- Real trading remains disabled.
- Brokerage access remains disabled.
- The broader universe should improve Atlas opportunity discovery, but actual
  autonomous paper activity still depends on daily signals and paper policy.

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

## June 25, 2026 - Paper Activity And Operating Modes

New capabilities:

- Add a Paper Portfolio activity feed that explains what Atlas bought and sold
  in simulation, with thesis text and up to three rationale bullets for each
  completed paper trade.
- Distinguish executed paper sells from trims and full exits using simulated
  holding context captured at execution time.
- Add a portfolio operating-mode section that makes the current
  recommendation-only workflow explicit while showing a future paper-only
  auto-manage mode as part of the roadmap.

Validated result:

- Dashboard image `20260625-paper-activity` is deployed.
- The Paper page now exposes both an executed paper activity audit and a
  portfolio operating-mode section.
- The full automated test suite passes with 302 tests.

Current boundaries:

- Atlas is still operating in recommendation mode today; it does not
  auto-execute paper trades on its own.
- The new activity feed describes simulated portfolio actions only.
- Real-money auto-trading remains disabled.

## June 25, 2026 - Sell-Side Intelligence Clarification

New capabilities:

- Make paper trim and exit reviews explain the actual trigger that caused the
  sell-side proposal instead of relying on a generic weakness message.
- Let daily thesis monitoring accumulate multiple review reasons at once, so a
  name can surface both score weakness and drawdown pressure in the same owner
  review.
- Rewrite sell-side thesis text so Atlas states whether it currently wants to
  review, reduce, or exit a simulated holding, including benchmark-lag context
  when it applies.
- Update the Paper page rationale labels so completed and pending sell-side
  actions read as `Why trim` or `Why exit` instead of a generic reduce label.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00044-xsg` is serving 100% traffic.
- Dashboard image `20260625-sell-intelligence` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 303 tests.

Current boundaries:

- Atlas still proposes and explains paper trims and exits; it does not
  auto-execute them.
- The new sell-side intelligence applies to simulated holdings only.
- No brokerage order is sent and no real money is spent.

## June 25, 2026 - Sell Decision Learning

New capabilities:

- Extend the paper feedback loop so Atlas now evaluates executed simulated
  trims and exits, not just simulated buys.
- Compare each completed simulated sell against the later market move in that
  same security, creating a counterfactual view of whether Atlas helped by
  exiting early or reduced exposure too soon.
- Keep benchmark context alongside the post-sell move so the owner can judge
  whether a sell decision helped, lagged, or produced a mixed result relative
  to SPY and QQQ.
- Update the Paper page language so the learning panel now clearly covers
  simulated buys, trims, and exits.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00045-b2l` is serving 100% traffic.
- Dashboard image `20260625-sell-learning` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 305 tests.

Current boundaries:

- Atlas still evaluates simulated sells after the fact; it does not use this
  learning to auto-execute paper trades.
- The learning panel remains simulation-only and does not evaluate real-money
  brokerage outcomes.
- No brokerage order is sent and no real money is spent.

## June 25, 2026 - Paper Learning Summary

New capabilities:

- Turn the Paper Portfolio learning section into an at-a-glance summary instead
  of requiring the owner to scan every post-trade feedback row manually.
- Show a headline readout of whether recent simulated paper decisions are
  leaning constructive, balanced, or slipping.
- Break learning into clear working, mixed, and lagging counts plus separate
  buy and sell calibration cards.
- Keep plain-language takeaways that explain how many judged simulated buys are
  working and how many judged trims or exits are helping.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00046-7lg` is serving 100% traffic.
- Dashboard image `20260625-learning-summary` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 306 tests.

Current boundaries:

- Atlas now summarizes paper learning more clearly, but it still does not
  auto-execute paper trades.
- The new calibration summary remains simulation-only and does not evaluate
  real-money brokerage outcomes.
- No brokerage order is sent and no real money is spent.

## June 27, 2026 - Recommendation Calibration From Paper Learning

New capabilities:

- Use recent simulated paper outcomes to calibrate active paper proposals
  instead of showing every new buy or sell idea without recent learning
  context.
- Add a plain-language `Paper learning` line to active recommendation cards and
  owner-control proposal cards so the owner can see whether similar simulated
  ideas have been supportive, cautionary, or still too early to judge.
- Distinguish buy-side calibration from sell-side calibration and retain
  ticker-specific context when Atlas has judged prior simulated outcomes in the
  same name.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00047-cgr` is serving 100% traffic.
- Dashboard image `20260627-paper-calibration` is deployed.
- `/readyz` returns `{"status":"ready"}`.
- Daily and weekly schedules remain enabled.
- The full automated test suite passes with 308 tests.

Current boundaries:

- Atlas now calibrates recommendation framing from simulated outcomes, but it
  still does not auto-execute paper trades.
- The new recommendation calibration remains simulation-only and does not
  evaluate real-money brokerage outcomes.
- No brokerage order is sent and no real money is spent.

## 2026-06-27 - Paper learning now prioritizes recommendations

New capabilities:

- Use paper-learning calibration to sort recommendation queues within each
  existing workflow stage instead of only showing a learning note inside each
  card.
- Keep approved buys ahead of pending buys, trims, and exits, while lifting the
  stronger paper-backed ideas to the top within each stage.
- Surface the same calibrated ordering in the `Atlas focus right now` summary,
  including judged-outcome counts when Atlas has enough evidence.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00049-74x` is serving 100% traffic.
- Dashboard image `20260627-recommendation-ranking` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 308 tests.

Current boundaries:

- Atlas still requires explicit owner approval before any paper buy, trim, or
  exit can be simulated.
- Recommendation ranking is now learning-aware, but it still remains
  simulation-only and does not send any real-money brokerage order.

## 2026-06-27 - Recommendation explanations now survive legacy proposals

New capabilities:

- Backfill structured rationale for older paper proposals using current score,
  category, sector, move, sizing, risk-review, and paper-learning context.
- Prefer real explanatory text in the web client before ever falling back to a
  generic placeholder, so the live Recommendations page stays readable even for
  legacy proposal records.
- Reuse proposal thesis as a safe user-facing fallback when structured
  rationale is missing, which removes the weakest `Awaiting rationale` owner
  experience from the live dashboard.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00051-2cc` is serving 100% traffic.
- Dashboard image `20260627-rationale-live` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 310 tests.

Current boundaries:

- Atlas explanations are now more usable for older paper ideas, but they still
  remain recommendation and simulation guidance only.
- No brokerage order is sent and no real capital is moved.

## 2026-06-27 - Recommendations now present the counter-case too

New capabilities:

- Add a structured `Why not` section for simulated buy recommendations so Atlas
  can surface the strongest reasons to hesitate, not just the reasons to act.
- Add a structured `What could go wrong` section for trim and exit proposals so
  simulated sell decisions also show the downside of acting too early or too
  aggressively.
- Use risk-review flags, conviction level, recent move quality, category, and
  paper-learning scarcity/caution to build these objections automatically.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00052-nlm` is serving 100% traffic.
- Dashboard image `20260627-why-not` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 310 tests.

Current boundaries:

- Atlas now frames both the pro case and the caution case, but the result is
  still a simulation-only research recommendation.
- No brokerage order is sent and no real capital is moved.

## 2026-06-27 - Recommendation objections now cite Atlas research memory

New capabilities:

- Add memory-aware recommendation objections so `Why not` and `What could go
  wrong` can cite Atlas's own prior risk-to-thesis reviews for the same
  security instead of relying only on generic conviction warnings.
- Surface recent disconfirming evidence titles from the latest completed Atlas
  research task when that ticker already has stored thesis-risk context.
- Make the latest research-context selection deterministic by preferring the
  most recently appended completed ticker review, which avoids same-second
  timestamp ties in both tests and live data.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00053-kr9` is serving 100% traffic.
- Dashboard image `20260627-memory-objections` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 310 tests.

Current boundaries:

- Atlas can now explain the counter-case with better internal evidence, but it
  is still a recommendation and paper-trading system rather than a live
  brokerage executor.
- No brokerage order is sent and no real capital is moved.

## 2026-06-27 - Paper Portfolio now shows thesis memory and execution context

New capabilities:

- Add Atlas research-memory summaries to open paper positions so the portfolio
  view can show how much stored thesis history exists for each holding and
  whether the latest review leaned supportive or risk to thesis.
- Enrich executed paper activity with an `Atlas context` block that surfaces
  execution-time risk-review flags, latest stored thesis alignment, and recent
  evidence titles from Atlas research memory.
- Preserve the paper ledger as the source of record while enriching the
  browser-facing dashboard model with current research context at render time.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00054-xw8` is serving 100% traffic.
- Dashboard image `20260627-activity-context` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 311 tests.

Current boundaries:

- Atlas now explains open simulated holdings and executed paper trades with
  more thesis history, but it still remains a paper portfolio and
  recommendation system.
- No brokerage order is sent and no real capital is moved.

## 2026-06-27 - Open positions now show a decision journal

New capabilities:

- Add a `What changed since entry` journal for each open paper position so
  Atlas can summarize basis versus latest price, benchmark-relative movement
  since the latest buy fill, the latest thesis review, and the current
  escalation cue.
- Reuse existing paper-performance snapshots and thesis-review events to build
  this narrative layer without introducing a separate journal datastore.
- Keep the portfolio UI compact while making it much clearer why a holding is
  still a hold, drifting toward review, or already on an escalation path.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00055-49r` is serving 100% traffic.
- Dashboard image `20260627-position-journal` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 311 tests.

Current boundaries:

- Atlas now tells a better hold-to-exit story for open paper positions, but
  this is still simulated portfolio management rather than autonomous live
  trading.
- No brokerage order is sent and no real capital is moved.

## 2026-06-27 - Paper Portfolio now groups positions by next action

New capabilities:

- Add a `Portfolio action ladder` to the Paper Portfolio page so Atlas can
  group open simulated positions into `Hold steady`, `Watch closely`, `Trim
  candidate`, and `Exit candidate`.
- Build the grouping from the live thesis-state labels already attached to each
  position, which keeps the new summary consistent with the underlying position
  rows and research memory.
- Show the highest-priority names in each bucket with compact thesis summaries
  and unrealized gain or loss so the owner can quickly see what Atlas believes
  needs patience versus intervention.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00057-p2s` is serving 100% traffic.
- Dashboard image `20260628-position-ladder` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The live Paper Portfolio page shows the grouped next-action layout, with the
  current simulated book fully in `Hold steady`.
- The focused dashboard test suite passes with 10 tests.
- The full automated test suite passes with 312 tests.

Current boundaries:

- The action ladder improves visibility into what Atlas wants to do next, but
  it still does not autonomously execute any trade.
- Real trading and brokerage access remain disabled.

## 2026-06-27 - Overview now surfaces portfolio focus earlier

New capabilities:

- Add a `Portfolio focus right now` panel to the Overview page so Atlas can
  expose paper-position posture before the owner drills into the Paper
  Portfolio page.
- Reuse the same live thesis-state labels behind the paper ladder to summarize
  the current book with a headline readout, healthy/watch/trim/exit counts,
  and the holdings that need review first.
- Keep the paper-portfolio ladder as the detailed destination while making the
  top-level workspace feel more like a daily operating console.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00058-wjn` is serving 100% traffic.
- Dashboard image `20260628-portfolio-focus` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The live Overview page shows the new portfolio-focus panel with current
  thesis-derived counts and holdings.
- The full automated test suite passes with 313 tests.

Current boundaries:

- Portfolio focus improves visibility into simulated holdings only.
- It does not approve, simulate, or execute any paper or real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-06-27 - Controls now rank paper proposals with open holding posture

New capabilities:

- Add a `Portfolio action queue` to the Controls page so Atlas can rank active
  paper proposals beside already-open simulated holdings that need closer
  review.
- Reuse live thesis-state posture from the paper book and suppress duplicate
  holding entries when an active trim or exit proposal already represents that
  name.
- Keep research decisions separate while making the paper workflow feel like a
  single owner operating queue instead of two disconnected views.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00059-clc` is serving 100% traffic.
- Dashboard image `20260628-controls-queue` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The live Controls page shows the ranked portfolio action queue with 3 current
  items on the present dataset.
- The full automated test suite passes with 315 tests.

Current boundaries:

- The portfolio action queue still ranks simulation-only paper workflow items.
- It does not approve, simulate, or execute any real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-06-28 - Controls now explain healthy holdings outside the action queue

New capabilities:

- Add a `Hold-steady holdings` section to the Controls page so Atlas can show
  which open simulated names are intentionally absent from the ranked action
  queue because they remain healthy.
- Reuse live thesis-state posture, portfolio context, and paper-performance
  context so the owner can understand both the names that need action and the
  names that do not from one control surface.
- Preserve the ranked action queue for proposals and non-healthy holdings while
  giving the owner a fuller paper-book operating picture.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00060-xgt` is serving 100% traffic.
- Dashboard image `20260628-healthy-holdings` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 316 tests.
- Live authenticated verification of the new section in a fresh in-app browser
  session was blocked by a new Google sign-in requirement after browser
  automation state reset.

Current boundaries:

- The healthy-holdings summary explains simulation-only paper positions.
- It does not approve, simulate, or execute any paper or real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-06-28 - Healthy holdings now include hold-state journal context

New capabilities:

- Add compact `What changed since entry` journal context to healthy holdings in
  the Controls workflow.
- Reuse the existing basis, benchmark-relative, latest thesis-review, and
  escalation-cue narrative layer so a healthy simulated position feels
  explained instead of merely labeled.
- Keep the ranked action queue focused on non-healthy or proposal-driven items
  while making the hold-steady section much more informative.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00061-sdr` is serving 100% traffic.
- Dashboard image `20260628-healthy-journal` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 316 tests.

Current boundaries:

- The healthy holding journal is still simulation-only context.
- It does not approve, simulate, or execute any paper or real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-07-02 - Controls now summarize paper-book posture at the section level

New capabilities:

- Add a `Paper book posture` summary to the Controls page so Atlas can explain
  the paper book before the owner scans the ranked queue and hold-steady cards.
- Summarize open holdings, ranked action items, hold-steady names,
  research-review count, and buy versus exit/trim proposal balance in one
  compact control-surface readout.
- Keep the detailed queue and holding cards intact while making the owner
  workflow faster to orient around at a glance.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00062-sj7` is serving 100% traffic.
- Dashboard image `20260702-controls-summary` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 317 tests.

Current boundaries:

- The Controls summary is still a simulation-only paper-book posture readout.
- It does not approve, simulate, or execute any paper or real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-07-02 - Controls summary now points to the freshest paper-book shift

New capabilities:

- Highlight the newest paper-book change directly inside the Controls `Paper
  book posture` summary.
- Distinguish whether the freshest shift belongs to the ranked `Portfolio
  action queue` or the `Hold-steady holdings` bucket.
- Reuse existing proposal-event and thesis-review timestamps so Atlas can
  orient the owner toward the most recent change without adding a new journal
  subsystem.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00063-7t2` is serving 100% traffic.
- Dashboard image `20260702-controls-freshness` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 317 tests.

Current boundaries:

- The freshness cue still summarizes simulation-only paper workflow and paper
  holdings.
- It does not approve, simulate, or execute any paper or real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-07-02 - Controls freshness cue now tags the exact paper-book card

New capabilities:

- Carry the Controls freshness cue from the summary into the exact matching
  `Portfolio action queue` or `Hold-steady holdings` card.
- Visibly tag the referenced queue or hold card as the freshest shift so the
  owner can connect the top-line posture readout to the underlying paper-book
  item immediately.
- Reuse the existing timestamp-derived freshness model instead of introducing a
  separate card-state tracker.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00064-97g` is serving 100% traffic.
- Dashboard image `20260702-controls-linked-freshness` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 317 tests.

Current boundaries:

- The linked freshness tag still applies only to simulation-only paper
  workflow and paper holdings.
- It does not approve, simulate, or execute any paper or real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-07-02 - Controls summary is prepared to jump to the tagged paper-book card

New capabilities:

- Add stable Controls anchor ids for the ranked paper-action cards and
  hold-steady holding cards.
- Prepare the Controls summary to render an `Open item` jump control that
  should move the owner directly to the freshest tagged card.
- Add client-side Controls-page scrolling behavior for this jump path.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00065-lnz` is serving 100% traffic.
- Dashboard image `20260702-controls-jump` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 317 tests.

Current boundaries:

- Local tests confirm the jump metadata and client behavior, but live
  authenticated verification did not yet show the `Open item` control after
  deploy, so this capability is not fully owner-verified in staging yet.
- The jump path still applies only to simulation-only paper workflow and paper
  holdings.
- It does not approve, simulate, or execute any paper or real-money trade.
- Real trading and brokerage access remain disabled.

## 2026-07-03 - Paper portfolio can now auto-manage simulated trades

New capabilities:

- Enable a paper-only `Auto-manage paper portfolio` mode on the simulated
  account policy.
- Let the daily Atlas paper cycle auto-approve clear or caution proposals after
  risk review, auto-reject hold-risk proposals, and auto-record simulated
  fills without waiting for manual owner approval.
- Reflect the active operating mode in the dashboard so the paper workflow can
  show when Atlas is in recommendation mode versus autonomous paper-only mode.
- Reuse the same append-only ledger and proposal linkage so every autonomous
  simulated fill remains auditable.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00068-qzw` is serving 100% traffic.
- Dashboard image `20260703-paper-auto-manage` is deployed.
- The cloud paper-account policy now has `auto_manage_enabled=True`.
- Cloud daily execution `atlas-daily-stg-vccqm` completed successfully after
  the job image update.
- Atlas auto-executed three previously approved simulated buys in cloud paper
  mode: MRVL, TSM, and AMD.
- The live cloud paper portfolio now holds 7 simulated positions.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 322 tests.

Current boundaries:

- Auto-manage applies only to the Atlas simulated paper portfolio.
- Brokerage access and real-money trading remain disabled.
- The current aggressiveness still comes from fixed paper-strategy thresholds;
  future tuning can make selection more or less active without changing the
  real-trading boundary.

## 2026-07-03 - Paper Portfolio now groups buy and sell history by ticker

New capabilities:

- Add a `View trade history` button to the Paper Portfolio execution-audit
  section.
- Open a grouped trade-history dialog that shows each simulated ticker's buy,
  trim, and exit timeline in one place.
- Reuse the append-only paper ledger plus existing execution context so the
  owner can review each name's purchase history without losing thesis and
  rationale notes.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00069-sxh` is serving 100% traffic.
- Dashboard image `20260703-trade-history` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 323 tests.

Current boundaries:

- The history view reports simulated paper trades only.
- It does not create, approve, or execute any real-money brokerage action.
- Real trading and brokerage access remain disabled.

## 2026-07-03 - Paper selection now targets benchmark outperformance across sectors

New capabilities:

- Rank paper-buy candidates using both Atlas score and benchmark-relative daily
  strength versus the stronger of `SPY` or `QQQ`.
- Prefer sector-diverse simulated selections before doubling up in the same
  area, which broadens Atlas beyond AI and IT when stronger opportunities show
  up elsewhere in the covered universe.
- Explain benchmark-relative excess return directly inside paper-buy thesis and
  rationale text so the owner can see why Atlas believes a name is helping the
  paper book try to beat major benchmarks.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00070-pjs` is serving 100% traffic.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` now use image
  `20260703-benchmark-focus`.
- Cloud daily execution `atlas-daily-stg-zw4bc` completed successfully on the
  updated strategy.
- The immediate post-run cloud paper book remained at 7 simulated positions,
  confirming the new ranking logic did not force an unnecessary trade on that
  specific daily snapshot.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The full automated test suite passes with 325 tests.

Current boundaries:

- This benchmark-focused ranking still applies only to the simulated paper
  portfolio.
- Atlas can now pursue broader-sector paper outperformance more explicitly, but
  brokerage access and real-money trading remain disabled.

## 2026-07-04 - Dashboard now explains SPY and QQQ in plain language

New capabilities:

- Label `SPY` in the dashboard as the `S&P 500 ETF benchmark` instead of
  leaving it as an unexplained ticker.
- Label `QQQ` in the dashboard as the `Nasdaq-100 ETF benchmark` and add a
  short plain-language note describing it as the growth and technology
  benchmark Atlas compares against.
- Reuse the expanded benchmark names in paper-feedback rows so return
  comparisons read more clearly when Atlas is judging simulated buys, trims,
  and exits.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00071-n4v` is serving 100% traffic.
- Dashboard image `20260704-benchmark-labels` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The focused web-dashboard test suite passes with 14 tests.
- The full automated test suite passes with 325 tests.

Current boundaries:

- This is a clarity and explainability update only.
- Benchmark labels are clearer, but Atlas still uses them only for simulated
  paper comparison and not for any real-money brokerage action.
- Real trading and brokerage access remain disabled.

## 2026-07-04 - Atlas now scores trend quality, not just simple recent returns

New capabilities:

- Extend `MomentumEngine` with a first pure-Python trend-indicator layer using
  the existing 1-year Yahoo chart history feed.
- Compute and publish additional trend features including `return_12m`,
  `sma_20`, `sma_50`, `sma_200`, `ema_20`, `ema_20_slope_pct`, `rsi_14`,
  `volatility_20d_pct`, `distance_from_52w_high_pct`, `trend_quality_score`,
  and `trend_state`.
- Preserve the old return-based logic as `legacy_momentum_score` while upgrading
  the exported `momentum_score` into a blended composite of legacy momentum and
  the new trend-quality readout.
- Let the paper strategy use `trend_quality_score` as an extra ranking signal
  when candidate scores are otherwise close, and explain the trend state
  directly inside simulated buy rationale text.

Validated result:

- Focused tests pass for `tests.test_momentum`,
  `tests.test_paper_strategy`, and `tests.test_market_data_metadata`.
- The full automated test suite passes locally with 330 tests.

Current boundaries:

- This is still a paper-only research and simulation improvement.
- The new trend signals improve Atlas scoring and simulated selection context,
  but they do not create any brokerage connection or enable real-money trading.
- This update is local in the repo and has not yet been redeployed to Cloud Run
  staging.

## 2026-07-04 - Staging now removes the separate About tab and folds Market into Overview

New capabilities:

- Remove the separate sidebar `About Atlas` entry from the live owner dashboard.
- Keep the Atlas overview page reachable from the top brand/logo link only, so
  the brand acts as the entry point for the product summary.
- Move benchmark performance and breadth charts onto Overview so the owner can
  see portfolio KPIs and market context together on one page.
- Deploy the first trend-quality scoring pass to staging at the same time,
  giving Atlas richer momentum context for simulated paper selection.

Validated result:

- Dashboard revision `atlas-dashboard-stg-00075-njb` is serving 100% traffic.
- Dashboard image `20260704-trend-nav` is deployed.
- `/readyz` returns `{\"status\":\"ready\"}`.
- The live root HTML no longer contains the `About Atlas` tab text or
  `href=\"#market\"`.
- Focused web-dashboard tests pass, and the full automated test suite passed
  locally with 330 tests before deploy.

Current boundaries:

- This remains an owner-only paper-research dashboard update.
- The navigation cleanup, single-page Overview layout, and trend-aware scoring
  still do not enable any brokerage connection or real-money trading.

## 2026-07-11 - Atlas now auto-retunes paper projection thresholds from judged outcomes

New capabilities:

- Add `projection_learning_enabled` and
  `projection_learning_min_judged_trades` to the paper-policy model so Atlas
  can gate adaptive paper retuning behind enough evidence.
- Add `PaperTradingAccount.projection_threshold_profile()` to translate judged
  projection-linked paper outcomes into bounded monitor overrides.
- Tighten winner-add breadth and trend-quality gates when
  `Projection-supported add` trades are lagging, and loosen them slightly when
  those adds are repeatedly confirming.
- Make projection review and trim triggers slightly earlier when projection
  caution sells are helping, and slightly slower when those sells appear too
  early.
- Route `PaperPositionMonitor.from_account(...)` through that adaptive profile
  so the daily paper monitor uses learned thresholds automatically.
- Surface the adaptive projection-tuning status and threshold adjustments in
  the dashboard learning summary so the owner can see when Atlas is watching
  versus actively retuning.

Validated result:

- Focused tests pass for `tests.test_paper_trading`,
  `tests.test_paper_monitor`, and `tests.test_web_dashboard`.
- The full automated test suite passes locally with 366 tests.

Current boundaries:

- This remains simulated paper-trading logic only.
- Real brokerage execution is still disabled, and the new adaptive threshold
  learning has not yet been redeployed to Cloud Run staging.

## 2026-07-11 - Staging now paints the executive dashboard before heavier detail

New capabilities:

- Add a fast `/api/dashboard/summary` read model for the Overview page.
- Split dashboard loading into two stages so Atlas renders top-line executive
  information first, then hydrates slower sections such as trade history,
  accountability, feedback, and owner controls.
- Keep the summary payload focused on the first-paint dashboard essentials:
  market pills, KPIs, benchmark performance, thesis overview, portfolio focus,
  operating mode, and current holdings.
- Preserve the full `/api/dashboard` payload for the richer paper-trading and
  owner-control sections after the initial screen is visible.

Validated result:

- Local timing checks reduced the summary build to about `0.18s` versus about
  `1.12s` for the full payload on the same repo state.
- Cloud Run service revision `atlas-dashboard-stg-00106-vwm` is live on image
  `20260711-dashboard-summary-fast`.
- The image digest is
  `sha256:13408efc01ed5c6ba7de8a8eecf078602bb2c1baec01de1d539d003557fd1c19`.
- `/readyz` returns `{\"status\":\"ready\"}` after deployment verification.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- Focused tests pass for `tests.test_web_dashboard` and
  `tests.test_web_cloud`, and the full automated test suite passes locally
  with 367 tests.

Current boundaries:

- This is still an owner-only dashboard performance improvement on the
  simulated Atlas workspace.
- No real-money trading or brokerage capability was added by this change.

## 2026-07-11 - Staging now serves a slimmer first-paint executive payload

New capabilities:

- Start the full `/api/dashboard` fetch in parallel with the fast summary
  request so Atlas no longer waits on a second network round trip to begin the
  heavy payload.
- Trim the first-paint summary to just the fields the Overview executive page
  actually renders, removing unused watchlist and task-detail data from the
  startup response.

Validated result:

- Local timing checks reduced the summary path from about `0.18s` and
  `22.2 KB` to about `0.11s` and `6.3 KB`.
- Cloud Run service revision `atlas-dashboard-stg-00107-bjn` is live on image
  `20260711-dashboard-summary-slim`.
- The image digest is
  `sha256:aee69dbb31c25eadcb5bc9746fcca722a09af81ff2bd0b336dc30835d4fb7688`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.

Current boundaries:

- This remains a dashboard responsiveness improvement for the owner-only paper
  workspace.
- No brokerage or real-money execution capability changed here.

## 2026-07-11 - Staging now reuses the last executive snapshot before refresh

New capabilities:

- Cache the latest executive dashboard summary in the browser.
- Hydrate the Overview page from that cached summary on startup so Atlas can
  show the last known executive state immediately on repeat visits.
- Refresh the cached summary in place after the network summary and full
  dashboard payload return.

Validated result:

- Cloud Run service revision `atlas-dashboard-stg-00108-gxl` is live on image
  `20260711-dashboard-cached-start`.
- The image digest is
  `sha256:413484d758ef6bb28b6cc1f82c3f7ee8ebc8670c21d431c346f3b09c017a3adf`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- Focused dashboard tests pass, and the full automated test suite remains green
  locally with 367 tests.

Current boundaries:

- This is still a dashboard-load responsiveness improvement only.
- No brokerage connection or real-money trading behavior changed.

## 2026-07-11 - Staging now reuses the last safe full dashboard snapshot

New capabilities:

- Cache the last full dashboard payload for read-only rendering on repeat
  opens.
- Strip cached `owner_controls` state before reuse so all live control actions
  still depend on the fresh authenticated response and current CSRF token.
- Let Atlas restore more of the paper portfolio context immediately, not just
  the executive summary row.

Validated result:

- Cloud Run service revision `atlas-dashboard-stg-00109-nlz` is live on image
  `20260711-dashboard-full-cache-safe`.
- The image digest is
  `sha256:b77068740a3389a8633d86ddf45de6f981668d58ef3665ed40bafcb367a29150`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- Focused dashboard tests pass, and the full automated test suite remains green
  locally with 367 tests.

Current boundaries:

- This remains a startup responsiveness improvement only.
- Owner-control actions still require the fresh live payload and current CSRF
  token.

## 2026-07-11 - Staging now labels cached, refreshing, and live dashboard states

New capabilities:

- Add a top-bar freshness badge for startup and refresh state.
- Label the dashboard as `Cached snapshot`, `Refreshing`, or `Live` so the
  owner can tell when Atlas is showing reused startup data versus the current
  network result.

Validated result:

- Cloud Run service revision `atlas-dashboard-stg-00110-gm5` is live on image
  `20260711-dashboard-freshness-badge`.
- The image digest is
  `sha256:daf10ff1b1af01b6245210ab619b2ff2cb34314708c1d90b2886ad477a38b87e`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- Focused dashboard tests pass, and the full automated test suite remains green
  locally with 367 tests.

Current boundaries:

- This remains a dashboard startup and transparency improvement only.
- No trading logic or owner-control permissions changed.

## 2026-07-11 - Staging now boots from a minimal cloud startup bundle

New capabilities:

- Change Cloud Run startup from a blocking full artifact pull to a minimal
  startup pull.
- Load only the latest research snapshot, paper account, paper ledger, and
  research task file before serving the dashboard.
- Continue the full cloud artifact sync in the background after the service is
  already available.

Validated result:

- Cloud Run service revision `atlas-dashboard-stg-00111-gjj` is live on image
  `20260711-dashboard-startup-bundle`.
- The image digest is
  `sha256:e94abce57b48f6363539069293f88d9bce13464acf45a3be3d262c76956a05a8`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- Focused cloud-storage and dashboard tests pass, and the full automated test
  suite remains green locally with 368 tests.

Current boundaries:

- This remains a cloud dashboard cold-start improvement only.
- No brokerage behavior or owner authorization model changed.

## 2026-07-12 - Stage 5 now learns from sustained paper-trade persistence

New capabilities:

- Store per-snapshot security prices inside paper-performance checkpoints.
- Score executed paper trades at 1-, 3-, and 5-snapshot horizons instead of
  only against the latest available mark.
- Expose persistence-aware Stage 5 validation metrics including judged-trade
  working rate, judged sell help rate, gross turnover, and 3-snapshot
  persistence.
- Surface persistence reads in the dashboard paper-learning section.
- Use 3-snapshot persistence inside owner-control `paper_calibration` so
  sustained winners and laggards can influence the autonomous queue.
- Feed persistence-aware paper learning into `PaperStrategy` so close buy-candidate
  rankings can lean toward setup types that actually held follow-through.

Validated result:

- Cloud Run service revision `atlas-dashboard-stg-00112-k9g` is live on image
  `20260712-stage5-persistence-learning`.
- The image digest is
  `sha256:913f35a98c4db6cd3c9ac06921f825e96c2eb69c0e8ad40a614281bed9743ec4`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- Focused strategy, owner-control, paper-trading, and dashboard tests pass
  locally for the persistence-learning path.

Current boundaries:

- This remains paper-trading validation and owner-dashboard logic only.
- No brokerage connection, real-money order routing, or live-trading authority
  was added.

## 2026-07-12 - Stage 5 learning now changes autonomous paper entry gates

New capabilities:

- Let supportive sustained paper-learning slightly relax otherwise borderline
  buy thresholds in `PaperStrategy`.
- Let cautionary sustained paper-learning block borderline buys when recent
  similar setups failed to hold follow-through.
- Extend the learning loop from measurement and ranking into the actual
  autonomous buy gate.

Validated result:

- Cloud Run service revision `atlas-dashboard-stg-00113-mc8` is live on image
  `20260712-stage5-learning-gate-tuning`.
- The image digest is
  `sha256:e67d14e33f3086bd2b262a9a81fc2d8f40873709d206a78693e33c1113ccc1a7`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- Focused strategy, owner-control, paper-trading, and dashboard tests pass
  locally for the gate-tuning path.

Current boundaries:

- This remains paper-only autonomous learning and validation.
- No brokerage connection, real-money order routing, or live-trading authority
  was added.

## 2026-07-12 - Stage 5 manual staging review now includes the signed-in dashboard walkthrough

New capabilities:

- Add an `owner_dashboard_stage5_review` evidence section to
  `cloud/staging_manual_validation.json`.
- Define the owner-side manual checks for Stage 5 scoreboard visibility,
  persistence-learning reads, benchmark labeling, autonomous queue behavior,
  and lot-level accountability review.
- Extend `scripts/gcp_manual_validation.ps1` with
  `RecordOwnerDashboardReview` so the walkthrough can be recorded with
  timestamped evidence.
- Keep the owner dashboard walkthrough visible as a pending manual gate inside
  `scripts/gcp_staging_readiness.ps1`.

Validated result:

- Focused `tests.test_gcp_scripts.GoogleCloudScriptTests` coverage passes for
  the updated readiness and manual-validation flow.

Current boundaries:

- This adds staging-validation evidence only.
- No product behavior, brokerage authority, or owner access policy changed.

## 2026-07-12 - Atlas staging can now self-verify the deployed dashboard contract

New capabilities:

- Add a token-protected `/api/dashboard/verification` endpoint in cloud mode.
- Return machine-readable checks for Stage 5 scoreboard presence,
  persistence-learning availability, SPY/QQQ benchmark labeling, autonomous
  paper-queue state, and accountability-report availability.
- Add `scripts/gcp_dashboard_verification.ps1` as a read-only live staging
  smoke-check script.
- Let `scripts/gcp_deploy_staging.ps1` enable that endpoint explicitly with
  `-VerificationToken`.

Validated result:

- Cloud Run service revision `atlas-dashboard-stg-00114-8bt` is live on image
  `20260712-dashboard-verification-selfcheck`.
- The image digest is
  `sha256:e56091e8dcb7f7db788921d4ff19e414751a8284a4e36af2965301112143b9e1`.
- `scripts/gcp_staging_readiness.ps1` passes on the deployed revision.
- `scripts/gcp_dashboard_verification.ps1` passes on the live service and
  confirms all five current dashboard checks.
- `cloud/staging_manual_validation.json` records the owner Stage 5 dashboard
  walkthrough as validated on `2026-07-12T16:15:00-07:00`.
- `scripts/gcp_staging_readiness.ps1` now reflects that recorded walkthrough
  status directly from the evidence file during live readiness review.
- `scripts/gcp_final_staging_review.ps1` now reports the actual remaining
  manual gates from the same evidence file during its final read-only closeout.

Current boundaries:

- This is a staging verification path, not a public or multi-user API.
- Cross-device owner login and non-owner denial remain the only separate
  manual staging gates.

## 2026-07-26 - Stage 5 sector outcome stabilization

New capabilities:

- Preserve the owner-visible sector-gate outcome contract while Atlas is
  waiting for enough judged simulated buys.
- Redact the dashboard verification token from deployment command output.
- Exclude temporary cloud-inspection downloads from version control.

Validated result:

- The full local automated suite passes with 399 tests.
- Cloud Run revision `atlas-dashboard-stg-00130-d28` is live on image
  `20260726-stabilize-sector-outcomes`.
- All 12 token-protected Stage 5 dashboard checks pass.
- Manual daily execution `atlas-daily-stg-bq5x9` and weekly execution
  `atlas-weekly-stg-qngb5` completed successfully.
- All 25 automated staging-readiness checks pass.
- Daily and weekly schedules are enabled under the existing approved cost
  envelope.

Current boundaries:

- Sector-gate outcome evidence is still accumulating and must not drive larger
  simulated strategy changes until the sample is meaningful.
- Brokerage integration and real-money order routing remain disabled.

## 2026-07-26 - Real-capital discussion readiness is explicit

New capabilities:

- Show nine conservative evidence standards inside the Stage 5 scoreboard.
- Mark each standard as passing or open with its current value and target.
- Keep the status at `Paper only` until every standard passes.
- Limit a fully passing result to `Ready for owner review`; it grants no
  brokerage or real-money authority.

Validated result:

- The full local automated suite passes with 399 tests.
- Cloud Run revision `atlas-dashboard-stg-00131-2qh` is live on image
  `20260726-real-capital-readiness`.
- The live paper account currently passes 3 of 9 standards.
- Existing dashboard contract verification remains green.

Current boundaries:

- This is a transparency and governance feature, not a trading integration.
- Atlas remains simulation-only.
