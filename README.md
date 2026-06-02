# Atlas Lite

A lightweight market monitoring tool that generates daily executive briefs for a curated watchlist of stocks.

## Features

- Monitors a watchlist of major tech, defense, and market index stocks
- Fetches real-time market data using yfinance
- Adds recent news headlines for major watchlist movers
- Generates a rule-based executive summary of market tone, leaders, risks, and volatility
- Generates Morning Executive Brief reports in markdown and HTML formats
- Supports Windows scheduled daily execution
- Saves reports to the `reports/` folder with timestamps

## Watchlist

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
5. **Top Movers** - Best and worst performing stocks
6. **News Highlights** - Recent headlines for stocks moving more than 2%
7. **Potential Opportunities** - Notable price changes
8. **Risks To Watch** - Key considerations

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
- Skips yfinance for the rest of a run after repeated yfinance failures, then uses the Yahoo fallback directly
- Fetch diagnostics are written to `logs/atlas_diagnostics.log`
- Reports are generated in markdown and HTML formats for easy sharing and viewing

## License

MIT
