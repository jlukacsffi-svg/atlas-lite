#!/usr/bin/env python3
"""
Atlas Lite - Morning Executive Brief Generator

A lightweight market monitoring tool that generates daily executive briefs
for a curated watchlist of stocks.
"""

import os
import sys
import urllib.request
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from app.market_data import MarketDataFetcher
from app.report_generator import ReportGenerator

LOG_DIR = Path(__file__).resolve().parent / "logs"


def verify_internet_connectivity(timeout=5):
    urls = [
        "https://www.google.com/",
        "https://query1.finance.yahoo.com/",
    ]

    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status == 200:
                    print(f"[ok] Connectivity check passed for {url}")
                    return True
        except Exception as exc:
            print(f"[warning] Connectivity check failed for {url}: {exc}")

    return False


# Define the watchlist
WATCHLIST = [
    # Tech Giants
    'NVDA', 'AMD', 'MSFT', 'AMZN', 'GOOGL', 'META',
    # Semiconductors
    'AVGO', 'TSM', 'ARM',
    # Defense/Aerospace
    'LMT', 'NOC', 'RTX',
    # Cybersecurity
    'CRWD', 'PANW',
    # Finance/Data
    'PLTR',
    # Market Indices
    'SPY', 'QQQ',
]


def main():
    """Main entry point for the application"""
    print("=" * 60)
    print("Atlas Lite - Morning Executive Brief Generator")
    print("=" * 60)
    print()

    print("[market] Fetching market data...")
    os.makedirs(LOG_DIR, exist_ok=True)
    if not verify_internet_connectivity():
        print("[warning] Internet unavailable. Yahoo fallback may be used where needed.")

    fetcher = MarketDataFetcher(WATCHLIST)

    try:
        market_data = fetcher.fetch_current_data()
        market_summary = fetcher.get_market_summary()

        available_count = sum(
            1 for data in market_data.values() if data.get('status') == 'available'
        )
        unavailable_count = len(market_data) - available_count
        print(f"[ok] Market data fetch complete. {available_count} available, {unavailable_count} unavailable.")

        if available_count == 0:
            print("[warning] Market data unavailable for this run. Generating fallback report.")

        print()
        print("[report] Generating report...")

        generator = ReportGenerator(market_data, market_summary)
        report_path = generator.save_report()

        print(f"[ok] Report saved to: {report_path}")
        if generator.last_html_path:
            print(f"[ok] HTML report saved to: {generator.last_html_path}")
        print("[ok] Report generation complete.")
        return 0

    except Exception as e:
        print(f"[error] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
