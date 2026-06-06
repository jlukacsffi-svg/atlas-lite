#!/usr/bin/env python3
"""Manage the local Atlas paper-trading account."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.paper_trading import PaperTradingAccount


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

    preview_parser = subparsers.add_parser("preview", help="Validate without executing.")
    preview_parser.add_argument("side", choices=["buy", "sell"])
    preview_parser.add_argument("ticker")
    preview_parser.add_argument("shares", type=float)
    preview_parser.add_argument("--price", type=float, required=True)
    preview_parser.add_argument("--thesis", required=True)

    subparsers.add_parser("status", help="Show simulated account state.")
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

        event = account.execute_order(**values, source=args.source)
        print(
            f"[ok] Simulated {event['side']} {event['shares']:g} {event['ticker']} "
            f"at ${event['price']:,.2f}."
        )
        print(f"[paper] Trade ID: {event['trade_id']}")
        print("[safety] No real order was transmitted.")
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

    for event in account.ledger():
        print(event)
    return 0


if __name__ == "__main__":
    sys.exit(main())
