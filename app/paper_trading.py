"""Strictly simulated paper-trading account for Atlas Stage 5."""

from datetime import datetime
import json
from pathlib import Path
import uuid

from app.paths import data_path

DEFAULT_PAPER_DIR = data_path("paper_trading")
DEFAULT_ACCOUNT_FILE = DEFAULT_PAPER_DIR / "account.json"
DEFAULT_LEDGER_FILE = DEFAULT_PAPER_DIR / "ledger.jsonl"

DEFAULT_POLICY = {
    "minimum_cash_reserve_pct": 10.0,
    "maximum_position_pct": 20.0,
    "maximum_daily_trades": 5,
    "require_risk_review": True,
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
        rationale=None,
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
            "rationale": self._normalize_rationale(rationale),
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
        rationale=None,
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
            "rationale": self._normalize_rationale(rationale),
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
        if decision == "approve":
            policy = self.load().get("policy", self.policy)
            if policy.get("require_risk_review", True):
                review = self.latest_proposal_risk_review(proposal_id)
                if not review:
                    raise ValueError("paper proposal requires a risk review before approval")
                if review.get("verdict") == "hold":
                    raise ValueError("paper proposal has a hold risk verdict")

        event = {
            "event": "paper_proposal_decision",
            "proposal_id": proposal_id,
            "timestamp": self.clock().isoformat(timespec="seconds"),
            "decision": decision,
            "notes": str(notes or "").strip(),
        }
        self._append_event(event)
        return event

    def record_proposal_risk_review(self, proposal_id, verdict, flags, source="paper_risk_v1"):
        """Append a CRO-style risk review for a pending paper proposal."""
        if not self._find_proposal(proposal_id):
            raise ValueError(f"paper proposal not found: {proposal_id}")
        if self.proposal_status(proposal_id) != "pending":
            raise ValueError("risk review requires a pending paper proposal")
        verdict = str(verdict).strip().lower()
        if verdict not in {"clear", "caution", "hold"}:
            raise ValueError("risk verdict must be clear, caution, or hold")
        event = {
            "event": "paper_proposal_risk_review",
            "proposal_id": proposal_id,
            "timestamp": self.clock().isoformat(timespec="seconds"),
            "verdict": verdict,
            "flags": [str(flag).strip() for flag in flags if str(flag).strip()],
            "source": source,
        }
        self._append_event(event)
        return event

    def latest_proposal_risk_review(self, proposal_id):
        reviews = [
            event
            for event in self.ledger()
            if event.get("event") == "paper_proposal_risk_review"
            and event.get("proposal_id") == proposal_id
        ]
        return reviews[-1] if reviews else None

    def record_position_review(
        self,
        ticker,
        verdict,
        current_price,
        return_pct,
        atlas_score,
        flags,
        thesis,
        source="paper_monitor_v1",
    ):
        """Append a daily thesis review for an open simulated position."""
        ticker = str(ticker).strip().upper()
        verdict = str(verdict).strip().lower()
        if verdict not in {"maintain", "review", "exit"}:
            raise ValueError("position verdict must be maintain, review, or exit")
        account = self.load()
        if ticker not in account.get("positions", {}):
            raise ValueError(f"paper position not found: {ticker}")
        event = {
            "event": "paper_position_review",
            "review_id": f"position_review_{uuid.uuid4().hex[:12]}",
            "timestamp": self.clock().isoformat(timespec="seconds"),
            "ticker": ticker,
            "verdict": verdict,
            "current_price": float(current_price),
            "return_pct": round(float(return_pct), 4),
            "atlas_score": round(float(atlas_score), 1) if atlas_score is not None else None,
            "flags": [str(flag).strip() for flag in flags if str(flag).strip()],
            "thesis": str(thesis).strip(),
            "source": source,
        }
        self._append_event(event)
        return event

    def position_reviews(self, ticker=None):
        reviews = [
            event
            for event in self.ledger()
            if event.get("event") == "paper_position_review"
        ]
        if ticker:
            ticker = str(ticker).strip().upper()
            reviews = [review for review in reviews if review.get("ticker") == ticker]
        return reviews

    def latest_position_reviews(self):
        latest = {}
        for review in self.position_reviews():
            latest[review["ticker"]] = review
        return latest

    def proposals(self, status=None):
        proposals = [
            dict(
                event,
                status=self.proposal_status(event["proposal_id"]),
                risk_review=self.latest_proposal_risk_review(event["proposal_id"]),
            )
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
        position_shares_before = float(position.get("shares") or 0.0)
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
        position_shares_after = float(
            account.get("positions", {}).get(ticker, {}).get("shares") or 0.0
        )

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
            "position_shares_before": round(position_shares_before, 4),
            "position_shares_after": round(position_shares_after, 4),
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
            "position_reviews": self.latest_position_reviews(),
            "excess_return_pct": {
                ticker: round(
                    latest["total_return_pct"] - benchmark_return,
                    4,
                )
                for ticker, benchmark_return in latest["benchmark_returns_pct"].items()
            },
        }

    def proposal_feedback(self):
        """Evaluate executed simulated buy proposals against later returns."""
        snapshots = self.performance_history()
        if not snapshots:
            return []

        latest = snapshots[-1]
        latest_positions = {
            position.get("ticker"): position
            for position in latest.get("positions", [])
        }
        trades = [
            event
            for event in self.ledger()
            if event.get("event") == "paper_trade"
            and event.get("side") == "buy"
            and event.get("proposal_id")
        ]
        proposals = {
            proposal["proposal_id"]: proposal
            for proposal in self.proposals()
        }
        rows = []
        for trade in trades:
            ticker = trade["ticker"]
            proposal = proposals.get(trade["proposal_id"], {})
            start = self._first_snapshot_after(snapshots, trade["timestamp"])
            latest_position = latest_positions.get(ticker)
            if not start or not latest_position:
                rows.append(
                    self._feedback_row(
                        trade,
                        proposal,
                        "not_enough_time",
                        "No comparable performance snapshot is available yet.",
                    )
                )
                continue

            security_return = self._pct_return(
                trade.get("price"),
                latest_position.get("price"),
            )
            benchmark_returns = {}
            for benchmark in ("SPY", "QQQ"):
                benchmark_returns[benchmark] = self._pct_return(
                    start.get("benchmark_prices", {}).get(benchmark),
                    latest.get("benchmark_prices", {}).get(benchmark),
                )
            usable_benchmarks = {
                ticker: value
                for ticker, value in benchmark_returns.items()
                if value is not None
            }
            if (
                security_return is None
                or start.get("timestamp") == latest.get("timestamp")
                or not usable_benchmarks
            ):
                verdict = "not_enough_time"
                summary = "Needs more daily snapshots before Atlas can judge this idea."
            else:
                best_benchmark = max(usable_benchmarks.values())
                worst_benchmark = min(usable_benchmarks.values())
                if security_return >= best_benchmark:
                    verdict = "working"
                    summary = "The simulated idea is ahead of both core benchmarks."
                elif security_return < worst_benchmark:
                    verdict = "lagging"
                    summary = "The simulated idea is behind both core benchmarks."
                else:
                    verdict = "mixed"
                    summary = "The simulated idea is between the two core benchmarks."
            rows.append(
                self._feedback_row(
                    trade,
                    proposal,
                    verdict,
                    summary,
                    security_return=security_return,
                    benchmark_returns=benchmark_returns,
                    snapshots=self._snapshots_since(snapshots, trade["timestamp"]),
                    latest_price=latest_position.get("price"),
                )
            )
        return sorted(rows, key=lambda item: item["filled_at"], reverse=True)

    def trade_activity(self, limit=8):
        """Return recent simulated buy and sell activity with execution context."""
        proposals = {
            proposal["proposal_id"]: proposal
            for proposal in self.proposals()
        }
        recommendations = {
            recommendation["recommendation_id"]: recommendation
            for recommendation in self.recommendations()
        }
        trades = [
            event
            for event in self.ledger()
            if event.get("event") == "paper_trade"
        ]
        rows = []
        for trade in list(reversed(trades))[:limit]:
            proposal = proposals.get(trade.get("proposal_id"), {})
            recommendation = recommendations.get(trade.get("recommendation_id"), {})
            rationale = proposal.get("rationale") or recommendation.get("rationale") or []
            title, summary = self._trade_activity_text(trade, proposal)
            rows.append(
                {
                    "trade_id": trade.get("trade_id"),
                    "timestamp": trade.get("timestamp"),
                    "ticker": trade.get("ticker"),
                    "side": trade.get("side"),
                    "action_label": self._trade_action_label(trade, proposal),
                    "shares": trade.get("shares"),
                    "fill_price": trade.get("price"),
                    "realized_gain_loss": trade.get("realized_gain_loss"),
                    "title": title,
                    "summary": summary,
                    "thesis": proposal.get("thesis") or trade.get("thesis"),
                    "rationale": rationale,
                }
            )
        return rows

    @staticmethod
    def _pct_return(start, end):
        if start in (None, 0) or end is None:
            return None
        return round((float(end) / float(start) - 1) * 100, 4)

    @staticmethod
    def _first_snapshot_after(snapshots, timestamp):
        for snapshot in snapshots:
            if str(snapshot.get("timestamp", "")) >= str(timestamp):
                return snapshot
        return None

    @staticmethod
    def _snapshots_since(snapshots, timestamp):
        return sum(
            1
            for snapshot in snapshots
            if str(snapshot.get("timestamp", "")) >= str(timestamp)
        )

    @staticmethod
    def _feedback_row(
        trade,
        proposal,
        verdict,
        summary,
        security_return=None,
        benchmark_returns=None,
        snapshots=0,
        latest_price=None,
    ):
        return {
            "proposal_id": trade.get("proposal_id"),
            "ticker": trade.get("ticker"),
            "side": trade.get("side"),
            "shares": trade.get("shares"),
            "filled_at": trade.get("timestamp"),
            "fill_price": trade.get("price"),
            "latest_price": latest_price,
            "security_return_pct": security_return,
            "benchmark_returns_pct": benchmark_returns or {},
            "snapshots": snapshots,
            "verdict": verdict,
            "summary": summary,
            "thesis": proposal.get("thesis") or trade.get("thesis"),
        }

    @staticmethod
    def _trade_action_label(trade, proposal):
        side = str(trade.get("side") or "").lower()
        if side == "buy":
            return "purchase"
        action = str(proposal.get("action_label") or "").strip().lower()
        if action in {"trim", "exit"}:
            return action
        before = float(trade.get("position_shares_before") or 0.0)
        after = float(trade.get("position_shares_after") or 0.0)
        if before and after > 0:
            return "trim"
        if before:
            return "exit"
        return "sell"

    @classmethod
    def _trade_activity_text(cls, trade, proposal):
        ticker = trade.get("ticker") or "Holding"
        shares = float(trade.get("shares") or 0.0)
        action = cls._trade_action_label(trade, proposal)
        thesis = proposal.get("thesis") or trade.get("thesis") or "No thesis supplied."
        if action == "purchase":
            return (
                f"Atlas purchased {ticker}",
                (
                    f"Atlas added {shares:g} shares to the simulated portfolio because "
                    f"{thesis}"
                ),
            )
        if action == "trim":
            return (
                f"Atlas trimmed {ticker}",
                (
                    f"Atlas reduced the simulated holding by {shares:g} shares because "
                    f"{thesis}"
                ),
            )
        if action == "exit":
            return (
                f"Atlas sold {ticker}",
                (
                    f"Atlas closed the simulated position because {thesis}"
                ),
            )
        return (
            f"Atlas sold {ticker}",
            f"Atlas recorded a simulated sale because {thesis}",
        )

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

        reviews = summary.get("position_reviews", {})
        lines.extend(["## Thesis Reviews", ""])
        if not reviews:
            lines.extend(["No daily position thesis reviews are available.", ""])
        else:
            lines.extend(
                [
                    "| Ticker | Verdict | Return | Atlas Score | Flags | Thesis |",
                    "|--------|---------|--------|-------------|-------|--------|",
                ]
            )
            for ticker, review in sorted(reviews.items()):
                flags = "; ".join(review.get("flags", [])) or "None"
                score = review.get("atlas_score")
                score_text = f"{score:.1f}" if score is not None else "N/A"
                lines.append(
                    f"| {ticker} | {review['verdict'].title()} | "
                    f"{review['return_pct']:+.2f}% | {score_text} | "
                    f"{flags.replace('|', '/')} | "
                    f"{review.get('thesis', 'N/A').replace('|', '/')} |"
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

    @staticmethod
    def _normalize_rationale(rationale):
        if rationale is None:
            return []
        if isinstance(rationale, str):
            rationale = [rationale]
        return [
            str(item).strip()
            for item in rationale
            if str(item).strip()
        ][:6]

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
