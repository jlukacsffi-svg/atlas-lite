# Atlas Capital Research Roadmap

Atlas Capital Research should develop in stages from a reliable research assistant into an autonomous investment research company.

Trading autonomy should be earned gradually through reliability, auditability, risk discipline, paper trading performance, and explicit owner approval.

Atlas will also develop a secure web platform so its intelligence can be
presented through modern dashboards, graphics, and private user accounts.
Web-platform maturity and trading autonomy are separate tracks: a richer
interface never grants additional financial authority.

## Guiding Principle

Atlas should earn autonomy one layer at a time.

The near-term mission is not to trade. The near-term mission is to become a dependable research, scoring, reporting, and portfolio-intelligence system.

## Stage 1: Reliable Daily Briefing

Complete.

Goal: make Atlas Lite consistently useful every day.

Build:

- Reliable market data fetching.
- Yahoo fallback behavior.
- Morning Executive Brief.
- Executive Summary.
- News Highlights.
- Risk and opportunity flags.
- HTML reports.
- Scheduled daily runs.
- Email delivery.

Success test:

Atlas produces a useful daily brief without babysitting.

## Stage 2: Research Memory And Scoring

Complete at the foundation level.

Goal: Atlas starts remembering and ranking securities.

Build:

- Expanded 100-150 security universe.
- Watchlist categories: Core, Watchlist, Emerging, Avoid.
- Growth, Quality, Moat, Momentum, and Risk scores.
- Historical report archive.
- Basic company profiles.
- Earnings calendar.
- Analyst rating changes.
- Insider transaction tracking.

Success test:

Atlas can say not just what moved, but what matters and how new information changes conviction.

## Stage 3: Portfolio Intelligence

Complete at the software-foundation level. Joe can add the private local portfolio file when ready.

Goal: Atlas understands Joe's actual holdings, but still does not trade.

Build:

- Manual portfolio import.
- Position tracking.
- Allocation analysis.
- Gain/loss tracking.
- Concentration risk.
- Benchmark comparison.
- Portfolio-specific risk alerts.
- Local portfolio history.

Success test:

Atlas can brief Joe on both the market and his portfolio exposure.

## Stage 4: Multi-Agent Research Organization

Complete at the first operational level.

Goal: Atlas becomes company-like.

Build:

- CEO Agent for prioritization.
- CIO Agent for investment thesis review.
- CRO Agent for risk challenge.
- Sector Analyst Agents.
- Reporting Agent.
- Research archive and task queue.
- Agent memory.
- Role-specific research briefs.
- Structured findings and owner-review workflow.

Success test:

Atlas can assign research, challenge assumptions, and produce organized recommendations.

Current result:

Atlas routes daily, weekly, sector, and portfolio signals into persistent role-based tasks; tracks their status; records findings; and presents recommendations for owner review.

## Stage 5: Paper Trading

Current phase. Software foundation complete; evaluation period has not started.

Goal: prove decision quality without risking money.

Build:

- Simulated portfolio.
- Buy/sell recommendation logging.
- Paper trade execution.
- Performance attribution.
- Win/loss tracking.
- Thesis tracking.
- Risk rule testing.

Success test:

Atlas beats or meaningfully informs benchmarks over time, with a clear audit trail.

Current result:

Atlas can maintain a strictly simulated account, enforce conservative risk
rules, log recommendations and linked fills, calculate realized and unrealized
performance, compare results with SPY and QQQ, and generate an audit report.
The account is initialized with $100,000 simulated cash. Atlas can generate
transparent, reviewable paper proposals, but separate simulation approval is
required before a fill. Stage 5 cannot be considered complete until it has
accumulated a meaningful performance history.

Software status:

The Stage 5 software scope is complete. The live paper evaluation period is now
running with a $100,000 simulated account and its first owner-approved position.
Stage 5 remains in validation until enough daily history exists to evaluate
returns, exits, win rate, and benchmark-relative behavior.

## Stage 6: Human-Approved Trading

Goal: Atlas recommends trades and prepares orders, but Joe approves execution.

Build:

- Brokerage integration in read-only mode first.
- Trade proposal workflow.
- Position sizing rules.
- Risk limits.
- Approval screen.
- Full audit log.

Success test:

Atlas produces disciplined trade proposals that Joe reviews and approves.

## Stage 7: Limited Autonomous Trading

Only after explicit owner approval.

Build:

- Strict trading policy.
- Maximum position size.
- Maximum daily trade count.
- No margin unless explicitly approved.
- No options unless explicitly approved.
- No leverage.
- Emergency stop.
- Human override.
- Full logs and alerts.

Success test:

Atlas executes only within narrow, pre-approved boundaries.

## Stage 8: Autonomous Capital Research Company

Long-term vision.

Atlas operates like a private investment research firm that never sleeps.

Capabilities:

- Monitors markets continuously.
- Maintains research memory.
- Tracks sectors and companies.
- Evaluates risk.
- Runs paper or live strategies, depending on approved autonomy level.
- Produces executive intelligence.
- Escalates decisions to Joe based on risk level.

## Parallel Track: Secure Web Platform

Detailed plan: `WEB_PLATFORM_PLAN.md`

Goal:

Turn Atlas into a modern, secure, cloud-hosted product where each user has a
private account and sees only their own research, portfolio, alerts, and
paper-trading information.

Phases:

1. Read-only local owner dashboard with modern charts and responsive design. Complete.
2. Secure single-user cloud hosting independent of Joe's laptop. Foundation in progress.
3. Invite-only multi-user accounts with strict tenant isolation.
4. Controlled customer beta with privacy, support, and subscription foundations.
5. Public self-service product only after security and operational readiness.

Core requirements:

- Modern financial dashboard design.
- Interactive portfolio, market, scoring, sector, risk, and performance graphics.
- Managed authentication, MFA/passkeys, secure recovery, and session controls.
- Server-side authorization and tenant isolation for every private record.
- Encryption, managed secrets, audit logs, backups, monitoring, and incident response.
- Per-user watchlists, reports, portfolios, research tasks, alerts, and paper accounts.
- Cloud scheduling so Atlas does not depend on Joe's laptop.
- Privacy, data export/deletion, legal disclosures, and security review before public launch.

Near-term rule:

Do not disrupt the active Stage 5 evaluation. Web Phase 1 should begin as a
read-only presentation layer over stable Atlas outputs, then advance
incrementally.

Current Web Phase 2 result:

- Cloud billing remains disabled and no paid resources are active; a
  minimal-cost staging direction is approved in principle.
- Authentication, private artifact storage, guarded deployment, and
  zero-cost controls are implemented.
- A checksum-verified private backup and isolated restoration drill are
  implemented and passing.
- The next gate is credit-expiration verification and explicit approval of the
  `$10` monthly staging alert budget before actual hosting begins.

## Current Recommended Sequence

1. Preserve and monitor the completed daily reporting, scoring, memory, portfolio, and research-organization foundations.
2. Begin Stage 5 with a strictly simulated portfolio and immutable recommendation log.
3. Establish paper-trading risk rules and benchmark evaluation.
4. Operate and refine the completed read-only local owner dashboard while paper results accumulate.
5. Plan secure single-user cloud hosting after the dashboard and service boundaries are stable.
6. Add multi-user accounts only after tenant isolation and security controls are tested.
7. Discuss real trading only after Atlas has proven reliability and discipline over a meaningful test period.
