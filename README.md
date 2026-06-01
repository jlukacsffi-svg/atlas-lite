# Atlas Lite

A lightweight market monitoring tool that generates daily executive briefs for a curated watchlist of stocks.

## Features

- Monitors a watchlist of major tech, defense, and market index stocks
- Fetches real-time market data using yfinance
- Generates a Morning Executive Brief in markdown format
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
2. **Market Summary** - Overview of major indices
3. **Watchlist Summary** - Current prices and performance
4. **Top Movers** - Best and worst performing stocks
5. **Potential Opportunities** - Notable price changes
6. **Risks To Watch** - Key considerations

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

## Project Structure

```
Atlas-lite/
├── app/                          # Core application modules
│   ├── __init__.py
│   ├── market_data.py           # Market data fetching
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
- Reports are generated in markdown format for easy sharing and viewing

## License

MIT
