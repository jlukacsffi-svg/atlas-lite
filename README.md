# Atlas Lite

A lightweight market monitoring tool that generates daily executive briefs for a curated watchlist of stocks.

## Features

- Loads a structured security universe with sector, category, notes, and company-profile metadata
- Calculates transparent Atlas Scoring Engine v1 rankings with automated Growth and Momentum
- Saves structured historical research snapshots for comparison over time
- Monitors a watchlist of major tech, defense, and market index stocks
- Fetches real-time market data using yfinance
- Adds recent news headlines for major watchlist movers
- Generates a rule-based executive summary of market tone, leaders, risks, and volatility
- Generates Morning Executive Brief reports in markdown and HTML formats
- Supports Windows scheduled daily execution
- Supports optional SMTP email delivery using environment variables
- Saves reports to the `reports/` folder with timestamps

## Watchlist

The active watchlist is loaded from:

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

Atlas currently uses a hybrid v2 scoring model:

- Growth is calculated automatically from annual revenue and net-income growth reported in SEC filings.
- Momentum is calculated automatically from recent market returns when Yahoo Finance history is available.
- Quality, Moat, and Risk remain manual seed inputs stored in `data/security_universe.json`.
- If automated Growth or Momentum data is unavailable, Atlas retains the corresponding manual seed score for that run.

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

- **Tech Giants**: NVDA, AMD, MSFT, AMZN, GOOGL, META
- **Semiconductors**: AVGO, TSM, ARM
- **Defense/Aerospace**: LMT, NOC, RTX
- **Cybersecurity**: CRWD, PANW
- **Finance/Data**: PLTR
- **Market Indices**: SPY, QQQ

## Report Contents

Each Morning Executive Brief includes:

1. **Date** - Report generation date
2. **Executive Summary** - Concise readout of market tone, leaders, risks, and volatility
3. **Market Summary** - Overview of major indices
4. **Watchlist Summary** - Current prices and performance
5. **Atlas Scoring Summary** - Weighted company rankings
6. **Company Profile Highlights** - Thesis, key driver, and key risk for top-ranked companies
7. **Automated Growth** - SEC filing growth scores and underlying annual comparisons
8. **Automated Momentum** - Momentum scores and recent return measurements
9. **Research Memory** - Changes since the most recent structured snapshot
10. **Top Movers** - Best and worst performing stocks
11. **News Highlights** - Recent headlines for stocks moving more than 2%
12. **Potential Opportunities** - Notable price changes
13. **Risks To Watch** - Key considerations

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

Reports are saved to the `reports/` folder with a timestamp in the filename.

Each run writes both:

- `morning_brief_YYYYMMDD_HHMMSS.md`
- `morning_brief_YYYYMMDD_HHMMSS.html`

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

Scheduled run logs are written to:

```text
logs/scheduled_run_YYYYMMDD_HHMMSS.log
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

## SEC Growth Data

Atlas identifies itself when requesting the official SEC Company Facts API. The default contact is the dedicated Atlas report email. To use a different SEC-compliant contact string:

```powershell
$env:ATLAS_SEC_USER_AGENT = "Atlas Capital Research contact@example.com"
```

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
- Uses the official SEC Company Facts API for automated Growth measurements
- Skips yfinance for the rest of a run after repeated yfinance failures, then uses the Yahoo fallback directly
- Fetch diagnostics are written to `logs/atlas_diagnostics.log`
- Reports are generated in markdown and HTML formats for easy sharing and viewing
- Email delivery requires SMTP environment variables and should use an app password or provider-specific secure credential

## License

MIT
