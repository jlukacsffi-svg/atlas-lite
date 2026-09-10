# Atlas Redesign Integration Map

The redesign prototype lives in `web_redesign/`. It is intentionally separate
from the live owner dashboard in `web/`.

## Existing Capability Reuse

| Product surface | Existing source | Integration work |
|---|---|---|
| Market quotes and daily movement | `app/market_data.py` | Normalize quote freshness and delayed-data labels. |
| Atlas Score and components | `app/scoring.py`, factor modules | Add score history and a security-detail view model. |
| Ranked ideas and recommendations | `app/paper_strategy.py`, dashboard API | Separate ranked ideas, actionable recommendations, and held positions. |
| Company thesis and evidence | `app/research_analyst.py`, `app/research_memory.py` | Build one security research endpoint with sources and update history. |
| News, earnings, analysts, insiders | Existing intelligence modules | Merge events into a dated company timeline with provenance. |
| Portfolio holdings and performance | `app/paper_trading.py`, `app/portfolio.py` | Add allocation, contribution, and period-selection view models. |
| Risk and position monitoring | `app/paper_risk.py`, `app/paper_monitor.py` | Produce concise portfolio and holding-level risk summaries. |
| Recommendation and decision history | Paper ledger and owner controls | Create a paginated, filterable activity API. |
| Reports | Existing report generator and archive | Add report metadata, reader content, download, and delivery actions. |
| Alerts | Existing owner attention and monitoring signals | Add durable read state, alert rules, severity, and delivery preferences. |
| Authentication and workspace | Existing OAuth and tenant foundations | Preserve owner-only cloud mode until multi-user gates close. |
| Audit and policy history | Existing append-only ledgers | Expose safe, filterable audit records without leaking private internals. |

## New Product APIs

The prototype needs a small set of stable, page-oriented endpoints rather than
one very large dashboard response:

- `GET /api/v2/today`
- `GET /api/v2/discover`
- `GET /api/v2/securities/{ticker}`
- `GET /api/v2/portfolios/{portfolio_id}`
- `GET /api/v2/activity`
- `GET /api/v2/reports`
- `GET /api/v2/reports/{report_id}`
- `GET /api/v2/alerts`
- `GET /api/v2/preferences`

Implemented read-only endpoints:

- `GET /api/v2/today`
- `GET /api/v2/ideas`

These endpoints are backed by the existing research archive and paper ledger.
The redesigned browser loads both before rendering and exposes failures,
staleness, and empty results rather than manufacturing replacement data.

The prototype also defines a contextual paper-decision preview that should be
fed by a fresh, server-calculated endpoint before writes are enabled:

- `POST /api/v2/paper-decisions/preview`

Later authenticated writes should be narrow and separately authorized:

- Watchlist membership
- Alert read state and preferences
- Report delivery requests
- Owner paper decisions
- Paper operating-mode and policy changes

The future submit endpoint must retain the existing exact simulation
confirmation, signed owner session, CSRF, risk review, idempotency, and
append-only audit requirements. Browser calculations are display-only and
must never authorize or construct the final server order.

No brokerage or real-money endpoint is part of this redesign phase.

## Frozen Read-Only Page Contracts

All responses use ISO 8601 timestamps, USD amounts as numbers, percentages as
numbers, and an explicit `data_status` object containing `as_of`, `session`,
`source`, and `is_live`. Missing data is `null`; it is never replaced with a
plausible-looking value.

| Page | Required response groups | Primary interaction |
|---|---|---|
| Today | snapshot status, primary decision, portfolio summary, ranked recommendations, risks, benchmarks, catalysts, recent research | Open evidence or a contextual report/alert |
| Ideas | security identity, action, score, price, daily move, confidence, catalyst, risk, ownership state | Filter locally, then open security research |
| Research | quote freshness, thesis, evidence, score components, financials, valuation, events, peers, history, portfolio context | Open a server-calculated paper preview |
| Portfolio | account summary, positions, cash, returns, benchmark series, allocation, attribution, risk observations | Open holding research or activity |
| Activity | recommendation, owner-decision, paper-fill, policy, and audit events with immutable IDs and timestamps | Filter and inspect; no mutation in read-only phase |
| Reports | report metadata plus sanitized rendered content | Select, download, or request approved delivery |
| Alerts | severity, status, subject, reason, created time, and destination route | Open related research; durable read state is deferred |

The first integration release covers Today, Ideas, Research, Portfolio, and
Reports. Activity and Alerts remain read-only until their pagination, durable
state, and tenant-isolation tests are complete.

Navigation is intentionally limited to Today, Ideas, Portfolio, and Activity.
Research is reached from a security, while Reports and Alerts are contextual
destinations. Settings remains an account-level destination. This structure is
part of the frozen prototype contract.

## Prototype Coverage

Implemented now:

- Responsive application shell and global search
- Today decision workspace
- Discover rankings and future screener structure
- Company research workspace
- Portfolio performance, holdings, allocation, attribution, risk, and scenarios
- Activity and governance history
- Report archive and reader
- Alert inbox and preference controls
- Account, paper mode, security, privacy, and integration settings
- Recommendation-to-paper-preview flow with calculated buy, trim, and exit
  impact, policy status, and a locked server confirmation boundary
- Real read-only Today and Ideas integration with server-derived freshness,
  research-status semantics, paper-account reconciliation, and explicit
  development fallback behavior

Prototype-only interactions are visibly labeled. They do not write to Atlas,
create a paper fill, send email, or change cloud state.

## Replacement Gate

The redesign can replace `web/` only after:

1. Owner approval of the information architecture and visual system.
2. Read-only data parity for Today, Discover, Research, Portfolio, and Reports.
3. Existing owner paper controls are reconnected with the same or stronger
   server-side authorization and audit behavior.
4. Responsive, accessibility, browser, and protected-contract checks pass.
5. The existing cloud dashboard remains available as a rollback revision.
