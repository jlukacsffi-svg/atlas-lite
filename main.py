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
from app.email_delivery import EmailDelivery
from app.analyst_actions import AnalystActionTracker
from app.earnings_calendar import EarningsCalendar
from app.insider_transactions import InsiderTransactionTracker
from app.research_memory import ResearchMemory
from app.security_universe import SecurityUniverse

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

    try:
        universe = SecurityUniverse()
        watchlist = universe.tickers()
        print(f"[universe] Loaded {len(watchlist)} active securities from universe v{universe.version}.")

        fetcher = MarketDataFetcher(watchlist, universe=universe)
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
        print("[earnings] Checking upcoming earnings...")
        try:
            earnings_calendar = EarningsCalendar()
            earnings_events = earnings_calendar.fetch_upcoming(watchlist)
            print(f"[ok] Found {len(earnings_events)} upcoming Atlas earnings events.")
        except Exception as earnings_error:
            earnings_events = []
            print(f"[warning] Earnings calendar unavailable: {earnings_error}")

        print()
        print("[analysts] Checking analyst actions...")
        try:
            analyst_tracker = AnalystActionTracker()
            analyst_actions = analyst_tracker.fetch_actions(market_data)
            print(f"[ok] Found {len(analyst_actions)} recent analyst-action headlines.")
        except Exception as analyst_error:
            analyst_actions = []
            print(f"[warning] Analyst-action tracking unavailable: {analyst_error}")

        print()
        print("[insiders] Checking insider transactions...")
        try:
            insider_tracker = InsiderTransactionTracker()
            insider_transactions = insider_tracker.fetch_transactions(market_data)
            print(f"[ok] Found {len(insider_transactions)} recent insider transactions.")
        except Exception as insider_error:
            insider_transactions = []
            print(f"[warning] Insider-transaction tracking unavailable: {insider_error}")

        print()
        print("[memory] Updating research archive...")
        memory = ResearchMemory()
        previous_snapshot = memory.load_latest_snapshot()
        snapshot_path = memory.save_snapshot(market_data, market_summary, universe.version)
        print(f"[ok] Research snapshot saved to: {snapshot_path}")

        print()
        print("[report] Generating report...")

        generator = ReportGenerator(
            market_data,
            market_summary,
            previous_snapshot=previous_snapshot,
            earnings_events=earnings_events,
            analyst_actions=analyst_actions,
            insider_transactions=insider_transactions,
        )
        report_path = generator.save_report()

        print(f"[ok] Report saved to: {report_path}")
        if generator.last_html_path:
            print(f"[ok] HTML report saved to: {generator.last_html_path}")

        index_path = memory.update_archive_index(
            snapshot_path=snapshot_path,
            report_path=report_path,
            html_report_path=generator.last_html_path,
        )
        if index_path:
            print(f"[ok] Research archive index updated: {index_path}")

        print()
        print("[email] Checking email delivery settings...")
        email_delivery = EmailDelivery()
        if email_delivery.config.enabled:
            try:
                email_delivery.send_report(report_path, generator.last_html_path)
                print("[ok] Report email sent.")
            except Exception as email_error:
                print(f"[warning] Email delivery failed: {email_error}")
        else:
            print("[email] Email delivery disabled.")

        print("[ok] Report generation complete.")
        return 0

    except Exception as e:
        print(f"[error] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
