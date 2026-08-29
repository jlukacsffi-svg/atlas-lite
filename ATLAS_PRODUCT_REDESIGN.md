# Atlas Website Redesign

Status: product prototype in progress

## Product Goal

Create a clear, professional investment workspace that helps a user answer five
questions quickly:

1. What changed?
2. What does Atlas recommend?
3. Why does Atlas recommend it?
4. What do I own, and how is it performing?
5. What needs my attention next?

The redesign is feature-first. It uses realistic, explicitly labeled prototype
data until each surface is connected to the existing Atlas research engine.
The current production dashboard remains intact during this work.

## Primary Navigation

- Today: daily priorities, recommendations, portfolio result, market context,
  risks, and upcoming catalysts.
- Discover: ranked ideas, screener, watchlists, sectors, and saved searches.
- Research: company overview, Atlas Score, thesis, financials, valuation,
  catalysts, risks, news, peers, and research history.
- Portfolio: performance, holdings, allocation, risk, income, attribution, and
  scenario analysis.
- Activity: recommendations, approvals, simulated transactions, closed
  positions, decisions, and audit history.
- Reports: morning, weekly, monthly, opportunity, risk, and portfolio reports.
- Alerts: actionable alerts, delivery rules, thresholds, and quiet hours.
- Settings: account, workspace, investment preferences, paper mode, security,
  data sources, billing, privacy, and future integrations.

## Experience Rules

- The first screen is a working decision surface, not a marketing page.
- Each page has one clear purpose and a small number of primary actions.
- Recommendations always show action, conviction, price context, thesis,
  catalyst, risk, and next step.
- Portfolio holdings and recommended purchases are visually distinct.
- Advanced evidence is available through drill-down, not shown by default.
- Technical operations, development progress, and internal diagnostics do not
  appear in the investor's primary navigation.
- Every chart labels its period, benchmark, units, and data freshness.
- Prototype data is visibly labeled and can never be mistaken for a live order.
- Trading mode and data freshness remain visible at all times.
- Mobile layouts preserve decisions and alerts before secondary analytics.

## Feature Inventory

### Today

- Daily executive brief
- Priority decision queue
- Recommended buys, holds, trims, and exits
- Portfolio value and benchmark comparison
- Market and sector pulse
- Risk alerts
- Earnings and catalyst calendar
- Latest Atlas activity

### Discover

- Search and security lookup
- Ranked opportunity list
- Multi-factor screener
- Custom and system watchlists
- Sector and theme exploration
- Saved filters
- Side-by-side comparison

### Research

- Quote and price history
- Atlas Score and five component scores
- Thesis, evidence, objections, and confidence
- Financial statements and growth trends
- Valuation and peer comparison
- Earnings, news, insider, analyst, and corporate-action timeline
- Research notes, tasks, sources, and score history

### Portfolio

- Account and portfolio selector
- Performance versus SPY and QQQ
- Holdings and cash
- Allocation and concentration
- Sector, factor, and position risk
- Gain/loss and attribution
- Dividends and income
- Scenarios, rebalancing, and tax-lot views
- Paper and future approved live-account separation

### Activity And Governance

- Recommendation history
- Owner decisions
- Paper fills and closed positions
- Buy/sell rationale journal
- Policy changes
- Exportable audit trail
- Explicit authority and approval state

### Reports And Alerts

- Report reader and archive
- Download, print, and email delivery
- Alert inbox and severity
- Price, score, earnings, risk, news, and portfolio alerts
- Channel, frequency, threshold, and quiet-hour preferences

### Account Platform

- Managed sign-in and recovery
- MFA/passkey support
- Private workspaces and roles
- Notification preferences
- Privacy export and deletion
- Sessions, devices, and security log
- Subscription and data-plan foundations
- Broker connections disabled until separately approved

## Reuse Strategy

The existing Python modules remain the source for market data, scoring,
research, reports, paper strategy, risk, portfolio accounting, audit history,
tenant isolation, authentication, and cloud storage. The new interface should
consume stable view-model APIs instead of duplicating that logic in the
browser.

## Delivery Sequence

1. Build and approve the complete interactive prototype.
2. Freeze the visual system and page contracts.
3. Map every prototype field to an existing API, a new API, or a deferred
   capability.
4. Connect read-only market, research, report, and paper-portfolio data.
5. Connect owner decisions and paper controls with existing authorization.
6. Validate accessibility, responsive behavior, security, and data integrity.
7. Replace the current dashboard only after parity and owner approval.

This redesign does not expand Atlas's financial authority. Real brokerage
execution remains disabled.
