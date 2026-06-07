# Stage 5 Plan: Paper Trading

Stage 5 tests Atlas recommendations with simulated capital only.

It must not connect to a brokerage, submit real orders, or create financial
commitments. Paper trading is an evaluation system, not permission to trade.

## Objective

Atlas should maintain a simulated account with a complete audit trail so its
recommendations, risk discipline, and performance can be measured against
benchmarks before any real-trading discussion.

## Initial Risk Policy

- Starting cash is explicitly chosen when the account is initialized.
- Long positions only.
- Market-style simulated fills only.
- No margin.
- No short selling.
- No options, leverage, or borrowed capital.
- Minimum cash reserve: 10% of account equity.
- Maximum position size after a buy: 20% of account equity.
- Maximum simulated trades per day: 5.
- Sell quantity may not exceed simulated holdings.
- Every order requires a thesis.

## Local Data

Paper-trading records live in:

```text
paper_trading/
```

The directory is ignored by Git because it contains owner-specific strategy
history.

Files:

- `account.json`: current simulated cash and positions.
- `ledger.jsonl`: append-only event history.

## First Milestone

Implement:

- Account initialization.
- Buy and sell validation.
- Simulated execution.
- Average-cost position accounting.
- Realized gain/loss accounting.
- Risk-rule enforcement.
- Append-only order ledger.
- Account status command.

## Evaluation Milestone

Implemented:

- Immutable recommendation IDs.
- Recommendation-to-fill linkage.
- Mark-to-market performance snapshots.
- SPY and QQQ comparison.
- Position-level unrealized attribution.
- Realized win/loss and win-rate tracking.
- Standalone Markdown performance report.
- Morning Brief paper-performance section.
- Separate recommendation, proposal, approval, and fill records.
- Single-use approved proposal requirement for every simulated fill.
- Explicit conversion from owner-approved research to a pending paper proposal.
- Transparent `paper_strategy_v1` candidate generation.
- Maximum three new daily proposals with approximately 5% target sizing.
- Pending proposal rationale in the Morning Brief.
- CRO-style risk reviews before proposal approval.
- Automatic policy rejection for hard-hold paper proposals.
- Maximum three active pending or approved buy proposals.
- Strategy-level rejection of new entries already down 8% or more.
- Daily open-position thesis reviews.
- Maintain, review, and exit verdicts with append-only history.
- Exit proposals that remain subject to risk review and simulation approval.
- Immutable recommendation linkage for every strategy-generated proposal.
- Automatic daily refresh of the standalone performance report.

## Safety Boundary

No Stage 5 code may:

- Connect to a brokerage.
- authenticate with a brokerage.
- transmit an order.
- imply that a paper fill occurred in a real market.

## Success Test

The foundation is successful when Atlas can simulate valid trades, reject
policy violations, preserve a complete ledger, and report account state without
touching real money.
