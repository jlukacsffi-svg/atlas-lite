"""Strictly simulated paper-trading account for Atlas Stage 5."""

from datetime import datetime
import json
from pathlib import Path
import uuid


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAPER_DIR = PROJECT_ROOT / "paper_trading"
DEFAULT_ACCOUNT_FILE = DEFAULT_PAPER_DIR / "account.json"
DEFAULT_LEDGER_FILE = DEFAULT_PAPER_DIR / "ledger.jsonl"

DEFAULT_POLICY = {
    "minimum_cash_reserve_pct": 10.0,
    "maximum_position_pct": 20.0,
    "maximum_daily_trades": 5,
}


class PaperTradingAccount:
    """Manage a local simulated account with conservative risk rules."""

    def __init__(
        self,
        account_file=DEFAULT_ACCOUNT_FILE,
        ledger_file=DEFAULT_LEDGER_FILE,
        policy=None,
        clock=None,
    ):
        self.account_file = Path(account_file)
        self.ledger_file = Path(ledger_file)
        self.policy = dict(DEFAULT_POLICY)
        if policy:
            self.policy.update(policy)
        self.clock = clock or datetime.now

    def initialize(self, starting_cash, name="Atlas Paper Portfolio"):
        starting_cash = float(starting_cash)
        if starting_cash <= 0:
            raise ValueError("starting cash must be positive")
        if self.account_file.exists():
            raise ValueError("paper account already exists")

        now = self.clock().isoformat(timespec="seconds")
        account = {
            "account_version": "1.0",
            "name": str(name).strip() or "Atlas Paper Portfolio",
            "created_at": now,
            "updated_at": now,
            "starting_cash": starting_cash,
            "cash": starting_cash,
            "realized_gain_loss": 0.0,
            "positions": {},
            "policy": dict(self.policy),
        }
        self._save_account(account)
        self._append_event(
            {
                "event": "account_initialized",
                "timestamp": now,
                "starting_cash": starting_cash,
                "policy": dict(self.policy),
            }
        )
        return account

    def load(self):
        if not self.account_file.exists():
            raise ValueError("paper account is not initialized")
        with open(self.account_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def preview_order(self, side, ticker, shares, price, thesis):
        account = self.load()
        order = self._normalize_order(side, ticker, shares, price, thesis)
        return self._validate_order(account, order, now=self.clock())

    def record_recommendation(
        self,
        side,
        ticker,
        shares,
        reference_price,
        thesis,
        confidence="medium",
        source="manual",
    ):
        """Append a paper recommendation without changing account holdings."""
        self.load()
        order = self._normalize_order(side, ticker, shares, reference_price, thesis)
        confidence = str(confidence).strip().lower()
        if confidence not in {"low", "medium", "high"}:
            raise ValueError("confidence must be low, medium, or high")

        event = {
            "event": "paper_recommendation",
            "recommendation_id": f"recommendation_{uuid.uuid4().hex[:12]}",
            "timestamp": self.clock().isoformat(timespec="seconds"),
            "source": source,
            "confidence": confidence,
            **order,
        }
        self._append_event(event)
        return event

    def create_proposal(
        self,
        side,
        ticker,
        shares,
        reference_price,
        thesis,
        recommendation_id=None,
        research_task_id=None,
        source="manual",
    ):
        """Append a reviewable paper-trade proposal without executing it."""
        self.load()
        order = self._normalize_order(side, ticker, shares, reference_price, thesis)
        if recommendation_id:
            recommendation = self._find_recommendation(recommendation_id)
            if not recommendation:
                raise ValueError(f"paper recommendation not found: {recommendation_id}")
            if recommendation["side"] != order["side"] or recommendation["ticker"] != order["ticker"]:
                raise ValueError("paper proposal does not match linked recommendation")

        event = {
            "event": "paper_proposal",
            "proposal_id": f"proposal_{uuid.uuid4().hex[:12]}",
            "timestamp": self.clock().isoformat(timespec="seconds"),
            "source": source,
            "recommendation_id": recommendation_id,
            "research_task_id": research_task_id,
            **order,
        }
        self._append_event(event)
        return event

    def decide_proposal(self, proposal_id, decision, notes=None):
        """Append an approval or rejection decision for a paper proposal."""
        decision = str(decision).strip().lower()
        if decision not in {"approve", "reject"}:
            raise ValueError("paper proposal decision must be approve or reject")
        proposal = self._find_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"paper proposal not found: {proposal_id}")
        if self.proposal_status(proposal_id) != "pending":
            raise ValueError("paper proposal already has a decision")

        event = {
            "event": "paper_proposal_decision",
            "proposal_id": proposal_id,
            "timestamp": self.clock().isoformat(timespec="seconds"),
            "decision": decision,
            "notes": str(notes or "").strip(),
        }
        self._append_event(event)
        return event

    def proposals(self, status=None):
        proposals = [
            dict(event, status=self.proposal_status(event["proposal_id"]))
            for event in self.ledger()
            if event.get("event") == "paper_proposal"
        ]
        if status:
            return [proposal for proposal in proposals if proposal["status"] == status]
        return proposals

    def proposal_status(self, proposal_id):
        executed = any(
            event.get("event") == "paper_trade"
            and event.get("proposal_id") == proposal_id
            for event in self.ledger()
        )
        if executed:
            return "executed"
        decisions = [
            event
            for event in self.ledger()
            if event.get("event") == "paper_proposal_decision"
            and event.get("proposal_id") == proposal_id
        ]
        if not decisions:
            return "pending"
        return "approved" if decisions[-1]["decision"] == "approve" else "rejected"

    def execute_order(
        self,
        side,
        ticker,
        shares,
        price,
        thesis,
        source="manual",
        recommendation_id=None,
        proposal_id=None,
    ):
        """Apply a simulated fill and append it to the local audit ledger."""
        account = self.load()
        order = self._normalize_order(side, ticker, shares, price, thesis)
        if not proposal_id:
            raise ValueError("an approved paper proposal is required")
        proposal = self._find_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"paper proposal not found: {proposal_id}")
        if self.proposal_status(proposal_id) != "approved":
            raise ValueError("paper proposal is not approved")
        if (
            proposal["side"] != order["side"]
            or proposal["ticker"] != order["ticker"]
            or abs(float(proposal["shares"]) - order["shares"]) > 0.0000001
        ):
            raise ValueError("paper order does not match approved proposal")

        recommendation = None
        recommendation_id = recommendation_id or proposal.get("recommendation_id")
        if recommendation_id:
            recommendation = self._find_recommendation(recommendation_id)
            if not recommendation:
                raise ValueError(f"paper recommendation not found: {recommendation_id}")
            if recommendation["side"] != order["side"] or recommendation["ticker"] != order["ticker"]:
                raise ValueError("paper order does not match linked recommendation")
        now_value = self.clock()
        validation = self._validate_order(account, order, now=now_value)
        if validation["errors"]:
            raise ValueError("; ".join(validation["errors"]))

        now = now_value.isoformat(timespec="seconds")
        ticker = order["ticker"]
        notional = order["notional"]
        position = account["positions"].get(
            ticker,
            {"shares": 0.0, "average_cost": 0.0},
        )
        realized = 0.0

        if order["side"] == "buy":
            prior_cost = position["shares"] * position["average_cost"]
            new_shares = position["shares"] + order["shares"]
            position = {
                "shares": new_shares,
                "average_cost": (prior_cost + notional) / new_shares,
            }
            account["cash"] -= notional
            account["positions"][ticker] = position
        else:
            realized = (order["price"] - position["average_cost"]) * order["shares"]
            remaining_shares = position["shares"] - order["shares"]
            account["cash"] += notional
            account["realized_gain_loss"] += realized
            if remaining_shares <= 0.0000001:
                account["positions"].pop(ticker, None)
            else:
                position["shares"] = remaining_shares
                account["positions"][ticker] = position

        account["updated_at"] = now
        self._save_account(account)
        event = {
            "event": "paper_trade",
            "trade_id": f"paper_{uuid.uuid4().hex[:12]}",
            "timestamp": now,
            "source": source,
            "recommendation_id": recommendation_id,
            "proposal_id": proposal_id,
            **order,
            "realized_gain_loss": round(realized, 2),
            "cash_after": round(account["cash"], 2),
            "policy": dict(account.get("policy", self.policy)),
        }
        self._append_event(event)
        return event

    def recommendations(self):
        return [
            event
            for event in self.ledger()
            if event.get("event") == "paper_recommendation"
        ]

    def record_performance_snapshot(self, prices, benchmark_prices):
        """Append a mark-to-market snapshot with SPY and QQQ comparisons."""
        account = self.load()
        missing = [
            ticker
            for ticker in account.get("positions", {})
            if prices.get(ticker) is None
        ]
        if missing:
            raise ValueError(
                "missing paper position prices: " + ", ".join(sorted(missing))
            )

        required_benchmarks = {"SPY", "QQQ"}
        missing_benchmarks = [
            ticker
            for ticker in required_benchmarks
            if benchmark_prices.get(ticker) is None
        ]
        if missing_benchmarks:
            raise ValueError(
                "missing benchmark prices: " + ", ".join(sorted(missing_benchmarks))
            )

        status = self.status(prices=prices)
        prior_snapshots = self.performance_history()
        first = prior_snapshots[0] if prior_snapshots else None
        benchmark_returns = {}
        for ticker in sorted(required_benchmarks):
            current_price = float(benchmark_prices[ticker])
            initial_price = (
                first.get("benchmark_prices", {}).get(ticker)
                if first
                else current_price
            )
            benchmark_returns[ticker] = (
                (current_price / initial_price - 1) * 100
                if initial_price
                else 0.0
            )

        event = {
            "event": "performance_snapshot",
            "timestamp": self.clock().isoformat(timespec="seconds"),
            "cash": round(status["cash"], 2),
            "market_value": round(status["market_value"], 2),
            "equity": round(status["equity"], 2),
            "total_return_pct": round(
                (status["equity"] / status["starting_cash"] - 1) * 100,
                4,
            ),
            "realized_gain_loss": round(status["realized_gain_loss"], 2),
            "unrealized_gain_loss": round(status["unrealized_gain_loss"], 2),
            "benchmark_prices": {
                ticker: float(benchmark_prices[ticker])
                for ticker in sorted(required_benchmarks)
            },
            "benchmark_returns_pct": {
                ticker: round(value, 4)
                for ticker, value in benchmark_returns.items()
            },
            "positions": [
                {
                    "ticker": item["ticker"],
                    "shares": item["shares"],
                    "price": item["price"],
                    "market_value": round(item["market_value"], 2),
                    "unrealized_gain_loss": round(item["unrealized_gain_loss"], 2),
                }
                for item in status["positions"]
            ],
        }
        self._append_event(event)
        return event

    def performance_history(self):
        return [
            event
            for event in self.ledger()
            if event.get("event") == "performance_snapshot"
        ]

    def performance_summary(self):
        snapshots = self.performance_history()
        if not snapshots:
            return {"available": False}
        latest = snapshots[-1]
        return {
            "available": True,
            "snapshots": len(snapshots),
            "latest": latest,
            "trade_statistics": self.trade_statistics(),
            "excess_return_pct": {
                ticker: round(
                    latest["total_return_pct"] - benchmark_return,
                    4,
                )
                for ticker, benchmark_return in latest["benchmark_returns_pct"].items()
            },
        }

    def trade_statistics(self):
        events = self.ledger()
        trades = [event for event in events if event.get("event") == "paper_trade"]
        recommendations = [
            event for event in events if event.get("event") == "paper_recommendation"
        ]
        exits = [
            event
            for event in trades
            if event.get("side") == "sell"
        ]
        wins = [event for event in exits if event.get("realized_gain_loss", 0) > 0]
        losses = [event for event in exits if event.get("realized_gain_loss", 0) < 0]
        linked = [event for event in trades if event.get("recommendation_id")]
        proposal_linked = [event for event in trades if event.get("proposal_id")]
        proposals = [
            event for event in events if event.get("event") == "paper_proposal"
        ]
        proposal_statuses = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "executed": 0,
        }
        for proposal in proposals:
            proposal_statuses[self.proposal_status(proposal["proposal_id"])] += 1
        return {
            "recommendations": len(recommendations),
            "trades": len(trades),
            "linked_trades": len(linked),
            "proposal_linked_trades": len(proposal_linked),
            "proposals": len(proposals),
            "proposal_statuses": proposal_statuses,
            "realized_exits": len(exits),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate_pct": len(wins) / len(exits) * 100 if exits else None,
        }

    def render_performance_report(self):
        summary = self.performance_summary()
        lines = [
            "# Atlas Paper Trading Performance",
            "",
            "Simulation only. No real capital or brokerage account is involved.",
            "",
        ]
        if not summary["available"]:
            lines.extend(
                [
                    "No performance snapshots are available.",
                    "",
                    "Run `py -3.12 paper_trading.py snapshot` after the account is initialized.",
                    "",
                ]
            )
            return "\n".join(lines)

        latest = summary["latest"]
        stats = summary["trade_statistics"]
        lines.extend(
            [
                "## Account Performance",
                "",
                f"- **Equity**: ${latest['equity']:,.2f}",
                f"- **Total Return**: {latest['total_return_pct']:+.2f}%",
                f"- **Realized Gain/Loss**: ${latest['realized_gain_loss']:,.2f}",
                f"- **Unrealized Gain/Loss**: ${latest['unrealized_gain_loss']:,.2f}",
                f"- **Snapshots**: {summary['snapshots']}",
                "",
                "## Benchmark Comparison",
                "",
                "| Benchmark | Return | Atlas Excess |",
                "|-----------|--------|--------------|",
            ]
        )
        for ticker, value in latest["benchmark_returns_pct"].items():
            lines.append(
                f"| {ticker} | {value:+.2f}% | "
                f"{summary['excess_return_pct'][ticker]:+.2f}% |"
            )

        win_rate = (
            f"{stats['win_rate_pct']:.1f}%"
            if stats["win_rate_pct"] is not None
            else "N/A"
        )
        lines.extend(
            [
                "",
                "## Decision Audit",
                "",
                f"- **Recommendations Logged**: {stats['recommendations']}",
                f"- **Simulated Trades**: {stats['trades']}",
                f"- **Trades Linked To Recommendations**: {stats['linked_trades']}",
                f"- **Paper Proposals**: {stats['proposals']}",
                f"- **Pending / Approved / Rejected / Executed Proposals**: "
                f"{stats['proposal_statuses']['pending']} / "
                f"{stats['proposal_statuses']['approved']} / "
                f"{stats['proposal_statuses']['rejected']} / "
                f"{stats['proposal_statuses']['executed']}",
                f"- **Trades Linked To Approved Proposals**: {stats['proposal_linked_trades']}",
                f"- **Realized Exits**: {stats['realized_exits']}",
                f"- **Wins / Losses**: {stats['wins']} / {stats['losses']}",
                f"- **Win Rate**: {win_rate}",
                "",
                "## Position Attribution",
                "",
            ]
        )
        positions = latest.get("positions", [])
        if not positions:
            lines.extend(["No open simulated positions.", ""])
        else:
            lines.extend(
                [
                    "| Ticker | Shares | Price | Market Value | Unrealized Gain/Loss |",
                    "|--------|--------|-------|--------------|----------------------|",
                ]
            )
            for position in sorted(
                positions,
                key=lambda item: item["market_value"],
                reverse=True,
            ):
                lines.append(
                    f"| {position['ticker']} | {position['shares']:g} | "
                    f"${position['price']:,.2f} | ${position['market_value']:,.2f} | "
                    f"${position['unrealized_gain_loss']:,.2f} |"
                )
            lines.append("")

        lines.extend(
            [
                "## Safety Boundary",
                "",
                "This report evaluates a simulation. It does not authorize or execute real trades.",
                "",
            ]
        )
        return "\n".join(lines)

    def save_performance_report(self, output_path=None):
        output_path = (
            Path(output_path)
            if output_path
            else self.account_file.parent / "performance.md"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render_performance_report(), encoding="utf-8")
        return output_path

    def status(self, prices=None):
        account = self.load()
        prices = prices or {}
        positions = []
        market_value = 0.0
        unrealized = 0.0

        for ticker, position in sorted(account["positions"].items()):
            price = prices.get(ticker)
            value = position["shares"] * price if price is not None else None
            gain_loss = (
                (price - position["average_cost"]) * position["shares"]
                if price is not None
                else None
            )
            if value is not None:
                market_value += value
                unrealized += gain_loss
            positions.append(
                {
                    "ticker": ticker,
                    **position,
                    "price": price,
                    "market_value": value,
                    "unrealized_gain_loss": gain_loss,
                }
            )

        equity = account["cash"] + market_value
        return {
            "name": account["name"],
            "starting_cash": account["starting_cash"],
            "cash": account["cash"],
            "market_value": market_value,
            "equity": equity,
            "realized_gain_loss": account["realized_gain_loss"],
            "unrealized_gain_loss": unrealized,
            "positions": positions,
            "policy": account.get("policy", dict(self.policy)),
        }

    def ledger(self):
        if not self.ledger_file.exists():
            return []
        events = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def _normalize_order(self, side, ticker, shares, price, thesis):
        side = str(side).strip().lower()
        ticker = str(ticker).strip().upper()
        shares = float(shares)
        price = float(price)
        thesis = str(thesis).strip()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if not ticker:
            raise ValueError("ticker is required")
        if shares <= 0:
            raise ValueError("shares must be positive")
        if price <= 0:
            raise ValueError("price must be positive")
        if not thesis:
            raise ValueError("a paper-trade thesis is required")
        return {
            "side": side,
            "ticker": ticker,
            "shares": shares,
            "price": price,
            "notional": round(shares * price, 2),
            "thesis": thesis,
        }

    def _validate_order(self, account, order, now=None):
        errors = []
        warnings = []
        policy = account.get("policy", self.policy)
        now = now or self.clock()
        trades_today = self._trades_on_date(now.date().isoformat())
        if trades_today >= int(policy["maximum_daily_trades"]):
            errors.append("maximum daily paper-trade count reached")

        positions = account.get("positions", {})
        position = positions.get(order["ticker"], {"shares": 0.0, "average_cost": 0.0})

        if order["side"] == "sell":
            if order["shares"] > position["shares"]:
                errors.append("paper sell exceeds simulated holdings; short selling is disabled")
        else:
            cash_after = account["cash"] - order["notional"]
            if cash_after < 0:
                errors.append("paper buy exceeds available simulated cash; margin is disabled")

            estimated_equity = account["cash"] + sum(
                item["shares"] * item["average_cost"]
                for item in positions.values()
            )
            reserve = estimated_equity * float(policy["minimum_cash_reserve_pct"]) / 100
            if cash_after < reserve:
                errors.append(
                    f"paper buy would breach {policy['minimum_cash_reserve_pct']:.1f}% cash reserve"
                )

            existing_value = position["shares"] * order["price"]
            resulting_value = existing_value + order["notional"]
            resulting_pct = resulting_value / estimated_equity * 100 if estimated_equity else 100
            if resulting_pct > float(policy["maximum_position_pct"]):
                errors.append(
                    f"paper buy would exceed {policy['maximum_position_pct']:.1f}% position limit"
                )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "order": order,
        }

    def _trades_on_date(self, date_text):
        return sum(
            1
            for event in self.ledger()
            if event.get("event") == "paper_trade"
            and str(event.get("timestamp", "")).startswith(date_text)
        )

    def _find_recommendation(self, recommendation_id):
        for event in self.recommendations():
            if event.get("recommendation_id") == recommendation_id:
                return event
        return None

    def _find_proposal(self, proposal_id):
        for event in self.ledger():
            if (
                event.get("event") == "paper_proposal"
                and event.get("proposal_id") == proposal_id
            ):
                return event
        return None

    def _save_account(self, account):
        self.account_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.account_file, "w", encoding="utf-8") as f:
            json.dump(account, f, indent=2, sort_keys=True)

    def _append_event(self, event):
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
