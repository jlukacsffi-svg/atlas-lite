# Atlas Capital Research Roadmap

Atlas Capital Research should develop in stages from a reliable research assistant into an autonomous investment research company.

Trading autonomy should be earned gradually through reliability, auditability, risk discipline, paper trading performance, and explicit owner approval.

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

## Current Recommended Sequence

1. Preserve and monitor the completed daily reporting, scoring, memory, portfolio, and research-organization foundations.
2. Begin Stage 5 with a strictly simulated portfolio and immutable recommendation log.
3. Establish paper-trading risk rules and benchmark evaluation.
4. Discuss real trading only after Atlas has proven reliability and discipline over a meaningful test period.
