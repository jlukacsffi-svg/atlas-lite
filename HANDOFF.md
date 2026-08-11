# Atlas Lite Handoff

Last updated: 2026-08-10

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

Stage 5: Paper Trading validation.

Stage 1 through Stage 4 are complete at their current planned software scope.
Stage 5 software is complete and the live simulated evaluation period is now
running. Web Phase 2 secure single-owner cloud hosting is complete at the
software and staging-verification level, with only two owner-assisted manual
identity checks still open before final sign-off:

- Cross-device owner login
- Non-owner Google account denial

Most recent Stage 5 refinement:

- Latest paper action context is live on Cloud Run revision
  `atlas-dashboard-stg-00171-qjf`. The dashboard, daily job, and weekly job use
  image `20260810-latest-action`, digest
  `sha256:45092dc5e3b9453c20c90578419b9fe8fdfe7237c08d7484255633d924936292`.
  All 434 local tests, 26 staging checks, and 24 protected dashboard checks
  pass. Recurring schedules are enabled, and neither job was manually
  executed during the release.
- Today now identifies the latest simulated buy, trim, or sale; states shares,
  fill price, time, and why Atlas acted; and shows the open or realized paper
  result. The activity shortcut opens the full Portfolio history.
- This closes the owner-visible gap between current recommendations and Atlas's
  most recent autonomous paper action without adding another large dashboard
  section.
- Next development focus: continue simplifying high-value owner workflows as
  real use reveals friction while Stage 5 evidence accumulates.

- The Today decision inbox is live on Cloud Run revision
  `atlas-dashboard-stg-00170-kg4`. The dashboard, daily job, and weekly job use
  image `20260810-decision-inbox`, digest
  `sha256:7e4a1a530211bfe4d0d13df99a5f9f5771d5a3e20a2b13aa89da3626a4af922b`.
  All 434 local tests, 26 staging checks, and 24 protected dashboard checks
  pass. Recurring schedules are enabled, and neither job was manually
  executed during the release.
- The primary recommendation now states Action, Why, and Next. One prioritized
  inbox replaces the three repetitive buy, sell, and portfolio overview cards.
  Portfolio risk appears first, followed by approved paper entries and new buy
  reviews; a quiet state appears when no decision needs attention.
- Current evidence is 163 snapshots, 63 judged decisions, and 11 completed
  paper positions. The August 9 weekly run and August 9-10 daily runs completed
  successfully.
- No elevated warning episode exists yet. Do not build or present the planned
  outcome scorecard until enough actual episodes resolve.
- Next development focus: continue simplifying owner workflows where real use
  reveals friction while scheduled Stage 5 evidence accumulates toward the
  250-snapshot, 100-judgment, and 30-completed-position targets.

- The owner workspace is simplified on Cloud Run revision
  `atlas-dashboard-stg-00169-6mm`. The dashboard, daily job, and weekly job use
  image `20260807-simplified-workspace`, digest
  `sha256:07fb701ecb1fae0c1fa72fd9388ae1908802bc9c7cd999408382c4a842a40928`.
  All 434 local tests, 26 staging checks, and 24 protected dashboard checks
  pass. Recurring schedules are enabled, and neither job was manually
  executed during the release.
- The default owner path is now Today, Ideas, Portfolio, and Reports. Less-used
  strategy settings, development evidence, security, and product background
  are under More.
- Today focuses on the current recommendation, portfolio result, important
  attention items, performance, and three action summaries. Portfolio opens
  with value, return, cash, positions, attention, and recent activity.
- Reports shows six recent items by default. Supporting research and advanced
  Stage 5 evidence remain available through clearly labeled detail controls.
- Next development focus: observe the simplified daily workflow while forward
  paper evidence accumulates, then build the elevated-warning outcome
  scorecard after enough episodes resolve.

- Escalation duration and resolution evidence is live on Cloud Run revision
  `atlas-dashboard-stg-00168-x5s`. The dashboard, daily job, and weekly job use
  image `20260805-escalation-outcomes`, digest
  `sha256:92b2c9b0460c01a05274bbac7c33c443538cde4c66732212cf1dd1dbd2149744`.
  All 434 local tests, 26 staging checks, and 24 protected dashboard checks
  pass. Recurring schedules are enabled, and neither job was manually
  executed during the release.
- Atlas opens an episode only when a warning meaningfully crosses into
  Monitor closely or Review now. It measures elapsed days, scheduled
  observations, peak priority, and whether the episode de-escalated or ended
  with a completed paper gain or loss.
- Current cloud evidence has no elevated episodes yet. Portfolio and reports
  say Atlas is building history rather than presenting a premature result.
- Episode evidence remains observational and cannot time a simulated exit,
  change strategy thresholds, or authorize real trading.
- Next development focus: build an elevated-warning outcome scorecard once
  resolved episodes exist, comparing episode behavior with paper outcomes
  before any owner-facing policy proposal.
- Meaningful priority escalation tracking is live on Cloud Run revision
  `atlas-dashboard-stg-00167-m8j`. The dashboard, daily job, and weekly job use
  image `20260805-priority-escalations`, digest
  `sha256:fdeb3fef5a95976001ac64b59e21a274a0ac0390acb7e663b810dce05dfceb9f`.
  All 433 local tests, 26 staging checks, and 23 protected dashboard checks
  pass. Recurring schedules are enabled, and neither job was manually
  executed during the release.
- Atlas records priority-band history but alerts the owner only when an
  existing warning crosses upward into Monitor closely or Review now. Score
  drift within a band, initial migration classification, recoveries, and
  archived outcomes do not generate escalation noise.
- The current evidence has zero elevated warnings and no new escalation, so
  Overview and Portfolio show a clear state. Daily and weekly reports use the
  same latest-snapshot rule.
- Escalation records remain review-only and disconnected from paper-order
  execution.
- Evidence-informed review priority is live on Cloud Run revision
  `atlas-dashboard-stg-00166-cqm`. The dashboard, daily job, and weekly job use
  image `20260805-review-priority`, digest
  `sha256:3c76f90b73394d8d1ad5647f29e41e5ed2d0e03026ab3336c6878c3d3992f610`.
  All 432 local tests, 26 staging checks, and 22 protected dashboard checks
  pass. Recurring schedules are enabled, and neither job was manually
  executed during the release.
- Atlas now ranks open defensive warnings from 0 to 100 using status,
  benchmark-relative movement, current trigger position, recovery durability,
  and relapses. Every score includes plain-language evidence.
- Closed LLY is archived as Outcome recorded at 0/100. Recovered CRWD is Low
  priority at 15/100, and no current warning needs elevated owner attention.
- The queue appears in Portfolio, daily reports, and weekly reports. It ranks
  review attention only and remains disconnected from paper-order execution.
- Recovery durability is live on Cloud Run revision
  `atlas-dashboard-stg-00165-zt7`. The dashboard, daily job, and weekly job use
  image `20260805-warning-durability`, digest
  `sha256:91abf4f65536a4f586f3cfea459cc9f510740a55033340d15e27f26c173015b2`.
  All 432 local tests, 26 staging checks, and 21 protected dashboard checks
  pass. The jobs were aligned without manually executing them.
- Atlas now measures time above trigger, relapse frequency, and current and
  longest recovery streaks. LLY has 57.1% durability with one relapse and is
  below trigger; CRWD has 92.3% durability, no relapses, and remains above.
- Recovery quality appears in Portfolio, daily reports, and weekly reports and
  remains observational evidence only.
- Warning timing is live on Cloud Run revision
  `atlas-dashboard-stg-00164-txh`. The dashboard, daily job, and weekly job use
  image `20260805-warning-timing`, digest
  `sha256:7303daac3c5aa7c3c68583ec3a61659a611fd76a881f3e566052c35c2ba6413c`.
  All 431 local tests, 26 staging checks, and 20 protected dashboard checks
  pass. The jobs were aligned without manually executing them.
- Atlas now measures warning spans in snapshots and days, plus the first later
  move above each trigger. Both current signals first crossed above trigger
  after 2 snapshots and about 1 day; LLY later failed, while CRWD sustained its
  recovery.
- Portfolio, daily reports, and weekly reports explicitly state that an early
  bounce can be temporary and is not warning resolution.
- Next development focus: measure recovery durability and relapse frequency
  while the scheduled forward sample continues growing.
- Benchmark-relative warning attribution is live on Cloud Run revision
  `atlas-dashboard-stg-00163-tqv`. The dashboard, daily job, and weekly job use
  image `20260805-warning-benchmarks`, digest
  `sha256:d7fa26bfb4d3a9333ef3c723889def73f06e5021b6341fe8e7c5ddcc096ab1b3`.
  All 431 local tests, 26 staging checks, and 19 protected dashboard checks
  pass. The jobs were aligned without manually executing them.
- Atlas now compares each post-warning stock move with the stronger SPY or QQQ
  move over the same period. The live evidence shows LLY 2.48 points behind
  SPY and CRWD 10.36 points ahead of QQQ, for 12.84 points of adjusted
  separation.
- Benchmark attribution appears in Portfolio, daily reports, and weekly
  reports, with an explicit statement that comparison does not establish
  causation or grant trade authority.
- Next development focus: measure warning duration and time to recovery while
  scheduled observations continue expanding the forward sample.
- Forward warning outcomes are live on Cloud Run revision
  `atlas-dashboard-stg-00162-v7s`. The dashboard, daily job, and weekly job use
  image `20260805-warning-outcomes`, digest
  `sha256:1c9fd418300e96838e407f25ad97d4e69e5b1a65f18cc42ffb39163d9143b7d4`.
  All 431 local tests, 26 staging checks, and 18 protected dashboard checks
  pass. The jobs were aligned without manually executing them.
- Atlas now measures each defensive warning from its trigger price through the
  latest move, worst excursion, and best recovery. The Portfolio page and
  generated reports compare confirmed weakness with recoveries or false
  alarms.
- The live sample contains two resolved signals: LLY is confirmed weakness at
  -0.74% since warning, while CRWD is a recovery at +16.79%, producing 17.53
  points of separation. The result remains an early sample and cannot change
  policy or execute a sale.
- Next development focus: let scheduled observations expand this study,
  strengthen benchmark-relative outcome attribution, and preserve the
  review-only authority boundary until the minimum gates pass.
- The cleaner command-center release is live on Cloud Run revision
  `atlas-dashboard-stg-00161-lbq`. The dashboard, daily job, and weekly job
  use image `20260729-command-center-2` with digest
  `sha256:82ccad4bf998599aa5afed957919422423e0c37a7959045188b98451c578e758`.
  All 431 local tests, 26 staging checks, and 17 protected dashboard checks
  pass. The jobs were aligned without manually executing them.
- Atlas now opens with a decision-first command center built around one
  readiness signal, today's recommended action, and current paper-portfolio
  context. Recommendations can be filtered into action queue, buy ideas, risk
  actions, and the full research list.
- Atlas Scores are now explainable in the dashboard: Growth, Quality, Moat,
  Momentum, and Risk drivers appear with the company thesis, primary driver,
  and key risk. Scores are explicitly labeled as research priority rather than
  return forecasts.
- Atlas now displays a live paper-entry evidence gate on Recommendations and
  Roadmap. Limited or suspicious all-zero daily movement pauses pending and
  approved simulated buys, while independent risk exits remain active.
- The dashboard now includes a dedicated graphical Roadmap page with separate
  investment-autonomy and secure-web lanes, live Stage 5 evidence counts, next
  gates, and the current authority boundary.
- The live Roadmap reports 139 snapshots, 52 judged decisions, 9 completed
  positions, 3 of 9 passing gates, and 64.7% Stage 5 evidence maturity. Desktop
  and mobile layouts pass visual review.
- Explicitly limited daily movement now fails closed across reports, mover
  rankings, research tasks, paper entries, benchmark context, sector breadth,
  and position projections. New simulated buys require valid daily movement;
  independent score-, trend-, thesis-, and news-based risk review remains
  active.
- Cloud Run revision `atlas-dashboard-stg-00158-g8d`, `atlas-daily-stg`, and
  `atlas-weekly-stg` use image `20260729-roadmap-quality-gate`, digest
  `sha256:7e5b21845480cdf6aaacb318df25a6b9bd82db22650ad060f64574580fe92c7d`.
- The full 429-test suite, all 26 readiness checks, and all 17 protected
  dashboard checks pass. The scheduled jobs were aligned without execution.
- Yahoo fallback now requests five days of close history and uses the latest
  two valid closes, with a metadata prior-close fallback for partial responses.
- Every fallback record carries explicit daily-movement quality and source
  evidence. Reports disclose how many available securities have valid
  prior-close comparisons.
- Overview warns when prices are present but daily movement evidence is
  limited, and the breadth graphic no longer presents an all-zero snapshot as
  a flat market.
- A live SPY, QQQ, NVDA, and AMD fallback check produced complete, nonzero
  daily comparisons. The full 424-test suite passes.
- Cloud Run revision `atlas-dashboard-stg-00157-24j`, `atlas-daily-stg`, and
  `atlas-weekly-stg` use image `20260729-daily-change-warning`, digest
  `sha256:b0bc30cad9d898b63c6a3895305db9890d152baf74a593771d5ddc8fc0feb4c5`.
- All 26 readiness checks and all 17 protected dashboard checks pass. The
  scheduled jobs were aligned without executing them.
- Today's owner briefing now shows executive-report freshness, the latest
  report timestamp and coverage, and a protected `Open latest report`
  shortcut.
- A Morning Executive Brief is labeled current for 36 hours. Older or missing
  daily reporting becomes an explicit owner-facing warning.
- The live Overview correctly reports the July 29 Morning Executive Brief as
  current with 140-security coverage, and the shortcut opens the full report.
- Cloud Run revision `atlas-dashboard-stg-00155-q57`, `atlas-daily-stg`, and
  `atlas-weekly-stg` use image `20260729-report-cadence`.
- The deployed image digest is
  `sha256:474d4935d25415e8547d5a97e324a9883c12ada7cee6f4881a591255b3fae6ff`.
- The full 416-test suite, all 26 readiness checks, and all 17 protected
  dashboard checks pass.
- The private Research report archive now has All, Daily, and Weekly filters,
  a live matching-report count, and a direct current-priority comparison.
- Daily report cards use `research_archive/archive_index.json` to preserve
  universe coverage and the contemporaneous Atlas score leader. Weekly cards
  are clearly labeled as seven-day evidence syntheses.
- The live archive currently shows six reports: four daily and two weekly.
  Historical evidence and current evidence remain visibly distinct.
- Cloud Run revision `atlas-dashboard-stg-00154-k9j`, `atlas-daily-stg`, and
  `atlas-weekly-stg` use image `20260729-report-evidence`.
- The deployed image digest is
  `sha256:66c0d61d7a79dc644133d10714dac9cc41d8fb736eb3aa7ac635eca67081714a`.
- The full 416-test suite, all 26 readiness checks, and all 17 protected
  dashboard checks pass.
- The Research page now includes a private Recent Executive Reports library.
  It lists the newest daily and weekly reports with explicit type and date,
  and opens a complete report in a separate owner-authenticated view.
- Cloud startup synchronization is bounded to the 12 newest generated HTML
  reports and a 2 MB report allowance. Strict report identifiers, resolved
  path checks, active-content rejection, owner authentication, and an isolated
  report Content Security Policy protect the archive.
- The live archive exposes six available reports and the July 29 Morning
  Executive Brief opens successfully in Chrome.
- Cloud Run revision `atlas-dashboard-stg-00153-6hl`, `atlas-daily-stg`, and
  `atlas-weekly-stg` use image `20260729-report-archive`.
- The deployed image digest is
  `sha256:c7e93e0e577aba71c8b32437e3742a735d45e0f270b60c0cb313beae8760f362`.
- The full 416-test suite, all 26 readiness checks, and all 17 protected
  dashboard checks pass.
- This is a private reporting capability only. Paper authority is unchanged,
  cloud email remains disabled, and real trading and brokerage access remain
  disabled.
- Daily and weekly executive reports now include forward defensive-review
  evidence. Daily reporting uses the three most recent paper snapshots;
  weekly reporting deduplicates and prioritizes the latest material state for
  each signal across seven days.
- Staging readiness now requires the dashboard, daily job, and weekly job to
  use one aligned container image. This caught that the scheduled jobs were
  still on an older image and had not activated the prospective tracker.
- The existing jobs were updated without changing schedules, cloud email
  policy, instance limits, or resource count. The next scheduled daily run
  will establish the clean forward-only study marker.
- Cloud Run revision `atlas-dashboard-stg-00152-czh`, `atlas-daily-stg`, and
  `atlas-weekly-stg` now use image `20260729-review-reporting-verified`.
- The deployed image digest is
  `sha256:aea76a82be166cd57fd26d153526ce8c24ca2f30e30d559d28fa727bf5ac911d`.
- The full 414-test suite, all 26 readiness checks, and all 17 protected
  dashboard checks pass. A 140-security isolated report smoke run also
  completed with email disabled.
- The live Stage 5 ledger has 139 snapshots, 52 judged decisions, and 9
  completed positions. The July 29 simulated return is `-3.32%`.
- These report sections remain review-only. Paper authority is unchanged, and
  real trading and brokerage access remain disabled.
- Recent prospective defensive-review changes now appear directly in Today's
  owner briefing on Overview, so the owner does not need to search the
  detailed Paper Portfolio for a material status change.
- The digest keeps only the latest state per signal, considers the last three
  paper snapshots, prioritizes completed loss and persistent weakness, and
  shows at most four concise updates.
- The live starting state correctly reads `Forward review study starts with
  the next snapshot`. The next scheduled paper run will establish the
  forward-only study marker; no manual run was forced.
- Cloud Run revision `atlas-dashboard-stg-00151-sb4` is live on image
  `20260726-owner-signal-digest-verified`; the full 411-test suite, all 25
  readiness checks, and all 17 protected dashboard checks pass.
- The deployed image digest is
  `sha256:251cc86a4ea5968afb3ea2b39cdc70bbc2d933b451e5c5fe8d6ceb9c141843be`.
- Desktop and 390-by-844 mobile Chrome checks show no overlap or horizontal
  overflow.
- This is a reporting refinement only. Paper policy is unchanged, and real
  trading and brokerage access remain disabled.
- The forward defensive-review study now has an effectiveness scorecard that
  separates confirmed weakness from recoveries and other false alarms.
- Atlas requires 10 resolved signals, 5 completed outcomes, and at least 65%
  weakness confirmation before the signal can become eligible for owner
  review.
- The scorecard currently shows `Waiting for first snapshot`, zero resolved
  signals, and 0% evidence progress. This is the correct forward-only state.
- Passing the gates permits owner review only and cannot change paper or
  real-trading authority.
- Cloud Run revision `atlas-dashboard-stg-00150-zsw` is live on image
  `20260726-review-effectiveness-verified`; the full 411-test suite, all 25
  readiness checks, and all 16 protected dashboard checks pass.
- The deployed image digest is
  `sha256:481d73f2d860e43bc172c47fdf12332c1482574e514c0ffe3ff5eed9b5116c71`.
- Atlas now has an append-only prospective tracker for the earlier defensive
  review signal. It starts from the next scheduled snapshot rather than
  retroactively relabeling earlier history.
- The tracker classifies each signal as new review, persistent weakness,
  recovered above trigger, completed loss, or completed gain.
- Signal transitions are recorded only when a review first appears or its
  classification changes, avoiding duplicate daily ledger noise.
- A temporary replay of the current cloud ledger identified KLAC, TSM, and
  CRWD as likely initial review-only signals while preserving all 44 paper
  trades.
- Cloud Run revision `atlas-dashboard-stg-00149-qfd` is live on image
  `20260726-prospective-reviews-verified`; the full 409-test suite, all 25
  readiness checks, and all 15 protected dashboard checks pass.
- The deployed image digest is
  `sha256:da5da5c0bbdb4154b259c276e2482ddf9c12e14fae89d62987e5104a1bed950d`.
- The live tracker currently displays `Starts next snapshot`. It remains
  review-only and cannot force a simulated or real trade.
- Atlas can now replay candidate defensive triggers against its recorded paper
  snapshots without placing or changing any paper trade.
- A review-only signal at `-2%` position return and `-3%` benchmark lag fired
  in 9 observed cycles. It improved the 3 completed-cycle comparison by
  `$171.10`, but 2 triggered holdings later recovered, so it remains a
  review-only candidate.
- An automatic full exit at `-3%` return and `-3%` lag was `$6.50` worse in
  the completed comparison and 4 of 9 triggered holdings later recovered.
  Atlas explicitly rejected that automatic rule.
- The Paper Portfolio presents both candidates with thresholds, recovery
  counts, completed results, and an explicit `No policy change` badge.
- Cloud Run revision `atlas-dashboard-stg-00148-t2h` is live on image
  `20260726-shadow-triggers-verified`; the full 407-test suite, all 25
  readiness checks, and all 14 protected dashboard checks pass.
- The deployed image digest is
  `sha256:b23fa7f4d5798a7195770461801567bd0c0209eecc65295663c725c66687a987`.
- The historical replay is evidence only. Paper behavior is unchanged, and
  real trading and brokerage access remain disabled.
- Atlas now diagnoses every completed paper cycle across entry timing, first
  defensive response, and exit execution.
- The first live diagnosis shows all 3 completed losses were already down at
  least 3% before Atlas acted defensively. The sample averaged a `-5.07%` loss
  over `23.2` days; NVDA had a sharp-decline entry, and MRVL/LRCX had
  fragmented exits.
- The Paper Portfolio now shows the shared finding and ticker-level evidence
  for NVDA, MRVL, and LRCX, with an explicit three-position sample warning.
- Cloud Run revision `atlas-dashboard-stg-00147-pbl` is live on image
  `20260726-loss-diagnostics-verified`; the full 406-test suite, all 25
  readiness checks, and all 13 protected dashboard checks pass.
- The deployed image digest is
  `sha256:adfd9363333cd2a5f108f618e9344c3e47efdc7cd15df58ab25a05a47367d43e`.
- Atlas now permits at most two partial trims within one uninterrupted paper
  holding cycle. A fresh third de-risk signal proposes a full simulated exit
  instead of another fractional remainder; a new entry resets the count.
- A replay of the live ledger reduces 33 sell executions to 21 and avoids 12
  redundant trims without forcing any immediate sale.
- The active `2 trims` guardrail is visible in the main Controls policy brief
  and the detailed Paper Portfolio operating-mode view.
- Cloud Run revision `atlas-dashboard-stg-00145-xl5` is live on image
  `20260726-trim-escalation-ui`; the full 405-test suite, all 25 readiness
  checks, and all 12 protected dashboard checks pass.
- The deployed image digest is
  `sha256:c07d2884afbf75663903e0a833a95b0a69a0c08811eed6375579f542247dc249`.
- Atlas now separates 30 partial trims from 3 fully completed paper positions
  instead of labeling all 33 sell executions as realized exits.
- Realized win rate is calculated from completed position cycles, including
  cumulative gain or loss across earlier trims.
- The three completed positions, NVDA, MRVL, and LRCX, all closed with
  simulated realized losses.
- Current live evidence maturity is 58.4%, with 2 of 9 conservative gates
  passing.
- Stage 5 remains simulated paper-only. Real trading and brokerage access
  remain disabled.

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

Recommended next roadmap task:

Diagnose repeated loss-driven trims. The accounting semantics are now correct:
30 partial trims and 3 completed losing positions. Identify which exit signals
caused repeated small sales, test whether cooldown or minimum-trim rules would
improve simulated behavior, and change strategy only when replayed evidence
supports the adjustment.

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
- Atlas can now run in autonomous paper-only mode, automatically approving
  paper proposals and research queue items inside the simulated environment
  when auto-manage is enabled.
- The secure dashboard now includes grouped trade history and an accountant-
  style basis report so each simulated buy, trim, and exit can be reviewed by
  ticker, timestamp, shares, fill price, basis, proceeds, realized result,
  and decision-driver context.
- Stage 5 benchmark reporting explicitly labels `SPY` as the `SPDR S&P 500
  ETF Trust` and `QQQ` as the `Invesco QQQ Trust`, so benchmark comparisons
  are readable to non-specialists.
- Atlas now carries projection-driver and sell-trigger explanations through
  Controls, Overview, trade history, and basis-report surfaces for better
  auditability of simulated autonomous decisions.

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
- Atlas paper-strategy tuning is now owner-editable from the secure dashboard
  Controls page. The owner can change auto-manage mode, buy-slot count, target
  size, buy and exit thresholds, benchmark and trend weighting, sector-repeat
  pressure, and the daily downside filter without editing files.
- Cloud Run revision `atlas-dashboard-stg-00079-6k7` serves the live strategy
  editor. The owner workspace has already been switched to a more aggressive
  autonomous paper preset: auto-manage on, 5 buy slots, 6% target size, 84
  buy threshold, 58 exit threshold, 2.4 benchmark weight, 0.35 trend weight,
  1.5 sector-repeat penalty, and -6% minimum daily move filter.
- Manual cloud execution `atlas-daily-stg-284c4` completed successfully on
  July 4, 2026 after the strategy update and refreshed the live workspace at
  5:38 PM Pacific. The run still produced `0 buy / 0 exit-trim`, which
  suggests the next meaningful lever is to widen the research universe rather
  than only tuning paper policy.
- Atlas Universe v1.6 now expands coverage from 100 to 125 tickers. The new
  additions emphasize liquid cross-sector leaders in industrials,
  infrastructure, energy majors, consumer staples, healthcare, data-center and
  wireless infrastructure, and materials so Atlas has more ways to pursue
  excess return beyond AI and IT.

Recommended next Stage 3/5 task:

- Deploy Atlas Universe v1.6 to staging and run a fresh cloud daily cycle to
  observe whether the broader field increases autonomous paper buy or trim
  activity under the current aggressive preset.
- If autonomous activity is still sparse, add a second universe expansion pass
  for sector ETFs, cyclicals, and market-structure leaders, then consider
  slightly loosening paper risk gates rather than lowering quality too far.

Latest live staging state on July 5, 2026:

- Atlas paper selection now uses sector-rotation context plus a new
  `follow_through_score` so autonomous paper buys and sells react to stronger
  leadership confirmation and weaker laggard behavior.
- Candidate ranking now includes sector-relative strength versus the active
  benchmark, and buy rationale text now explains sector rotation and
  follow-through explicitly.
- Exit logic now escalates more readily when a held name has both weak sector
  confirmation and weak follow-through, even before it fully degrades into the
  worst regime bucket.
- Cloud Run revision `atlas-dashboard-stg-00085-l78` is live on image tag
  `20260705-rotation-followthrough`.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image without pausing the owner-approved autonomous schedules.
- Manual Cloud Run execution `atlas-daily-stg-vz7ld` completed successfully on
  July 5, 2026 after the job update.
- The Paper Portfolio page now includes an `Open basis report` button beside
  the grouped trade-history workflow.
- Atlas now exposes an accountant-style accountability report derived directly
  from the append-only paper ledger, including weighted-average cost, open
  basis, realized gain or loss, and full transaction drill-down by ticker.
- Each transaction row now includes timestamp, action, shares, fill price,
  gross amount, basis per share, basis amount, proceeds, realized gain or
  loss, remaining position size, thesis, and source metadata.
- The dashboard can export this detail as `atlas-paper-basis-report.csv` for
  outside review and cost-basis support.
- Cloud Run revision `atlas-dashboard-stg-00083-hmn` is live on image tag
  `20260705-basis-report`.
- Focused tests for `tests.test_paper_trading` and `tests.test_web_dashboard`
  pass, and staging `/readyz` returns `{"status":"ready"}` after deployment.
- The first broader universe pass shipped as `Atlas Universe v1.6` and the
  second pass shipped as `Atlas Universe v1.7`.
- `v1.7` expands the tracked set from 125 to 140 names by adding sector,
  style, and benchmark ETFs including `XLF`, `XLE`, `XLV`, `XLI`, `XLP`,
  `XLU`, `XLB`, `XLRE`, `XLC`, `IWM`, `DIA`, `RSP`, `VTV`, `VUG`, and
  `SCHD`.
- Cloud Run revision `atlas-dashboard-stg-00081-qp9` is live on image tag
  `20260705-universe-v17`.
- Manual Cloud Run execution `atlas-daily-stg-fmtsj` completed successfully on
  July 5, 2026 and published a fresh private snapshot with
  `universe_version=1.7`, `tracked=140`, and `available=140`.
- The persisted paper-account policy remains in aggressive autonomous mode:
  auto-manage on, 5 buy slots, 6% target size, 84 buy threshold, 58 exit
  threshold, 2.4 benchmark weight, 0.35 trend weight, 1.5 sector-repeat
  penalty, and a -6% daily downside filter.
- The secure dashboard experience now includes the moved benchmark chart on
  Overview, benchmark labels that explain `SPY` and `QQQ`, a visible revision
  badge, a click-through Atlas logo/header, and paper trade history by ticker.
- Live browser verification before the session reset confirmed there is no
  `About Atlas` nav tab and the Controls page no longer shows pending manual
  approval items when autonomous mode is active.
- The live UI briefly lagged behind the latest private snapshot because
  `/api/dashboard` was slow to refresh, but direct cloud-artifact inspection
  confirmed the backend state is already at `140/140`.
- The next live strategy pass is now deployed on revision
  `atlas-dashboard-stg-00082-cd4` and image `20260705-regime-strategy`.
- This pass adds richer regime-aware trend fields such as
  `trend_regime_score`, `trend_regime`, drawdown context, and moving-average
  distance context, then uses them inside paper selection and exit gating.
- Cloud job execution `atlas-daily-stg-ng595` completed successfully on the
  matching image digest and published private snapshot
  `snapshot_20260705_180651.json`.
- That latest snapshot still shows `universe_version=1.7`, `tracked=140`, and
  `available=140`, with new benchmark ETF regime data present in the private
  artifacts.
- The new regime-aware run improved signal quality but did not create any new
  simulated buy or exit actions on that exact market snapshot.
- `atlas-daily-stg` and `atlas-weekly-stg` scheduler jobs are resumed and
  `ENABLED` in `America/Los_Angeles`, matching the owner's request for Atlas to
  continue autonomously.

Recommended next Stage 3/5 task now:

- Verify the next live dashboard snapshot for whether the stronger rotation and
  follow-through signals actually increase autonomous paper buy or sell
  activity on the current broader universe.
- If activity is still too sparse, add one more market-structure layer such as
  multi-day follow-through persistence, sector breadth, or benchmark breadth
  deterioration so Atlas can separate real leadership from one-day noise more
  confidently.
- Verify the live `Open basis report` modal and CSV export inside the
  authenticated dashboard, then carry that same basis and lifecycle detail
  into the position cards so the owner can drill from a holding directly into
  its cost basis and realized history.
- Improve the signal engine further so Atlas opens and closes simulated
  positions more often for good reasons, not just because the universe is
  larger.
- Focus next on stronger relative-strength, rotation, and follow-through
  inputs layered on top of the new regime engine so Atlas can recognize sector
  leadership changes and deteriorating winners sooner.

Estimated overall Atlas program completion: 85%.

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
- On June 22, 2026, dashboard readiness notifications were tuned after noisy
  Google alert emails. `/readyz` returned `200 {"status":"ready"}`, Cloud Run
  revision `atlas-dashboard-stg-00015-hrd` was healthy, and recent readiness
  logs showed successful checks. The dashboard alert now requires sustained
  multi-region pass fraction below `0.67` for `600s`. Job-failure alerts remain
  immediate.
- Context-aware research reviews are deployed on dashboard revision
  `atlas-dashboard-stg-00016-mgp` and image `20260622-context-research`.
  Automated reviews now include Atlas score/category/sector, plus upcoming
  earnings, analyst actions, insider Form 4 activity, and tracked portfolio
  exposure when those signals are available. Controlled execution
  `atlas-daily-stg-wpcqs` produced AVAV, ARM, and MDB risk reviews with internal
  score context and company-specific headline evidence. Daily and weekly
  schedules were resumed afterward. All 284 tests pass.
- Catalyst classification is deployed on dashboard revision
  `atlas-dashboard-stg-00017-w94` and image
  `20260622-catalyst-classification`. Completed reviews now include
  `catalyst_type` and `thesis_action`. Controlled execution
  `atlas-daily-stg-2ltsk` classified AVAV as `score_risk` and ARM/NFLX as
  `company_news`. Daily and weekly schedules were resumed afterward. All 286
  tests pass.
- Thesis-memory research reviews are deployed on dashboard revision
  `atlas-dashboard-stg-00018-gtc` and image `20260622-thesis-memory`.
  Completed reviews now include `thesis_alignment`, add stored thesis-profile
  evidence when available, and display thesis alignment in the owner decision
  center. Controlled execution `atlas-daily-stg-pbbqx` produced thesis-aware
  reviews for AVAV, ARM, and MDB; AVAV was `score_risk` with
  `risk_to_thesis`. Daily and weekly schedules were resumed afterward. All 287
  tests pass.
- Thesis-drift tracking is deployed on dashboard revision
  `atlas-dashboard-stg-00019-627` and image `20260622-thesis-drift`.
  Completed reviews now include `thesis_drift` and thesis-history evidence.
  Controlled execution `atlas-daily-stg-vgxcx` produced AVAV and ARM as
  `recurring_risk` and NFLX as `new_risk`. Daily and weekly schedules were
  resumed afterward. All 288 tests pass.
- Owner review ranking is deployed on dashboard revision
  `atlas-dashboard-stg-00020-dx7` and image `20260622-review-ranking`.
  Owner decision cards now include `attention_score`, `attention_label`, and
  `attention_reasons`, and are sorted by review urgency. Daily and weekly
  schedules remained enabled. All 289 tests pass.
- Daily owner action list is deployed on dashboard revision
  `atlas-dashboard-stg-00021-g9z` and image `20260623-daily-action-list`.
  The Controls page now shows `daily_action_list` above detailed research
  cards, including suggested owner dispositions. Daily and weekly schedules
  remained enabled. All 289 tests pass.
- Action evidence anchors are deployed on dashboard revision
  `atlas-dashboard-stg-00022-kdx` and image `20260623-action-evidence`.
  Daily action cards now include an `evidence_anchor` line so each suggested
  owner disposition is tied to a compact research-evidence reference or
  conclusion fallback. Daily and weekly schedules remained enabled. All 289
  tests pass.
- Action exposure and paper context are deployed on dashboard revision
  `atlas-dashboard-stg-00023-dxs` and image `20260623-action-context`.
  Daily action cards now include simulated `portfolio_context` and
  `paper_context` lines, tying owner review to open paper exposure, current
  simulated account performance, benchmark-relative context, and latest thesis
  review where available. Daily and weekly schedules remained enabled. All 289
  tests pass.
- Owner outcome learning is deployed on dashboard revision
  `atlas-dashboard-stg-00024-dqp` and image `20260623-outcome-learning`.
  The Controls page now includes an Outcome Learning card with research
  approval/defer/reject counts, approval rate, paper proposal status counts,
  recent owner decisions, and a conservative learning signal. Daily and weekly
  schedules remained enabled. All 290 tests pass.
- Outcome-calibrated attention scoring is deployed on dashboard revision
  `atlas-dashboard-stg-00025-8m4` and image
  `20260624-outcome-calibration`. Owner decision history can now apply small,
  conservative attention-score adjustments for prior ticker caution or similar
  recommendation outcomes, and the Controls page displays the adjustment when
  it affects a review. Daily and weekly schedules remained enabled. All 291
  tests pass.
- Dashboard help and term clarification is deployed on dashboard revision
  `atlas-dashboard-stg-00026-qcq` and image `20260624-dashboard-help`.
  Major dashboard sections now have clickable information controls explaining
  SPY, QQQ, Atlas scores, watchlist moves, open simulated positions, research
  agenda, market breadth, sector tape, data integrity, controls, and
  access/security. Daily and weekly schedules remained enabled. All 292 tests
  pass.
- Dashboard pages and recommendation clarity are deployed on dashboard revision
  `atlas-dashboard-stg-00027-8hv` and image `20260624-dashboard-pages`.
  The secure dashboard now has page-style navigation, a dedicated
  Recommendations page, clear separation between paper purchase recommendations
  and the current Atlas list, and a plain-language Simulate fill workflow.
  Daily and weekly schedules remained enabled. All 292 tests pass.
- Paper recommendation feedback is deployed on dashboard revision
  `atlas-dashboard-stg-00028-248` and image `20260624-paper-feedback`.
  The Paper Portfolio page now includes a Recommendation Performance panel
  that compares executed simulated buy proposals against SPY and QQQ, labels
  each idea as working, lagging, mixed, or not enough time, and keeps all
  activity simulation-only. Daily and weekly schedules remained enabled. All
  293 tests pass.
- Paper proposal why-now rationale is deployed on dashboard revision
  `atlas-dashboard-stg-00031-bb7` and image `20260624-why-now-v3`. New
  Atlas-generated paper proposals now carry structured rationale bullets, and
  the dashboard displays a Why now box explaining score threshold, strongest
  score inputs, category, sector, daily move, and simulated sizing before any
  owner decision. Daily and weekly schedules remained enabled. All 293 tests
  pass.
- Simulated exit/trim recommendations are deployed on dashboard revision
  `atlas-dashboard-stg-00037-tcb` and image `20260624-exit-trim`. The
  dashboard now separates paper purchase ideas from paper exit/trim ideas,
  updates the owner-control and Simulate fill language for sells, and allows
  weak-score sell proposals to pass CRO review as exit support instead of being
  blocked as entry risk. Daily and weekly schedules remained enabled. All 295
  tests pass.
- Benchmark-lag paper trim trigger is deployed on dashboard revision
  `atlas-dashboard-stg-00038-rtz` and image `20260625-benchmark-lag-trim`.
  Atlas now reviews open simulated holdings when they lag both SPY and QQQ by
  at least 3 percentage points across multiple paper snapshots, and creates a
  reviewable simulated half-trim sell proposal when lag reaches 8 percentage
  points. Owner approval and explicit Simulate fill confirmation remain
  required. Daily and weekly schedules remained enabled. All 297 tests pass.
- Proposal clarity and help-popover refinement are deployed on dashboard
  revision `atlas-dashboard-stg-00039-hrs` and image
  `20260625-proposal-clarity`. Simulated sell proposals now distinguish trim
  versus exit based on current simulated holdings, explain the holding impact
  before approval or simulated fill, and use clearer purchase/trim/exit copy
  across Recommendations, Controls, and the confirmation dialog. Help
  popovers now stay readable while hovered or focused and close naturally when
  the cursor or focus leaves them. Daily and weekly schedules remained enabled.
  All 299 tests pass.
- Position thesis status layer is deployed on dashboard revision
  `atlas-dashboard-stg-00040-2xc` and image `20260625-thesis-status`.
  Open simulated paper holdings now show a plain-language thesis badge
  (`healthy`, `watch`, `trim`, or `exit`) plus a short evidence summary on the
  Paper Portfolio page. Status is derived from the latest thesis review and any
  active simulated sell proposal. Daily and weekly schedules remained enabled.
  All 300 tests pass.
- Thesis overview attention layer is deployed on dashboard revision
  `atlas-dashboard-stg-00041-xbf` and image `20260625-thesis-overview`.
  The Paper Portfolio page now summarizes how many holdings are `healthy`,
  `watch`, `trim`, or `exit`, and ranks the top names needing attention first
  above the detailed position list. Daily and weekly schedules remained
  enabled. All 301 tests pass.
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

Latest staging update:

- Atlas now applies paper-learning calibration directly to active paper
  recommendations and owner-control proposal cards.
- Recommendation cards now state whether recent simulated outcomes have been
  supportive, cautionary, or still too sparse to guide confidence.
- Active Cloud Run revision is `atlas-dashboard-stg-00047-cgr`.
- Cache-busted web asset image tag is `20260627-paper-calibration`.
- Full test suite passes with 308 tests before deploy.

Latest staging update:

- The next software step is to incorporate this calibration into ranking and
  prioritization, so the highest-signal recommendations rise first instead of
  only showing the learning note inside each card.
- Current dashboard behavior still requires explicit owner approval and
  Simulate fill confirmation before any paper buy, trim, or exit is recorded.

Latest staging update:

- Atlas now uses paper-learning calibration to sort active recommendation
  queues, not just annotate them.
- Recommendation ordering still respects workflow stage first (approved buys,
  pending buys, trims, exits), but Atlas now pushes stronger simulated learnings
  to the top within each stage.
- The `Atlas focus right now` summary now surfaces the same calibrated priority
  order and shows judged-outcome counts when Atlas has enough paper evidence.
- Cloud Run revision `atlas-dashboard-stg-00049-74x` is serving 100% traffic.
- Cache-busted web asset image tag is `20260627-recommendation-ranking`.
- Full test suite passes with 308 tests before deploy.

Latest staging update:

- Legacy recommendation cards no longer need to fall back to the dead-end
  `Awaiting rationale` path when Atlas already has a useful thesis or can
  synthesize rationale from current score, sector, move, sizing, and paper
  learning context.
- Owner-control proposal payloads now backfill structured rationale for older
  buy and sell proposals so historical paper ideas remain readable instead of
  looking unfinished.
- The web client now prefers structured rationale first, then proposal thesis,
  before ever showing a generic placeholder. This gives the live dashboard a
  much better floor even for older proposal records.
- Cloud Run revision `atlas-dashboard-stg-00051-2cc` is serving 100% traffic.
- Cache-busted web asset image tag is `20260627-rationale-live`.
- Full test suite passes with 310 tests before deploy.

Latest staging update:

- Recommendation cards now carry both the affirmative case and the caution
  case. Atlas can explain `Why now` and also `Why not` or `What could go
  wrong` using score, category, move, risk-review, and paper-learning context.
- Older paper proposals now read more like disciplined research notes instead
  of one-sided prompts, which makes the live dashboard feel much closer to a
  usable investment workbench.
- Cloud Run revision `atlas-dashboard-stg-00052-nlm` is serving 100% traffic.
- Cache-busted web asset image tag is `20260627-why-not`.
- Full test suite passes with 310 tests before deploy.

Latest staging update:

- Recommendation caution text now pulls from Atlas research memory instead of
  relying only on generic score/category warnings. Live cards can cite prior
  risk-to-thesis reviews and recent disconfirming evidence titles when Atlas
  already has that context on file.
- Legacy recommendations benefit too, because the objection builder now
  backfills memory-aware counterpoints for older paper proposals instead of
  making them look freshly generated but shallow.
- Cloud Run revision `atlas-dashboard-stg-00053-kr9` is serving 100% traffic.
- Cache-busted web asset image tag is `20260627-memory-objections`.
- Full test suite passes with 310 tests before deploy.

Latest staging update:

- Open simulated positions now show a compact Atlas research-memory readout so
  the Paper Portfolio page exposes how much thesis history Atlas already has on
  each holding, plus whether the latest stored review leaned supportive or risk
  to thesis.
- Executed paper buys and sells now include an `Atlas context` block that can
  cite execution-time risk-review flags, stored thesis alignment, and recent
  evidence titles. The activity feed now reads more like an investment journal
  than a bare trade ledger.
- Cloud Run revision `atlas-dashboard-stg-00054-xw8` is serving 100% traffic.
- Cache-busted web asset image tag is `20260627-activity-context`.
- Full test suite passes with 311 tests before deploy.

Latest staging update:

- Open positions now include a `What changed since entry` journal block. Atlas
  summarizes current basis versus latest price, relative performance since the
  latest buy fill against SPY/QQQ when enough snapshots exist, the latest
  thesis review, and the current escalation cue toward hold, trim, or exit.
- This gives the Paper Portfolio page a real through-line from entry to
  present, so holdings feel less like static rows and more like tracked
  decisions with evolving conviction.
- Cloud Run revision `atlas-dashboard-stg-00055-49r` is serving 100% traffic.
- Cache-busted web asset image tag is `20260627-position-journal`.
- Full test suite passes with 311 tests before deploy.

Latest staging update:

- The Paper Portfolio page now includes a `Portfolio action ladder` that groups
  simulated holdings into `Hold steady`, `Watch closely`, `Trim candidate`, and
  `Exit candidate`.
- Atlas builds the ladder directly from the latest thesis-state labels so the
  owner can see the portfolio's next-action posture at a glance instead of
  inferring it one row at a time.
- Each ladder column includes a short description, position count, and the
  highest-priority names in that bucket with compact gain/loss context.
- Cloud Run revision `atlas-dashboard-stg-00057-p2s` is serving 100% traffic.
- Cache-busted web asset image tag is `20260628-position-ladder`.
- `/readyz` returns `{"status":"ready"}`.
- The live Paper Portfolio page shows the grouped next-action layout, with the
  current simulated book fully in `Hold steady`.
- Full test suite passes with 312 tests before deploy.

Latest staging update:

- Atlas now surfaces the same portfolio posture earlier on the Overview page
  through a compact `Portfolio focus right now` panel.
- The new summary reuses live thesis-state labels to show a headline portfolio
  readout, healthy/watch/trim/exit counts, and the holdings that need review
  first without requiring a jump into the Paper Portfolio page.
- Cloud Run revision `atlas-dashboard-stg-00058-wjn` is serving 100% traffic.
- Cache-busted web asset image tag is `20260628-portfolio-focus`.
- `/readyz` returns `{"status":"ready"}`.
- The live Overview page now shows the portfolio-focus panel with current paper
  holdings and thesis-derived posture counts.
- Full test suite passes with 313 tests before deploy.

Latest staging update:

- Atlas now merges paper proposals and open-position posture into a ranked
  `Portfolio action queue` inside the Controls workflow.
- The new queue surfaces active paper proposals beside already-open simulated
  holdings that need closer review, while suppressing duplicate holding entries
  when an active trim or exit proposal already represents that name.
- This keeps paper workflow and live paper posture in one owner-facing control
  surface instead of splitting attention between the Paper page and Controls.
- Cloud Run revision `atlas-dashboard-stg-00059-clc` is serving 100% traffic.
- Cache-busted web asset image tag is `20260628-controls-queue`.
- `/readyz` returns `{"status":"ready"}`.
- The live Controls page shows the ranked portfolio action queue with 3 current
  items on the present dataset.
- Full test suite passes with 315 tests before deploy.

Latest staging update:

- Controls now include a `Hold-steady holdings` section that explains which
  open simulated names are intentionally absent from the ranked action queue
  because Atlas still considers them healthy.
- The new summary reuses live paper-position thesis status plus portfolio and
  paper context, so the owner can distinguish between names needing action and
  names deliberately staying steady from the same control surface.
- Cloud Run revision `atlas-dashboard-stg-00060-xgt` is serving 100% traffic.
- Cache-busted web asset image tag is `20260628-healthy-holdings`.
- `/readyz` returns `{"status":"ready"}`.
- Full test suite passes with 316 tests before deploy.
- Live authenticated content verification for this specific section was blocked
  in the fresh in-app browser session because Google sign-in was required again
  after the browser automation session reset.

Latest staging update:

- The Controls `Hold-steady holdings` section now includes compact
  `What changed since entry` journal context for healthy positions.
- This reuses the same basis, benchmark-relative, thesis-review, and
  escalation-cue narrative layer already available on the Paper Portfolio page,
  so steady names feel explained from the Controls workflow instead of merely
  listed as healthy.
- Cloud Run revision `atlas-dashboard-stg-00061-sdr` is serving 100% traffic.
- Cache-busted web asset image tag is `20260628-healthy-journal`.
- `/readyz` returns `{"status":"ready"}`.
- Full test suite passes with 316 tests before deploy.

Current in-flight stage:

- The next software step is to let the Controls workflow summarize the current
  paper book at the section level, so the owner can see one top-line posture
  readout for actions needed, healthy holds, and queue coverage before drilling
  into individual cards.

Latest staging update:

- Controls now include a top-line `Paper book posture` summary above the
  ranked action queue and healthy-holdings section.
- The new summary gives one section-level readout for open holdings, ranked
  queue size, healthy hold count, research-review count, and buy versus
  exit/trim proposal balance before the owner drills into individual cards.
- Cloud Run revision `atlas-dashboard-stg-00062-sj7` is serving 100% traffic.
- Cache-busted web asset image tag is `20260702-controls-summary`.
- `/readyz` returns `{"status":"ready"}`.
- Full test suite passes with 317 tests before deploy.

Current in-flight stage:

- The next software step is to make the Controls summary more directional by
  highlighting which bucket changed most recently, so the top-line posture
  readout can point the owner toward the freshest shift in the paper book.

Latest staging update:

- The Controls `Paper book posture` summary now calls out the freshest paper-
  book shift, including whether the newest change landed in the ranked action
  queue or the hold-steady bucket.
- Atlas derives this from existing proposal and thesis-review timestamps, so
  the owner gets a more directional top-line readout without introducing a
  separate state tracker.
- Cloud Run revision `atlas-dashboard-stg-00063-7t2` is serving 100% traffic.
- Cache-busted web asset image tag is `20260702-controls-freshness`.
- `/readyz` returns `{"status":"ready"}`.
- Full test suite passes with 317 tests before deploy.

Current in-flight stage:

- The next software step is to carry this freshness cue into the matching
  queue or hold-steady card itself, so the top-line summary and the underlying
  paper-book item feel explicitly linked instead of only verbally connected.

Latest staging update:

- Atlas now carries the Controls freshness cue into the matching paper-book
  card itself, so the exact queue or hold-steady item referenced by the
  summary is visibly tagged as the freshest shift.
- This keeps the top-line `Paper book posture` summary and the underlying
  owner workflow card aligned without changing any approval or simulation
  authority.
- Cloud Run revision `atlas-dashboard-stg-00064-97g` is serving 100% traffic.
- Cache-busted web asset image tag is `20260702-controls-linked-freshness`.
- `/readyz` returns `{"status":"ready"}`.
- Full test suite passes with 317 tests before deploy.
- Live authenticated content verification for this specific pass was blocked in
  the in-app browser because Google sign-in was required again before the
  Controls page could be inspected.

Current in-flight stage:

- The next software step is to make this linkage actionable by letting the
  summary jump or scroll directly to the tagged queue or hold-steady card, so
  the owner can move from posture readout to the exact item in one click.

Latest staging update:

- The Controls freshness summary now tries to expose a direct `Open item`
  jump control so the owner can move from the top-line posture readout to the
  tagged queue or hold-steady card in one click.
- Stable card anchor ids are now generated in the owner-controls model and
  rendered into the Controls cards, with the web client prepared to switch to
  the Controls page and scroll the matching card into view.
- Cloud Run revision `atlas-dashboard-stg-00065-lnz` is serving 100% traffic.
- Cache-busted web asset image tag is `20260702-controls-jump`.
- `/readyz` returns `{"status":"ready"}`.
- Full test suite passes with 317 tests before deploy.
- Live authenticated verification partially succeeded: the in-app browser
  picked up the new `controls-jump` assets after reload, but the rendered
  Controls summary still did not show the `Open item` control, so the next
  software step is to inspect why the live owner-controls payload is not yet
  surfacing the expected anchor metadata.

Current in-flight stage:

- The next software step is to debug the live owner-controls payload versus the
  local tested model, so the deployed Controls summary actually renders the
  jump control and card anchors in production as intended.

Latest staging update:

- The Controls freshness summary now renders and jumps to the tagged card in
  live staging, and the top-line Overview `Portfolio focus right now` panel is
  also prepared to jump directly into the matching Paper Portfolio holding.
- Atlas now supports a paper-only `Auto-manage paper portfolio` mode. When the
  paper-account policy enables it, the daily run auto-approves clear or caution
  paper proposals after risk review, rejects hold-risk proposals, and records
  simulated fills without waiting for manual owner approval.
- The local simulated paper account was switched to auto-manage mode.
- The cloud paper-account bundle was switched to auto-manage mode and pushed
  back to the private bucket.
- Cloud Run revision `atlas-dashboard-stg-00068-qzw` is serving 100% traffic.
- Cache-busted web asset image tag is `20260703-paper-auto-manage`.
- The Cloud Run jobs were updated to image `20260703-paper-auto-manage`.
- Manual cloud daily execution `atlas-daily-stg-vccqm` completed successfully
  after the job update and auto-executed three previously approved simulated
  buys: MRVL, TSM, and AMD.
- The live cloud paper portfolio now holds 7 simulated positions: NVDA, ANET,
  KLAC, LRCX, MRVL, TSM, and AMD.
- `/readyz` returns `{"status":"ready"}`.
- Full automated test suite passes with 322 tests before deploy.

Current in-flight stage:

- The next software step is to make autonomous paper mode tunable, so Atlas can
  become more or less aggressive about new simulated selections without
  changing the real-trading boundary.

Latest staging update:

- The Paper Portfolio page now includes a `View trade history` button in the
  executed-activity section.
- The new dialog groups simulated buys, trims, and exits by ticker so the owner
  can inspect each name's purchase and sell timeline without scanning the mixed
  global activity feed.
- The history view reuses the append-only paper ledger and existing execution
  context instead of introducing a second activity store.
- Cloud Run revision `atlas-dashboard-stg-00069-sxh` is serving 100% traffic.
- Cache-busted web asset image tag is `20260703-trade-history`.
- `/readyz` returns `{"status":"ready"}`.
- Full automated test suite passes with 323 tests before deploy.

Current in-flight stage:

- The next software step is to let the owner drill from that grouped trade
  history back into per-position lifecycle context, such as current open result
  versus each prior entry and exit in the same name.

Latest staging update:

- Atlas paper selection is now more explicitly benchmark-focused and sector-
  aware.
- The investable universe was already broader than AI and IT, but the paper
  strategy had still been acting like a score-first queue. It now compares
  candidate daily strength against the stronger of `SPY` or `QQQ`, uses that
  benchmark-relative excess return inside ranking, and prefers sector-diverse
  picks before doubling up in the same area.
- This keeps the simulated strategy aimed at beating the major benchmarks while
  remaining open to opportunities across software, healthcare, financials,
  consumer, defense, energy, cybersecurity, automation, and other covered
  sectors.
- Cloud Run revision `atlas-dashboard-stg-00070-pjs` is serving 100% traffic.
- The Cloud Run jobs were updated to image `20260703-benchmark-focus`.
- Manual cloud daily execution `atlas-daily-stg-zw4bc` completed successfully
  on the updated benchmark-focused strategy.
- The immediate post-run cloud paper book remained at 7 simulated positions, so
  the new ranking logic did not force an unnecessary trade on this specific
  daily snapshot.
- `/readyz` returns `{"status":"ready"}`.
- Full automated test suite passes with 325 tests before deploy.

Current in-flight stage:

- The next software step is to make this benchmark-focused paper strategy
  tunable, including more aggressive buy-slot counts, stronger benchmark-excess
  weighting, and adjustable sector-diversity pressure.

Latest staging update:

- Atlas now spells out the benchmark names more clearly anywhere they are most
  visible in the owner dashboard.
- The Market performance legend now labels `SPY` as the `S&P 500 ETF
  benchmark` and `QQQ` as the `Nasdaq-100 ETF benchmark`, with a short
  explanatory note directly under the chart.
- The Paper recommendation-performance section also includes an inline
  benchmark explainer, and paper feedback rows now expand the benchmark names
  instead of showing bare ticker symbols only.
- Cloud Run revision `atlas-dashboard-stg-00071-n4v` is serving 100% traffic.
- Cache-busted web asset image tag is `20260704-benchmark-labels`.
- `/readyz` returns `{"status":"ready"}`.
- Focused web-dashboard tests pass, and the full automated test suite still
  passes with 325 tests before deploy.

Current in-flight stage:

- The next software step is still to make the benchmark-focused paper strategy
  tunable, including more aggressive buy-slot counts, stronger benchmark-excess
  weighting, and adjustable sector-diversity pressure.

Latest local update not yet deployed:

- Atlas now has a first trend-quality layer inside the momentum engine instead
  of relying only on simple 1-month and 3-month return scoring.
- `MomentumEngine` now computes additional pure-Python trend features from the
  same 1-year Yahoo price history:
  - `return_12m`
  - `sma_20`, `sma_50`, `sma_200`
  - `ema_20` and `ema_20_slope_pct`
  - `rsi_14`
  - `volatility_20d_pct`
  - `distance_from_52w_high_pct`
  - `trend_quality_score`
  - `trend_state`
- The legacy return-based score is preserved as `legacy_momentum_score`, and
  the published `momentum_score` is now a blended composite of the legacy score
  and the new `trend_quality_score`.
- The paper strategy now reads `momentum_metrics.trend_quality_score` and
  `trend_state` when present, uses trend quality as an extra ranking input when
  candidates are otherwise close, and explains that trend context directly in
  buy rationale text.
- This is still paper-only logic. It improves simulated selection quality and
  explainability only; it does not enable brokerage integration or real-money
  trading.
- Focused tests pass for `tests.test_momentum`,
  `tests.test_paper_strategy`, and `tests.test_market_data_metadata`.
- Full automated test suite passes locally with 330 tests.

Current in-flight stage:

- The next software step is to make this new trend-aware paper strategy
  tunable and visible, including owner-facing controls for aggressiveness,
  stronger trend weighting, and dashboard surfacing of the new trend-quality
  signals inside Atlas recommendations.

Latest staging update:

- Cloud Run revision `atlas-dashboard-stg-00075-njb` is now serving 100% of
  traffic as of 2026-07-04.
- Dashboard image `20260704-trend-nav` is deployed.
- The sidebar no longer includes a separate `About Atlas` tab; the Atlas
  overview remains reachable only from the top brand/logo link.
- The former Market page content is folded into Overview, so portfolio KPIs,
  benchmark performance, and breadth sit together on one dashboard page.
- The deployed bundle also includes the first trend-quality engine pass, so
  Atlas now computes richer trend context and can lean on it during simulated
  paper selection.
- `/readyz` returns `{"status":"ready"}` after deploy.
- The live root HTML no longer contains `About Atlas` tab text or `href="#market"`.
- Focused web-dashboard tests pass, and the full automated test suite passed
  locally with 330 tests before deploy.

Latest staging update:

- Atlas paper selection now uses broader confirmation instead of leaning too
  heavily on a single day's move.
- The paper strategy now scores benchmark breadth across `SPY`, `QQQ`, `IWM`,
  and `RSP`, measures sector breadth participation, and calculates a
  multi-day persistence score from recent returns, trend slope, price versus
  moving averages, and drawdown context.
- These new signals now feed autonomous buy ranking, cautious-market buy
  gating, and exit escalation so Atlas can prefer names with stronger
  follow-through and reduce holdings faster when participation fades.
- Paper recommendation and proposal rationale storage now preserves more lines,
  which means the dashboard can surface the added breadth, persistence, and
  follow-through explanation instead of truncating it away.
- Cloud Run revision `atlas-dashboard-stg-00086-cfh` is serving 100% of
  traffic as of 2026-07-05.
- Dashboard and job image tag `20260705-persistence-breadth` is deployed.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` now use the same
  image.
- Manual cloud daily execution `atlas-daily-stg-wcw9d` completed successfully
  in 4m34s on the updated strategy.
- Manual cloud weekly execution `atlas-weekly-stg-dddr7` also completed
  successfully after the jobs update.
- `/readyz` returns `{"status":"ready"}` after deploy.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` scheduler jobs are
  enabled again after manual verification.
- The full local automated test suite passes with 348 tests before deploy.

Current in-flight stage:

- The next practical software step is to add position-management intelligence
  on top of the stronger entry engine, especially staged adds/trims, holding-
  period awareness, and benchmark-relative rebalance rules so Atlas can manage
  open winners and laggards more proactively instead of only deciding initial
  entries and exits.

Latest staging update:

- The daily workflow now refreshes paper-performance snapshots after the
  autonomous paper cycle runs, not just before it.
- This closes a live reporting gap where Atlas could execute an autonomous
  sell and still publish a stale pre-trade `performance.md` artifact.
- The updated live bundle now consistently reflects the same-run autonomous
  `NVDA` exit across `paper_trading/account.json` and
  `paper_trading/performance.md`.
- Cloud Run revision `atlas-dashboard-stg-00087-q79` is serving 100% of
  traffic as of 2026-07-05.
- Dashboard and job image tag `20260705-posttrade-sync` is deployed.
- Manual cloud daily execution `atlas-daily-stg-hzqxn` completed successfully
  on the updated reporting-sync build.
- `/readyz` returns `{"status":"ready"}` after deploy.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` scheduler jobs are
  enabled again after manual verification.
- The full local automated test suite passes with 348 tests before deploy.

Current in-flight stage:

- The next practical software step remains richer position-management
  intelligence, especially staged adds/trims, holding-period awareness, and
  benchmark-relative rebalance rules so Atlas can manage open winners and
  laggards more proactively after entry.

Latest staging update:

- Atlas now has its first proactive open-position management layer in the
  paper account, not just entry selection and hard exits.
- `PaperPositionMonitor` can now escalate repeated review-level weakness into
  a trim proposal, and it can also open a follow-on simulated buy proposal for
  a held leader that keeps outperforming after entry with enough benchmark
  confirmation.
- This logic stays inside the same proposal, risk-review, approval, and
  autonomous-execution path, so the decision trail remains audit-friendly.
- Cloud Run revision `atlas-dashboard-stg-00088-z5f` is serving 100% of
  traffic as of 2026-07-05.
- Dashboard and job image tag `20260705-position-management` is deployed.
- Manual cloud daily execution `atlas-daily-stg-p8zdn` completed successfully
  on the updated build.
- The live paper book immediately used the new trim logic on `KLAC`, reducing
  the position from `19` to `9.5` simulated shares after repeated review-level
  weakness and benchmark lag. Cash increased to `$57,354.78`, and realized
  gain or loss moved to `-$426.88`.
- `/readyz` returns `{"status":"ready"}` after deploy.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` scheduler jobs are
  enabled again after manual verification.
- The full local automated test suite passes with 350 tests before deploy.

Latest staging update:

- Atlas now shows company-news tone directly in the owner dashboard.
- The Overview `Portfolio focus right now` panel, Paper Portfolio holdings,
  ranked Controls queue, hold-steady holdings, and paper proposal cards now
  render the persisted `news_signal` so the owner can see whether recent
  company-specific news is supportive, constructive, neutral, cautious, or
  adverse.
- Cloud Run service revision `atlas-dashboard-stg-00091-bmz` is live on image
  `20260706-dashboard-news-tone`.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- The full local automated test suite now passes with 355 tests.

Latest staging update:

- Atlas now has a live news-aware paper-decision layer in staging. The daily
  run refreshes company-news signals for held names, major movers, and top
  ranked candidates before paper selection and open-position review.
- Cloud Run service revision `atlas-dashboard-stg-00090-rv7` is live on image
  `20260705-news-audit`.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` both point to the
  same image.
- Manual cloud daily execution `atlas-daily-stg-4pfbw` completed successfully
  and published a new private manifest at `2026-07-06T02:40:59Z`.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` scheduler jobs are
  enabled again after this verification pass. The jobs-deploy script paused
  them during rollout, and they were resumed after the post-deploy checks.
- The latest cloud paper account remains at 9 open simulated positions:
  `AMD`, `ANET`, `CRWD`, `KLAC`, `LLY`, `LRCX`, `MRVL`, `MU`, and `TSM`.
- The latest cloud paper equity remains `$99,095.01` with cash
  `$57,354.78`, realized gain or loss `-$426.88`, and unrealized gain or
  loss `-$478.10`.
- This verification run did not create a new simulated buy, trim, or exit; it
  confirmed that the news-aware build ran successfully and preserved the post-
  `KLAC` trim state.
- The former archive-visibility gap is now closed. The latest archived cloud
  snapshot `research_archive/snapshot_20260706_024044.json` preserves
  `news_signal` for live tracked names, and held names such as `AMD`, `ANET`,
  `CRWD`, `KLAC`, `LLY`, `LRCX`, `MRVL`, `MU`, and `TSM` now show persisted
  neutral signals in the cloud snapshot on this dataset.
- Focused local tests for `tests.test_news_data`, `tests.test_paper_strategy`,
  `tests.test_paper_monitor`, and `tests.test_research_memory` pass.
- The full local automated test suite passes with 354 tests.

Current in-flight stage:

- Atlas now has richer news intelligence, owner-visible event explanations,
  and report-level event context live in Cloud Run staging.
- `app/news_data.py` classifies company headlines into higher-signal event
  types such as `earnings_beat`, `earnings_miss`, `guidance_raise`,
  `guidance_cut`, `analyst_upgrade`, `analyst_downgrade`, `product_launch`,
  `contract_win`, `approval`, `legal_risk`, and `offering_or_dilution`.
- News signals now carry lightweight source weighting, high-impact event
  counts, positive and negative weighted totals, a dominant event type, and a
  compact `headline_events` summary list so Atlas can react differently to a
  routine mention versus a lawsuit, guidance cut, or earnings surprise.
- `PaperStrategy` now blocks otherwise-strong paper buys when even a single
  high-impact negative event is present, not only when multiple weak negative
  headlines accumulate.
- `PaperPositionMonitor` now escalates adverse single-event news risk into a
  trim or closer thesis review when that event is severe enough.
- The dashboard and owner controls now show the specific event class driving
  the news tone, not just the positive or negative label.
- The paper decision trail now names the dominant news event inside buy,
  review, trim, and exit language so autonomous paper actions read like a real
  audit journal.
- The saved paper performance report and accountability report now preserve
  recent execution context with inferred news-event summaries, keeping the
  exported artifacts aligned with the live dashboard and decision logic.
- The paper position-detail drilldown and basis-report workflow now carry the
  same event-specific context, including a per-execution `News event` field,
  so a reviewer can trace entry, trim, and exit decisions without switching
  between panels.
- The holding lifecycle drilldown now also exposes a compact trend-diagnostics
  block built from Atlas momentum metrics, including trend quality, regime,
  moving-average posture, RSI, EMA slope, and distance from the 52-week high.
- The holding lifecycle drilldown now also exposes a sector-and-benchmark
  confirmation block so Atlas can show whether a name's move is being
  confirmed by its sector and the broader benchmark tape, not only by the
  chart structure of the single name.
- The holding lifecycle drilldown now also exposes an outcome-framing block
  so Atlas can separate genuine leadership from simple market lift by
  comparing each open holding's post-entry return with the stronger of `SPY`
  or `QQQ`.
- The holding lifecycle drilldown now also exposes a `Projection watch` block
  so Atlas can turn trend, confirmation, outcome, and news context into a
  forward-looking read plus concrete watchpoints.
- Cloud Run service revision `atlas-dashboard-stg-00100-xrb` is live on image
  `20260706-position-projection-watch`.
- Manual cloud daily execution `atlas-daily-stg-wnp4r` completed successfully
  at `2026-07-07T02:57:55Z`.
- Manual cloud weekly execution `atlas-weekly-stg-8nhdp` completed
  successfully at `2026-07-07T02:54:01Z`.
- The refreshed private manifest now reports `generated_at` of
  `2026-07-07T02:57:51+00:00`.
- The latest archived cloud snapshot
  `research_archive/snapshot_20260707_025733.json` is present in the private
  manifest after the projection-watch rollout.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` scheduler jobs are
  enabled again after the rollout checks passed.
- The full local automated test suite now passes with 359 tests.

Recommended next practical step:

- Extend this predictive layer one step further by surfacing the new
  projection-driven paper-monitor decisions more explicitly in the owner
  dashboard, especially which trims or reviews were triggered by benchmark
  lag, thin sector breadth, damaged trend posture, or supportive add
  confirmation.

Latest staging update:

- `PaperPositionMonitor` now converts the same ingredients behind the
  dashboard's `Projection watch` block into actual autonomous paper-management
  thresholds in live staging.
- The monitor now computes lightweight projection signals from post-entry
  benchmark excess, sector breadth, trend regime, trend quality, and current
  news tone.
- Atlas can now escalate a holding from maintain to review when projection
  confirmation is no longer clearly supportive, even if older hard-stop rules
  have not fired yet.
- Atlas can now trigger a projection-driven trim when post-entry benchmark lag,
  weak sector participation, and damaged trend posture line up together.
- Winner-add proposals are now stricter: Atlas requires a supportive
  projection posture, stronger sector breadth, and healthier trend quality
  before adding to an existing leader.
- Cloud Run service revision `atlas-dashboard-stg-00101-rg4` is live on image
  `20260710-projection-monitor`.
- Manual cloud daily execution `atlas-daily-stg-6fckm` completed successfully
  at `2026-07-11T02:33:53Z`.
- Manual cloud weekly execution `atlas-weekly-stg-4vw4k` completed
  successfully at `2026-07-11T02:29:23Z`.
- The refreshed private manifest now reports `generated_at` of
  `2026-07-11T02:33:48+00:00`.
- The latest archived cloud snapshot
  `research_archive/snapshot_20260711_023331.json` is present in the private
  manifest after the projection-monitor rollout.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- The recurring `atlas-daily-stg` and `atlas-weekly-stg` scheduler jobs are
  enabled again after the rollout checks passed.
- Focused tests for `tests.test_paper_monitor`, `tests.test_web_dashboard`,
  and `tests.test_paper_strategy` pass, and the full local automated test
  suite now passes with 361 tests.

Current in-flight stage:

- The next practical software step is to carry this same projection-driver
  labeling beyond Controls into the broader paper workflow, especially the
  Overview portfolio-focus summary, paper holding drilldowns, and exported
  accountability artifacts so the same autonomous reason is visible
  everywhere the owner audits a position.

Latest staging update:

- Atlas now explicitly labels when a ranked paper action is being driven by
  the new projection layer instead of only older score, lag, or news wording.
- The Controls `Portfolio action queue` and `Hold-steady holdings` cards now
  show compact decision-driver tags such as `Projection de-risk`,
  `Projection caution`, `Projection leadership`, and
  `Projection-supported add`.
- The queue evidence anchor now prefers the exact projection trigger line when
  one exists, so the owner can see whether Atlas acted because of benchmark
  lag, thinning sector breadth, weakened trend posture, or still-supportive
  continuation.
- This deploy changes the live dashboard surface only. The daily and weekly
  jobs remain on the prior `20260710-projection-monitor` image because the
  new logic is owner-visibility code rather than execution-path logic.
- Cloud Run service revision `atlas-dashboard-stg-00102-5gw` is live on image
  `20260710-projection-driver-ui`.
- The image digest is
  `sha256:a7747bc40911b86a768d63afd61d50c5a89382fe74b9f87f02844164e03ea15e`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00102-5gw` as both the latest created and latest ready
  revision.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- Focused tests for `tests.test_owner_controls` and `tests.test_web_dashboard`
  pass, and the full local automated test suite now passes with 363 tests.

Current in-flight stage:

- The next practical software step is to push the same projection-driver
  labeling one layer deeper into Atlas's saved paper exports and execution
  narratives, especially trade-history cards, paper-performance artifacts, and
  any owner-facing summaries that still talk about trims or adds without
  naming the exact projection reason.

Latest staging update:

- Atlas now carries the same projection-driver language across the broader
  paper workflow, not just the Controls page.
- The Overview `Portfolio focus right now` list now shows the same driver tag
  beside high-priority paper holdings, so the owner can see at a glance when
  a name is under `Projection caution` or `Projection de-risk`.
- Open holding rows and the paper holding lifecycle dialog now display the
  same decision-driver badge, keeping the autonomous reason aligned from the
  overview dashboard down into the per-position drilldown.
- The accountant-style accountability report now includes a `Driver` column
  per simulated trade, and the CSV export now includes both `Driver` and
  `Driver Detail` fields for outside review.
- The accountability payload now infers these driver labels directly from the
  stored thesis and rationale trail rather than introducing a second manual
  explanation store.
- This deploy changes the live dashboard and owner-visible export workflow
  only. The daily and weekly jobs remain on the prior
  `20260710-projection-monitor` image because the new work is explainability
  and reporting code rather than execution-path logic.
- Cloud Run service revision `atlas-dashboard-stg-00103-ppw` is live on image
  `20260710-projection-driver-workflow`.
- The image digest is
  `sha256:c4c98578bd1fe8613d96942a53b7eaa4adf9c85572c6eea824cbaa8ed970effb`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00103-ppw` as both the latest created and latest ready
  revision.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- Focused tests for `tests.test_web_dashboard`, `tests.test_paper_trading`,
  and `tests.test_owner_controls` pass, and the full local automated test
  suite still passes with 363 tests.

Current in-flight stage:

- The next practical software step is to make the same projection-driver
  language part of Atlas's post-trade learning loop itself, especially paper
  feedback summaries and any future comparative review of which projection-led
  adds, trims, or exits actually worked best versus the benchmarks.

Latest staging update:

- Atlas now carries projection-driver labels through the recent paper activity
  feed, grouped trade-history cards, and saved paper-performance reporting.
- The live `What Atlas bought and sold` activity cards now show the same
  driver badge that appears in Controls and holding drilldowns.
- The grouped `View trade history` workflow now shows that same driver badge
  on each simulated trade row, so historical buys, trims, and exits keep the
  autonomous reason visible.
- The saved `performance.md` report now adds a `Driver` column inside
  `Recent Execution Context`, which keeps the durable paper-performance
  artifact aligned with the live dashboard's projection explanation.
- This deploy is still owner-visibility code only. The daily and weekly jobs
  remain on the prior `20260710-projection-monitor` image because no execution
  thresholds or autonomous trading logic changed here.
- Cloud Run service revision `atlas-dashboard-stg-00104-nzq` is live on image
  `20260710-projection-driver-history`.
- The image digest is
  `sha256:6e2ba3a01ee62d82bb4becc706390b01c9b16fbd83d01bd7285c94ec6fff58f2`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00104-nzq` as both the latest created and latest ready
  revision.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- Focused tests for `tests.test_paper_trading` and `tests.test_web_dashboard`
  pass, and the full local automated test suite still passes with 363 tests.

Current in-flight stage:

- The next practical software step is to close the loop between projection-led
  learning and actual autonomous thresholds, especially whether Atlas should
  gradually tune add, review, or trim aggressiveness based on which
  projection-driver patterns are outperforming or underperforming over time.

Latest staging update:

- Atlas now folds projection-driver learning directly into the paper feedback
  readout instead of only labeling past decisions.
- The paper learning summary now tracks judged outcomes by projection driver,
  such as `Projection-supported add` versus `Projection caution`, and shows a
  compact working-rate card for the strongest recent projection patterns.
- The learning takeaway list now explicitly names the strongest and weaker
  projection reads observed so far, giving the owner a clearer signal about
  which autonomous projection patterns are earning trust.
- Executed paper-feedback rows now also render the same driver badge, so the
  learning list, trade history, accountability report, and activity feed all
  use one aligned projection explanation path.
- This deploy remains owner-visibility and learning-summary code only. The
  daily and weekly jobs still run the prior `20260710-projection-monitor`
  execution image because the new work does not yet change autonomous
  thresholds or execution logic.
- Cloud Run service revision `atlas-dashboard-stg-00105-xdg` is live on image
  `20260711-projection-learning`.
- The image digest is
  `sha256:0c09091ad011f782afb8bb009d449b8997353b6dd9be26abe6da853801305253`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00105-xdg` as both the latest created and latest ready
  revision.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- `scripts/gcp_staging_readiness.ps1` now reports a new successful daily
  manual execution `atlas-daily-stg-72tww` while the weekly verified execution
  remains `atlas-weekly-stg-4vw4k`.
- Focused tests for `tests.test_paper_trading` and `tests.test_web_dashboard`
  pass, and the full local automated test suite still passes with 363 tests.

Latest local repo update:

- Atlas now uses judged projection-driver outcomes to gently retune the
  simulated paper monitor instead of only reporting which driver was working.
- `PaperTradingAccount.projection_threshold_profile()` now converts judged
  projection-linked buy and sell outcomes into a bounded adaptive profile for
  winner-add, review, and trim thresholds.
- `PaperPositionMonitor.from_account(...)` now reads that adaptive profile so
  the daily paper monitor can tighten or ease projection confirmation gates
  without changing any real-money boundary.
- The dashboard learning panel now shows whether adaptive projection tuning is
  merely watching or actively retuning, plus the specific threshold changes
  Atlas made from judged paper outcomes.
- This update is currently local only. It changes autonomous paper-monitor
  behavior, so it has not been deployed to staging yet.
- Focused tests for `tests.test_paper_trading`, `tests.test_paper_monitor`,
  and `tests.test_web_dashboard` pass, and the full automated test suite now
  passes locally with 366 tests.

Current in-flight stage:

- The next practical step is to validate the new adaptive paper thresholds in
  staging, observe whether the retuning creates clearer autonomous buys and
  sells, and then decide whether owner-visible policy controls are needed for
  projection-learning sensitivity or minimum evidence thresholds.

Latest staging update:

- Atlas now loads the executive dashboard in two stages so the Overview page
  can paint its top-line readout before heavier paper-trade detail finishes.
- The new fast path adds `/api/dashboard/summary`, which serves the Overview
  essentials first: market pills, KPI totals, benchmark chart data, paper-book
  posture, thesis overview, portfolio focus, and the current holdings list.
- The browser now renders that summary immediately, then follows with the full
  `/api/dashboard` payload for deeper sections such as accountability, trade
  history, feedback, and owner controls.
- Local timing checks on the new code path reduced the first response build
  from about `1.12s` for the full payload to about `0.18s` for the summary
  payload.
- Cloud Run service revision `atlas-dashboard-stg-00106-vwm` is live on image
  `20260711-dashboard-summary-fast`.
- The image digest is
  `sha256:13408efc01ed5c6ba7de8a8eecf078602bb2c1baec01de1d539d003557fd1c19`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00106-vwm` as both the latest created and latest ready
  revision.
- `/readyz` returns `{"status":"ready"}` after deployment verification.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00106-vwm`.
- Focused tests for `tests.test_web_dashboard` and `tests.test_web_cloud`
  pass, and the full automated test suite now passes locally with 367 tests.

Latest staging refinement:

- Atlas now starts the full dashboard fetch in parallel with the summary fetch
  instead of waiting for the summary request to finish first.
- The summary payload was also trimmed to only the fields the Overview first
  paint actually uses, dropping unused watchlist and task-detail data from the
  initial response.
- Local timing checks on the refined path reduced the summary build again from
  about `0.18s` and `22.2 KB` down to about `0.11s` and `6.3 KB`, while the
  full payload remains available for the richer follow-up render.
- Cloud Run service revision `atlas-dashboard-stg-00107-bjn` is live on image
  `20260711-dashboard-summary-slim`.
- The image digest is
  `sha256:aee69dbb31c25eadcb5bc9746fcca722a09af81ff2bd0b336dc30835d4fb7688`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00107-bjn` as both the latest created and latest ready
  revision.
- `/readyz` remains healthy after deployment verification.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00107-bjn`.

Latest staging refinement:

- Atlas now hydrates the executive dashboard from the browser's last cached
  summary snapshot before it asks the network for fresh data.
- That means repeat opens can show the last known Overview immediately, then
  refresh in place with the current summary and full dashboard payload.
- The cached startup path is additive to the existing slim summary endpoint and
  parallel full-dashboard fetch, so Atlas now combines browser-side reuse with
  the lighter server-side first paint path.
- Cloud Run service revision `atlas-dashboard-stg-00108-gxl` is live on image
  `20260711-dashboard-cached-start`.
- The image digest is
  `sha256:413484d758ef6bb28b6cc1f82c3f7ee8ebc8670c21d431c346f3b09c017a3adf`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00108-gxl` as both the latest created and latest ready
  revision.
- `/readyz` remains healthy after deployment verification.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00108-gxl`.

Latest staging refinement:

- Atlas now reuses a cached full dashboard snapshot for the read-only sections
  on repeat opens, not just the executive summary tiles.
- Cached owner-control state is explicitly stripped before reuse, so controls
  still wait for the fresh authenticated network response and current CSRF
  token.
- This keeps Overview, paper positions, trade-history context, and other
  read-only sections feeling fuller immediately while preserving safe live
  control behavior.
- Cloud Run service revision `atlas-dashboard-stg-00109-nlz` is live on image
  `20260711-dashboard-full-cache-safe`.
- The image digest is
  `sha256:b77068740a3389a8633d86ddf45de6f981668d58ef3665ed40bafcb367a29150`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00109-nlz` as both the latest created and latest ready
  revision.
- `/readyz` remains healthy after deployment verification.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00109-nlz`.

Latest staging refinement:

- Atlas now shows an explicit freshness badge in the top bar so the faster
  startup states are visible to the owner.
- The badge now steps through `Cached snapshot`, `Refreshing`, and `Live`
  during startup and refresh, making the cached-first behavior legible instead
  of silent.
- This pairs with the cached summary and cached safe full-dashboard reuse so
  Atlas can feel both faster and clearer about what it is showing.
- Cloud Run service revision `atlas-dashboard-stg-00110-gm5` is live on image
  `20260711-dashboard-freshness-badge`.
- The image digest is
  `sha256:daf10ff1b1af01b6245210ab619b2ff2cb34314708c1d90b2886ad477a38b87e`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00110-gm5` as both the latest created and latest ready
  revision.
- `/readyz` remains healthy after deployment verification.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00110-gm5`.

Latest staging refinement:

- Atlas no longer blocks Cloud Run cold start on a full private-artifact pull
  before the dashboard can serve.
- The cloud dashboard now pulls only a startup bundle at boot: the latest
  research snapshot, the paper account, the paper ledger, and the research
  task file. A full artifact sync now continues in the background after the
  service is already available.
- This is the first startup optimization aimed directly at the very first open
  on a cold instance, not just repeat visits inside the browser.
- Cloud Run service revision `atlas-dashboard-stg-00111-gjj` is live on image
  `20260711-dashboard-startup-bundle`.
- The image digest is
  `sha256:e94abce57b48f6363539069293f88d9bce13464acf45a3be3d262c76956a05a8`.
- Direct post-deploy verification confirms the service reports
  `atlas-dashboard-stg-00111-gjj` as both the latest created and latest ready
  revision.
- `/readyz` remains healthy after deployment verification.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00111-gjj`.

Latest Stage 5 learning deploy:

- Atlas Stage 5 paper validation now tracks sustained learning, not just the
  latest verdict.
- Paper snapshots now retain the security-price map used for each
  mark-to-market checkpoint.
- Executed paper trades now record 1-, 3-, and 5-snapshot persistence reads,
  so Atlas can tell whether a trade only worked briefly or kept working across
  multiple checkpoints.
- The Stage 5 validation summary and standalone paper performance report now
  include judged-trade working rate, judged sell help rate, gross turnover,
  and multi-snapshot persistence context.
- The owner dashboard now surfaces persistence in the paper feedback section,
  and owner-control paper calibration now treats 3-snapshot persistence as an
  extra support/caution input.
- `PaperStrategy` now uses judged paper-learning context during close ranking
  decisions, so sustained prior winners or laggards can tilt otherwise similar
  buy candidates.
- Cloud Run service revision `atlas-dashboard-stg-00112-k9g` is live on image
  `20260712-stage5-persistence-learning`.
- The image digest is
  `sha256:913f35a98c4db6cd3c9ac06921f825e96c2eb69c0e8ad40a614281bed9743ec4`.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00112-k9g`.
- Focused strategy, owner-control, paper-trading, and dashboard tests pass
  locally for the new persistence-learning path.

Latest strategy-learning follow-up:

- Atlas now uses supportive sustained paper-learning not only for proposal
  ranking, but also for modest buy-gate relaxation on borderline setups.
- Negative sustained paper-learning can now block borderline paper buys when
  similar setups recently lost follow-through.
- This pushes Stage 5 learning from reporting, to calibration, to actual
  autonomous entry behavior.
- Cloud Run service revision `atlas-dashboard-stg-00113-mc8` is live on image
  `20260712-stage5-learning-gate-tuning`.
- The image digest is
  `sha256:e67d14e33f3086bd2b262a9a81fc2d8f40873709d206a78693e33c1113ccc1a7`.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00113-mc8`.
- Focused strategy, owner-control, paper-trading, and dashboard tests pass
  locally for the new gate-tuning path.

Latest staging-validation refinement:

- Manual staging validation now includes an explicit signed-in owner dashboard
  walkthrough, not just login and deny-list confirmation.
- `cloud/staging_manual_validation.json` now records the expected Stage 5
  walkthrough checks: validation scoreboard visibility, persistence-learning
  reads, benchmark labeling, autonomous queue behavior, and lot-level
  accountability review.
- `scripts/gcp_manual_validation.ps1` can now display and record that owner
  walkthrough as a separate evidence gate.
- `scripts/gcp_staging_readiness.ps1` now keeps that dashboard walkthrough
  visible as a pending manual gate during automated readiness review.

Latest self-verification deploy:

- Atlas cloud mode now supports a token-protected
  `/api/dashboard/verification` endpoint for staging smoke checks.
- The verification payload checks the live Stage 5 scoreboard contract,
  persistence-learning availability, SPY/QQQ benchmark labeling, autonomous
  paper-queue behavior, and accountability-report availability without
  requiring interactive browser login.
- `scripts/gcp_dashboard_verification.ps1` now calls that endpoint in a
  read-only way and reports pass/fail for each dashboard contract.
- `scripts/gcp_deploy_staging.ps1` can now enable the verification endpoint by
  passing `-VerificationToken`.
- Cloud Run service revision `atlas-dashboard-stg-00114-8bt` is live on image
  `20260712-dashboard-verification-selfcheck`.
- The image digest is
  `sha256:e56091e8dcb7f7db788921d4ff19e414751a8284a4e36af2965301112143b9e1`.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00114-8bt`.
- `scripts/gcp_dashboard_verification.ps1` passes on the deployed service and
  confirms all five current dashboard checks.
- `cloud/staging_manual_validation.json` now records the owner Stage 5
  dashboard walkthrough as validated on `2026-07-12T16:15:00-07:00`.
- `scripts/gcp_staging_readiness.ps1` now reads the same manual-validation
  evidence file, so it reports the owner Stage 5 dashboard walkthrough as
  validated instead of showing a stale hardcoded pending line.
- Remaining manual staging gates are now only cross-device owner login and
  non-owner Google account denial.
- `scripts/gcp_final_staging_review.ps1` now supports an optional
  `-VerificationToken` so the final read-only review can include the live
  dashboard contract check in the same pass.
- `scripts/gcp_final_staging_review.ps1` now also reads the manual-validation
  evidence file and names the actual remaining manual gates directly in its
  closeout instead of ending with only a generic pending sign-off line.

Latest staging update:

- Adaptive daily trade-pressure and benchmark-trust visibility is deployed to
  staging across Controls, holding drilldowns, performance reporting, and
  accountant-style basis exports.
- Cloud Run service revision `atlas-dashboard-stg-00115-xqh` is live on image
  `20260712-adaptive-audit-context`.
- The deployed image digest is
  `sha256:43c4581b555a3d0ab7f0c64aadcc2258f3894a6cff234219b4b22a1906f4cf57`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00115-xqh` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, autonomous queue behavior, and accountability
  report availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image; manual executions `atlas-daily-stg-cxwbh` and
  `atlas-weekly-stg-44drh` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow:
  `atlas-daily-stg` at `0 7 * * * America/Los_Angeles` and
  `atlas-weekly-stg` at `0 8 * * 0 America/Los_Angeles`.
- `scripts/gcp_set_schedules_staging.ps1` and
  `scripts/gcp_staging_status.ps1` now sort Cloud Run executions newest-first
  before reading latest execution status, avoiding stale failed executions
  appearing as the current job state.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00115-xqh`.
- `scripts/gcp_final_staging_review.ps1 -VerificationToken ...` passes on
  revision `00115-xqh`, with 100% uptime telemetry across 2,592 samples in the
  24-hour report window.
- `cloud/staging_manual_validation.json` now records the owner Stage 5
  dashboard walkthrough on revision `00115-xqh` and records recurring schedules
  as enabled after the successful daily and weekly manual executions.
- Remaining manual gates are still only cross-device owner login and
  non-owner Google account denial, followed by final owner security/cost
  sign-off.

Latest staging update:

- Atlas now builds a benchmark-specific Stage 5 decision scorecard for `SPY`
  and `QQQ`.
- Simulated buys are scored by whether the owned stock beat each benchmark,
  while trims/exits are scored by whether selling avoided later weakness
  versus each benchmark.
- The dashboard paper-learning panel now shows the benchmark scorecard with
  judged comparisons, working/mixed/lagging counts, working rate, and average
  decision edge.
- The saved paper-performance report now includes the same benchmark-specific
  scorecard, and the token-protected staging verification contract now checks
  that the scorecard data and UI strings are present.
- Cloud Run service revision `atlas-dashboard-stg-00116-zv8` is live on image
  `20260712-benchmark-scorecards`.
- The deployed image digest is
  `sha256:80698bcfe94bc080935df38d11b84e8e4d7c921102960593ce18d43dc1285db3`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00116-zv8` and now confirms the new `benchmark_scorecard` contract in
  addition to the Stage 5 scoreboard, persistence learning, benchmark labels,
  autonomous queue behavior, and accountability report availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image; manual executions `atlas-daily-stg-5jshm` and
  `atlas-weekly-stg-qhfzc` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00116-zv8`.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_owner_controls`, `tests.test_web_dashboard`,
  `tests.test_web_cloud`, and `tests.test_gcp_scripts` pass with 159 tests.

Current in-flight stage:

- The next practical step is to decide whether the new benchmark-specific
  scorecards should retune autonomous paper exit strictness or sector pacing,
  while continuing to keep real trading and brokerage access disabled.

Latest staging update:

- Atlas now uses benchmark-specific sell scorecards to gently retune
  autonomous paper exit strictness.
- The benchmark scorecard now tracks sell-only judged counts, working/mixed/
  lagging counts, sell working rate, and sell average decision edge for `SPY`
  and `QQQ`.
- When projection-driver and sell-trigger learning have not already adjusted
  the paper monitor, strong benchmark-specific sell evidence can move
  projection review/trim thresholds slightly earlier; weak benchmark-specific
  sell evidence can move them slightly slower.
- The adaptive projection-tuning profile now includes `benchmark_exit_stats`,
  and the token-protected staging verification contract checks the new
  `benchmark_exit_tuning` evidence path.
- Cloud Run service revision `atlas-dashboard-stg-00117-5vw` is live on image
  `20260712-benchmark-exit-tuning`.
- The deployed image digest is
  `sha256:bdac74ccd5c83fadcae8c40344b02afd87985286dfa550d3115e0cec76f3fb4e`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00117-5vw` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, benchmark scorecard, benchmark exit tuning,
  autonomous queue behavior, and accountability report availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image; manual executions `atlas-daily-stg-q684b` and
  `atlas-weekly-stg-dwdfh` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00117-5vw`.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` pass with 175 tests.

Current in-flight stage:

- The next practical step is to decide whether benchmark-specific scorecards
  should also affect sector pacing or capital rotation pressure, while keeping
  all autonomy limited to the simulated paper account.

Latest staging update:

- Atlas now uses benchmark-specific buy scorecards to gently retune autonomous
  paper entry pacing and capital rotation pressure.
- The benchmark scorecard now tracks buy-only judged counts, working/mixed/
  lagging counts, buy working rate, and buy average decision edge for `SPY`
  and `QQQ`.
- When broader buy/persistence learning has not already adjusted entry rules,
  strong benchmark-specific buy evidence can slightly increase target entry
  size, add one new-idea slot, and loosen sector-repeat pressure; weak
  benchmark-specific buy evidence can slightly reduce target size, remove one
  new-idea slot, and strengthen sector diversification pressure.
- The entry strategy profile now includes `benchmark_rotation_stats`, and the
  token-protected staging verification contract checks the new
  `benchmark_entry_pacing` evidence path.
- Cloud Run service revision `atlas-dashboard-stg-00118-f7x` is live on image
  `20260712-benchmark-entry-pacing`.
- The deployed image digest is
  `sha256:e469493715c0b890ca323166ac20fe32003ad2d589b604fe35cdc09a07f8851b`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00118-f7x` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, benchmark scorecard, benchmark exit tuning,
  benchmark entry pacing, autonomous queue behavior, and accountability report
  availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image; manual executions `atlas-daily-stg-xdnhd` and
  `atlas-weekly-stg-n2lwj` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00118-f7x`.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` pass with 177 tests.

Latest staging update:

- Atlas now exposes an owner-facing capital-rotation scoreboard in the Stage 5
  paper-learning section.
- The scoreboard groups simulated capital by sector and shows open exposure,
  open weight, gross buys, gross sells, net committed capital, realized and
  unrealized P/L, judged buy counts, buy working rate, and average
  benchmark-relative edge.
- Each sector receives a plain-language posture such as `press`, `watch`,
  `diversify`, or `review`, so the owner can see whether Atlas believes a
  sector is earning more simulated capital or should face concentration/review
  pressure.
- The token-protected dashboard verification contract now includes
  `capital_rotation_scoreboard`.
- Cloud Run service revision `atlas-dashboard-stg-00120-lmh` is live on image
  `20260713-capital-rotation-scoreboard-fast`.
- The deployed image digest is
  `sha256:8dffd994b555e381d49735107eff613ee9236e756516a4e0c22d7368dee1942f`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00120-lmh` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, benchmark scorecard, benchmark exit tuning,
  benchmark entry pacing, capital rotation scoreboard, autonomous queue
  behavior, and accountability report availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same optimized image; manual executions `atlas-daily-stg-7pcmh` and
  `atlas-weekly-stg-v8nm5` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00120-lmh`.
- The in-app browser reaches the live staging app and correctly redirects to
  the owner Google sign-in boundary.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` pass with 178 tests.

Latest staging update:

- Atlas now exposes the sector-level paper-learning bridge behind its small
  strategy boosts and cautions.
- The strategy helper now summarizes 3-snapshot sector buy evidence using the
  same rules already used for paper-entry ranking: sectors with at least two
  judged buys and more working than lagging outcomes can receive a `+1.5`
  paper-learning sector boost, while sectors with more lagging than working
  outcomes can receive a `-2.0` caution.
- The dashboard paper-learning panel now shows a `Sector learning bridge`
  card with the checkpoint, minimum judged-buy count, sector posture,
  working/mixed/lagging counts, and visible `Strategy tilt` amount.
- The token-protected dashboard verification contract now includes
  `sector_learning_bridge`.
- The verification endpoint no longer calls the full owner-control model; it
  checks the already-built paper payload directly, avoiding unnecessary
  autonomous-review work during read-only smoke checks.
- Cloud Run service revision `atlas-dashboard-stg-00122-2vz` is live on image
  `20260715-sector-learning-bridge-verification-fast`.
- The deployed image digest is
  `sha256:d2a4aab7827d7cda17341deecf67b742102f9ea22e02e6ea75666d9ef9fe9b41`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00122-2vz` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, benchmark scorecard, benchmark exit tuning,
  benchmark entry pacing, capital rotation scoreboard, sector learning bridge,
  autonomous queue behavior, and accountability report availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same optimized image; manual executions `atlas-daily-stg-tchkh` and
  `atlas-weekly-stg-kb9jf` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00122-2vz`.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` pass with 180 tests.
- The in-app browser controller could not be used on this pass because the
  current bundled browser runtime failed during setup by attempting to redefine
  a protected `process` global in the Node kernel. Live dashboard verification
  and staging readiness still passed through the token-protected contract.

Latest staging update:

- Atlas now uses sector-learning cautions as a stronger simulated paper-entry
  gate, not just a ranking adjustment.
- Sectors with at least two judged 3-snapshot buys and more lagging than
  working outcomes still receive the visible `-2.0` sector caution, and Atlas
  now requires stronger benchmark excess, sector-relative strength, sector
  breadth, trend quality, persistence, and follow-through before opening
  another simulated buy in that sector.
- Positive sector learning remains intentionally modest: it can still provide a
  small `+1.5` simulated strategy boost and slightly easier confirmation
  thresholds, but it does not bypass trend, news, risk, or benchmark filters.
- The sector-learning bridge headline and caution summaries now explain that
  lagging sectors face stronger simulated-entry confirmation.
- Cloud Run service revision `atlas-dashboard-stg-00123-kh4` is live on image
  `20260715-sector-caution-gating`.
- The deployed image digest is
  `sha256:0e4f84fd5a1ac49d9186247a5e6a077374d5e497b2aa3dc3fec78c03247c9b47`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00123-kh4` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, benchmark scorecard, benchmark exit tuning,
  benchmark entry pacing, capital rotation scoreboard, sector learning bridge,
  autonomous queue behavior, and accountability report availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image; manual executions `atlas-daily-stg-tr5dp` and
  `atlas-weekly-stg-c2cgk` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00123-kh4`.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` pass with 181 tests.
- The in-app browser controller still cannot be used because the current
  bundled browser runtime fails during setup by attempting to redefine a
  protected `process` global in the Node kernel. Live dashboard verification
  and staging readiness passed through the token-protected contract.

Current in-flight stage:

- The next practical step is to measure whether sector-gate cleared,
  tightened, and boosted decisions subsequently outperform their SPY/QQQ
  benchmarks, then use that evidence to tune sector-specific simulated entry
  strictness and position pacing. Keep all autonomy limited to the simulated
  paper account and preserve the owner-visible audit trail.

Latest staging update:

- Atlas now exposes a `Sector gate audit` in the paper-learning dashboard,
  counting active sector-gated candidates by cleared, tightened, boosted, and
  eligible status.
- Accepted simulated buy recommendations are now audited for sector-gate
  rationale usage, so Atlas can show how many accepted paper buys cleared,
  tightened, or benefited from constructive sector evidence.
- The strategy learning context now uses the same 3-snapshot sector checkpoint
  that the owner-visible sector-learning bridge already shows, keeping
  candidate gating and dashboard telemetry aligned.
- The token-protected dashboard verification contract now includes
  `sector_gate_audit`.
- Cloud Run service revision `atlas-dashboard-stg-00128-n86` is live on image
  `20260715-sector-gate-audit`.
- The deployed image digest is
  `sha256:e97cd40d025c39696a6cab8e018d97af17a24093419c15be137a7eaf7f25db37`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00128-n86` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, benchmark scorecard, benchmark exit tuning,
  benchmark entry pacing, capital rotation scoreboard, sector learning bridge,
  sector gate audit, autonomous queue behavior, and accountability report
  availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image; manual executions `atlas-daily-stg-9znm9` and
  `atlas-weekly-stg-8r55h` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00128-n86` with both
  recurring schedules enabled.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` pass with 185 tests.
- The in-app browser controller still cannot be used because the current
  bundled browser runtime fails during setup by attempting to redefine a
  protected `process` global in the Node kernel. Live dashboard verification
  and staging readiness passed through the token-protected contract.

Latest staging update:

- Atlas now exposes sector-learning gate telemetry in accepted simulated buy
  rationales and the owner dashboard sector bridge.
- Strong lagging-sector paper buys now show that they cleared stronger
  confirmation, including the number of gate checks that passed.
- The dashboard verification endpoint now uses a lightweight
  `build_verification()` read model that bypasses the refresh wrapper and full
  dashboard build, preventing smoke-check timeouts while preserving Stage 5
  contract fields.
- Cloud Run service revision `atlas-dashboard-stg-00127-88b` is live on image
  `20260715-sector-gate-telemetry-lightverify2`.
- The deployed image digest is
  `sha256:363bdd77ba297591b3074f83270bdc95dd5507021a6e589393852b4649ef0969`.
- `scripts/gcp_dashboard_verification.ps1` passes against revision
  `00127-88b` and confirms the Stage 5 dashboard contract, persistence
  learning, benchmark labels, benchmark scorecard, benchmark exit tuning,
  benchmark entry pacing, capital rotation scoreboard, sector learning bridge,
  autonomous queue behavior, and accountability report availability.
- Cloud Run jobs `atlas-daily-stg` and `atlas-weekly-stg` were updated to the
  same image; manual executions `atlas-daily-stg-5n4vl` and
  `atlas-weekly-stg-rcmgx` both completed successfully.
- Recurring schedules are enabled again after the guarded resume flow.
- `scripts/gcp_staging_readiness.ps1` passes on revision `00127-88b` with both
  recurring schedules enabled.
- Focused tests for `tests.test_paper_strategy`, `tests.test_paper_trading`,
  `tests.test_paper_monitor`, `tests.test_owner_controls`,
  `tests.test_web_dashboard`, `tests.test_web_cloud`, and
  `tests.test_gcp_scripts` pass with 184 tests.
- The in-app browser controller still cannot be used because the current
  bundled browser runtime fails during setup by attempting to redefine a
  protected `process` global in the Node kernel. Live dashboard verification
  and staging readiness passed through the token-protected contract.

Latest stabilization update:

- Atlas now preserves the sector-gate outcome contract even when the live
  paper account has not accumulated a judged sector-gate buy yet.
- The deployment helper redacts the dashboard verification token from its
  displayed Cloud Run command.
- Temporary cloud-inspection downloads are ignored by Git and must remain
  private local artifacts.
- Cloud Run service revision `atlas-dashboard-stg-00130-d28` is live on image
  `20260726-stabilize-sector-outcomes`.
- The deployed image digest is
  `sha256:95f8aff567fc0e76e1765fd1b3ad68bfa340966e14f12dbab3dcce0e9cc9558e`.
- The token-protected dashboard verification passes all 12 Stage 5 contract
  checks, including sector-gate outcomes.
- Manual executions `atlas-daily-stg-bq5x9` and
  `atlas-weekly-stg-qngb5` both completed successfully on the same image.
- Recurring schedules are enabled again under the existing owner-approved
  `$0-$5` monthly target and `$10` gross-usage alert.
- `scripts/gcp_staging_readiness.ps1` passes all 25 automated checks on
  revision `00130-d28`.
- The full local automated suite passes with 399 tests.
- The only remaining Web Phase 2 manual identity gates are cross-device owner
  login and non-owner Google account denial.

Current in-flight stage:

- Accumulate live simulated sector-gate outcome evidence and use it only after
  a meaningful sample exists to tune sector-specific paper entry strictness
  and position pacing. Keep all autonomy limited to the simulated paper
  account and preserve the owner-visible audit trail.

Latest owner-readiness update:

- Atlas now exposes a conservative `Real-capital discussion gate` inside the
  Stage 5 validation scoreboard.
- The gate measures nine standards: observation depth, judged decisions,
  realized exits, SPY/QQQ outperformance, decision quality, exit quality,
  realized win rate, five-snapshot persistence, and turnover discipline.
- Passing every standard can only mark Atlas ready for owner review. It cannot
  enable brokerage access or real-money trading.
- Current live status is `Paper only`, with 3 of 9 standards passing.
- Cloud Run revision `atlas-dashboard-stg-00131-2qh` is live on image
  `20260726-real-capital-readiness`.
- The deployed image digest is
  `sha256:d9edb76b7385af3e1700915b90675788cf9aa9b74269abb6fb247dd3397ba6ed`.
- All existing token-protected dashboard checks pass on revision `00131-2qh`.
- The full local automated suite passes with 399 tests.

Current in-flight stage:

- Let the enabled daily and weekly paper cycle accumulate evidence against the
  nine discussion gates. Improve decision and exit quality before considering
  any expansion beyond paper simulation.

Latest owner-workspace usability and reliability update:

- The Overview page now opens with a concise owner briefing that answers what
  Atlas is doing, what needs attention, the current paper result, and whether
  the owner needs to act.
- Each navigation page now has its own title and plain-language purpose text.
- The briefing is responsive and was visually checked at desktop and phone
  widths.
- Full dashboard generation now evaluates paper feedback once per request and
  reuses a file-signature cache for the append-only paper ledger.
- Cloud refreshes now download only the current account, ledger, task state,
  and latest market snapshot instead of repeatedly transferring the historical
  artifact bundle.
- A cloud-sized local profile improved from 133.8 seconds to 1.7 seconds on the
  first build and 1.4 seconds on a repeated build.
- Cloud Run revision `atlas-dashboard-stg-00135-pl7` is live on image
  `20260726-owner-briefing-live`.
- The deployed image digest is
  `sha256:a8caee14a8de84dbb67fabc5974dbd050a9b3bc0b227264f0ff6fe3369a2a248`.
- The signed-in live dashboard reached `Live` in 2.1 seconds with no error
  banner or browser console errors.
- The full local automated suite passes with 402 tests.

Current in-flight stage:

- Continue accumulating Stage 5 paper evidence while simplifying each
  owner workflow. The next usability work should prioritize decision
  summaries and progressive disclosure on Recommendations and Paper Portfolio
  without weakening the detailed audit trail.
