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
from app.news_data import NewsFetcher
from app.report_generator import ReportGenerator
from app.email_delivery import EmailDelivery
from app.analyst_actions import AnalystActionTracker
from app.earnings_calendar import EarningsCalendar
from app.insider_transactions import InsiderTransactionTracker
from app.paper_trading import PaperTradingAccount
from app.paper_strategy import PaperStrategy
from app.paper_risk import PaperRiskReviewer
from app.paper_monitor import PaperPositionMonitor
from app.portfolio import Portfolio
from app.research_memory import ResearchMemory
from app.research_tasks import ResearchTaskQueue
from app.research_analyst import ResearchAnalyst
from app.security_universe import SecurityUniverse
from app.paths import data_path

LOG_DIR = data_path("logs")


def news_focus_tickers(market_data, held_tickers=None, max_ranked=12, move_threshold=2.0):
    held_tickers = {str(ticker).strip().upper() for ticker in (held_tickers or []) if str(ticker).strip()}
    focus = set(held_tickers)

    movers = sorted(
        (
            ticker
            for ticker, data in market_data.items()
            if data.get("status") == "available"
            and data.get("sector") != "Benchmark ETF"
            and abs(float(data.get("percent_change") or 0.0)) >= move_threshold
        ),
        key=lambda ticker: abs(float(market_data[ticker].get("percent_change") or 0.0)),
        reverse=True,
    )
    focus.update(movers[:max_ranked])

    scored = sorted(
        (
            (ticker, data)
            for ticker, data in market_data.items()
            if data.get("status") == "available"
            and data.get("sector") != "Benchmark ETF"
            and data.get("scores")
        ),
        key=lambda item: (
            sum(float(value or 0.0) for value in item[1].get("scores", {}).values()),
            float(item[1].get("percent_change") or 0.0),
        ),
        reverse=True,
    )
    focus.update(ticker for ticker, _data in scored[:max_ranked])
    return sorted(focus)


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
        print("[portfolio] Checking local portfolio configuration...")
        try:
            portfolio = Portfolio()
            portfolio_summary = portfolio.analyze(market_data)
            if portfolio_summary.get("configured"):
                portfolio.add_history_comparison(portfolio_summary)
                portfolio_history_path = portfolio.save_history(portfolio_summary)
                print(f"[ok] Portfolio loaded with {len(portfolio_summary.get('positions', []))} positions.")
                if portfolio_history_path:
                    print(f"[ok] Portfolio snapshot saved to: {portfolio_history_path}")
            else:
                print("[portfolio] No local portfolio file configured.")
        except Exception as portfolio_error:
            portfolio_summary = {"configured": False, "error": str(portfolio_error)}
            print(f"[warning] Portfolio analysis unavailable: {portfolio_error}")

        print()
        print("[tasks] Updating research task queue...")
        try:
            task_queue = ResearchTaskQueue()
            closed_tasks = task_queue.maintain_generated_tasks()
            market_tasks = task_queue.generate_from_market_data(market_data)
            portfolio_tasks = task_queue.generate_from_portfolio_summary(portfolio_summary)
            completed_research = ResearchAnalyst().complete_priority_tasks(
                task_queue,
                market_data,
                earnings_events=earnings_events,
                analyst_actions=analyst_actions,
                insider_transactions=insider_transactions,
                portfolio_summary=portfolio_summary,
            )
            review_paths = task_queue.save_review_outputs()
            print(
                f"[ok] Generated {len(market_tasks)} market tasks and "
                f"{len(portfolio_tasks)} portfolio tasks."
            )
            if completed_research:
                print(
                    f"[ok] Completed {len(completed_research)} priority research "
                    "reviews for owner decision."
                )
            if closed_tasks:
                print(
                    f"[ok] Closed {len(closed_tasks)} stale or duplicate "
                    "generated tasks."
                )
            print(f"[ok] Research agenda refreshed: {review_paths['agenda']}")
        except Exception as task_error:
            print(f"[warning] Research task generation unavailable: {task_error}")

        print()
        print("[paper] Checking simulated paper account...")
        try:
            paper_account = PaperTradingAccount()
            if paper_account.account_file.exists():
                held_tickers = set(paper_account.load().get("positions", {}).keys())
                focused_news = news_focus_tickers(market_data, held_tickers=held_tickers)
                NewsFetcher().enrich_market_data(market_data, focused_news)
                print(
                    f"[ok] Refreshed company-news signals for {len(focused_news)} focus ticker(s)."
                )
                prices = {
                    ticker: data.get("price")
                    for ticker, data in market_data.items()
                    if data.get("status") == "available"
                }
                paper_account.record_performance_snapshot(
                    prices=prices,
                    benchmark_prices={
                        "SPY": prices.get("SPY"),
                        "QQQ": prices.get("QQQ"),
                    },
                )
                paper_proposals = PaperStrategy.from_account_policy(
                    paper_account
                ).generate(paper_account, market_data)
                position_monitor = PaperPositionMonitor.from_account(
                    paper_account,
                    latest_prices=prices,
                ).review(
                    paper_account,
                    market_data,
                )
                paper_reviews = PaperRiskReviewer().review_pending(
                    paper_account,
                    market_data,
                )
                autonomous_cycle = paper_account.run_autonomous_cycle(
                    latest_prices=prices,
                    market_data=market_data,
                )
                # Refresh the performance snapshot after any autonomous actions so
                # the saved report reflects the actual post-trade paper book.
                paper_account.record_performance_snapshot(
                    prices=prices,
                    benchmark_prices={
                        "SPY": prices.get("SPY"),
                        "QQQ": prices.get("QQQ"),
                    },
                )
                paper_summary = paper_account.performance_summary()
                paper_summary["configured"] = True
                paper_summary["prospective_review_tracker"] = (
                    paper_account.prospective_defensive_review_tracker(
                        paper_account.ledger()
                    )
                )
                paper_summary["pending_proposals"] = paper_account.proposals(
                    status="pending"
                )
                performance_report_path = paper_account.save_performance_report()
                print(
                    f"[ok] Paper account marked at "
                    f"${paper_summary['latest']['equity']:,.2f} simulated equity."
                )
                print(
                    f"[ok] Generated {len(paper_proposals)} new pending paper proposals."
                )
                print(
                    f"[ok] Recorded {len(position_monitor['reviews'])} position "
                    f"reviews and {len(position_monitor['exit_proposals'])} exit proposals."
                )
                print(f"[ok] Recorded {len(paper_reviews)} paper proposal risk reviews.")
                if autonomous_cycle["enabled"]:
                    print(
                        f"[ok] Auto-managed paper mode approved "
                        f"{len(autonomous_cycle['approved'])}, rejected "
                        f"{len(autonomous_cycle['rejected'])}, and executed "
                        f"{len(autonomous_cycle['executed'])} simulated proposal(s)."
                    )
                    if autonomous_cycle["skipped"]:
                        print(
                            f"[paper] Auto-managed paper mode skipped "
                            f"{len(autonomous_cycle['skipped'])} proposal(s) that still "
                            "needed data or failed policy checks."
                        )
                print(f"[ok] Paper performance report refreshed: {performance_report_path}")
            else:
                paper_summary = {"configured": False, "available": False}
                print("[paper] No simulated paper account initialized.")
        except Exception as paper_error:
            paper_summary = {
                "configured": True,
                "available": False,
                "error": str(paper_error),
            }
            print(f"[warning] Paper account snapshot unavailable: {paper_error}")

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
            portfolio_summary=portfolio_summary,
            paper_summary=paper_summary,
        )
        report_path = generator.save_report(reports_dir=data_path("reports"))

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
