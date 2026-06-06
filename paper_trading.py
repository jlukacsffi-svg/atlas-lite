#!/usr/bin/env python3
"""Manage the local Atlas paper-trading account."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.paper_trading import PaperTradingAccount
from app.research_memory import ResearchMemory


def build_parser():
    parser = argparse.ArgumentParser(
        description="Manage Atlas simulated paper trading. No real orders are possible."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a simulated account.")
    init_parser.add_argument("--cash", type=float, required=True)
    init_parser.add_argument("--name", default="Atlas Paper Portfolio")

    order_parser = subparsers.add_parser("order", help="Execute a simulated paper order.")
    order_parser.add_argument("side", choices=["buy", "sell"])
    order_parser.add_argument("ticker")
    order_parser.add_argument("shares", type=float)
    order_parser.add_argument("--price", type=float, required=True)
    order_parser.add_argument("--thesis", required=True)
    order_parser.add_argument("--source", default="manual")
    order_parser.add_argument("--recommendation-id", default=None)

    recommend_parser = subparsers.add_parser(
        "recommend",
        help="Record a simulated recommendation without changing holdings.",
    )
    recommend_parser.add_argument("side", choices=["buy", "sell"])
    recommend_parser.add_argument("ticker")
    recommend_parser.add_argument("shares", type=float)
    recommend_parser.add_argument("--price", type=float, required=True)
    recommend_parser.add_argument("--thesis", required=True)
    recommend_parser.add_argument("--confidence", choices=["low", "medium", "high"], default="medium")
    recommend_parser.add_argument("--source", default="manual")

    preview_parser = subparsers.add_parser("preview", help="Validate without executing.")
    preview_parser.add_argument("side", choices=["buy", "sell"])
    preview_parser.add_argument("ticker")
    preview_parser.add_argument("shares", type=float)
    preview_parser.add_argument("--price", type=float, required=True)
    preview_parser.add_argument("--thesis", required=True)

    subparsers.add_parser("status", help="Show simulated account state.")
    subparsers.add_parser(
        "snapshot",
        help="Record performance using prices from the latest Atlas research snapshot.",
    )
    subparsers.add_parser("performance", help="Show latest paper performance.")
    report_parser = subparsers.add_parser(
        "report",
        help="Write a Markdown paper-performance report.",
    )
    report_parser.add_argument("--output", default=None)
    subparsers.add_parser("recommendations", help="Show paper recommendations.")
    subparsers.add_parser("ledger", help="Show the append-only paper ledger.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    account = PaperTradingAccount()

    if args.command == "init":
        state = account.initialize(starting_cash=args.cash, name=args.name)
        print(f"[ok] Initialized '{state['name']}' with ${state['cash']:,.2f} simulated cash.")
        print("[safety] This account cannot connect to a brokerage or place a real order.")
        return 0

    if args.command in {"order", "preview"}:
        values = {
            "side": args.side,
            "ticker": args.ticker,
            "shares": args.shares,
            "price": args.price,
            "thesis": args.thesis,
        }
        if args.command == "preview":
            result = account.preview_order(**values)
            print(f"[paper] Valid: {result['valid']}")
            for error in result["errors"]:
                print(f"[error] {error}")
            return 0 if result["valid"] else 1

        event = account.execute_order(
            **values,
            source=args.source,
            recommendation_id=args.recommendation_id,
        )
        print(
            f"[ok] Simulated {event['side']} {event['shares']:g} {event['ticker']} "
            f"at ${event['price']:,.2f}."
        )
        print(f"[paper] Trade ID: {event['trade_id']}")
        print("[safety] No real order was transmitted.")
        return 0

    if args.command == "recommend":
        event = account.record_recommendation(
            side=args.side,
            ticker=args.ticker,
            shares=args.shares,
            reference_price=args.price,
            thesis=args.thesis,
            confidence=args.confidence,
            source=args.source,
        )
        print(
            f"[ok] Recorded paper recommendation {event['recommendation_id']}: "
            f"{event['side']} {event['shares']:g} {event['ticker']}."
        )
        print("[safety] No simulated or real order was executed.")
        return 0

    if args.command == "status":
        status = account.status()
        print(f"Account: {status['name']}")
        print(f"Cash: ${status['cash']:,.2f}")
        print(f"Positions: {len(status['positions'])}")
        print(f"Realized gain/loss: ${status['realized_gain_loss']:,.2f}")
        for position in status["positions"]:
            print(
                f"  {position['ticker']}: {position['shares']:g} shares "
                f"at ${position['average_cost']:,.2f} average cost"
            )
        return 0

    if args.command == "snapshot":
        latest = ResearchMemory().load_latest_snapshot()
        if not latest:
            raise ValueError("no Atlas research snapshot is available")
        securities = latest.get("securities", {})
        prices = {
            ticker: data.get("price")
            for ticker, data in securities.items()
            if data.get("status") == "available"
        }
        event = account.record_performance_snapshot(
            prices=prices,
            benchmark_prices={
                "SPY": prices.get("SPY"),
                "QQQ": prices.get("QQQ"),
            },
        )
        print(f"[ok] Paper performance snapshot recorded at equity ${event['equity']:,.2f}.")
        print(f"[paper] Total return: {event['total_return_pct']:+.2f}%")
        return 0

    if args.command == "performance":
        summary = account.performance_summary()
        if not summary["available"]:
            print("[paper] No performance snapshots are available.")
            return 0
        latest = summary["latest"]
        print(f"Snapshots: {summary['snapshots']}")
        print(f"Equity: ${latest['equity']:,.2f}")
        print(f"Total return: {latest['total_return_pct']:+.2f}%")
        for ticker, value in latest["benchmark_returns_pct"].items():
            print(
                f"{ticker}: {value:+.2f}% "
                f"(Atlas excess {summary['excess_return_pct'][ticker]:+.2f}%)"
            )
        return 0

    if args.command == "report":
        output_path = account.save_performance_report(output_path=args.output)
        print(f"[ok] Paper performance report saved to: {output_path}")
        return 0

    events = account.recommendations() if args.command == "recommendations" else account.ledger()
    for event in events:
        print(event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
