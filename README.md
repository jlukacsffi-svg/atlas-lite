# Atlas Lite

A lightweight market monitoring tool that generates daily executive briefs for a curated watchlist of stocks.

## Features

- Loads a structured security universe with sector, category, notes, and company-profile metadata
- Calculates transparent Atlas Scoring Engine v1 rankings with automated Growth, Quality, and Momentum
- Produces sector scorecards and a catalyst-aware Atlas Priority Ranking
- Produces conservative watchlist category review recommendations
- Caches SEC Company Facts locally to make repeated daily runs faster and more resilient
- Tracks upcoming earnings events for Atlas universe securities
- Tracks recent analyst-action headlines for upgrades, downgrades, initiations, and price-target changes
- Tracks recent SEC Form 4 insider transactions for Atlas universe companies
- Saves structured historical research snapshots for comparison over time
- Maintains a local research archive index for recent snapshots and reports
- Generates weekly research summaries from the local archive index
- Supports optional email delivery for daily briefs and weekly summaries
- Supports optional local portfolio exposure monitoring without trading
- Monitors a 100-security universe across AI infrastructure, AI power, cloud/software, defense, cybersecurity, robotics, healthcare, financials, consumer platforms, and ETFs
- Fetches real-time market data using yfinance
- Adds recent news headlines for major watchlist movers
- Generates a rule-based executive summary of market tone, sector strength, priority names, catalysts, risks, and volatility
- Generates Morning Executive Brief reports in markdown and HTML formats
- Supports Windows scheduled daily execution
- Supports optional SMTP email delivery using environment variables
- Saves reports to the `reports/` folder with timestamps

## Security Universe

The active security universe is loaded from:

```text
data/security_universe.json
```

Each security includes:

- Ticker
- Company name
- Sector
- Category: Core, Watchlist, Emerging, or Avoid
- Notes
- Basic company profile: thesis, key driver, and key risk
- Manual v1 component scores used as transparent seed values

## Atlas Scoring Engine v1

Atlas calculates a weighted total score from 0-100:

- Growth Score: 40%
- Quality Score: 20%
- Moat Score: 15%
- Momentum Score: 15%
- Risk Score: 10%

Higher scores are better. A higher Risk Score means a stronger risk profile, not more risk.

Atlas currently uses a hybrid v3 scoring model:

- Growth is calculated automatically from annual revenue and net-income growth reported in SEC filings.
- Quality is calculated automatically from annual profitability and cash-generation margins reported in SEC filings.
- Momentum is calculated automatically from recent market returns when Yahoo Finance history is available.
- Moat and Risk remain manual seed inputs stored in `data/security_universe.json`.
- If automated Growth, Quality, or Momentum data is unavailable, Atlas retains the corresponding manual seed score for that run.

The automated Growth Score uses annual filing comparisons from the SEC Company Facts API:

- Revenue growth is the primary input with a 70% weight.
- Net-income growth is a secondary input with a 30% weight when the prior year is positive.
- Each available metric is converted to a bounded 0-100 score centered on 50.
- The report displays the underlying growth rates and latest fiscal year so the input is auditable.

```text
Revenue metric score = 50 + (annual revenue growth * 2.0)
Net-income metric score = 50 + (annual net-income growth * 1.0)
Growth Score = weighted average of available metric scores, bounded from 0-100
```

The automated Quality Score uses metrics from the same annual SEC filing period:

- Net margin: 40% weight
- Operating cash-flow margin: 35% weight
- Free-cash-flow margin: 25% weight
- Available metric weights are renormalized when a filing metric is unavailable.

```text
Net-margin score = 50 + (net margin * 2.0)
Operating cash-flow margin score = 50 + (operating cash-flow margin * 1.5)
Free-cash-flow margin score = 50 + (free-cash-flow margin * 2.0)
Quality Score = weighted average of available metric scores, bounded from 0-100
```

The automated Momentum Score is centered on 50, uses 1-month and 3-month returns, and is bounded from 0-100:

```text
50 + (1-month return * 1.5) + (3-month return * 0.75)
```

The report also displays 1-month, 3-month, and 6-month returns so the automated input is auditable.

## Research Memory

Each run saves a structured JSON snapshot containing market data, security metadata, and Atlas scores.

Snapshots are written to:

```text
research_archive/snapshot_YYYYMMDD_HHMMSS.json
```

The archive is generated locally and ignored by Git. The Morning Executive Brief compares the current run with the most recent prior snapshot.

Each run also updates:

```text
research_archive/archive_index.json
research_archive/archive_index.md
```

The archive index keeps recent run metadata together, including snapshot links, report links, top movers, and score leaders. It is local-only and ignored by Git.

- **AI & Semiconductors**: NVDA, AMD, AVGO, TSM, ARM, ASML, MU, MRVL, QCOM, AMAT, LRCX, KLAC, INTC, ON
- **AI Networking & Infrastructure**: ANET, DELL, VRT
- **AI Power & Energy**: ETN, CEG, VST, GEV
- **Energy & Power**: NEE, FSLR, ENPH, BE
- **Cloud Platforms / Software / AI Software**: MSFT, AMZN, GOOGL, META, ORCL, CRM, NOW, ADBE, SNOW, DDOG, NET, AI, PLTR
- **Financials & Fintech**: V, MA, JPM, COIN, HOOD, SOFI
- **Defense & Aerospace**: LMT, NOC, RTX, GD, BA, HII, KTOS, AVAV, TXT, HEI, LHX, LDOS, BWXT, TDG, CW, MRCY
- **Cybersecurity**: CRWD, PANW, FTNT, ZS, OKTA, S, QLYS, CHKP, TENB
- **Software Expansion**: MDB, TEAM, HUBS, WDAY
- **Robotics & Automation**: ROK, CGNX, SYM, TER, ISRG
- **Healthcare & Life Sciences**: TMO, DHR, ABT, SYK, BSX, GEHC, VEEV, RXRX
- **Consumer & Platforms**: NFLX, UBER, SHOP, MELI, COST, BKNG
- **Benchmark ETFs**: SPY, QQQ, VGT, BOTZ, ROBO, CIBR, SMH, SOXX

## Report Contents

Each Morning Executive Brief includes:

1. **Date** - Report generation date
2. **Executive Summary** - Concise readout of market tone, sector strength, priority names, catalysts, risks, and volatility
3. **Research Agenda** - Open Stage 4 research tasks from the local queue
4. **Market Summary** - Overview of major indices
5. **Upcoming Earnings** - Atlas universe earnings events expected in the next 7 days
6. **Watchlist Summary** - Current prices and performance
7. **Portfolio Intelligence** - Optional local portfolio exposure monitoring
8. **Atlas Scoring Summary** - Weighted company rankings
9. **Sector Scorecard** - Sector-level average scores, day moves, and leaders
10. **Atlas Priority Ranking** - Research triage ranking using scores and near-term signals
11. **Watchlist Change Recommendations** - Conservative category review prompts
12. **Company Profile Highlights** - Thesis, key driver, and key risk for top-ranked companies
13. **Automated Growth** - SEC filing growth scores and underlying annual comparisons
14. **Automated Quality** - SEC filing profitability and cash-generation measurements
15. **Automated Momentum** - Momentum scores and recent return measurements
16. **Research Memory** - Changes since the most recent structured snapshot
17. **Top Movers** - Best and worst performing stocks
18. **News Highlights** - Recent headlines for stocks moving more than 2%
19. **Analyst Actions** - Recent analyst-action headlines for Atlas universe companies
20. **Insider Transactions** - Recent SEC Form 4 non-derivative transactions
21. **Potential Opportunities** - Notable price changes
22. **Risks To Watch** - Key considerations

## Installation

1. Clone or download the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script to generate today's Morning Executive Brief:

```bash
py -3.12 main.py
```

Run the Web Phase 1 local owner dashboard:

```bash
py -3.12 dashboard.py
```

Then open:

```text
http://127.0.0.1:8765
```

The dashboard is a read-only presentation of local Atlas research, paper-account,
performance, market, and research-queue data. It binds only to this computer and
does not create public accounts or expose Atlas to the internet.

To exercise the cloud-ready WSGI boundary locally:

```bash
py -3.12 -m pip install -r requirements-web.txt
py -3.12 cloud_dashboard.py
```

Cloud mode is deliberately fail-closed. It requires Google Identity-Aware Proxy,
the configured owner identity, an exact IAP audience, and persistent Atlas data.
See `WEB_PHASE2_PLAN.md` before attempting deployment.

Reports are saved to the `reports/` folder with a timestamp in the filename.

Each run writes both:

- `morning_brief_YYYYMMDD_HHMMSS.md`
- `morning_brief_YYYYMMDD_HHMMSS.html`

To generate a weekly research summary from the local archive index:

```bash
py -3.12 weekly_summary.py
```

The weekly run also adds deduplicated CIO and CRO assignments to the local research queue from score changes, recurring movers, sector weakness, and recurring score leaders.

Weekly summaries are saved to the `reports/` folder:

- `weekly_summary_YYYYMMDD_HHMMSS.md`
- `weekly_summary_YYYYMMDD_HHMMSS.html`

Each weekly summary includes:

- Weekly overview
- What Changed This Week narrative
- Key score changes across available snapshots
- Sector trend shifts
- Research action prompts
- Recurring top movers
- Recurring score leaders
- Run log with links to daily reports

If email delivery is enabled, the weekly summary command emails both weekly summary files.

## Stage 4 Planning

The Stage 4 multi-agent research organization should begin with a local research task queue, not a large autonomous agent framework.

The planning document is:

```text
STAGE4_PLAN.md
```

To list open local research tasks:

```bash
py -3.12 research_tasks.py list
```

To add a research-only task:

```bash
py -3.12 research_tasks.py add --role CIO --subject NVDA "Review thesis quality."
```

To generate task suggestions from the latest Atlas research archive:

```bash
py -3.12 research_tasks.py generate
```

To summarize the task queue by status, role, and priority:

```bash
py -3.12 research_tasks.py summary
```

To update task status with an optional note:

```bash
py -3.12 research_tasks.py status task_id closed --notes "Reviewed and closed."
```

To write a Markdown research agenda:

```bash
py -3.12 research_tasks.py agenda
```

To write a focused role brief:

```bash
py -3.12 research_tasks.py brief --role CRO
```

Use `CEO`, `CIO`, `CRO`, `Reporting`, or `"Sector Analyst"`. The CEO brief includes the full queue for prioritization; other briefs include only tasks assigned to that role.

To record a completed research finding and route it to owner review:

```bash
py -3.12 research_tasks.py complete task_id --conclusion "Thesis remains intact." --recommendation monitor --confidence medium --evidence "Earnings release"
```

To write the owner-review queue:

```bash
py -3.12 research_tasks.py review
```

To record Joe's disposition:

```bash
py -3.12 research_tasks.py decide task_id approve --notes "Reviewed."
```

Approval here records acceptance of a research recommendation only. It never authorizes or executes a trade.

Daily and weekly runs refresh the agenda and all role briefs automatically. When a local portfolio is configured, portfolio concentration, drawdown, and missing-data alerts also create reviewable CRO or Reporting tasks.

Local task data and generated role briefs are saved in `research_tasks/`, which is ignored by Git.

## Stage 5 Paper Trading

Paper trading is strictly simulated and cannot connect to a brokerage.

The design and risk policy are documented in:

```text
STAGE5_PLAN.md
```

Initialize a local simulated account:

```bash
py -3.12 paper_trading.py init --cash 100000
```

Preview a paper order without changing the account:

```bash
py -3.12 paper_trading.py preview buy NVDA 10 --price 150 --thesis "Example paper thesis."
```

Execute a simulated order:

```bash
py -3.12 paper_trading.py order buy NVDA 10 --price 150 --thesis "Example paper thesis."
```

Log a recommendation before a simulated fill:

```bash
py -3.12 paper_trading.py recommend buy NVDA 10 --price 150 --thesis "Example paper thesis." --confidence medium
```

The returned recommendation ID can be linked to a later simulated order with `--recommendation-id`.

Create and review a paper proposal:

```bash
py -3.12 paper_trading.py propose buy NVDA 10 --price 150 --thesis "Example paper thesis." --recommendation-id recommendation_id
py -3.12 paper_trading.py decide-proposal proposal_id approve --notes "Approved for simulation."
```

An approved proposal is required for every simulated fill and can be used only once:

```bash
py -3.12 paper_trading.py order buy NVDA 10 --price 150 --thesis "Example paper thesis." --proposal-id proposal_id
```

An owner-approved research finding can be converted into a pending paper proposal:

```bash
py -3.12 paper_trading.py propose-research task_id buy 10 --price 150
```

This conversion still does not execute a simulated order. The paper proposal requires a separate approval.

Review account state or the append-only ledger:

```bash
py -3.12 paper_trading.py status
py -3.12 paper_trading.py ledger
py -3.12 paper_trading.py proposals --status pending
```

Record performance from the latest Atlas research snapshot and generate the evaluation report:

```bash
py -3.12 paper_trading.py snapshot
py -3.12 paper_trading.py performance
py -3.12 paper_trading.py report
```

Daily Atlas runs automatically add a mark-to-market snapshot and Morning Brief section after a paper account has been intentionally initialized.

The daily run also uses `paper_strategy_v1` to create at most three deduplicated pending proposals from eligible high-scoring securities. The strategy targets roughly 5% of starting simulated cash per entry, excludes benchmarks and Avoid names, and never approves or executes its own proposals.

`paper_strategy_v1` skips new entries already down 8% or more in the current session. `paper_risk_v1` independently reviews every pending proposal. Sharp downside, missing data, or weak scores produce a hard hold and automatic paper-policy rejection. Elevated volatility or proposal concentration produces caution and leaves the proposal pending. At most three active buy proposals may remain in the queue.

`paper_monitor_v1` reviews each open simulated position once per day. It records the current return, Atlas score, thesis status, and a `maintain`, `review`, or `exit` verdict. Exit verdicts create pending sell proposals only; they still require risk review and separate simulation approval.

Every strategy-generated proposal first records an immutable recommendation and links the proposal to it. The daily run also refreshes `paper_trading/performance.md` after snapshots, proposal reviews, and position thesis reviews.

The initial policy prohibits margin, short selling, options, and leverage; preserves a 10% cash reserve; limits positions to 20% of simulated equity; and permits at most five simulated trades per day.

Paper account data is saved locally in ignored `paper_trading/`. No paper-trading command can transmit a real order.

## Future Web Platform

Atlas is planned to evolve into a modern, secure web product with responsive
dashboards, financial graphics, cloud operation, and private user accounts.

The staged product, design, architecture, multi-user, and security plan is:

```text
WEB_PLATFORM_PLAN.md
```

The current research and paper-evaluation work remains the foundation. The
first web phase will be a read-only local owner dashboard; public accounts will
not be enabled until authentication, authorization, tenant isolation, privacy,
backup, monitoring, and incident-response controls are validated.

## Scheduled Execution

Atlas includes PowerShell scripts for Windows Task Scheduler.

To test the scheduled runner manually:

```powershell
.\scripts\run_atlas_daily.ps1
```

To create or update a daily scheduled task at 7:00 AM:

```powershell
.\scripts\setup_windows_scheduled_task.ps1
```

To use a different time:

```powershell
.\scripts\setup_windows_scheduled_task.ps1 -RunTime "06:30"
```

To test the weekly summary scheduled runner manually:

```powershell
.\scripts\run_atlas_weekly.ps1
```

To create or update a weekly summary scheduled task for Sunday at 8:00 AM:

```powershell
.\scripts\setup_windows_weekly_summary_task.ps1
```

To use a different weekly schedule:

```powershell
.\scripts\setup_windows_weekly_summary_task.ps1 -RunDay "Friday" -RunTime "16:30"
```

Scheduled run logs are written to:

```text
logs/scheduled_run_YYYYMMDD_HHMMSS.log
logs/weekly_summary_run_YYYYMMDD_HHMMSS.log
```

## Email Delivery

Email delivery is optional and disabled by default.

Do not store email passwords or app passwords in this repository.

To enable email delivery, set these environment variables outside the repo:

```powershell
$env:ATLAS_EMAIL_ENABLED = "true"
$env:ATLAS_SMTP_HOST = "smtp.example.com"
$env:ATLAS_SMTP_PORT = "587"
$env:ATLAS_SMTP_USER = "your-email@example.com"
$env:ATLAS_SMTP_PASSWORD = "your-app-password"
$env:ATLAS_EMAIL_FROM = "your-email@example.com"
$env:ATLAS_EMAIL_TO = "recipient@example.com"
```

Optional settings:

```powershell
$env:ATLAS_SMTP_USE_STARTTLS = "true"
$env:ATLAS_SMTP_USE_SSL = "false"
```

When enabled, Atlas attaches both the Markdown and HTML reports to the email.

## Portfolio Intelligence

Portfolio intelligence is optional and local-only. Atlas does not trade and does not connect to brokerage accounts.

To enable portfolio exposure monitoring, copy:

```text
data/portfolio.example.json
```

to:

```text
data/portfolio.json
```

Then edit `data/portfolio.json` with local holdings. The real portfolio file is ignored by Git and should not be committed.

To validate the local portfolio file before running the daily brief:

```bash
py -3.12 portfolio_check.py
```

When configured, the daily brief includes:

- Estimated portfolio market value
- Estimated daily portfolio change
- SPY and QQQ benchmark context
- Change since previous local portfolio snapshot
- Top tracked positions
- Sector exposure
- Portfolio risk alerts such as position concentration, sector concentration, holding drawdowns, and missing market data

When a portfolio is configured, Atlas saves local portfolio snapshots in:

```text
portfolio_history/
```

This folder is ignored by Git.

## SEC Growth And Quality Data

Atlas identifies itself when requesting the official SEC Company Facts API. The default contact is the dedicated Atlas report email. To use a different SEC-compliant contact string:

```powershell
$env:ATLAS_SEC_USER_AGENT = "Atlas Capital Research contact@example.com"
```

SEC data is cached locally in:

```text
data_cache/sec/
```

The ticker-to-CIK map is cached for 30 days. Company Facts filings are cached for 7 days. If a fresh SEC request fails, Atlas may use a stale local cache rather than dropping automated Growth and Quality scores for that run. The `data_cache/` folder is ignored by Git.

## Earnings Calendar Data

Atlas retrieves upcoming earnings events from Nasdaq's public earnings calendar and filters the results to the active Atlas security universe.

Earnings calendar data is cached locally in:

```text
data_cache/earnings/
```

Daily earnings calendar payloads are cached for 18 hours. If a fresh request fails, Atlas may use a stale local cache so the report can still include the most recent known earnings calendar context. The `data_cache/` folder is ignored by Git.

## Analyst Action Data

Atlas tracks recent analyst-action signals by scanning finance headlines for terms such as upgrades, downgrades, initiations, reiterations, and price-target changes. This is headline-based tracking, not a full structured analyst-ratings database.

Analyst-action headline data is cached locally in:

```text
data_cache/analyst_actions/
```

Per-security analyst-action headline results are cached for 12 hours. If a fresh request fails, Atlas may use a stale local cache so the report can still include the most recent known analyst-action context. The `data_cache/` folder is ignored by Git.

## Insider Transaction Data

Atlas tracks recent insider transactions by scanning SEC company submissions for Form 4 and Form 4/A filings, then reading the raw ownership filing XML when available. The report currently displays non-derivative transactions such as purchases, sales, awards, option exercises, gifts, and tax-withholding dispositions.

Insider transaction data is cached locally in:

```text
data_cache/insider_transactions/
```

SEC company submissions are cached for 12 hours. Raw Form 4 filing XML is cached for 30 days. If a fresh request fails, Atlas may use stale local cache data so the report can still include the most recent known insider-transaction context. The `data_cache/` folder is ignored by Git.

If environment variables set in PowerShell are not visible to Atlas, create a local `.env` file in the project root. The `.env` file is ignored by Git and must not be committed.

Example `.env`:

```text
ATLAS_EMAIL_ENABLED=true
ATLAS_SMTP_HOST=smtp.gmail.com
ATLAS_SMTP_PORT=587
ATLAS_SMTP_USER=atlas.capital.reports@gmail.com
ATLAS_SMTP_PASSWORD=your-app-password
ATLAS_EMAIL_FROM=atlas.capital.reports@gmail.com
ATLAS_EMAIL_TO=jlukacsffi@gmail.com
ATLAS_SMTP_USE_STARTTLS=true
ATLAS_SMTP_USE_SSL=false
```

## Project Structure

The `scripts/` folder contains Windows scheduled execution helpers.

```
Atlas-lite/
├── app/                          # Core application modules
│   ├── __init__.py
│   ├── market_data.py           # Market data fetching
│   ├── news_data.py             # News headline fetching
│   └── report_generator.py      # Report generation
├── reports/                      # Generated reports
├── tests/                        # Test files
├── main.py                       # Entry point
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

## Notes

- No trading functionality
- No brokerage connections
- Data is fetched from Yahoo Finance via yfinance
- Uses Yahoo Finance fallback data when yfinance history is unavailable
- Uses the official SEC Company Facts API for automated Growth and Quality measurements
- Caches SEC Company Facts locally in `data_cache/sec/`
- Caches Nasdaq earnings calendar data locally in `data_cache/earnings/`
- Caches analyst-action headline data locally in `data_cache/analyst_actions/`
- Caches SEC insider-transaction data locally in `data_cache/insider_transactions/`
- Skips yfinance for the rest of a run after repeated yfinance failures, then uses the Yahoo fallback directly
- Fetch diagnostics are written to `logs/atlas_diagnostics.log`
- Reports are generated in markdown and HTML formats for easy sharing and viewing
- Email delivery requires SMTP environment variables and should use an app password or provider-specific secure credential

## License

MIT
