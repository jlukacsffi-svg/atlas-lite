#!/usr/bin/env python3
"""Manage the local Atlas paper-trading account."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.paper_trading import PaperTradingAccount
from app.research_memory import ResearchMemory
from app.research_tasks import ResearchTaskQueue


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
    order_parser.add_argument("--proposal-id", required=True)

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

    propose_parser = subparsers.add_parser(
        "propose",
        help="Create a reviewable paper-trade proposal without executing it.",
    )
    propose_parser.add_argument("side", choices=["buy", "sell"])
    propose_parser.add_argument("ticker")
    propose_parser.add_argument("shares", type=float)
    propose_parser.add_argument("--price", type=float, required=True)
    propose_parser.add_argument("--thesis", required=True)
    propose_parser.add_argument("--recommendation-id", default=None)
    propose_parser.add_argument("--research-task-id", default=None)
    propose_parser.add_argument("--source", default="manual")

    decide_parser = subparsers.add_parser(
        "decide-proposal",
        help="Approve or reject a paper proposal.",
    )
    decide_parser.add_argument("proposal_id")
    decide_parser.add_argument("decision", choices=["approve", "reject"])
    decide_parser.add_argument("--notes", default=None)

    research_parser = subparsers.add_parser(
        "propose-research",
        help="Create a paper proposal from an owner-approved research finding.",
    )
    research_parser.add_argument("task_id")
    research_parser.add_argument("side", choices=["buy", "sell"])
    research_parser.add_argument("shares", type=float)
    research_parser.add_argument("--price", type=float, required=True)
    research_parser.add_argument("--thesis", default=None)

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
    proposals_parser = subparsers.add_parser("proposals", help="Show paper proposals.")
    proposals_parser.add_argument(
        "--status",
        choices=["pending", "approved", "rejected", "executed"],
    )
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
            proposal_id=args.proposal_id,
        )
        print(
            f"[ok] Simulated {event['side']} {event['shares']:g} {event['ticker']} "
            f"at ${event['price']:,.2f}."
        )
        print(f"[paper] Trade ID: {event['trade_id']}")
        print("[safety] No real order was transmitted.")
        return 0

    if args.command == "propose":
        event = account.create_proposal(
            side=args.side,
            ticker=args.ticker,
            shares=args.shares,
            reference_price=args.price,
            thesis=args.thesis,
            recommendation_id=args.recommendation_id,
            research_task_id=args.research_task_id,
            source=args.source,
        )
        print(
            f"[ok] Created paper proposal {event['proposal_id']}: "
            f"{event['side']} {event['shares']:g} {event['ticker']}."
        )
        print("[safety] The proposal is pending and no simulated order was executed.")
        return 0

    if args.command == "decide-proposal":
        event = account.decide_proposal(
            args.proposal_id,
            args.decision,
            notes=args.notes,
        )
        print(
            f"[ok] Paper proposal {event['proposal_id']} "
            f"{event['decision']}d."
        )
        print("[safety] Approval permits simulation only; no real order is possible.")
        return 0

    if args.command == "propose-research":
        tasks = ResearchTaskQueue().list_tasks()
        task = next((item for item in tasks if item.get("id") == args.task_id), None)
        if not task:
            raise ValueError(f"research task not found: {args.task_id}")
        owner_decision = task.get("owner_decision", {}).get("decision")
        if owner_decision != "approve" or task.get("status") != "closed":
            raise ValueError("research task must be closed with owner approval")
        ticker = str(task.get("subject", "")).strip().upper()
        if not ticker or " " in ticker:
            raise ValueError("research task subject must be a ticker")
        thesis = args.thesis or task.get("result", {}).get("conclusion")
        if not thesis:
            raise ValueError("approved research task has no conclusion")

        event = account.create_proposal(
            side=args.side,
            ticker=ticker,
            shares=args.shares,
            reference_price=args.price,
            thesis=thesis,
            research_task_id=args.task_id,
            source="owner_approved_research",
        )
        print(
            f"[ok] Created paper proposal {event['proposal_id']} "
            f"from approved research task {args.task_id}."
        )
        print("[safety] The proposal remains pending; no simulated order was executed.")
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

    if args.command == "recommendations":
        events = account.recommendations()
    elif args.command == "proposals":
        events = account.proposals(status=args.status)
    else:
        events = account.ledger()
    for event in events:
        print(event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
