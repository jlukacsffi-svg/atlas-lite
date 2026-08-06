"""Strictly simulated paper-trading account for Atlas Stage 5."""

from datetime import datetime
import json
from pathlib import Path
import re
import uuid

from app.data_quality import daily_movement_summary
from app.decision_driver import infer_decision_driver
from app.paper_monitor import (
    DEFAULT_PROJECTION_ADD_SECTOR_BREADTH_PCT,
    DEFAULT_PROJECTION_ADD_TREND_QUALITY,
    DEFAULT_PROJECTION_REVIEW_EXCESS_PCT,
    DEFAULT_PROJECTION_REVIEW_SECTOR_BREADTH_PCT,
    DEFAULT_PROJECTION_TRIM_EXCESS_PCT,
    DEFAULT_PROJECTION_TRIM_SECTOR_BREADTH_PCT,
)
from app.paths import data_path

DEFAULT_PAPER_DIR = data_path("paper_trading")
DEFAULT_ACCOUNT_FILE = DEFAULT_PAPER_DIR / "account.json"
DEFAULT_LEDGER_FILE = DEFAULT_PAPER_DIR / "ledger.jsonl"
DEFENSIVE_REVIEW_LOSS_THRESHOLD_PCT = -2.0
DEFENSIVE_REVIEW_LAG_THRESHOLD_PCT = -3.0

DEFAULT_POLICY = {
    "minimum_cash_reserve_pct": 10.0,
    "maximum_position_pct": 20.0,
    "maximum_daily_trades": 5,
    "require_risk_review": True,
    "auto_manage_enabled": False,
    "strategy_minimum_buy_score": 88.0,
    "strategy_maximum_exit_score": 60.0,
    "strategy_target_position_pct": 5.0,
    "strategy_maximum_new_proposals": 3,
    "strategy_minimum_daily_move_pct": -8.0,
    "strategy_benchmark_excess_weight": 1.5,
    "strategy_preferred_benchmark": "auto",
    "strategy_trend_quality_weight": 0.2,
    "strategy_sector_repeat_penalty": 3.0,
    "maximum_partial_trims_per_position": 2,
    "projection_learning_enabled": True,
    "projection_learning_min_judged_trades": 3,
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
        self._ledger_cache_signature = None
        self._ledger_cache = []

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

    def update_policy(self, updates, source="manual"):
        account = self.load()
        normalized = {}
        bool_fields = {"auto_manage_enabled", "projection_learning_enabled"}
        float_fields = {
            "minimum_cash_reserve_pct",
            "maximum_position_pct",
            "strategy_minimum_buy_score",
            "strategy_maximum_exit_score",
            "strategy_target_position_pct",
            "strategy_minimum_daily_move_pct",
            "strategy_benchmark_excess_weight",
            "strategy_trend_quality_weight",
            "strategy_sector_repeat_penalty",
        }
        string_fields = {"strategy_preferred_benchmark"}
        int_fields = {
            "maximum_daily_trades",
            "strategy_maximum_new_proposals",
            "maximum_partial_trims_per_position",
            "projection_learning_min_judged_trades",
        }
        for key, value in dict(updates or {}).items():
            if key in bool_fields:
                normalized[key] = bool(value)
            elif key in float_fields:
                normalized[key] = float(value)
            elif key in string_fields:
                preferred = str(value or "auto").strip().upper()
                normalized[key] = preferred if preferred in {"SPY", "QQQ"} else "auto"
            elif key in int_fields:
                normalized[key] = int(value)
        if not normalized:
            return dict(account.get("policy", self.policy))

        account_policy = dict(self.policy)
        account_policy.update(account.get("policy", {}))
        account_policy.update(normalized)
        now = self.clock().isoformat(timespec="seconds")
        account["policy"] = account_policy
        account["updated_at"] = now
        self._save_account(account)
        self._append_event(
            {
                "event": "paper_policy_update",
                "timestamp": now,
                "source": source,
                "changes": dict(normalized),
            }
        )
        return dict(account_policy)

    def effective_policy(self):
        account = self.load()
        policy = dict(self.policy)
        policy.update(account.get("policy", {}))
        return policy

    def auto_manage_enabled(self):
        return bool(self.effective_policy().get("auto_manage_enabled"))

    def run_autonomous_cycle(
        self,
        latest_prices,
        source="paper_auto_manage_v1",
        market_data=None,
    ):
        if not self.auto_manage_enabled():
            return {
                "enabled": False,
                "approved": [],
                "rejected": [],
                "executed": [],
                "skipped": [],
            }

        approved = []
        rejected = []
        executed = []
        skipped = []
        entry_evidence = (
            daily_movement_summary(market_data)
            if market_data is not None
            else {"status": "not_checked"}
        )
        entries_paused = entry_evidence["status"] == "limited"

        pending = sorted(
            self.proposals(status="pending"),
            key=lambda item: (
                str(item.get("timestamp") or ""),
                str(item.get("proposal_id") or ""),
            ),
        )
        for proposal in pending:
            proposal_id = proposal["proposal_id"]
            if proposal.get("side") == "buy" and entries_paused:
                skipped.append(
                    {
                        "proposal_id": proposal_id,
                        "reason": "limited_daily_movement_evidence",
                    }
                )
                continue
            review = self.latest_proposal_risk_review(proposal_id)
            if not review:
                skipped.append(
                    {
                        "proposal_id": proposal_id,
                        "reason": "missing_risk_review",
                    }
                )
                continue
            verdict = str(review.get("verdict") or "").strip().lower()
            if verdict == "hold":
                self.decide_proposal(
                    proposal_id,
                    "reject",
                    notes="Auto-managed paper mode rejected this hold-risk proposal.",
                )
                rejected.append(proposal_id)
                continue
            self.decide_proposal(
                proposal_id,
                "approve",
                notes=(
                    "Auto-managed paper mode approved this proposal after "
                    f"{verdict or 'available'} risk review."
                ),
            )
            approved.append(proposal_id)

        ready = sorted(
            self.proposals(status="approved"),
            key=lambda item: (
                str(item.get("timestamp") or ""),
                str(item.get("proposal_id") or ""),
            ),
        )
        for proposal in ready:
            proposal_id = proposal["proposal_id"]
            if proposal.get("side") == "buy" and entries_paused:
                skipped.append(
                    {
                        "proposal_id": proposal_id,
                        "reason": "limited_daily_movement_evidence",
                    }
                )
                continue
            ticker = str(proposal.get("ticker") or "").strip().upper()
            price = latest_prices.get(ticker)
            if price is None:
                skipped.append(
                    {
                        "proposal_id": proposal_id,
                        "reason": "missing_price",
                    }
                )
                continue
            try:
                trade = self.execute_order(
                    proposal["side"],
                    ticker,
                    proposal["shares"],
                    float(price),
                    proposal["thesis"],
                    source=source,
                    recommendation_id=proposal.get("recommendation_id"),
                    proposal_id=proposal_id,
                )
            except ValueError as exc:
                skipped.append(
                    {
                        "proposal_id": proposal_id,
                        "reason": str(exc),
                    }
                )
                continue
            executed.append(trade["trade_id"])

        return {
            "enabled": True,
            "approved": approved,
            "rejected": rejected,
            "executed": executed,
            "skipped": skipped,
            "entry_evidence": entry_evidence,
        }

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

        timestamp = self.clock().isoformat(timespec="seconds")
        if not any(
            item.get("event") == "defensive_review_tracking_started"
            for item in self.ledger()
        ):
            self._append_event(
                {
                    "event": "defensive_review_tracking_started",
                    "timestamp": timestamp,
                    "mode": "review_only",
                    "loss_threshold_pct": DEFENSIVE_REVIEW_LOSS_THRESHOLD_PCT,
                    "lag_threshold_pct": DEFENSIVE_REVIEW_LAG_THRESHOLD_PCT,
                    "policy_changed": False,
                }
            )

        event = {
            "event": "performance_snapshot",
            "timestamp": timestamp,
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
            "security_prices": {
                str(ticker).upper(): float(price)
                for ticker, price in prices.items()
                if price is not None
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
        self._sync_prospective_defensive_review_events()
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

    def stage5_validation_summary(self, latest_prices=None, feedback_summary=None):
        """Summarize whether Stage 5 paper validation is building proof of quality."""
        performance = self.performance_summary()
        if not performance.get("available"):
            return {
                "available": False,
                "status": "not_started",
                "status_label": "Not started",
                "headline": "Atlas has not logged any paper-performance snapshots yet.",
                "detail": (
                    "Stage 5 validation begins after the paper account records benchmark-aware "
                    "performance snapshots."
                ),
                "takeaways": [
                    "Run the paper portfolio long enough to capture benchmark-relative history."
                ],
                "scorecards": [],
            }

        latest = performance["latest"]
        trade_stats = performance.get("trade_statistics") or self.trade_statistics()
        feedback = feedback_summary or self.proposal_feedback_summary(
            latest_prices=latest_prices
        )
        snapshots = int(performance.get("snapshots") or 0)
        judged = int(feedback.get("judged") or 0)
        realized_exits = int(trade_stats.get("realized_exits") or 0)
        win_rate = trade_stats.get("win_rate_pct")
        turnover_pct = trade_stats.get("turnover_pct")
        judged_sell_count = int(feedback.get("judged_side_counts", {}).get("sell") or 0)
        judged_sell_working = int(feedback.get("working_side_counts", {}).get("sell") or 0)
        judged_working = int(feedback.get("verdict_counts", {}).get("working") or 0)
        judged_sell_help_rate_pct = (
            round((judged_sell_working / judged_sell_count) * 100.0, 1)
            if judged_sell_count
            else None
        )
        judged_trade_working_rate_pct = (
            round((judged_working / judged) * 100.0, 1)
            if judged
            else None
        )
        horizon_learning = list(feedback.get("horizon_learning") or [])
        persistence_3 = next(
            (item for item in horizon_learning if item.get("snapshots") == 3),
            None,
        )
        persistence_5 = next(
            (item for item in horizon_learning if item.get("snapshots") == 5),
            None,
        )
        benchmark_excess = performance.get("excess_return_pct") or {}
        positive_benchmarks = [
            ticker for ticker, value in benchmark_excess.items() if value is not None and value > 0
        ]
        strongest_benchmark = None
        if latest.get("benchmark_returns_pct"):
            strongest_benchmark = max(
                latest["benchmark_returns_pct"].items(),
                key=lambda item: item[1],
            )[0]

        if snapshots < 5 or judged < 3:
            status = "building"
            status_label = "Evidence building"
            headline = "Stage 5 is still collecting enough paper evidence to judge Atlas fairly."
        elif len(positive_benchmarks) == len(benchmark_excess) and (win_rate or 0.0) >= 50.0:
            status = "encouraging"
            status_label = "Encouraging"
            headline = "Atlas is showing encouraging benchmark-relative paper results so far."
        elif len(positive_benchmarks) == 0 and judged >= 3:
            status = "caution"
            status_label = "Needs caution"
            headline = "Atlas has enough paper evidence to show caution versus the current benchmark bar."
        else:
            status = "mixed"
            status_label = "Mixed"
            headline = "Atlas has started to build a real paper track record, but the validation read is still mixed."

        strongest_excess = (
            benchmark_excess.get(strongest_benchmark)
            if strongest_benchmark
            else None
        )
        detail = (
            f"{snapshots} benchmark-aware snapshots, {judged} judged trade outcomes, "
            f"and {realized_exits} realized exits are available for Stage 5 validation."
        )
        if strongest_benchmark and strongest_excess is not None:
            detail += (
                f" Atlas is currently {strongest_excess:+.2f}% versus the strongest tracked "
                f"benchmark ({strongest_benchmark})."
            )

        win_rate_text = (
            f"{win_rate:.1f}%"
            if win_rate is not None
            else "N/A"
        )
        scorecards = [
            {
                "label": "Judged trade outcomes",
                "value": str(judged),
                "detail": "Executed paper decisions with enough later market data to score."
            },
            {
                "label": "Realized exit win rate",
                "value": win_rate_text,
                "detail": "Percentage of realized simulated sells that closed with a gain."
            },
            {
                "label": "Paper snapshots",
                "value": str(snapshots),
                "detail": "Benchmark-aware performance checkpoints recorded in the paper ledger."
            },
        ]
        if judged_trade_working_rate_pct is not None:
            scorecards.append(
                {
                    "label": "Judged trade working rate",
                    "value": f"{judged_trade_working_rate_pct:.1f}%",
                    "detail": "Share of judged simulated decisions currently scoring as working.",
                }
            )
        if judged_sell_help_rate_pct is not None:
            scorecards.append(
                {
                    "label": "Judged sell help rate",
                    "value": f"{judged_sell_help_rate_pct:.1f}%",
                    "detail": "Share of judged trims and exits that helped after Atlas sold.",
                }
            )
        if turnover_pct is not None:
            scorecards.append(
                {
                    "label": "Gross turnover",
                    "value": f"{turnover_pct:.1f}%",
                    "detail": "Executed buy plus sell notional as a share of starting paper capital.",
                }
            )
        if persistence_3 and persistence_3.get("working_rate_pct") is not None:
            scorecards.append(
                {
                    "label": "3-snapshot persistence",
                    "value": f"{persistence_3['working_rate_pct']:.1f}%",
                    "detail": "Share of judged trades still working three snapshots after execution.",
                }
            )
        if persistence_5 and persistence_5.get("working_rate_pct") is not None:
            scorecards.append(
                {
                    "label": "5-snapshot persistence",
                    "value": f"{persistence_5['working_rate_pct']:.1f}%",
                    "detail": "Share of judged trades still working five snapshots after execution.",
                }
            )
        for ticker in ("SPY", "QQQ"):
            value = benchmark_excess.get(ticker)
            if value is None:
                continue
            scorecards.append(
                {
                    "label": f"Excess vs {ticker}",
                    "value": f"{value:+.2f}%",
                    "detail": f"Atlas total return minus {ticker} return since paper tracking began.",
                }
            )

        takeaways = [
            (
                f"Atlas return is {latest['total_return_pct']:+.2f}% with "
                f"${latest['realized_gain_loss']:,.2f} realized and "
                f"${latest['unrealized_gain_loss']:,.2f} unrealized."
            ),
            (
                f"Judged learning mix: {feedback.get('verdict_counts', {}).get('working', 0)} working, "
                f"{feedback.get('verdict_counts', {}).get('mixed', 0)} mixed, and "
                f"{feedback.get('verdict_counts', {}).get('lagging', 0)} lagging."
            ),
        ]
        if len(positive_benchmarks) == len(benchmark_excess) and benchmark_excess:
            takeaways.append("Atlas is ahead of both tracked benchmarks right now.")
        elif positive_benchmarks:
            takeaways.append(
                "Atlas is ahead of "
                + " and ".join(positive_benchmarks)
                + " but still trailing at least one tracked benchmark."
            )
        else:
            takeaways.append("Atlas is not yet ahead of the tracked benchmarks on total paper return.")
        if judged_sell_help_rate_pct is not None:
            takeaways.append(
                f"Exit quality is {judged_sell_help_rate_pct:.1f}% on judged trims and exits."
            )
        if turnover_pct is not None:
            takeaways.append(
                f"Gross turnover has reached {turnover_pct:.1f}% of starting paper capital."
            )
        if persistence_3 and persistence_3.get("working_rate_pct") is not None:
            takeaways.append(
                f"{persistence_3['working_rate_pct']:.1f}% of judged trades are still working by the 3-snapshot checkpoint."
            )
        if judged < 3:
            takeaways.append(
                "The roadmap still needs more judged trades before Stage 5 can be treated as proven."
            )
        elif realized_exits < 2:
            takeaways.append(
                "Exit evidence is still light, so win-rate and sell-discipline reads are early."
            )
        persistence_5_rate = (
            persistence_5.get("working_rate_pct") if persistence_5 else None
        )
        def evidence_progress(current, target):
            if current is None or target <= 0:
                return 0.0
            return round(min(max(float(current) / float(target), 0.0), 1.0) * 100.0, 1)

        readiness_criteria = [
            {
                "id": "observation_depth",
                "label": "Observation depth",
                "passed": snapshots >= 250,
                "current": str(snapshots),
                "target": "250+ snapshots",
                "progress_pct": evidence_progress(snapshots, 250),
                "next_step": "Keep the scheduled paper account running to accumulate daily benchmark checkpoints.",
            },
            {
                "id": "judged_decisions",
                "label": "Judged decisions",
                "passed": judged >= 100,
                "current": str(judged),
                "target": "100+ outcomes",
                "progress_pct": evidence_progress(judged, 100),
                "next_step": "Allow executed paper decisions enough later market data to become judged outcomes.",
            },
            {
                "id": "realized_exits",
                "label": "Completed positions",
                "passed": realized_exits >= 30,
                "current": str(realized_exits),
                "target": "30+ completed",
                "progress_pct": evidence_progress(realized_exits, 30),
                "next_step": "Complete more full paper position cycles without forcing unnecessary turnover.",
            },
            {
                "id": "benchmark_outperformance",
                "label": "Benchmark outperformance",
                "passed": bool(benchmark_excess)
                and len(positive_benchmarks) == len(benchmark_excess),
                "current": (
                    f"{len(positive_benchmarks)} of {len(benchmark_excess)} ahead"
                ),
                "target": "Ahead of SPY and QQQ",
                "progress_pct": (
                    evidence_progress(len(positive_benchmarks), len(benchmark_excess))
                    if benchmark_excess
                    else 0.0
                ),
                "next_step": "Improve sustained total return relative to both SPY and QQQ.",
            },
            {
                "id": "decision_quality",
                "label": "Decision quality",
                "passed": (judged_trade_working_rate_pct or 0.0) >= 55.0,
                "current": (
                    f"{judged_trade_working_rate_pct:.1f}%"
                    if judged_trade_working_rate_pct is not None
                    else "N/A"
                ),
                "target": "55%+ working",
                "progress_pct": evidence_progress(judged_trade_working_rate_pct, 55.0),
                "next_step": "Accumulate more judged buys and sells while preserving a majority of working decisions.",
            },
            {
                "id": "exit_quality",
                "label": "Exit quality",
                "passed": (judged_sell_help_rate_pct or 0.0) >= 55.0,
                "current": (
                    f"{judged_sell_help_rate_pct:.1f}%"
                    if judged_sell_help_rate_pct is not None
                    else "N/A"
                ),
                "target": "55%+ helpful",
                "progress_pct": evidence_progress(judged_sell_help_rate_pct, 55.0),
                "next_step": "Measure whether trims and exits avoid later weakness often enough to be helpful.",
            },
            {
                "id": "realized_win_rate",
                "label": "Realized win rate",
                "passed": (win_rate or 0.0) >= 50.0,
                "current": win_rate_text,
                "target": "50%+ profitable",
                "progress_pct": evidence_progress(win_rate, 50.0),
                "next_step": "Build a larger sample of completed simulated positions with disciplined outcomes.",
            },
            {
                "id": "persistence",
                "label": "Five-snapshot persistence",
                "passed": (persistence_5_rate or 0.0) >= 55.0,
                "current": (
                    f"{persistence_5_rate:.1f}%"
                    if persistence_5_rate is not None
                    else "N/A"
                ),
                "target": "55%+ working",
                "progress_pct": evidence_progress(persistence_5_rate, 55.0),
                "next_step": "Give paper decisions five later snapshots to prove their results persist.",
            },
            {
                "id": "turnover_discipline",
                "label": "Turnover discipline",
                "passed": turnover_pct is not None and turnover_pct <= 100.0,
                "current": (
                    f"{turnover_pct:.1f}%" if turnover_pct is not None else "N/A"
                ),
                "target": "100% or less",
                "progress_pct": (
                    0.0
                    if turnover_pct is None
                    else 100.0
                    if turnover_pct <= 100.0
                    else round((100.0 / turnover_pct) * 100.0, 1)
                ),
                "next_step": "Keep gross paper turnover at or below starting capital over the evaluation window.",
            },
        ]
        passed_criteria = sum(1 for item in readiness_criteria if item["passed"])
        evidence_progress_pct = round(
            sum(item["progress_pct"] for item in readiness_criteria)
            / len(readiness_criteria),
            1,
        )
        incomplete_criteria = [
            item for item in readiness_criteria if not item["passed"]
        ]
        foundation_order = {
            "observation_depth": 0,
            "judged_decisions": 1,
            "realized_exits": 2,
        }
        foundation_milestones = sorted(
            (
                item
                for item in incomplete_criteria
                if item["id"] in foundation_order
            ),
            key=lambda item: foundation_order[item["id"]],
        )
        outcome_milestones = sorted(
            (
                item
                for item in incomplete_criteria
                if item["id"] not in foundation_order
            ),
            key=lambda item: (item["progress_pct"], item["label"]),
        )
        next_milestones = (foundation_milestones + outcome_milestones)[:3]
        capital_readiness = {
            "ready_for_owner_review": passed_criteria == len(readiness_criteria),
            "status": (
                "owner_review"
                if passed_criteria == len(readiness_criteria)
                else "paper_only"
            ),
            "status_label": (
                "Ready for owner review"
                if passed_criteria == len(readiness_criteria)
                else "Paper only"
            ),
            "headline": (
                "Atlas has cleared the initial evidence gates for an owner-led "
                "real-capital discussion."
                if passed_criteria == len(readiness_criteria)
                else "Atlas has not yet earned a real-capital discussion."
            ),
            "detail": (
                f"{passed_criteria} of {len(readiness_criteria)} conservative "
                "evidence gates currently pass. Passing every gate does not "
                "enable brokerage access or real-money trading."
            ),
            "passed": passed_criteria,
            "total": len(readiness_criteria),
            "progress_pct": evidence_progress_pct,
            "next_milestones": next_milestones,
            "criteria": readiness_criteria,
        }
        feedback_total = int(feedback.get("total") or 0)
        awaiting_judgment = max(feedback_total - judged, 0)
        judgment_coverage_pct = (
            round((judged / feedback_total) * 100.0, 1)
            if feedback_total
            else 0.0
        )
        evidence_pipeline = {
            "source": "Active paper ledger",
            "latest_snapshot_at": latest.get("timestamp"),
            "snapshot_count": snapshots,
            "executed_decisions": feedback_total,
            "judged_decisions": judged,
            "awaiting_judgment": awaiting_judgment,
            "judgment_coverage_pct": judgment_coverage_pct,
            "realized_exits": realized_exits,
            "completed_positions": realized_exits,
            "partial_trims": int(trade_stats.get("partial_trims") or 0),
            "sell_executions": int(trade_stats.get("sell_executions") or 0),
            "headline": (
                f"{judged} of {feedback_total} executed paper decisions have "
                "enough later market data for judgment."
                if feedback_total
                else "Atlas has not executed a paper decision to judge yet."
            ),
            "next_action": (
                f"Allow {awaiting_judgment} recent simulated decision"
                f"{'' if awaiting_judgment == 1 else 's'} to receive another "
                "scheduled benchmark-aware snapshot."
                if awaiting_judgment
                else "Keep the daily paper cycle running so future decisions receive later comparison snapshots."
            ),
        }
        paper_trades = [
            event
            for event in self.ledger()
            if event.get("event") == "paper_trade"
        ]
        completed_position_diagnostics = self.completed_position_diagnostics(
            paper_trades
        )
        shadow_trigger_analysis = self.shadow_defensive_trigger_analysis(
            paper_trades,
            self.performance_history(),
        )
        prospective_review_tracker = (
            self.prospective_defensive_review_tracker(self.ledger())
        )
        prospective_review_effectiveness = (
            self.prospective_review_effectiveness(
                prospective_review_tracker
            )
        )
        return {
            "available": True,
            "status": status,
            "status_label": status_label,
            "headline": headline,
            "detail": detail,
            "snapshots": snapshots,
            "judged_trades": judged,
            "realized_exits": realized_exits,
            "win_rate_pct": round(win_rate, 1) if win_rate is not None else None,
            "scorecards": scorecards,
            "takeaways": takeaways[:8],
            "capital_readiness": capital_readiness,
            "evidence_pipeline": evidence_pipeline,
            "completed_position_diagnostics": completed_position_diagnostics,
            "shadow_trigger_analysis": shadow_trigger_analysis,
            "prospective_review_tracker": prospective_review_tracker,
            "prospective_review_effectiveness": (
                prospective_review_effectiveness
            ),
        }

    def proposal_feedback(self, latest_prices=None):
        """Evaluate executed simulated proposals against later outcomes."""
        snapshots = self.performance_history()
        if not snapshots:
            return []

        latest = snapshots[-1]
        latest_prices = latest_prices or {}
        trades = [
            event
            for event in self.ledger()
            if event.get("event") == "paper_trade"
            and event.get("proposal_id")
        ]
        proposals = {
            proposal["proposal_id"]: proposal
            for proposal in self.proposals()
        }
        recommendations = {
            recommendation["recommendation_id"]: recommendation
            for recommendation in self.recommendations()
        }
        rows = []
        for trade in trades:
            ticker = trade["ticker"]
            proposal = proposals.get(trade["proposal_id"], {})
            recommendation = recommendations.get(trade.get("recommendation_id"), {})
            rationale = (
                proposal.get("rationale")
                or recommendation.get("rationale")
                or []
            )
            start = self._first_snapshot_after(snapshots, trade["timestamp"])
            latest_price = latest_prices.get(ticker)
            if not start or latest_price is None:
                rows.append(
                    self._feedback_row(
                        trade,
                        proposal,
                        "not_enough_time",
                        "No comparable performance snapshot is available yet.",
                        rationale=rationale,
                    )
                )
                continue

            security_return = self._pct_return(
                trade.get("price"),
                latest_price,
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
                verdict, summary = self._proposal_feedback_verdict(
                    trade=trade,
                    security_return=security_return,
                    benchmark_returns=usable_benchmarks,
                )
            rows.append(
                self._feedback_row(
                    trade,
                    proposal,
                    verdict,
                    summary,
                    security_return=security_return,
                    benchmark_returns=benchmark_returns,
                    snapshots=self._snapshots_since(snapshots, trade["timestamp"]),
                    latest_price=latest_price,
                    horizon_outcomes=self._feedback_horizon_outcomes(trade, snapshots),
                    rationale=rationale,
                )
            )
        return sorted(rows, key=lambda item: item["filled_at"], reverse=True)

    def proposal_feedback_summary(self, latest_prices=None, rows=None):
        """Summarize post-trade learning across simulated buys and sells."""
        rows = (
            self.proposal_feedback(latest_prices=latest_prices)
            if rows is None
            else rows
        )
        verdict_counts = {
            "working": 0,
            "mixed": 0,
            "lagging": 0,
            "not_enough_time": 0,
        }
        side_counts = {"buy": 0, "sell": 0}
        judged_side_counts = {"buy": 0, "sell": 0}
        working_side_counts = {"buy": 0, "sell": 0}
        lagging_side_counts = {"buy": 0, "sell": 0}
        driver_stats = {}
        sell_trigger_stats = {}
        horizon_stats = {}
        sector_gate_stats = {}

        for row in rows:
            side = str(row.get("side") or "buy").lower()
            if side not in side_counts:
                side = "buy"
            verdict = str(row.get("verdict") or "not_enough_time")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            side_counts[side] += 1
            if verdict != "not_enough_time":
                judged_side_counts[side] += 1
                if verdict == "working":
                    working_side_counts[side] += 1
                elif verdict == "lagging":
                    lagging_side_counts[side] += 1
            driver = row.get("decision_driver") or {}
            driver_code = str(driver.get("code") or "").strip().lower()
            if driver_code and verdict != "not_enough_time":
                stats = driver_stats.setdefault(
                    driver_code,
                    {
                        "code": driver_code,
                        "label": str(
                            driver.get("label") or driver_code.replace("_", " ")
                        ),
                        "judged": 0,
                        "working": 0,
                        "mixed": 0,
                        "lagging": 0,
                    },
                )
                stats["judged"] += 1
                if verdict == "working":
                    stats["working"] += 1
                elif verdict == "mixed":
                    stats["mixed"] += 1
                elif verdict == "lagging":
                    stats["lagging"] += 1
            trigger = row.get("sell_trigger") or {}
            trigger_code = str(trigger.get("code") or "").strip().lower()
            if side == "sell" and trigger_code and verdict != "not_enough_time":
                stats = sell_trigger_stats.setdefault(
                    trigger_code,
                    {
                        "code": trigger_code,
                        "label": str(
                            trigger.get("label") or trigger_code.replace("_", " ")
                        ),
                        "judged": 0,
                        "working": 0,
                        "mixed": 0,
                        "lagging": 0,
                    },
                )
                stats["judged"] += 1
                if verdict == "working":
                    stats["working"] += 1
                elif verdict == "mixed":
                    stats["mixed"] += 1
                elif verdict == "lagging":
                    stats["lagging"] += 1
            for horizon in row.get("horizon_outcomes") or []:
                if not horizon.get("available"):
                    continue
                key = int(horizon.get("snapshots") or 0)
                verdict = str(horizon.get("verdict") or "").strip().lower()
                if verdict not in {"working", "mixed", "lagging"} or key <= 0:
                    continue
                stats = horizon_stats.setdefault(
                    key,
                    {
                        "label": f"{key}-snapshot persistence",
                        "snapshots": key,
                        "judged": 0,
                        "working": 0,
                        "mixed": 0,
                        "lagging": 0,
                    },
                )
                stats["judged"] += 1
                stats[verdict] += 1
            sector_gate = row.get("sector_gate") or {}
            sector_gate_status = str(sector_gate.get("status") or "").strip().lower()
            if (
                side == "buy"
                and sector_gate_status
                and sector_gate_status != "watch"
                and verdict != "not_enough_time"
            ):
                stats = sector_gate_stats.setdefault(
                    sector_gate_status,
                    {
                        "status": sector_gate_status,
                        "label": str(
                            sector_gate.get("label")
                            or sector_gate_status.replace("_", " ")
                        ),
                        "judged": 0,
                        "working": 0,
                        "mixed": 0,
                        "lagging": 0,
                        "avg_edge_pct": None,
                    },
                )
                stats["judged"] += 1
                if verdict == "working":
                    stats["working"] += 1
                elif verdict == "mixed":
                    stats["mixed"] += 1
                elif verdict == "lagging":
                    stats["lagging"] += 1
                edge = self._best_benchmark_edge(row)
                if edge is not None:
                    stats.setdefault("_edges", []).append(edge)

        total = len(rows)
        judged = total - verdict_counts["not_enough_time"]
        if total == 0:
            headline = "No executed simulated trades are available for learning yet."
        elif judged == 0:
            headline = "Atlas is still collecting enough post-trade evidence to judge recent ideas."
        elif verdict_counts["working"] > verdict_counts["lagging"]:
            headline = "Recent simulated paper decisions are leaning constructive so far."
        elif verdict_counts["lagging"] > verdict_counts["working"]:
            headline = "Recent simulated paper decisions are showing more slippage than confirmation so far."
        else:
            headline = "Recent simulated paper decisions are balanced so far between confirmation and slippage."

        takeaways = [
            (
                f"Judged outcomes: {verdict_counts['working']} working, "
                f"{verdict_counts['mixed']} mixed, and {verdict_counts['lagging']} lagging."
            )
        ]
        if judged_side_counts["buy"]:
            takeaways.append(
                f"Entries ahead of both SPY and QQQ: {working_side_counts['buy']} of "
                f"{judged_side_counts['buy']} judged buys."
            )
        if judged_side_counts["sell"]:
            takeaways.append(
                f"Sells helping after trim or exit: {working_side_counts['sell']} of "
                f"{judged_side_counts['sell']} judged sell decisions."
            )
        if verdict_counts["not_enough_time"]:
            takeaways.append(
                f"Still gathering evidence on {verdict_counts['not_enough_time']} recent simulated trade"
                f"{'' if verdict_counts['not_enough_time'] == 1 else 's'}."
            )

        decision_driver_learning = self._decision_driver_learning(driver_stats)
        sell_trigger_learning = self._decision_driver_learning(sell_trigger_stats)
        horizon_learning = self._horizon_learning(horizon_stats)
        sector_gate_outcomes = self._sector_gate_outcomes(sector_gate_stats)
        if decision_driver_learning:
            strongest = max(
                decision_driver_learning,
                key=lambda item: (
                    item.get("working_rate_pct") or 0.0,
                    item.get("judged") or 0,
                ),
            )
            takeaways.append(
                f"Best projection read so far: {strongest['label']} is working on "
                f"{strongest['working']} of {strongest['judged']} judged trade"
                f"{'' if strongest['judged'] == 1 else 's'}."
            )
            weakest = min(
                decision_driver_learning,
                key=lambda item: (
                    item.get("working_rate_pct") or 0.0,
                    -(item.get("judged") or 0),
                ),
            )
            if weakest["code"] != strongest["code"]:
                takeaways.append(
                    f"Weaker projection read so far: {weakest['label']} is working on "
                    f"{weakest['working']} of {weakest['judged']} judged trade"
                    f"{'' if weakest['judged'] == 1 else 's'}."
                )
        if sell_trigger_learning:
            strongest_sell_trigger = max(
                sell_trigger_learning,
                key=lambda item: (
                    item.get("working_rate_pct") or 0.0,
                    item.get("judged") or 0,
                ),
            )
            takeaways.append(
                f"Best sell trigger so far: {strongest_sell_trigger['label']} is helping on "
                f"{strongest_sell_trigger['working']} of {strongest_sell_trigger['judged']} judged trim"
                f"{'' if strongest_sell_trigger['judged'] == 1 else 's'} or exits."
            )
            weakest_sell_trigger = min(
                sell_trigger_learning,
                key=lambda item: (
                    item.get("working_rate_pct") or 0.0,
                    -(item.get("judged") or 0),
                ),
            )
            if weakest_sell_trigger["code"] != strongest_sell_trigger["code"]:
                takeaways.append(
                    f"Weaker sell trigger so far: {weakest_sell_trigger['label']} is helping on "
                    f"{weakest_sell_trigger['working']} of {weakest_sell_trigger['judged']} judged trim"
                    f"{'' if weakest_sell_trigger['judged'] == 1 else 's'} or exits."
                )

        projection_threshold_profile = self._projection_threshold_profile_from_rows(
            rows,
            decision_driver_learning=decision_driver_learning,
        )
        entry_strategy_profile = self._entry_strategy_profile_from_rows(rows)
        trade_pressure_profile = self._trade_pressure_profile_from_rows(rows)
        benchmark_preference_profile = self._benchmark_preference_profile_from_rows(rows)
        benchmark_scorecard = self._benchmark_scorecard_from_rows(rows)
        if horizon_learning:
            longest = max(horizon_learning, key=lambda item: item.get("snapshots") or 0)
            takeaways.append(
                f"Longest persistence read so far: {longest['working']} of {longest['judged']} "
                f"judged trades are still working by the {longest['label']} checkpoint."
            )
        if trade_pressure_profile.get("active"):
            adjustment = (trade_pressure_profile.get("adjustments") or [{}])[0]
            takeaways.append(
                f"Daily paper trade pressure is now {adjustment.get('direction', 'adjusted')} "
                f"from {adjustment.get('from', '--')} to {adjustment.get('to', '--')} trades."
            )
        if benchmark_preference_profile.get("active"):
            adjustment = (benchmark_preference_profile.get("adjustments") or [{}])[0]
            takeaways.append(
                f"Benchmark trust is currently leaning on {adjustment.get('to', 'auto')} "
                "for borderline paper entries."
            )
        if entry_strategy_profile.get("active"):
            rotation = entry_strategy_profile.get("benchmark_rotation_stats") or {}
            if rotation.get("benchmark"):
                takeaways.append(
                    f"Sector and capital pacing is adapting from buy evidence versus "
                    f"{rotation['benchmark']}."
                )
        if benchmark_scorecard.get("leader"):
            leader = benchmark_scorecard["leader"]
            takeaways.append(
                f"Benchmark scorecard leader: Atlas decisions have a "
                f"{leader['working_rate_pct']:.0f}% working rate versus {leader['benchmark']}."
            )
        if sector_gate_outcomes.get("active") and sector_gate_outcomes.get("leader"):
            leader = sector_gate_outcomes["leader"]
            takeaways.append(
                f"Sector gate outcome leader: {leader['label']} is working on "
                f"{leader['working']} of {leader['judged']} judged gated paper buys."
            )

        return {
            "total": total,
            "judged": judged,
            "headline": headline,
            "verdict_counts": verdict_counts,
            "side_counts": side_counts,
            "judged_side_counts": judged_side_counts,
            "working_side_counts": working_side_counts,
            "lagging_side_counts": lagging_side_counts,
            "decision_driver_learning": decision_driver_learning[:4],
            "sell_trigger_learning": sell_trigger_learning[:4],
            "horizon_learning": horizon_learning,
            "entry_strategy_profile": entry_strategy_profile,
            "projection_threshold_profile": projection_threshold_profile,
            "trade_pressure_profile": trade_pressure_profile,
            "benchmark_preference_profile": benchmark_preference_profile,
            "benchmark_scorecard": benchmark_scorecard,
            "sector_gate_outcomes": sector_gate_outcomes,
            "takeaways": takeaways[:8],
        }

    @staticmethod
    def _decision_driver_learning(driver_stats):
        return sorted(
            [
                {
                    **stats,
                    "working_rate_pct": round(
                        (stats["working"] / stats["judged"]) * 100.0,
                        1,
                    )
                    if stats["judged"]
                    else None,
                }
                for stats in driver_stats.values()
                if stats["judged"] > 0
            ],
            key=lambda item: (
                -(item.get("judged") or 0),
                -(item.get("working_rate_pct") or 0.0),
                item.get("label") or "",
            ),
        )

    @staticmethod
    def _horizon_learning(horizon_stats):
        return sorted(
            [
                {
                    **stats,
                    "working_rate_pct": round(
                        (stats["working"] / stats["judged"]) * 100.0,
                        1,
                    )
                    if stats["judged"]
                    else None,
                }
                for stats in horizon_stats.values()
                if stats["judged"] > 0
            ],
            key=lambda item: item.get("snapshots") or 0,
        )

    @staticmethod
    def _sector_gate_outcomes(sector_gate_stats):
        scorecards = []
        for stats in sector_gate_stats.values():
            edges = stats.pop("_edges", [])
            judged = int(stats.get("judged") or 0)
            working = int(stats.get("working") or 0)
            scorecards.append(
                {
                    **stats,
                    "working_rate_pct": (
                        round((working / judged) * 100.0, 1) if judged else None
                    ),
                    "avg_edge_pct": (
                        round(sum(edges) / len(edges), 2) if edges else None
                    ),
                }
            )
        scorecards = sorted(
            scorecards,
            key=lambda item: (
                int(item.get("judged") or 0),
                float(item.get("working_rate_pct") or 0.0),
                float(item.get("avg_edge_pct") or 0.0),
                item.get("label") or "",
            ),
            reverse=True,
        )
        if scorecards:
            headline = (
                "Atlas is judging whether accepted sector-gate decisions are "
                "beating the benchmark bar."
            )
        else:
            headline = "Atlas is waiting for judged accepted sector-gate buys."
        return {
            "enabled": True,
            "active": bool(scorecards),
            "headline": headline,
            "scorecards": scorecards,
            "leader": scorecards[0] if scorecards else None,
        }

    def projection_threshold_profile(self, latest_prices=None):
        rows = self.proposal_feedback(latest_prices=latest_prices)
        return self._projection_threshold_profile_from_rows(rows)

    def entry_strategy_profile(self, latest_prices=None):
        rows = self.proposal_feedback(latest_prices=latest_prices)
        return self._entry_strategy_profile_from_rows(rows)

    def trade_pressure_profile(self, latest_prices=None):
        rows = self.proposal_feedback(latest_prices=latest_prices)
        return self._trade_pressure_profile_from_rows(rows)

    def benchmark_preference_profile(self, latest_prices=None):
        rows = self.proposal_feedback(latest_prices=latest_prices)
        return self._benchmark_preference_profile_from_rows(rows)

    def benchmark_scorecard(self, latest_prices=None):
        rows = self.proposal_feedback(latest_prices=latest_prices)
        return self._benchmark_scorecard_from_rows(rows)

    def _benchmark_scorecard_from_rows(self, rows):
        scorecards = []
        for benchmark in ("SPY", "QQQ"):
            stats = {
                "benchmark": benchmark,
                "label": (
                    "SPY - SPDR S&P 500 ETF Trust"
                    if benchmark == "SPY"
                    else "QQQ - Invesco QQQ Trust"
                ),
                "judged": 0,
                "working": 0,
                "mixed": 0,
                "lagging": 0,
                "buy_judged": 0,
                "buy_working": 0,
                "buy_mixed": 0,
                "buy_lagging": 0,
                "sell_judged": 0,
                "sell_working": 0,
                "sell_mixed": 0,
                "sell_lagging": 0,
                "avg_decision_edge_pct": None,
                "buy_avg_decision_edge_pct": None,
                "sell_avg_decision_edge_pct": None,
                "working_rate_pct": None,
                "buy_working_rate_pct": None,
                "sell_working_rate_pct": None,
            }
            edges = []
            buy_edges = []
            sell_edges = []
            for row in rows:
                side = str(row.get("side") or "").strip().lower()
                verdict = str(row.get("verdict") or "").strip().lower()
                benchmark_return = (row.get("benchmark_returns_pct") or {}).get(benchmark)
                security_return = row.get("security_return_pct")
                if (
                    side not in {"buy", "sell"}
                    or verdict not in {"working", "mixed", "lagging"}
                    or benchmark_return is None
                    or security_return is None
                ):
                    continue
                raw_edge = float(security_return) - float(benchmark_return)
                decision_edge = raw_edge if side == "buy" else -raw_edge
                edges.append(decision_edge)
                stats["judged"] += 1
                if side == "buy":
                    stats["buy_judged"] += 1
                    buy_edges.append(decision_edge)
                else:
                    stats["sell_judged"] += 1
                    sell_edges.append(decision_edge)
                if decision_edge >= 2.0:
                    stats["working"] += 1
                    if side == "buy":
                        stats["buy_working"] += 1
                    else:
                        stats["sell_working"] += 1
                elif decision_edge <= -2.0:
                    stats["lagging"] += 1
                    if side == "buy":
                        stats["buy_lagging"] += 1
                    else:
                        stats["sell_lagging"] += 1
                else:
                    stats["mixed"] += 1
                    if side == "buy":
                        stats["buy_mixed"] += 1
                    else:
                        stats["sell_mixed"] += 1
            if stats["judged"]:
                stats["avg_decision_edge_pct"] = round(sum(edges) / len(edges), 4)
                stats["working_rate_pct"] = round(
                    (stats["working"] / stats["judged"]) * 100.0,
                    1,
                )
            if stats["buy_judged"]:
                stats["buy_avg_decision_edge_pct"] = round(
                    sum(buy_edges) / len(buy_edges),
                    4,
                )
                stats["buy_working_rate_pct"] = round(
                    (stats["buy_working"] / stats["buy_judged"]) * 100.0,
                    1,
                )
            if stats["sell_judged"]:
                stats["sell_avg_decision_edge_pct"] = round(
                    sum(sell_edges) / len(sell_edges),
                    4,
                )
                stats["sell_working_rate_pct"] = round(
                    (stats["sell_working"] / stats["sell_judged"]) * 100.0,
                    1,
                )
            scorecards.append(stats)

        judged = sum(item["judged"] for item in scorecards)
        leader_candidates = [item for item in scorecards if item["judged"]]
        leader = (
            max(
                leader_candidates,
                key=lambda item: (
                    item.get("working_rate_pct") or 0.0,
                    item.get("avg_decision_edge_pct") or 0.0,
                ),
            )
            if leader_candidates
            else None
        )
        if not judged:
            headline = "Atlas needs more judged paper trades before benchmark-specific scorecards are meaningful."
        elif leader:
            headline = (
                f"Atlas's judged paper decisions are currently strongest versus "
                f"{leader['benchmark']}."
            )
        else:
            headline = "Atlas is collecting benchmark-specific paper decision evidence."
        return {
            "enabled": True,
            "headline": headline,
            "judged": judged,
            "leader": leader,
            "scorecards": scorecards,
        }

    def _entry_strategy_profile_from_rows(self, rows):
        policy = self.effective_policy()
        baseline = {
            "strategy_minimum_buy_score": float(
                policy.get("strategy_minimum_buy_score", 88.0)
            ),
            "strategy_target_position_pct": float(
                policy.get("strategy_target_position_pct", 5.0)
            ),
            "strategy_maximum_new_proposals": int(
                policy.get("strategy_maximum_new_proposals", 3)
            ),
            "strategy_benchmark_excess_weight": float(
                policy.get("strategy_benchmark_excess_weight", 1.5)
            ),
            "strategy_trend_quality_weight": float(
                policy.get("strategy_trend_quality_weight", 0.2)
            ),
            "strategy_sector_repeat_penalty": float(
                policy.get("strategy_sector_repeat_penalty", 3.0)
            ),
        }
        judged_buys = [
            row
            for row in rows
            if str(row.get("side") or "").strip().lower() == "buy"
            and str(row.get("verdict") or "").strip().lower() in {"working", "mixed", "lagging"}
        ]
        min_judged = int(policy.get("projection_learning_min_judged_trades", 3) or 3)
        if len(judged_buys) < min_judged:
            return {
                "enabled": True,
                "active": False,
                "headline": (
                    "Atlas is still collecting enough judged buy outcomes before "
                    "retuning paper entry rules."
                ),
                "judged_trades": len(judged_buys),
                "adjustments": [],
                "strategy_overrides": {},
                "baseline": baseline,
                "buy_stats": self._buy_learning_bucket(judged_buys),
            }

        buy_stats = self._buy_learning_bucket(judged_buys)
        persistence_stats = self._buy_persistence_bucket(judged_buys, snapshots=3)
        overrides = {}
        adjustments = []
        working_rate = buy_stats.get("working_rate_pct")
        persistence_rate = persistence_stats.get("working_rate_pct")

        if (
            working_rate is not None
            and persistence_rate is not None
            and working_rate >= 67.0
            and persistence_rate >= 67.0
            and buy_stats.get("working", 0) >= 2
        ):
            overrides["strategy_minimum_buy_score"] = max(
                baseline["strategy_minimum_buy_score"] - 1.0,
                86.0,
            )
            overrides["strategy_target_position_pct"] = round(
                min(
                    baseline["strategy_target_position_pct"] + 0.5,
                    6.5,
                ),
                4,
            )
            overrides["strategy_maximum_new_proposals"] = min(
                baseline["strategy_maximum_new_proposals"] + 1,
                4,
            )
            overrides["strategy_sector_repeat_penalty"] = round(
                max(
                    baseline["strategy_sector_repeat_penalty"] - 1.0,
                    1.5,
                ),
                4,
            )
            adjustments.extend(
                [
                    {
                        "field": "strategy_minimum_buy_score",
                        "label": "Paper buy threshold",
                        "direction": "looser",
                        "from": baseline["strategy_minimum_buy_score"],
                        "to": overrides["strategy_minimum_buy_score"],
                        "reason": (
                            "Recent judged buys have been confirming, so Atlas can "
                            "admit slightly earlier leaders."
                        ),
                    },
                    {
                        "field": "strategy_target_position_pct",
                        "label": "Target entry size",
                        "direction": "larger",
                        "from": baseline["strategy_target_position_pct"],
                        "to": overrides["strategy_target_position_pct"],
                        "reason": (
                            "Recent judged buys have held up well, so Atlas can size "
                            "new paper entries a little more aggressively."
                        ),
                    },
                    {
                        "field": "strategy_maximum_new_proposals",
                        "label": "New idea capacity",
                        "direction": "broader",
                        "from": baseline["strategy_maximum_new_proposals"],
                        "to": overrides["strategy_maximum_new_proposals"],
                        "reason": (
                            "Recent judged buys have held up well, so Atlas can open "
                            "slightly more new paper ideas at once."
                        ),
                    },
                    {
                        "field": "strategy_sector_repeat_penalty",
                        "label": "Sector repeat pressure",
                        "direction": "looser",
                        "from": baseline["strategy_sector_repeat_penalty"],
                        "to": overrides["strategy_sector_repeat_penalty"],
                        "reason": (
                            "Recent judged buys have held up well, so Atlas can allow "
                            "a little more concentration in leading sectors."
                        ),
                    },
                ]
            )
        elif (
            working_rate is not None
            and persistence_rate is not None
            and working_rate <= 34.0
            and persistence_rate <= 34.0
            and buy_stats.get("lagging", 0) >= 2
        ):
            overrides["strategy_minimum_buy_score"] = min(
                baseline["strategy_minimum_buy_score"] + 2.0,
                92.0,
            )
            overrides["strategy_target_position_pct"] = round(
                max(
                    baseline["strategy_target_position_pct"] - 0.5,
                    3.5,
                ),
                4,
            )
            overrides["strategy_maximum_new_proposals"] = max(
                baseline["strategy_maximum_new_proposals"] - 1,
                1,
            )
            overrides["strategy_benchmark_excess_weight"] = round(
                min(
                    baseline["strategy_benchmark_excess_weight"] + 0.5,
                    2.5,
                ),
                4,
            )
            overrides["strategy_trend_quality_weight"] = round(
                min(
                    baseline["strategy_trend_quality_weight"] + 0.1,
                    0.5,
                ),
                4,
            )
            overrides["strategy_sector_repeat_penalty"] = round(
                min(
                    baseline["strategy_sector_repeat_penalty"] + 1.0,
                    5.0,
                ),
                4,
            )
            adjustments.extend(
                [
                    {
                        "field": "strategy_minimum_buy_score",
                        "label": "Paper buy threshold",
                        "direction": "tighter",
                        "from": baseline["strategy_minimum_buy_score"],
                        "to": overrides["strategy_minimum_buy_score"],
                        "reason": (
                            "Recent judged buys have been lagging, so Atlas now demands "
                            "higher raw score quality before new entries."
                        ),
                    },
                    {
                        "field": "strategy_target_position_pct",
                        "label": "Target entry size",
                        "direction": "smaller",
                        "from": baseline["strategy_target_position_pct"],
                        "to": overrides["strategy_target_position_pct"],
                        "reason": (
                            "Recent judged buys have been lagging, so Atlas now sizes "
                            "new paper entries more cautiously."
                        ),
                    },
                    {
                        "field": "strategy_maximum_new_proposals",
                        "label": "New idea capacity",
                        "direction": "narrower",
                        "from": baseline["strategy_maximum_new_proposals"],
                        "to": overrides["strategy_maximum_new_proposals"],
                        "reason": (
                            "Recent judged buys have been lagging, so Atlas now opens "
                            "fewer new paper ideas at once."
                        ),
                    },
                    {
                        "field": "strategy_benchmark_excess_weight",
                        "label": "Benchmark confirmation weight",
                        "direction": "stronger",
                        "from": baseline["strategy_benchmark_excess_weight"],
                        "to": overrides["strategy_benchmark_excess_weight"],
                        "reason": (
                            "Recent judged buys have been lagging, so Atlas now puts more "
                            "weight on benchmark outperformance when ranking entries."
                        ),
                    },
                    {
                        "field": "strategy_trend_quality_weight",
                        "label": "Trend quality weight",
                        "direction": "stronger",
                        "from": baseline["strategy_trend_quality_weight"],
                        "to": overrides["strategy_trend_quality_weight"],
                        "reason": (
                            "Recent judged buys have been lagging, so Atlas now puts more "
                            "weight on trend quality before opening new paper entries."
                        ),
                    },
                    {
                        "field": "strategy_sector_repeat_penalty",
                        "label": "Sector repeat pressure",
                        "direction": "stronger",
                        "from": baseline["strategy_sector_repeat_penalty"],
                        "to": overrides["strategy_sector_repeat_penalty"],
                        "reason": (
                            "Recent judged buys have been lagging, so Atlas now pushes "
                            "harder against concentrating too many new ideas in one sector."
                        ),
                    },
                ]
            )

        benchmark_scorecard = self._benchmark_scorecard_from_rows(rows)
        benchmark_rotation_stats = self._benchmark_rotation_bucket(
            benchmark_scorecard.get("scorecards") or []
        )
        rotation_rate = benchmark_rotation_stats.get("working_rate_pct")
        if (
            benchmark_rotation_stats["judged"] >= min_judged
            and rotation_rate is not None
            and "strategy_target_position_pct" not in overrides
            and "strategy_sector_repeat_penalty" not in overrides
        ):
            if rotation_rate >= 67.0 and benchmark_rotation_stats["working"] >= 2:
                overrides["strategy_target_position_pct"] = round(
                    min(baseline["strategy_target_position_pct"] + 0.5, 6.5),
                    4,
                )
                overrides["strategy_maximum_new_proposals"] = min(
                    baseline["strategy_maximum_new_proposals"] + 1,
                    4,
                )
                overrides["strategy_sector_repeat_penalty"] = round(
                    max(baseline["strategy_sector_repeat_penalty"] - 0.5, 1.5),
                    4,
                )
                adjustments.extend(
                    [
                        {
                            "field": "strategy_target_position_pct",
                            "label": "Benchmark-led target size",
                            "direction": "larger",
                            "from": baseline["strategy_target_position_pct"],
                            "to": overrides["strategy_target_position_pct"],
                            "reason": (
                                "Benchmark-specific buy scorecards show new entries "
                                f"working versus {benchmark_rotation_stats['benchmark']}, so Atlas "
                                "can rotate slightly more capital into fresh leaders."
                            ),
                        },
                        {
                            "field": "strategy_sector_repeat_penalty",
                            "label": "Benchmark-led sector pacing",
                            "direction": "looser",
                            "from": baseline["strategy_sector_repeat_penalty"],
                            "to": overrides["strategy_sector_repeat_penalty"],
                            "reason": (
                                "Benchmark-specific buy scorecards show new entries "
                                f"working versus {benchmark_rotation_stats['benchmark']}, so Atlas "
                                "can allow a little more sector leadership concentration."
                            ),
                        },
                    ]
                )
            elif rotation_rate <= 34.0 and benchmark_rotation_stats["lagging"] >= 2:
                overrides["strategy_target_position_pct"] = round(
                    max(baseline["strategy_target_position_pct"] - 0.5, 3.5),
                    4,
                )
                overrides["strategy_maximum_new_proposals"] = max(
                    baseline["strategy_maximum_new_proposals"] - 1,
                    1,
                )
                overrides["strategy_sector_repeat_penalty"] = round(
                    min(baseline["strategy_sector_repeat_penalty"] + 0.5, 5.0),
                    4,
                )
                adjustments.extend(
                    [
                        {
                            "field": "strategy_target_position_pct",
                            "label": "Benchmark-led target size",
                            "direction": "smaller",
                            "from": baseline["strategy_target_position_pct"],
                            "to": overrides["strategy_target_position_pct"],
                            "reason": (
                                "Benchmark-specific buy scorecards show new entries "
                                f"lagging versus {benchmark_rotation_stats['benchmark']}, so Atlas "
                                "will rotate less capital into fresh ideas."
                            ),
                        },
                        {
                            "field": "strategy_sector_repeat_penalty",
                            "label": "Benchmark-led sector pacing",
                            "direction": "stronger",
                            "from": baseline["strategy_sector_repeat_penalty"],
                            "to": overrides["strategy_sector_repeat_penalty"],
                            "reason": (
                                "Benchmark-specific buy scorecards show new entries "
                                f"lagging versus {benchmark_rotation_stats['benchmark']}, so Atlas "
                                "will diversify new ideas more aggressively."
                            ),
                        },
                    ]
                )

        headline = (
            "Atlas has enough judged buy evidence, but current paper entry rules remain in balance."
            if not adjustments
            else "Atlas is auto-retuning paper entry rules from judged buy outcomes."
        )
        return {
            "enabled": True,
            "active": bool(adjustments),
            "headline": headline,
            "judged_trades": len(judged_buys),
            "adjustments": adjustments[:4],
            "strategy_overrides": overrides,
            "baseline": baseline,
            "buy_stats": buy_stats,
            "persistence_stats": persistence_stats,
            "benchmark_rotation_stats": benchmark_rotation_stats,
        }

    @staticmethod
    def _benchmark_rotation_bucket(scorecards):
        usable = [
            item
            for item in scorecards
            if int(item.get("buy_judged") or 0) > 0
            and item.get("buy_working_rate_pct") is not None
        ]
        if not usable:
            return {
                "benchmark": None,
                "judged": 0,
                "working": 0,
                "mixed": 0,
                "lagging": 0,
                "working_rate_pct": None,
                "avg_decision_edge_pct": None,
            }
        best = max(
            usable,
            key=lambda item: (
                int(item.get("buy_judged") or 0),
                abs(float(item.get("buy_avg_decision_edge_pct") or 0.0)),
                float(item.get("buy_working_rate_pct") or 0.0),
            ),
        )
        return {
            "benchmark": best.get("benchmark"),
            "judged": int(best.get("buy_judged") or 0),
            "working": int(best.get("buy_working") or 0),
            "mixed": int(best.get("buy_mixed") or 0),
            "lagging": int(best.get("buy_lagging") or 0),
            "working_rate_pct": best.get("buy_working_rate_pct"),
            "avg_decision_edge_pct": best.get("buy_avg_decision_edge_pct"),
        }

    def _trade_pressure_profile_from_rows(self, rows):
        policy = self.effective_policy()
        baseline = {
            "maximum_daily_trades": int(policy.get("maximum_daily_trades", 5) or 5),
        }
        judged_rows = [
            row
            for row in rows
            if str(row.get("verdict") or "").strip().lower() in {"working", "mixed", "lagging"}
        ]
        min_judged = int(policy.get("projection_learning_min_judged_trades", 3) or 3)
        verdicts = {"judged": 0, "working": 0, "mixed": 0, "lagging": 0}
        sell_verdicts = {"judged": 0, "working": 0, "mixed": 0, "lagging": 0}
        for row in judged_rows:
            verdict = str(row.get("verdict") or "").strip().lower()
            verdicts["judged"] += 1
            verdicts[verdict] += 1
            if str(row.get("side") or "").strip().lower() == "sell":
                sell_verdicts["judged"] += 1
                sell_verdicts[verdict] += 1
        verdicts["working_rate_pct"] = (
            round((verdicts["working"] / verdicts["judged"]) * 100.0, 1)
            if verdicts["judged"]
            else None
        )
        sell_verdicts["working_rate_pct"] = (
            round((sell_verdicts["working"] / sell_verdicts["judged"]) * 100.0, 1)
            if sell_verdicts["judged"]
            else None
        )
        if len(judged_rows) < min_judged:
            return {
                "enabled": True,
                "active": False,
                "headline": (
                    "Atlas is still collecting enough judged outcomes before retuning "
                    "daily paper trade pressure."
                ),
                "judged_trades": len(judged_rows),
                "adjustments": [],
                "policy_overrides": {},
                "baseline": baseline,
                "verdicts": verdicts,
                "sell_verdicts": sell_verdicts,
            }

        overrides = {}
        adjustments = []
        working_rate = verdicts.get("working_rate_pct")
        sell_rate = sell_verdicts.get("working_rate_pct")
        if (
            working_rate is not None
            and working_rate >= 67.0
            and verdicts["working"] >= 3
            and (sell_rate is None or sell_rate >= 50.0)
        ):
            overrides["maximum_daily_trades"] = min(
                baseline["maximum_daily_trades"] + 1,
                6,
            )
            adjustments.append(
                {
                    "field": "maximum_daily_trades",
                    "label": "Daily paper trade capacity",
                    "direction": "higher",
                    "from": baseline["maximum_daily_trades"],
                    "to": overrides["maximum_daily_trades"],
                    "reason": (
                        "Recent judged paper decisions have been confirming, so Atlas can "
                        "operate with slightly more daily execution capacity."
                    ),
                }
            )
        elif (
            working_rate is not None
            and working_rate <= 34.0
            and verdicts["lagging"] >= 3
        ):
            overrides["maximum_daily_trades"] = max(
                baseline["maximum_daily_trades"] - 1,
                2,
            )
            adjustments.append(
                {
                    "field": "maximum_daily_trades",
                    "label": "Daily paper trade capacity",
                    "direction": "lower",
                    "from": baseline["maximum_daily_trades"],
                    "to": overrides["maximum_daily_trades"],
                    "reason": (
                        "Recent judged paper decisions have been lagging, so Atlas now "
                        "slows daily execution pressure."
                    ),
                }
            )

        headline = (
            "Atlas has enough judged evidence, but daily paper trade pressure remains in balance."
            if not adjustments
            else "Atlas is auto-retuning daily paper trade pressure from judged outcomes."
        )
        return {
            "enabled": True,
            "active": bool(adjustments),
            "headline": headline,
            "judged_trades": len(judged_rows),
            "adjustments": adjustments,
            "policy_overrides": overrides,
            "baseline": baseline,
            "verdicts": verdicts,
            "sell_verdicts": sell_verdicts,
        }

    def _benchmark_preference_profile_from_rows(self, rows):
        policy = self.effective_policy()
        baseline = {
            "strategy_preferred_benchmark": str(
                policy.get("strategy_preferred_benchmark", "auto") or "auto"
            ).strip().upper()
        }
        if baseline["strategy_preferred_benchmark"] not in {"SPY", "QQQ"}:
            baseline["strategy_preferred_benchmark"] = "auto"
        judged_buys = [
            row
            for row in rows
            if str(row.get("side") or "").strip().lower() == "buy"
            and str(row.get("verdict") or "").strip().lower() in {"working", "mixed", "lagging"}
            and row.get("security_return_pct") is not None
            and isinstance(row.get("benchmark_returns_pct"), dict)
        ]
        min_judged = int(policy.get("projection_learning_min_judged_trades", 3) or 3)
        benchmark_stats = {
            "SPY": {
                "judged": 0,
                "working": 0,
                "mixed": 0,
                "lagging": 0,
                "avg_excess_pct": None,
                "agreement_rate_pct": None,
            },
            "QQQ": {
                "judged": 0,
                "working": 0,
                "mixed": 0,
                "lagging": 0,
                "avg_excess_pct": None,
                "agreement_rate_pct": None,
            },
        }
        agreement_scores = {}
        for benchmark in ("SPY", "QQQ"):
            all_excess = []
            matches = 0
            for row in judged_buys:
                benchmark_return = row.get("benchmark_returns_pct", {}).get(benchmark)
                security_return = row.get("security_return_pct")
                verdict = str(row.get("verdict") or "").strip().lower()
                if benchmark_return is None or security_return is None:
                    continue
                excess = round(float(security_return) - float(benchmark_return), 4)
                all_excess.append(excess)
                benchmark_stats[benchmark]["judged"] += 1
                predicted = self._benchmark_relative_verdict(
                    security_return,
                    benchmark_return,
                )
                if predicted in {"working", "mixed", "lagging"}:
                    benchmark_stats[benchmark][predicted] += 1
                    if predicted == verdict:
                        matches += 1
            if all_excess:
                benchmark_stats[benchmark]["avg_excess_pct"] = round(
                    sum(all_excess) / len(all_excess),
                    4,
                )
            if benchmark_stats[benchmark]["judged"]:
                agreement_scores[benchmark] = matches
                benchmark_stats[benchmark]["agreement_rate_pct"] = round(
                    (matches / benchmark_stats[benchmark]["judged"]) * 100.0,
                    1,
                )
            else:
                agreement_scores[benchmark] = None

        if len(judged_buys) < min_judged:
            return {
                "enabled": True,
                "active": False,
                "headline": (
                    "Atlas is still collecting enough judged buy outcomes before "
                    "retuning which benchmark bar to trust most."
                ),
                "judged_trades": len(judged_buys),
                "adjustments": [],
                "strategy_overrides": {},
                "baseline": baseline,
                "benchmark_stats": benchmark_stats,
                "agreement_scores": agreement_scores,
            }

        preferred = None
        spy_score = agreement_scores.get("SPY")
        qqq_score = agreement_scores.get("QQQ")
        if (
            spy_score is not None
            and qqq_score is not None
            and benchmark_stats["SPY"]["judged"] >= min_judged
            and benchmark_stats["QQQ"]["judged"] >= min_judged
        ):
            if qqq_score >= (spy_score + 1):
                preferred = "QQQ"
            elif spy_score >= (qqq_score + 1):
                preferred = "SPY"

        overrides = {}
        adjustments = []
        if preferred and preferred != baseline["strategy_preferred_benchmark"]:
            overrides["strategy_preferred_benchmark"] = preferred
            adjustments.append(
                {
                    "field": "strategy_preferred_benchmark",
                    "label": "Benchmark trust bar",
                    "direction": "adaptive",
                    "from": baseline["strategy_preferred_benchmark"],
                    "to": preferred,
                    "reason": (
                        f"Recent judged buys separate working versus lagging outcomes more "
                        f"cleanly against {preferred}, so Atlas will trust that market bar more."
                    ),
                }
            )

        headline = (
            "Atlas has enough judged buy evidence, but benchmark selection remains in balance."
            if not adjustments
            else "Atlas is auto-retuning which benchmark bar to trust from judged buy outcomes."
        )
        return {
            "enabled": True,
            "active": bool(adjustments),
            "headline": headline,
            "judged_trades": len(judged_buys),
            "adjustments": adjustments,
            "strategy_overrides": overrides,
            "baseline": baseline,
            "benchmark_stats": benchmark_stats,
            "agreement_scores": agreement_scores,
        }

    @staticmethod
    def _benchmark_relative_verdict(security_return, benchmark_return):
        if security_return is None or benchmark_return is None:
            return None
        excess = float(security_return) - float(benchmark_return)
        if excess >= 2.0:
            return "working"
        if excess <= -2.0:
            return "lagging"
        return "mixed"

    def _projection_threshold_profile_from_rows(
        self,
        rows,
        *,
        decision_driver_learning=None,
    ):
        policy = self.effective_policy()
        baseline = {
            "projection_trim_excess_pct": DEFAULT_PROJECTION_TRIM_EXCESS_PCT,
            "projection_trim_sector_breadth_pct": DEFAULT_PROJECTION_TRIM_SECTOR_BREADTH_PCT,
            "projection_review_excess_pct": DEFAULT_PROJECTION_REVIEW_EXCESS_PCT,
            "projection_review_sector_breadth_pct": DEFAULT_PROJECTION_REVIEW_SECTOR_BREADTH_PCT,
            "projection_add_sector_breadth_pct": DEFAULT_PROJECTION_ADD_SECTOR_BREADTH_PCT,
            "projection_add_trend_quality": DEFAULT_PROJECTION_ADD_TREND_QUALITY,
        }
        judged_rows = [
            row for row in rows if str(row.get("verdict") or "") != "not_enough_time"
        ]
        min_judged = int(policy.get("projection_learning_min_judged_trades", 3) or 3)
        if not bool(policy.get("projection_learning_enabled", True)):
            return {
                "enabled": False,
                "active": False,
                "headline": "Adaptive projection tuning is turned off.",
                "judged_trades": len(judged_rows),
                "adjustments": [],
                "monitor_overrides": {},
                "baseline": baseline,
            }
        if len(judged_rows) < min_judged:
            return {
                "enabled": True,
                "active": False,
                "headline": (
                    "Atlas is still collecting enough judged projection outcomes "
                    "before retuning the paper monitor."
                ),
                "judged_trades": len(judged_rows),
                "adjustments": [],
                "monitor_overrides": {},
                "baseline": baseline,
            }

        supportive_stats = self._projection_driver_bucket(
            judged_rows,
            side="buy",
            codes={"projection_supported_add", "projection_continued_leadership"},
        )
        protective_stats = self._projection_driver_bucket(
            judged_rows,
            side="sell",
            codes={"projection_caution", "projection_needs_proof", "projection_de_risk"},
        )
        sell_trigger_stats = self._sell_trigger_bucket(
            judged_rows,
            codes={
                "confirmation_weakness",
                "confirmation_weakness__risk_flags",
                "risk_flags__confirmation_weakness",
                "thesis_risk__confirmation_weakness",
                "confirmation_weakness__thesis_risk",
                "confirmation_weakness__paper_learning_caution",
                "paper_learning_caution__confirmation_weakness",
            },
        )
        overrides = {}
        adjustments = []

        supportive_rate = supportive_stats.get("working_rate_pct")
        if supportive_stats["judged"] >= 2 and supportive_rate is not None:
            if supportive_rate <= 34.0:
                overrides["projection_add_sector_breadth_pct"] = min(
                    baseline["projection_add_sector_breadth_pct"] + 5.0,
                    75.0,
                )
                overrides["projection_add_trend_quality"] = min(
                    baseline["projection_add_trend_quality"] + 5.0,
                    85.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_add_sector_breadth_pct",
                            "label": "Winner-add breadth gate",
                            "direction": "tighter",
                            "from": baseline["projection_add_sector_breadth_pct"],
                            "to": overrides["projection_add_sector_breadth_pct"],
                            "reason": (
                                "Projection-led adds have been lagging, so Atlas now "
                                "demands broader sector participation before adding."
                            ),
                        },
                        {
                            "field": "projection_add_trend_quality",
                            "label": "Winner-add trend gate",
                            "direction": "tighter",
                            "from": baseline["projection_add_trend_quality"],
                            "to": overrides["projection_add_trend_quality"],
                            "reason": (
                                "Projection-led adds have been lagging, so Atlas now "
                                "demands stronger trend quality before adding."
                            ),
                        },
                    ]
                )
            elif supportive_rate >= 67.0 and supportive_stats["working"] >= 2:
                overrides["projection_add_sector_breadth_pct"] = max(
                    baseline["projection_add_sector_breadth_pct"] - 5.0,
                    50.0,
                )
                overrides["projection_add_trend_quality"] = max(
                    baseline["projection_add_trend_quality"] - 3.0,
                    65.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_add_sector_breadth_pct",
                            "label": "Winner-add breadth gate",
                            "direction": "looser",
                            "from": baseline["projection_add_sector_breadth_pct"],
                            "to": overrides["projection_add_sector_breadth_pct"],
                            "reason": (
                                "Projection-led adds have been confirming well, so "
                                "Atlas is allowing slightly earlier adds."
                            ),
                        },
                        {
                            "field": "projection_add_trend_quality",
                            "label": "Winner-add trend gate",
                            "direction": "looser",
                            "from": baseline["projection_add_trend_quality"],
                            "to": overrides["projection_add_trend_quality"],
                            "reason": (
                                "Projection-led adds have been confirming well, so "
                                "Atlas is allowing slightly less perfect trend posture."
                            ),
                        },
                    ]
                )

        protective_rate = protective_stats.get("working_rate_pct")
        if protective_stats["judged"] >= 2 and protective_rate is not None:
            if protective_rate >= 67.0 and protective_stats["working"] >= 2:
                overrides["projection_trim_excess_pct"] = min(
                    baseline["projection_trim_excess_pct"] + 0.5,
                    -1.5,
                )
                overrides["projection_trim_sector_breadth_pct"] = min(
                    baseline["projection_trim_sector_breadth_pct"] + 5.0,
                    45.0,
                )
                overrides["projection_review_excess_pct"] = min(
                    baseline["projection_review_excess_pct"] + 0.5,
                    1.0,
                )
                overrides["projection_review_sector_breadth_pct"] = min(
                    baseline["projection_review_sector_breadth_pct"] + 5.0,
                    55.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_trim_excess_pct",
                            "label": "Projection trim trigger",
                            "direction": "earlier",
                            "from": baseline["projection_trim_excess_pct"],
                            "to": overrides["projection_trim_excess_pct"],
                            "reason": (
                                "Projection caution sells have been helping, so Atlas "
                                "will trim a little earlier when confirmation breaks."
                            ),
                        },
                        {
                            "field": "projection_review_excess_pct",
                            "label": "Projection review trigger",
                            "direction": "earlier",
                            "from": baseline["projection_review_excess_pct"],
                            "to": overrides["projection_review_excess_pct"],
                            "reason": (
                                "Projection caution sells have been helping, so Atlas "
                                "will escalate weak confirmation reviews a little sooner."
                            ),
                        },
                    ]
                )
            elif protective_rate <= 34.0:
                overrides["projection_trim_excess_pct"] = max(
                    baseline["projection_trim_excess_pct"] - 0.5,
                    -4.0,
                )
                overrides["projection_trim_sector_breadth_pct"] = max(
                    baseline["projection_trim_sector_breadth_pct"] - 5.0,
                    25.0,
                )
                overrides["projection_review_excess_pct"] = max(
                    baseline["projection_review_excess_pct"] - 0.5,
                    -1.0,
                )
                overrides["projection_review_sector_breadth_pct"] = max(
                    baseline["projection_review_sector_breadth_pct"] - 5.0,
                    35.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_trim_excess_pct",
                            "label": "Projection trim trigger",
                            "direction": "slower",
                            "from": baseline["projection_trim_excess_pct"],
                            "to": overrides["projection_trim_excess_pct"],
                            "reason": (
                                "Projection caution sells have been too early, so "
                                "Atlas now waits for weaker confirmation before trimming."
                            ),
                        },
                        {
                            "field": "projection_review_excess_pct",
                            "label": "Projection review trigger",
                            "direction": "slower",
                            "from": baseline["projection_review_excess_pct"],
                            "to": overrides["projection_review_excess_pct"],
                            "reason": (
                                "Projection caution sells have been too early, so "
                                "Atlas now waits for more proof before escalating review."
                            ),
                        },
                    ]
                )

        sell_trigger_rate = sell_trigger_stats.get("working_rate_pct")
        if sell_trigger_stats["judged"] >= 2 and sell_trigger_rate is not None:
            if (
                sell_trigger_rate >= 67.0
                and sell_trigger_stats["working"] >= 2
                and "projection_trim_excess_pct" not in overrides
            ):
                overrides["projection_trim_excess_pct"] = min(
                    baseline["projection_trim_excess_pct"] + 0.5,
                    -1.5,
                )
                overrides["projection_trim_sector_breadth_pct"] = min(
                    baseline["projection_trim_sector_breadth_pct"] + 5.0,
                    45.0,
                )
                overrides["projection_review_excess_pct"] = min(
                    baseline["projection_review_excess_pct"] + 0.5,
                    1.0,
                )
                overrides["projection_review_sector_breadth_pct"] = min(
                    baseline["projection_review_sector_breadth_pct"] + 5.0,
                    55.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_trim_excess_pct",
                            "label": "Confirmation-weakness trim trigger",
                            "direction": "earlier",
                            "from": baseline["projection_trim_excess_pct"],
                            "to": overrides["projection_trim_excess_pct"],
                            "reason": (
                                "Confirmation-weakness trims have been helping, so Atlas "
                                "will de-risk a little earlier when leadership and breadth fade."
                            ),
                        },
                        {
                            "field": "projection_review_excess_pct",
                            "label": "Confirmation-weakness review trigger",
                            "direction": "earlier",
                            "from": baseline["projection_review_excess_pct"],
                            "to": overrides["projection_review_excess_pct"],
                            "reason": (
                                "Confirmation-weakness trims have been helping, so Atlas "
                                "will escalate review sooner when confirmation softens."
                            ),
                        },
                    ]
                )
            elif (
                sell_trigger_rate <= 34.0
                and "projection_trim_excess_pct" not in overrides
            ):
                overrides["projection_trim_excess_pct"] = max(
                    baseline["projection_trim_excess_pct"] - 0.5,
                    -4.0,
                )
                overrides["projection_trim_sector_breadth_pct"] = max(
                    baseline["projection_trim_sector_breadth_pct"] - 5.0,
                    25.0,
                )
                overrides["projection_review_excess_pct"] = max(
                    baseline["projection_review_excess_pct"] - 0.5,
                    -1.0,
                )
                overrides["projection_review_sector_breadth_pct"] = max(
                    baseline["projection_review_sector_breadth_pct"] - 5.0,
                    35.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_trim_excess_pct",
                            "label": "Confirmation-weakness trim trigger",
                            "direction": "slower",
                            "from": baseline["projection_trim_excess_pct"],
                            "to": overrides["projection_trim_excess_pct"],
                            "reason": (
                                "Confirmation-weakness trims have been too early, so Atlas "
                                "now waits for a clearer breakdown before trimming."
                            ),
                        },
                        {
                            "field": "projection_review_excess_pct",
                            "label": "Confirmation-weakness review trigger",
                            "direction": "slower",
                            "from": baseline["projection_review_excess_pct"],
                            "to": overrides["projection_review_excess_pct"],
                            "reason": (
                                "Confirmation-weakness trims have been too early, so Atlas "
                                "now waits for more proof before escalating review."
                            ),
                        },
                    ]
                )

        benchmark_scorecard = self._benchmark_scorecard_from_rows(rows)
        benchmark_exit_stats = self._benchmark_exit_bucket(
            benchmark_scorecard.get("scorecards") or []
        )
        benchmark_exit_rate = benchmark_exit_stats.get("working_rate_pct")
        if (
            benchmark_exit_stats["judged"] >= 2
            and benchmark_exit_rate is not None
            and "projection_trim_excess_pct" not in overrides
        ):
            if benchmark_exit_rate >= 67.0 and benchmark_exit_stats["working"] >= 2:
                overrides["projection_trim_excess_pct"] = min(
                    baseline["projection_trim_excess_pct"] + 0.5,
                    -1.5,
                )
                overrides["projection_trim_sector_breadth_pct"] = min(
                    baseline["projection_trim_sector_breadth_pct"] + 5.0,
                    45.0,
                )
                overrides["projection_review_excess_pct"] = min(
                    baseline["projection_review_excess_pct"] + 0.5,
                    1.0,
                )
                overrides["projection_review_sector_breadth_pct"] = min(
                    baseline["projection_review_sector_breadth_pct"] + 5.0,
                    55.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_trim_excess_pct",
                            "label": "Benchmark-scorecard trim trigger",
                            "direction": "earlier",
                            "from": baseline["projection_trim_excess_pct"],
                            "to": overrides["projection_trim_excess_pct"],
                            "reason": (
                                "Benchmark-specific sell scorecards show trims/exits "
                                f"helping versus {benchmark_exit_stats['benchmark']}, so Atlas "
                                "will de-risk a little earlier when confirmation breaks."
                            ),
                        },
                        {
                            "field": "projection_review_excess_pct",
                            "label": "Benchmark-scorecard review trigger",
                            "direction": "earlier",
                            "from": baseline["projection_review_excess_pct"],
                            "to": overrides["projection_review_excess_pct"],
                            "reason": (
                                "Benchmark-specific sell scorecards show trims/exits "
                                f"helping versus {benchmark_exit_stats['benchmark']}, so Atlas "
                                "will escalate review sooner when a holding starts lagging."
                            ),
                        },
                    ]
                )
            elif benchmark_exit_rate <= 34.0:
                overrides["projection_trim_excess_pct"] = max(
                    baseline["projection_trim_excess_pct"] - 0.5,
                    -4.0,
                )
                overrides["projection_trim_sector_breadth_pct"] = max(
                    baseline["projection_trim_sector_breadth_pct"] - 5.0,
                    25.0,
                )
                overrides["projection_review_excess_pct"] = max(
                    baseline["projection_review_excess_pct"] - 0.5,
                    -1.0,
                )
                overrides["projection_review_sector_breadth_pct"] = max(
                    baseline["projection_review_sector_breadth_pct"] - 5.0,
                    35.0,
                )
                adjustments.extend(
                    [
                        {
                            "field": "projection_trim_excess_pct",
                            "label": "Benchmark-scorecard trim trigger",
                            "direction": "slower",
                            "from": baseline["projection_trim_excess_pct"],
                            "to": overrides["projection_trim_excess_pct"],
                            "reason": (
                                "Benchmark-specific sell scorecards show trims/exits "
                                f"lagging versus {benchmark_exit_stats['benchmark']}, so Atlas "
                                "now waits for a clearer breakdown before trimming."
                            ),
                        },
                        {
                            "field": "projection_review_excess_pct",
                            "label": "Benchmark-scorecard review trigger",
                            "direction": "slower",
                            "from": baseline["projection_review_excess_pct"],
                            "to": overrides["projection_review_excess_pct"],
                            "reason": (
                                "Benchmark-specific sell scorecards show trims/exits "
                                f"lagging versus {benchmark_exit_stats['benchmark']}, so Atlas "
                                "now waits for more proof before escalating review."
                            ),
                        },
                    ]
                )

        if decision_driver_learning is None:
            decision_driver_learning = self._decision_driver_learning(
                self._decision_driver_stats(rows)
            )
        strongest = (
            decision_driver_learning[0]["label"] if decision_driver_learning else None
        )
        weakest = (
            decision_driver_learning[-1]["label"] if decision_driver_learning else None
        )
        if adjustments:
            headline = "Atlas is auto-retuning paper projection thresholds from observed trade outcomes."
        else:
            headline = "Atlas has enough judged projection evidence, but current thresholds remain in balance."
        if strongest and weakest and strongest != weakest:
            headline += f" Strongest read: {strongest}. Weakest read: {weakest}."
        return {
            "enabled": True,
            "active": bool(adjustments),
            "headline": headline,
            "judged_trades": len(judged_rows),
            "adjustments": adjustments[:4],
            "monitor_overrides": overrides,
            "baseline": baseline,
            "supportive_stats": supportive_stats,
            "protective_stats": protective_stats,
            "sell_trigger_stats": sell_trigger_stats,
            "benchmark_exit_stats": benchmark_exit_stats,
        }

    @staticmethod
    def _benchmark_exit_bucket(scorecards):
        usable = [
            item
            for item in scorecards
            if int(item.get("sell_judged") or 0) > 0
            and item.get("sell_working_rate_pct") is not None
        ]
        if not usable:
            return {
                "benchmark": None,
                "judged": 0,
                "working": 0,
                "mixed": 0,
                "lagging": 0,
                "working_rate_pct": None,
                "avg_decision_edge_pct": None,
            }
        best = max(
            usable,
            key=lambda item: (
                int(item.get("sell_judged") or 0),
                float(item.get("sell_avg_decision_edge_pct") or 0.0),
                float(item.get("sell_working_rate_pct") or 0.0),
            ),
        )
        return {
            "benchmark": best.get("benchmark"),
            "judged": int(best.get("sell_judged") or 0),
            "working": int(best.get("sell_working") or 0),
            "mixed": int(best.get("sell_mixed") or 0),
            "lagging": int(best.get("sell_lagging") or 0),
            "working_rate_pct": best.get("sell_working_rate_pct"),
            "avg_decision_edge_pct": best.get("sell_avg_decision_edge_pct"),
        }

    @staticmethod
    def _decision_driver_stats(rows):
        driver_stats = {}
        for row in rows:
            verdict = str(row.get("verdict") or "not_enough_time")
            driver = row.get("decision_driver") or {}
            driver_code = str(driver.get("code") or "").strip().lower()
            if not driver_code or verdict == "not_enough_time":
                continue
            stats = driver_stats.setdefault(
                driver_code,
                {
                    "code": driver_code,
                    "label": str(driver.get("label") or driver_code.replace("_", " ")),
                    "judged": 0,
                    "working": 0,
                    "mixed": 0,
                    "lagging": 0,
                },
            )
            stats["judged"] += 1
            if verdict == "working":
                stats["working"] += 1
            elif verdict == "mixed":
                stats["mixed"] += 1
            elif verdict == "lagging":
                stats["lagging"] += 1
        return driver_stats

    @staticmethod
    def _projection_driver_bucket(rows, *, side, codes):
        verdicts = {"judged": 0, "working": 0, "mixed": 0, "lagging": 0}
        for row in rows:
            if str(row.get("side") or "").strip().lower() != side:
                continue
            driver = row.get("decision_driver") or {}
            code = str(driver.get("code") or "").strip().lower()
            if code not in codes:
                continue
            verdict = str(row.get("verdict") or "").strip().lower()
            if verdict not in {"working", "mixed", "lagging"}:
                continue
            verdicts["judged"] += 1
            verdicts[verdict] += 1
        verdicts["working_rate_pct"] = (
            round((verdicts["working"] / verdicts["judged"]) * 100.0, 1)
            if verdicts["judged"]
            else None
        )
        return verdicts

    @staticmethod
    def _buy_learning_bucket(rows):
        verdicts = {"judged": 0, "working": 0, "mixed": 0, "lagging": 0}
        for row in rows:
            verdict = str(row.get("verdict") or "").strip().lower()
            if verdict not in {"working", "mixed", "lagging"}:
                continue
            verdicts["judged"] += 1
            verdicts[verdict] += 1
        verdicts["working_rate_pct"] = (
            round((verdicts["working"] / verdicts["judged"]) * 100.0, 1)
            if verdicts["judged"]
            else None
        )
        return verdicts

    @staticmethod
    def _buy_persistence_bucket(rows, *, snapshots):
        verdicts = {"judged": 0, "working": 0, "mixed": 0, "lagging": 0}
        target = int(snapshots or 0)
        for row in rows:
            for horizon in row.get("horizon_outcomes") or []:
                if not horizon.get("available"):
                    continue
                if int(horizon.get("snapshots") or 0) != target:
                    continue
                verdict = str(horizon.get("verdict") or "").strip().lower()
                if verdict not in {"working", "mixed", "lagging"}:
                    continue
                verdicts["judged"] += 1
                verdicts[verdict] += 1
                break
        verdicts["working_rate_pct"] = (
            round((verdicts["working"] / verdicts["judged"]) * 100.0, 1)
            if verdicts["judged"]
            else None
        )
        return verdicts

    @staticmethod
    def _sell_trigger_bucket(rows, *, codes):
        verdicts = {"judged": 0, "working": 0, "mixed": 0, "lagging": 0}
        allowed = {str(code or "").strip().lower() for code in codes or set()}
        for row in rows:
            if str(row.get("side") or "").strip().lower() != "sell":
                continue
            trigger = row.get("sell_trigger") or {}
            code = str(trigger.get("code") or "").strip().lower()
            if code not in allowed:
                continue
            verdict = str(row.get("verdict") or "").strip().lower()
            if verdict not in {"working", "mixed", "lagging"}:
                continue
            verdicts["judged"] += 1
            verdicts[verdict] += 1
        verdicts["working_rate_pct"] = (
            round((verdicts["working"] / verdicts["judged"]) * 100.0, 1)
            if verdicts["judged"]
            else None
        )
        return verdicts

    @staticmethod
    def _proposal_feedback_verdict(trade, security_return, benchmark_returns):
        side = str(trade.get("side") or "").lower()
        best_benchmark = max(benchmark_returns.values())
        worst_benchmark = min(benchmark_returns.values())
        if side == "buy":
            if security_return >= best_benchmark:
                return "working", "The simulated buy is ahead of both core benchmarks."
            if security_return < worst_benchmark:
                return "lagging", "The simulated buy is behind both core benchmarks."
            return "mixed", "The simulated buy is between the two core benchmarks."

        avoided_return = -float(security_return)
        if security_return <= worst_benchmark:
            return (
                "working",
                "Atlas's simulated sell is helping so far because the security fell after the exit or trim.",
            )
        if security_return > best_benchmark:
            return (
                "lagging",
                "Atlas's simulated sell looks early so far because the security outperformed after the exit or trim.",
            )
        if avoided_return > 0:
            return (
                "mixed",
                "Atlas avoided some post-sell weakness, but the result is mixed against the core benchmarks.",
            )
        return (
            "mixed",
            "Atlas gave up some upside after the sell, but the result is mixed against the core benchmarks.",
        )

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
            thesis = proposal.get("thesis") or trade.get("thesis")
            action_label = self._trade_action_label(trade, proposal)
            title, summary = self._trade_activity_text(trade, proposal)
            rows.append(
                {
                    "trade_id": trade.get("trade_id"),
                    "proposal_id": trade.get("proposal_id"),
                    "timestamp": trade.get("timestamp"),
                    "ticker": trade.get("ticker"),
                    "side": trade.get("side"),
                    "action_label": action_label,
                    "shares": trade.get("shares"),
                    "fill_price": trade.get("price"),
                    "realized_gain_loss": trade.get("realized_gain_loss"),
                    "title": title,
                    "summary": summary,
                    "thesis": thesis,
                    "rationale": rationale,
                    "risk_review": proposal.get("risk_review"),
                    "decision_driver": infer_decision_driver(
                        list(rationale) + [thesis],
                        side=trade.get("side"),
                        action_label=action_label,
                    ),
                    "news_event_summary": self._news_event_summary(
                        thesis=thesis,
                        rationale=rationale,
                    ),
                }
            )
        return rows

    def accountability_report(self):
        """Return an accountant-friendly transaction and basis report."""
        account = self.load()
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
        positions = account.get("positions", {})
        adaptive_regime = self._accountability_adaptive_regime()
        grouped = {}

        for trade in trades:
            ticker = str(trade.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            proposal = proposals.get(trade.get("proposal_id"), {})
            recommendation = recommendations.get(trade.get("recommendation_id"), {})
            rationale = proposal.get("rationale") or recommendation.get("rationale") or []
            action_label = self._trade_action_label(trade, {})
            shares = float(trade.get("shares") or 0.0)
            fill_price = float(trade.get("price") or 0.0)
            notional = float(trade.get("notional") or round(shares * fill_price, 2))
            realized = float(trade.get("realized_gain_loss") or 0.0)
            if trade.get("side") == "buy":
                basis_per_share = fill_price
                basis_amount = notional
                proceeds = None
            else:
                proceeds = notional
                basis_amount = proceeds - realized
                basis_per_share = (basis_amount / shares) if shares else None

            row = {
                "trade_id": trade.get("trade_id"),
                "timestamp": trade.get("timestamp"),
                "side": trade.get("side"),
                "action_label": action_label,
                "shares": shares,
                "fill_price": fill_price,
                "gross_amount": round(notional, 2),
                "basis_per_share": round(basis_per_share, 4) if basis_per_share is not None else None,
                "basis_amount": round(basis_amount, 2),
                "proceeds": round(proceeds, 2) if proceeds is not None else None,
                "realized_gain_loss": round(realized, 2),
                "position_shares_before": float(trade.get("position_shares_before") or 0.0),
                "position_shares_after": float(trade.get("position_shares_after") or 0.0),
                "source": trade.get("source"),
                "thesis": trade.get("thesis"),
                "decision_driver": infer_decision_driver(
                    list(rationale) + [proposal.get("thesis") or trade.get("thesis")],
                    side=trade.get("side"),
                    action_label=action_label,
                ),
                "news_event_summary": self._news_event_summary(
                    thesis=proposal.get("thesis") or trade.get("thesis"),
                    rationale=rationale,
                ),
                "adaptive_regime": adaptive_regime,
            }
            grouped.setdefault(ticker, []).append(row)

        ticker_rows = []
        total_buy_basis = 0.0
        total_sale_proceeds = 0.0
        total_realized = 0.0

        for ticker, rows in grouped.items():
            buy_shares = sum(item["shares"] for item in rows if item["side"] == "buy")
            sell_shares = sum(item["shares"] for item in rows if item["side"] == "sell")
            total_buy_basis += sum(item["basis_amount"] for item in rows if item["side"] == "buy")
            total_sale_proceeds += sum((item.get("proceeds") or 0.0) for item in rows if item["side"] == "sell")
            total_realized += sum(item["realized_gain_loss"] for item in rows if item["side"] == "sell")
            open_position = positions.get(ticker, {})
            open_shares = float(open_position.get("shares") or 0.0)
            average_cost = float(open_position.get("average_cost") or 0.0) if open_shares else None
            open_basis = round(open_shares * average_cost, 2) if open_shares and average_cost is not None else 0.0
            ticker_rows.append(
                {
                    "ticker": ticker,
                    "buy_shares": round(buy_shares, 4),
                    "sell_shares": round(sell_shares, 4),
                    "open_shares": round(open_shares, 4),
                    "average_cost": round(average_cost, 4) if average_cost is not None else None,
                    "open_basis": open_basis,
                    "realized_gain_loss": round(
                        sum(item["realized_gain_loss"] for item in rows if item["side"] == "sell"),
                        2,
                    ),
                    "latest_timestamp": rows[-1].get("timestamp"),
                    "transactions": rows,
                }
            )

        ticker_rows.sort(
            key=lambda item: (
                str(item.get("latest_timestamp") or ""),
                str(item.get("ticker") or ""),
            ),
            reverse=True,
        )
        open_positions = sum(1 for item in ticker_rows if item["open_shares"] > 0)
        return {
            "generated_at": account.get("updated_at") or account.get("created_at"),
            "accounting_method": "weighted_average_cost",
            "summary": {
                "tickers": len(ticker_rows),
                "open_positions": open_positions,
                "transactions": sum(len(item["transactions"]) for item in ticker_rows),
                "total_buy_basis": round(total_buy_basis, 2),
                "total_sale_proceeds": round(total_sale_proceeds, 2),
                "total_realized_gain_loss": round(total_realized, 2),
                "total_open_basis": round(sum(item["open_basis"] for item in ticker_rows), 2),
            },
            "tickers": ticker_rows,
        }

    def _accountability_adaptive_regime(self):
        try:
            feedback_summary = self.proposal_feedback_summary()
        except ValueError:
            return ""
        trade_pressure = feedback_summary.get("trade_pressure_profile") or {}
        benchmark_preference = feedback_summary.get("benchmark_preference_profile") or {}
        pieces = []
        trade_cap = trade_pressure.get("policy_overrides", {}).get(
            "maximum_daily_trades",
            trade_pressure.get("baseline", {}).get("maximum_daily_trades"),
        )
        if trade_cap is not None:
            state = "active" if trade_pressure.get("active") else "watching"
            pieces.append(f"daily trade cap {trade_cap} ({state})")
        benchmark_bar = str(
            benchmark_preference.get("strategy_overrides", {}).get(
                "strategy_preferred_benchmark",
                benchmark_preference.get("baseline", {}).get(
                    "strategy_preferred_benchmark",
                    "auto",
                ),
            )
        ).upper()
        if benchmark_bar:
            state = "active" if benchmark_preference.get("active") else "watching"
            pieces.append(f"benchmark trust {benchmark_bar} ({state})")
        return "; ".join(pieces)

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
    def _snapshots_from(snapshots, timestamp):
        return [
            snapshot
            for snapshot in snapshots
            if str(snapshot.get("timestamp", "")) >= str(timestamp)
        ]

    @classmethod
    def _feedback_horizon_outcomes(cls, trade, snapshots):
        ticker = str(trade.get("ticker") or "").strip().upper()
        trade_price = trade.get("price")
        rows = []
        filtered = cls._snapshots_from(snapshots, trade.get("timestamp"))
        for horizon in (1, 3, 5):
            if len(filtered) < horizon:
                rows.append(
                    {
                        "label": f"{horizon}-snapshot",
                        "snapshots": horizon,
                        "available": False,
                    }
                )
                continue
            snapshot = filtered[horizon - 1]
            security_price = snapshot.get("security_prices", {}).get(ticker)
            security_return = cls._pct_return(trade_price, security_price)
            benchmark_returns = {
                benchmark: cls._pct_return(
                    filtered[0].get("benchmark_prices", {}).get(benchmark),
                    snapshot.get("benchmark_prices", {}).get(benchmark),
                )
                for benchmark in ("SPY", "QQQ")
            }
            usable_benchmarks = {
                name: value
                for name, value in benchmark_returns.items()
                if value is not None
            }
            if security_return is None or not usable_benchmarks:
                rows.append(
                    {
                        "label": f"{horizon}-snapshot",
                        "snapshots": horizon,
                        "available": False,
                    }
                )
                continue
            verdict, summary = cls._proposal_feedback_verdict(
                trade=trade,
                security_return=security_return,
                benchmark_returns=usable_benchmarks,
            )
            rows.append(
                {
                    "label": f"{horizon}-snapshot",
                    "snapshots": horizon,
                    "available": True,
                    "security_return_pct": security_return,
                    "benchmark_returns_pct": benchmark_returns,
                    "verdict": verdict,
                    "summary": summary,
                }
            )
        return rows

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
        horizon_outcomes=None,
        rationale=None,
    ):
        action_label = PaperTradingAccount._trade_action_label(trade, proposal)
        thesis = proposal.get("thesis") or trade.get("thesis")
        rationale = rationale if rationale is not None else proposal.get("rationale") or []
        return {
            "proposal_id": trade.get("proposal_id"),
            "ticker": trade.get("ticker"),
            "side": trade.get("side"),
            "action_label": action_label,
            "shares": trade.get("shares"),
            "filled_at": trade.get("timestamp"),
            "fill_price": trade.get("price"),
            "latest_price": latest_price,
            "security_return_pct": security_return,
            "benchmark_returns_pct": benchmark_returns or {},
            "snapshots": snapshots,
            "horizon_outcomes": horizon_outcomes or [],
            "verdict": verdict,
            "summary": summary,
            "thesis": thesis,
            "decision_driver": infer_decision_driver(
                list(rationale) + [thesis],
                side=trade.get("side"),
                action_label=action_label,
            ),
            "sell_trigger": PaperTradingAccount._sell_trigger_learning_tag(
                proposal,
                action_label=action_label,
            ),
            "sector_gate": PaperTradingAccount._sector_gate_learning_tag(rationale),
        }

    @staticmethod
    def _sector_gate_learning_tag(rationale):
        for item in rationale or []:
            line = str(item or "").strip()
            if not line.startswith("Sector learning gate:"):
                continue
            lower_line = line.lower()
            if "cleared" in lower_line:
                status = "cleared"
                label = "Cleared sector gate"
            elif "tightened" in lower_line:
                status = "tightened"
                label = "Tightened sector gate"
            elif "constructive" in lower_line or "boost" in lower_line:
                status = "boost"
                label = "Constructive sector boost"
            else:
                status = "watch"
                label = "Sector gate"
            return {
                "status": status,
                "label": label,
                "rationale": line,
            }
        return None

    @staticmethod
    def _best_benchmark_edge(row):
        security_return = row.get("security_return_pct")
        benchmark_returns = row.get("benchmark_returns_pct") or {}
        usable = [
            float(value)
            for value in benchmark_returns.values()
            if value is not None
        ]
        if security_return is None or not usable:
            return None
        return float(security_return) - max(usable)

    @staticmethod
    def _sell_trigger_learning_tag(proposal, *, action_label="sell"):
        action_label = str(action_label or "").strip().lower()
        if action_label not in {"trim", "exit", "sell"}:
            return None
        proposal = proposal or {}
        review = proposal.get("risk_review") or {}
        flags = [
            str(flag).strip()
            for flag in review.get("flags") or []
            if str(flag).strip()
        ]
        texts = [
            str(proposal.get("thesis") or "").strip(),
            *[str(item).strip() for item in proposal.get("rationale") or []],
            *flags,
        ]
        combined = " ".join(texts).lower()

        parts = []
        if "risk to thesis" in combined or "thesis weak" in combined or "thesis deterioration" in combined:
            parts.append(("thesis_risk", "Thesis risk"))
        if flags:
            parts.append(("risk_flags", "Risk flags"))
        if (
            "projection caution" in combined
            or "projection de-risk" in combined
            or "benchmark lag" in combined
            or "trend posture" in combined
            or "sector breadth" in combined
            or "confirmation weakness" in combined
            or "latest move is -" in combined
            or "defensive posture" in combined
        ):
            parts.append(("confirmation_weakness", "Confirmation weakness"))
        if (
            re.search(r"score\s+\d", combined)
            or "score weakness" in combined
            or "weak score" in combined
            or "avoid" in combined
        ):
            parts.append(("score_pressure", "Score pressure"))
        if "paper learning" in combined or "paper-learning caution" in combined:
            parts.append(("paper_learning_caution", "Paper learning caution"))

        if not parts:
            label = "General sell review"
            if action_label == "trim":
                label = "General trim review"
            elif action_label == "exit":
                label = "General exit review"
            return {
                "code": f"{action_label}_general_review",
                "label": label,
                "summary": (
                    "Atlas recorded a sell decision without a more specific trigger family "
                    "yet."
                ),
            }

        parts = parts[:2]
        return {
            "code": "__".join(code for code, _label in parts),
            "label": " + ".join(label for _code, label in parts),
            "summary": (
                "Atlas is learning how this sell-trigger pattern performs across judged "
                "simulated trims and exits."
            ),
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

    @staticmethod
    def _completed_position_outcomes(trades):
        """Aggregate realized gain/loss across each fully closed position cycle."""
        active = {}
        outcomes = []
        for event in trades:
            ticker = str(event.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            side = str(event.get("side") or "").strip().lower()
            before = float(event.get("position_shares_before") or 0.0)
            after = float(event.get("position_shares_after") or 0.0)
            if side == "buy":
                if ticker not in active or before <= 0.0000001:
                    active[ticker] = {
                        "ticker": ticker,
                        "opened_at": event.get("timestamp"),
                        "realized_gain_loss": 0.0,
                        "sell_executions": 0,
                    }
                continue
            if side != "sell":
                continue
            cycle = active.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "opened_at": None,
                    "realized_gain_loss": 0.0,
                    "sell_executions": 0,
                },
            )
            cycle["realized_gain_loss"] += float(
                event.get("realized_gain_loss") or 0.0
            )
            cycle["sell_executions"] += 1
            if after <= 0.0000001:
                outcomes.append(
                    {
                        **cycle,
                        "closed_at": event.get("timestamp"),
                        "realized_gain_loss": round(
                            cycle["realized_gain_loss"],
                            2,
                        ),
                    }
                )
                active.pop(ticker, None)
        return outcomes

    @staticmethod
    def _days_between(start, end):
        if not start or not end:
            return None
        try:
            elapsed = datetime.fromisoformat(str(end)) - datetime.fromisoformat(str(start))
        except (TypeError, ValueError):
            return None
        return round(max(elapsed.total_seconds(), 0.0) / 86400.0, 1)

    @classmethod
    def completed_position_diagnostics(cls, trades):
        """Explain entry, response, and execution patterns for closed paper cycles."""
        active = {}
        cycles = []
        for event in trades:
            ticker = str(event.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            side = str(event.get("side") or "").strip().lower()
            before = float(event.get("position_shares_before") or 0.0)
            after = float(event.get("position_shares_after") or 0.0)
            shares = float(event.get("shares") or 0.0)
            price = float(event.get("price") or 0.0)
            notional = float(event.get("notional") or round(shares * price, 2))

            if side == "buy":
                if ticker not in active or before <= 0.0000001:
                    thesis = str(event.get("thesis") or "")
                    move_match = re.search(
                        r"current move(?: is)?\s*([+-]?\d+(?:\.\d+)?)%",
                        thesis,
                        flags=re.IGNORECASE,
                    ) or re.search(
                        r"([+-]?\d+(?:\.\d+)?)%\s*current move",
                        thesis,
                        flags=re.IGNORECASE,
                    )
                    active[ticker] = {
                        "ticker": ticker,
                        "opened_at": event.get("timestamp"),
                        "entry_move_pct": (
                            float(move_match.group(1)) if move_match else None
                        ),
                        "buy_shares": 0.0,
                        "buy_notional": 0.0,
                        "sell_shares": 0.0,
                        "sell_proceeds": 0.0,
                        "realized_gain_loss": 0.0,
                        "sells": [],
                    }
                cycle = active[ticker]
                cycle["buy_shares"] += shares
                cycle["buy_notional"] += notional
                continue

            if side != "sell" or ticker not in active:
                continue
            cycle = active[ticker]
            cycle["sell_shares"] += shares
            cycle["sell_proceeds"] += notional
            cycle["realized_gain_loss"] += float(
                event.get("realized_gain_loss") or 0.0
            )
            cycle["sells"].append(event)
            if after > 0.0000001:
                continue

            entry_price = (
                cycle["buy_notional"] / cycle["buy_shares"]
                if cycle["buy_shares"]
                else None
            )
            average_exit_price = (
                cycle["sell_proceeds"] / cycle["sell_shares"]
                if cycle["sell_shares"]
                else None
            )
            first_sell = cycle["sells"][0]
            first_sell_price = float(first_sell.get("price") or 0.0)
            first_action_return = (
                ((first_sell_price / entry_price) - 1.0) * 100.0
                if entry_price and first_sell_price
                else None
            )
            realized_return = (
                (cycle["realized_gain_loss"] / cycle["buy_notional"]) * 100.0
                if cycle["buy_notional"]
                else None
            )
            entry_move = cycle.get("entry_move_pct")
            if entry_move is not None and entry_move <= -4.0:
                entry_finding = (
                    f"Entered during a sharp {entry_move:+.1f}% daily decline, "
                    "which increased timing risk."
                )
                entry_status = "caution"
            else:
                entry_finding = (
                    "The recorded daily move did not indicate an unusually sharp "
                    "entry-day dislocation."
                )
                entry_status = "neutral"
            if first_action_return is not None and first_action_return <= -3.0:
                response_finding = (
                    "Atlas first acted defensively after the position was already "
                    f"down {abs(first_action_return):.1f}%."
                )
                response_status = "caution"
            else:
                response_finding = (
                    "Atlas began its defensive response before a 3% position loss "
                    "was visible."
                )
                response_status = "neutral"
            sell_executions = len(cycle["sells"])
            if sell_executions > 2:
                execution_finding = (
                    f"The exit was fragmented across {sell_executions} sell "
                    "executions, extending the decision path."
                )
                execution_status = "caution"
            else:
                execution_finding = (
                    f"The position closed in {sell_executions} sell execution"
                    f"{'' if sell_executions == 1 else 's'}."
                )
                execution_status = "neutral"

            cycles.append(
                {
                    "ticker": ticker,
                    "opened_at": cycle["opened_at"],
                    "closed_at": event.get("timestamp"),
                    "holding_days": cls._days_between(
                        cycle["opened_at"],
                        event.get("timestamp"),
                    ),
                    "days_to_first_risk_action": cls._days_between(
                        cycle["opened_at"],
                        first_sell.get("timestamp"),
                    ),
                    "entry_price": round(entry_price, 2) if entry_price else None,
                    "average_exit_price": (
                        round(average_exit_price, 2)
                        if average_exit_price
                        else None
                    ),
                    "entry_move_pct": entry_move,
                    "first_risk_action_return_pct": (
                        round(first_action_return, 2)
                        if first_action_return is not None
                        else None
                    ),
                    "realized_return_pct": (
                        round(realized_return, 2)
                        if realized_return is not None
                        else None
                    ),
                    "realized_gain_loss": round(
                        cycle["realized_gain_loss"],
                        2,
                    ),
                    "sell_executions": sell_executions,
                    "partial_trims": max(sell_executions - 1, 0),
                    "entry": {
                        "status": entry_status,
                        "finding": entry_finding,
                    },
                    "risk_response": {
                        "status": response_status,
                        "finding": response_finding,
                    },
                    "execution": {
                        "status": execution_status,
                        "finding": execution_finding,
                    },
                }
            )
            active.pop(ticker, None)

        losses = [
            cycle for cycle in cycles if cycle.get("realized_gain_loss", 0.0) < 0
        ]
        late_responses = [
            cycle
            for cycle in losses
            if (cycle.get("first_risk_action_return_pct") or 0.0) <= -3.0
        ]
        sharp_decline_entries = [
            cycle
            for cycle in losses
            if cycle.get("entry_move_pct") is not None
            and cycle["entry_move_pct"] <= -4.0
        ]
        fragmented_exits = [
            cycle for cycle in losses if cycle.get("sell_executions", 0) > 2
        ]
        average_loss = (
            sum(cycle["realized_return_pct"] for cycle in losses)
            / len(losses)
            if losses
            else None
        )
        average_holding = (
            sum(cycle["holding_days"] for cycle in cycles)
            / len(cycles)
            if cycles
            else None
        )
        if losses and len(late_responses) == len(losses):
            headline = (
                "Every completed loss was already down at least 3% before "
                "Atlas first acted defensively."
            )
            primary_finding = (
                "The strongest shared signal is late risk response, not a single "
                "sector or security-selection conclusion."
            )
        elif losses:
            headline = (
                "Completed losses show a mix of entry timing and exit-discipline "
                "weakness."
            )
            primary_finding = (
                "Atlas needs more completed cycles before one pattern can be "
                "treated as dominant."
            )
        else:
            headline = "Atlas does not yet have a completed losing position to diagnose."
            primary_finding = "Continue collecting completed paper-position evidence."
        return {
            "available": bool(cycles),
            "sample_size": len(cycles),
            "losses": len(losses),
            "headline": headline,
            "primary_finding": primary_finding,
            "average_loss_pct": round(average_loss, 2) if average_loss is not None else None,
            "average_holding_days": (
                round(average_holding, 1) if average_holding is not None else None
            ),
            "late_risk_responses": len(late_responses),
            "sharp_decline_entries": len(sharp_decline_entries),
            "fragmented_exits": len(fragmented_exits),
            "sample_warning": (
                f"Only {len(cycles)} completed position"
                f"{'' if len(cycles) == 1 else 's'} are available. Treat these "
                "patterns as early diagnostic evidence, not a proven strategy conclusion."
            ),
            "cycles": list(reversed(cycles)),
        }

    @staticmethod
    def _snapshot_security_price(snapshot, ticker):
        value = (snapshot.get("security_prices") or {}).get(ticker)
        if value is not None:
            return float(value)
        for position in snapshot.get("positions") or []:
            if (
                str(position.get("ticker") or "").strip().upper() == ticker
                and position.get("price") is not None
            ):
                return float(position["price"])
        return None

    @classmethod
    def shadow_defensive_trigger_analysis(cls, trades, snapshots):
        """Compare earlier defensive triggers without changing paper policy."""
        active = {}
        cycles = []
        for event in trades:
            ticker = str(event.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            side = str(event.get("side") or "").strip().lower()
            before = float(event.get("position_shares_before") or 0.0)
            after = float(event.get("position_shares_after") or 0.0)
            shares = float(event.get("shares") or 0.0)
            price = float(event.get("price") or 0.0)
            notional = float(event.get("notional") or round(shares * price, 2))
            if side == "buy":
                if ticker not in active or before <= 0.0000001:
                    active[ticker] = {
                        "ticker": ticker,
                        "opened_at": event.get("timestamp"),
                        "buy_shares": 0.0,
                        "buy_notional": 0.0,
                        "realized_gain_loss": 0.0,
                        "closed": False,
                    }
                active[ticker]["buy_shares"] += shares
                active[ticker]["buy_notional"] += notional
                continue
            if side != "sell" or ticker not in active:
                continue
            active[ticker]["realized_gain_loss"] += float(
                event.get("realized_gain_loss") or 0.0
            )
            if after <= 0.0000001:
                active[ticker]["closed"] = True
                active[ticker]["closed_at"] = event.get("timestamp")
                cycles.append(active.pop(ticker))
        cycles.extend(active.values())

        candidates = [
            {
                "id": "early_review",
                "label": "Earlier review signal",
                "loss_threshold_pct": -2.0,
                "lag_threshold_pct": -3.0,
                "action": "Review only",
            },
            {
                "id": "automatic_full_exit",
                "label": "Earlier automatic full exit",
                "loss_threshold_pct": -3.0,
                "lag_threshold_pct": -3.0,
                "action": "Hypothetical full exit",
            },
        ]
        results = []
        ordered_snapshots = sorted(
            snapshots,
            key=lambda snapshot: str(snapshot.get("timestamp") or ""),
        )
        for candidate in candidates:
            triggered = []
            for cycle in cycles:
                entry_price = (
                    cycle["buy_notional"] / cycle["buy_shares"]
                    if cycle["buy_shares"]
                    else None
                )
                if not entry_price:
                    continue
                cycle_snapshots = []
                for snapshot in ordered_snapshots:
                    timestamp = str(snapshot.get("timestamp") or "")
                    if timestamp < str(cycle.get("opened_at") or ""):
                        continue
                    if (
                        cycle.get("closed")
                        and timestamp > str(cycle.get("closed_at") or "")
                    ):
                        continue
                    security_price = cls._snapshot_security_price(
                        snapshot,
                        cycle["ticker"],
                    )
                    if security_price is not None:
                        cycle_snapshots.append((snapshot, security_price))
                if not cycle_snapshots:
                    continue
                baseline = cycle_snapshots[0][0]
                trigger = None
                for snapshot, security_price in cycle_snapshots:
                    security_return = cls._pct_return(
                        entry_price,
                        security_price,
                    )
                    benchmark_returns = []
                    for benchmark in ("SPY", "QQQ"):
                        benchmark_return = cls._pct_return(
                            (baseline.get("benchmark_prices") or {}).get(
                                benchmark
                            ),
                            (snapshot.get("benchmark_prices") or {}).get(
                                benchmark
                            ),
                        )
                        if benchmark_return is not None:
                            benchmark_returns.append(benchmark_return)
                    if security_return is None or not benchmark_returns:
                        continue
                    benchmark_lag = round(
                        security_return - max(benchmark_returns),
                        2,
                    )
                    if (
                        security_return
                        <= candidate["loss_threshold_pct"]
                        and benchmark_lag
                        <= candidate["lag_threshold_pct"]
                    ):
                        trigger = {
                            "timestamp": snapshot.get("timestamp"),
                            "price": security_price,
                            "security_return_pct": security_return,
                            "benchmark_lag_pct": benchmark_lag,
                        }
                        break
                if trigger is None:
                    continue
                latest_price = cycle_snapshots[-1][1]
                recovered_after_trigger = latest_price > trigger["price"]
                shadow_gain_loss = round(
                    (cycle["buy_shares"] * trigger["price"])
                    - cycle["buy_notional"],
                    2,
                )
                triggered.append(
                    {
                        "ticker": cycle["ticker"],
                        "closed": bool(cycle.get("closed")),
                        "triggered_at": trigger["timestamp"],
                        "trigger_return_pct": trigger["security_return_pct"],
                        "benchmark_lag_pct": trigger["benchmark_lag_pct"],
                        "recovered_after_trigger": recovered_after_trigger,
                        "shadow_gain_loss": shadow_gain_loss,
                        "actual_gain_loss": (
                            round(cycle["realized_gain_loss"], 2)
                            if cycle.get("closed")
                            else None
                        ),
                    }
                )
            completed = [row for row in triggered if row["closed"]]
            recovered = [
                row for row in triggered if row["recovered_after_trigger"]
            ]
            actual_completed = round(
                sum(row["actual_gain_loss"] for row in completed),
                2,
            )
            shadow_completed = round(
                sum(row["shadow_gain_loss"] for row in completed),
                2,
            )
            improvement = round(shadow_completed - actual_completed, 2)
            recovery_rate = (
                round((len(recovered) / len(triggered)) * 100.0, 1)
                if triggered
                else 0.0
            )
            if candidate["id"] == "early_review":
                decision = "study"
                decision_label = "Keep as review-only candidate"
                conclusion = (
                    "The earlier warning may help Atlas investigate weakness "
                    "sooner, but recovery risk argues against automatic selling."
                )
            else:
                supported = improvement > 0 and recovery_rate < 25.0
                decision = "support" if supported else "reject"
                decision_label = (
                    "Candidate supported"
                    if supported
                    else "Do not adopt"
                )
                conclusion = (
                    "The automatic exit candidate improved completed outcomes "
                    "without excessive recovery risk."
                    if supported
                    else "The automatic exit candidate did not improve the "
                    "completed sample reliably and would risk selling recoveries."
                )
            results.append(
                {
                    **candidate,
                    "decision": decision,
                    "decision_label": decision_label,
                    "conclusion": conclusion,
                    "triggered_cycles": len(triggered),
                    "completed_cycles": len(completed),
                    "recovered_cycles": len(recovered),
                    "recovery_rate_pct": recovery_rate,
                    "actual_completed_gain_loss": actual_completed,
                    "shadow_completed_gain_loss": shadow_completed,
                    "completed_improvement": improvement,
                    "cycles": triggered,
                }
            )

        automatic_exit = next(
            (
                result
                for result in results
                if result["id"] == "automatic_full_exit"
            ),
            {},
        )
        return {
            "available": bool(cycles and snapshots),
            "mode": "shadow_only",
            "policy_changed": False,
            "headline": (
                "Earlier review deserves more study; earlier automatic exit "
                "is not supported."
            ),
            "decision": "No live strategy change",
            "detail": (
                "Atlas replayed earlier loss and benchmark-lag triggers against "
                "recorded snapshots. The comparison is observational and cannot "
                "place or alter a paper trade."
            ),
            "automatic_exit_improvement": automatic_exit.get(
                "completed_improvement"
            ),
            "automatic_exit_recovery_rate_pct": automatic_exit.get(
                "recovery_rate_pct"
            ),
            "sample_warning": (
                f"The replay covers {len(cycles)} observed holding cycle"
                f"{'' if len(cycles) == 1 else 's'}, including "
                f"{sum(1 for cycle in cycles if cycle.get('closed'))} completed. "
                "Continue collecting evidence before changing policy."
            ),
            "candidates": results,
        }

    @classmethod
    def prospective_defensive_review_tracker(cls, events):
        """Track review-only defensive signals recorded after study activation."""
        marker = next(
            (
                event
                for event in events
                if event.get("event") == "defensive_review_tracking_started"
            ),
            None,
        )
        transitions = [
            event
            for event in events
            if event.get("event") == "defensive_review_signal"
        ]
        if marker is None:
            return {
                "available": True,
                "activated": False,
                "mode": "review_only",
                "policy_changed": False,
                "headline": "Prospective tracking begins with the next scheduled snapshot.",
                "detail": (
                    "Atlas will start a clean forward-only study without "
                    "relabeling earlier paper history."
                ),
                "loss_threshold_pct": DEFENSIVE_REVIEW_LOSS_THRESHOLD_PCT,
                "lag_threshold_pct": DEFENSIVE_REVIEW_LAG_THRESHOLD_PCT,
                "started_at": None,
                "transition_count": 0,
                "recent_transition_count": 0,
                "recent_transitions": [],
                "counts": {
                    "total": 0,
                    "active": 0,
                    "persistent_weakness": 0,
                    "recovered": 0,
                    "completed_loss": 0,
                    "completed_gain": 0,
                },
                "signals": [],
            }

        trades = [
            event for event in events if event.get("event") == "paper_trade"
        ]
        snapshots = sorted(
            [
                event
                for event in events
                if event.get("event") == "performance_snapshot"
            ],
            key=lambda snapshot: str(snapshot.get("timestamp") or ""),
        )
        active = {}
        cycles = []
        for trade in trades:
            ticker = str(trade.get("ticker") or "").strip().upper()
            side = str(trade.get("side") or "").strip().lower()
            if not ticker:
                continue
            before = float(trade.get("position_shares_before") or 0.0)
            after = float(trade.get("position_shares_after") or 0.0)
            shares = float(trade.get("shares") or 0.0)
            price = float(trade.get("price") or 0.0)
            notional = float(
                trade.get("notional") or round(shares * price, 2)
            )
            if side == "buy":
                if ticker not in active or before <= 0.0000001:
                    opened_at = str(trade.get("timestamp") or "")
                    active[ticker] = {
                        "signal_id": "review_"
                        + re.sub(r"[^a-zA-Z0-9]+", "_", f"{ticker}_{opened_at}")
                        .strip("_")
                        .lower(),
                        "ticker": ticker,
                        "opened_at": opened_at,
                        "buy_shares": 0.0,
                        "buy_notional": 0.0,
                        "realized_gain_loss": 0.0,
                        "closed": False,
                    }
                active[ticker]["buy_shares"] += shares
                active[ticker]["buy_notional"] += notional
                continue
            if side != "sell" or ticker not in active:
                continue
            active[ticker]["realized_gain_loss"] += float(
                trade.get("realized_gain_loss") or 0.0
            )
            if after <= 0.0000001:
                active[ticker]["closed"] = True
                active[ticker]["closed_at"] = str(
                    trade.get("timestamp") or ""
                )
                cycles.append(active.pop(ticker))
        cycles.extend(active.values())

        marker_timestamp = str(marker.get("timestamp") or "")
        signals = []
        for cycle in cycles:
            entry_price = (
                cycle["buy_notional"] / cycle["buy_shares"]
                if cycle["buy_shares"]
                else None
            )
            if not entry_price:
                continue
            cycle_snapshots = []
            for snapshot in snapshots:
                timestamp = str(snapshot.get("timestamp") or "")
                if timestamp < cycle["opened_at"]:
                    continue
                if cycle.get("closed") and timestamp > cycle["closed_at"]:
                    continue
                price = cls._snapshot_security_price(
                    snapshot,
                    cycle["ticker"],
                )
                if price is not None:
                    cycle_snapshots.append((snapshot, price))
            if not cycle_snapshots:
                continue
            baseline = cycle_snapshots[0][0]

            def observation(snapshot, security_price):
                security_return = cls._pct_return(
                    entry_price,
                    security_price,
                )
                snapshot_benchmark_prices = {}
                benchmark_returns = []
                for benchmark in ("SPY", "QQQ"):
                    benchmark_price = (
                        snapshot.get("benchmark_prices") or {}
                    ).get(benchmark)
                    benchmark_return = cls._pct_return(
                        (baseline.get("benchmark_prices") or {}).get(
                            benchmark
                        ),
                        benchmark_price,
                    )
                    if benchmark_return is not None:
                        benchmark_returns.append(benchmark_return)
                    if benchmark_price is not None:
                        snapshot_benchmark_prices[benchmark] = float(
                            benchmark_price
                        )
                if security_return is None or not benchmark_returns:
                    return None
                return {
                    "timestamp": snapshot.get("timestamp"),
                    "price": security_price,
                    "benchmark_prices": snapshot_benchmark_prices,
                    "return_pct": round(security_return, 4),
                    "lag_pct": round(
                        security_return - max(benchmark_returns),
                        2,
                    ),
                }

            observed = [
                value
                for snapshot, price in cycle_snapshots
                if str(snapshot.get("timestamp") or "") >= marker_timestamp
                for value in [observation(snapshot, price)]
                if value is not None
            ]
            trigger_index = next(
                (
                    index
                    for index, value in enumerate(observed)
                    if value["return_pct"]
                    <= DEFENSIVE_REVIEW_LOSS_THRESHOLD_PCT
                    and value["lag_pct"]
                    <= DEFENSIVE_REVIEW_LAG_THRESHOLD_PCT
                ),
                None,
            )
            if trigger_index is None:
                continue
            trigger = observed[trigger_index]
            after_trigger = observed[trigger_index:]
            latest = after_trigger[-1]
            post_trigger_moves = [
                cls._pct_return(trigger["price"], value["price"])
                for value in after_trigger
            ]
            post_trigger_moves = [
                round(value, 4)
                for value in post_trigger_moves
                if value is not None
            ]
            benchmark_relative_observations = []
            for value in after_trigger:
                benchmark_moves = {}
                for benchmark in ("SPY", "QQQ"):
                    benchmark_move = cls._pct_return(
                        (trigger.get("benchmark_prices") or {}).get(
                            benchmark
                        ),
                        (value.get("benchmark_prices") or {}).get(
                            benchmark
                        ),
                    )
                    if benchmark_move is not None:
                        benchmark_moves[benchmark] = round(
                            benchmark_move,
                            4,
                        )
                security_move = cls._pct_return(
                    trigger["price"],
                    value["price"],
                )
                if security_move is None or not benchmark_moves:
                    continue
                comparison_benchmark = max(
                    benchmark_moves,
                    key=benchmark_moves.get,
                )
                comparison_move = benchmark_moves[comparison_benchmark]
                benchmark_relative_observations.append(
                    {
                        "timestamp": value.get("timestamp"),
                        "benchmark_returns_pct": benchmark_moves,
                        "comparison_benchmark": comparison_benchmark,
                        "comparison_benchmark_move_pct": comparison_move,
                        "benchmark_relative_move_pct": round(
                            security_move - comparison_move,
                            4,
                        ),
                    }
                )
            latest_benchmark_relative = (
                benchmark_relative_observations[-1]
                if benchmark_relative_observations
                else {}
            )
            benchmark_relative_moves = [
                value["benchmark_relative_move_pct"]
                for value in benchmark_relative_observations
            ]
            latest_relative_move = latest_benchmark_relative.get(
                "benchmark_relative_move_pct"
            )
            if latest_relative_move is None:
                benchmark_attribution_label = "Benchmark comparison unavailable"
            elif latest_relative_move <= -2.0:
                benchmark_attribution_label = "Lagged stronger benchmark"
            elif latest_relative_move >= 2.0:
                benchmark_attribution_label = "Outpaced stronger benchmark"
            else:
                benchmark_attribution_label = "Moved near stronger benchmark"
            recovered = any(
                value["timestamp"] != trigger["timestamp"]
                and value["price"] > trigger["price"]
                for value in after_trigger
            )
            if cycle.get("closed"):
                status = (
                    "completed_loss"
                    if cycle["realized_gain_loss"] < 0
                    else "completed_gain"
                )
            elif recovered:
                status = "recovered"
            elif len(after_trigger) >= 3:
                status = "persistent_weakness"
            else:
                status = "active"
            status_labels = {
                "active": "New review",
                "persistent_weakness": "Weakness persists",
                "recovered": "Recovered above trigger",
                "completed_loss": "Completed loss",
                "completed_gain": "Completed gain",
            }
            signals.append(
                {
                    "signal_id": cycle["signal_id"],
                    "ticker": cycle["ticker"],
                    "status": status,
                    "status_label": status_labels[status],
                    "triggered_at": trigger["timestamp"],
                    "trigger_price": round(trigger["price"], 4),
                    "trigger_return_pct": trigger["return_pct"],
                    "trigger_lag_pct": trigger["lag_pct"],
                    "latest_at": latest["timestamp"],
                    "latest_price": round(latest["price"], 4),
                    "latest_return_pct": latest["return_pct"],
                    "latest_lag_pct": latest["lag_pct"],
                    "post_trigger_move_pct": (
                        post_trigger_moves[-1]
                        if post_trigger_moves
                        else None
                    ),
                    "worst_post_trigger_move_pct": (
                        min(post_trigger_moves)
                        if post_trigger_moves
                        else None
                    ),
                    "best_post_trigger_move_pct": (
                        max(post_trigger_moves)
                        if post_trigger_moves
                        else None
                    ),
                    "post_trigger_benchmark_returns_pct": (
                        latest_benchmark_relative.get(
                            "benchmark_returns_pct"
                        )
                        or {}
                    ),
                    "comparison_benchmark": latest_benchmark_relative.get(
                        "comparison_benchmark"
                    ),
                    "comparison_benchmark_move_pct": (
                        latest_benchmark_relative.get(
                            "comparison_benchmark_move_pct"
                        )
                    ),
                    "benchmark_relative_move_pct": latest_relative_move,
                    "worst_benchmark_relative_move_pct": (
                        min(benchmark_relative_moves)
                        if benchmark_relative_moves
                        else None
                    ),
                    "best_benchmark_relative_move_pct": (
                        max(benchmark_relative_moves)
                        if benchmark_relative_moves
                        else None
                    ),
                    "benchmark_attribution_label": (
                        benchmark_attribution_label
                    ),
                    "snapshots_observed": len(after_trigger),
                    "realized_gain_loss": (
                        round(cycle["realized_gain_loss"], 2)
                        if cycle.get("closed")
                        else None
                    ),
                }
            )

        status_order = {
            "persistent_weakness": 0,
            "active": 1,
            "completed_loss": 2,
            "recovered": 3,
            "completed_gain": 4,
        }
        signals.sort(
            key=lambda item: (
                status_order.get(item["status"], 9),
                str(item.get("triggered_at") or ""),
            )
        )
        counts = {
            "total": len(signals),
            "active": 0,
            "persistent_weakness": 0,
            "recovered": 0,
            "completed_loss": 0,
            "completed_gain": 0,
        }
        for signal in signals:
            counts[signal["status"]] += 1
        latest_snapshot_timestamps = {
            str(snapshot.get("timestamp") or "")
            for snapshot in snapshots[-3:]
        }
        latest_transition_by_signal = {}
        for transition in transitions:
            signal_id = str(transition.get("signal_id") or "")
            if signal_id:
                latest_transition_by_signal[signal_id] = transition
        transition_priority = {
            "completed_loss": 0,
            "persistent_weakness": 1,
            "active": 2,
            "recovered": 3,
            "completed_gain": 4,
        }
        recent_transitions = sorted(
            [
                {
                    "signal_id": transition.get("signal_id"),
                    "ticker": transition.get("ticker"),
                    "status": transition.get("status"),
                    "status_label": transition.get("status_label"),
                    "timestamp": transition.get("timestamp"),
                    "latest_return_pct": transition.get(
                        "latest_return_pct"
                    ),
                    "latest_lag_pct": transition.get("latest_lag_pct"),
                    "snapshots_observed": transition.get(
                        "snapshots_observed"
                    ),
                }
                for transition in latest_transition_by_signal.values()
                if str(transition.get("timestamp") or "")
                in latest_snapshot_timestamps
            ],
            key=lambda item: (
                transition_priority.get(item.get("status"), 9),
                str(item.get("timestamp") or ""),
            ),
        )[:4]
        headline = (
            f"Atlas is following {len(signals)} prospective review signal"
            f"{'' if len(signals) == 1 else 's'}."
            if signals
            else "No prospective review signals have appeared yet."
        )
        return {
            "available": True,
            "activated": True,
            "mode": "review_only",
            "policy_changed": False,
            "headline": headline,
            "detail": (
                "Signals are observations only. Atlas records persistence, "
                "recovery, and completed outcomes without forcing a sale."
            ),
            "loss_threshold_pct": DEFENSIVE_REVIEW_LOSS_THRESHOLD_PCT,
            "lag_threshold_pct": DEFENSIVE_REVIEW_LAG_THRESHOLD_PCT,
            "started_at": marker.get("timestamp"),
            "transition_count": len(transitions),
            "recent_transition_count": len(recent_transitions),
            "recent_transitions": recent_transitions,
            "counts": counts,
            "signals": signals,
        }

    def _sync_prospective_defensive_review_events(self):
        tracker = self.prospective_defensive_review_tracker(self.ledger())
        prior = {}
        for event in self.ledger():
            if event.get("event") == "defensive_review_signal":
                prior[event.get("signal_id")] = event
        for signal in tracker.get("signals") or []:
            previous = prior.get(signal["signal_id"])
            if previous and previous.get("status") == signal["status"]:
                continue
            self._append_event(
                {
                    "event": "defensive_review_signal",
                    "timestamp": signal["latest_at"],
                    "mode": "review_only",
                    "policy_changed": False,
                    **signal,
                }
            )

    @staticmethod
    def prospective_review_effectiveness(tracker):
        """Score forward review signals only after conservative evidence gates."""
        signals = list(tracker.get("signals") or [])
        counts = tracker.get("counts") or {}
        confirmed_weakness = int(
            counts.get("persistent_weakness") or 0
        ) + int(counts.get("completed_loss") or 0)
        false_alarms = int(counts.get("recovered") or 0) + int(
            counts.get("completed_gain") or 0
        )
        resolved = confirmed_weakness + false_alarms
        completed = int(counts.get("completed_loss") or 0) + int(
            counts.get("completed_gain") or 0
        )
        confirmation_rate = (
            round((confirmed_weakness / resolved) * 100.0, 1)
            if resolved
            else None
        )
        false_alarm_rate = (
            round((false_alarms / resolved) * 100.0, 1)
            if resolved
            else None
        )
        outcome_rows = []
        for signal in signals:
            status = str(signal.get("status") or "")
            if status in {"persistent_weakness", "completed_loss"}:
                classification = "confirmed_weakness"
                classification_label = "Warning confirmed"
            elif status in {"recovered", "completed_gain"}:
                classification = "false_alarm"
                classification_label = "Recovery / false alarm"
            else:
                continue
            outcome_rows.append(
                {
                    "signal_id": signal.get("signal_id"),
                    "ticker": signal.get("ticker"),
                    "status": status,
                    "status_label": signal.get("status_label"),
                    "classification": classification,
                    "classification_label": classification_label,
                    "post_trigger_move_pct": signal.get(
                        "post_trigger_move_pct"
                    ),
                    "worst_post_trigger_move_pct": signal.get(
                        "worst_post_trigger_move_pct"
                    ),
                    "best_post_trigger_move_pct": signal.get(
                        "best_post_trigger_move_pct"
                    ),
                    "comparison_benchmark": signal.get(
                        "comparison_benchmark"
                    ),
                    "comparison_benchmark_move_pct": signal.get(
                        "comparison_benchmark_move_pct"
                    ),
                    "benchmark_relative_move_pct": signal.get(
                        "benchmark_relative_move_pct"
                    ),
                    "worst_benchmark_relative_move_pct": signal.get(
                        "worst_benchmark_relative_move_pct"
                    ),
                    "best_benchmark_relative_move_pct": signal.get(
                        "best_benchmark_relative_move_pct"
                    ),
                    "benchmark_attribution_label": signal.get(
                        "benchmark_attribution_label"
                    ),
                    "snapshots_observed": int(
                        signal.get("snapshots_observed") or 0
                    ),
                }
            )

        def average_metric(rows, field):
            values = [
                float(row[field])
                for row in rows
                if row.get(field) is not None
            ]
            return round(sum(values) / len(values), 2) if values else None

        confirmed_rows = [
            row
            for row in outcome_rows
            if row["classification"] == "confirmed_weakness"
        ]
        false_alarm_rows = [
            row
            for row in outcome_rows
            if row["classification"] == "false_alarm"
        ]
        confirmed_avg_move = average_metric(
            confirmed_rows,
            "post_trigger_move_pct",
        )
        false_alarm_avg_move = average_metric(
            false_alarm_rows,
            "post_trigger_move_pct",
        )
        outcome_separation = (
            round(false_alarm_avg_move - confirmed_avg_move, 2)
            if confirmed_avg_move is not None
            and false_alarm_avg_move is not None
            else None
        )
        confirmed_avg_relative_move = average_metric(
            confirmed_rows,
            "benchmark_relative_move_pct",
        )
        false_alarm_avg_relative_move = average_metric(
            false_alarm_rows,
            "benchmark_relative_move_pct",
        )
        benchmark_adjusted_separation = (
            round(
                false_alarm_avg_relative_move
                - confirmed_avg_relative_move,
                2,
            )
            if confirmed_avg_relative_move is not None
            and false_alarm_avg_relative_move is not None
            else None
        )
        outcome_comparison = {
            "confirmed_avg_post_trigger_move_pct": confirmed_avg_move,
            "confirmed_avg_worst_post_trigger_move_pct": average_metric(
                confirmed_rows,
                "worst_post_trigger_move_pct",
            ),
            "false_alarm_avg_post_trigger_move_pct": false_alarm_avg_move,
            "false_alarm_avg_best_post_trigger_move_pct": average_metric(
                false_alarm_rows,
                "best_post_trigger_move_pct",
            ),
            "outcome_separation_pct": outcome_separation,
            "confirmed_avg_benchmark_relative_move_pct": (
                confirmed_avg_relative_move
            ),
            "false_alarm_avg_benchmark_relative_move_pct": (
                false_alarm_avg_relative_move
            ),
            "benchmark_adjusted_separation_pct": (
                benchmark_adjusted_separation
            ),
        }
        minimum_resolved = 10
        minimum_completed = 5
        resolved_progress = min(
            100.0,
            round((resolved / minimum_resolved) * 100.0, 1),
        )
        completed_progress = min(
            100.0,
            round((completed / minimum_completed) * 100.0, 1),
        )
        evidence_progress = round(
            (resolved_progress + completed_progress) / 2.0,
            1,
        )
        gates = [
            {
                "id": "resolved_signals",
                "label": "Resolved signals",
                "passed": resolved >= minimum_resolved,
                "current": resolved,
                "target": minimum_resolved,
                "progress_pct": resolved_progress,
            },
            {
                "id": "completed_outcomes",
                "label": "Completed outcomes",
                "passed": completed >= minimum_completed,
                "current": completed,
                "target": minimum_completed,
                "progress_pct": completed_progress,
            },
            {
                "id": "confirmation_quality",
                "label": "Weakness confirmation",
                "passed": (
                    resolved >= minimum_resolved
                    and confirmation_rate is not None
                    and confirmation_rate >= 65.0
                ),
                "current": confirmation_rate,
                "target": 65.0,
                "progress_pct": (
                    min(
                        100.0,
                        round((confirmation_rate / 65.0) * 100.0, 1),
                    )
                    if confirmation_rate is not None
                    else 0.0
                ),
            },
        ]
        ready = all(gate["passed"] for gate in gates)
        if not tracker.get("activated"):
            status = "waiting_activation"
            status_label = "Waiting for first snapshot"
            headline = "The forward study has not started yet."
            next_action = (
                "Let the next scheduled paper snapshot establish the study "
                "boundary."
            )
        elif resolved == 0:
            status = "collecting"
            status_label = "Collecting evidence"
            headline = "No review signals have reached an outcome yet."
            next_action = (
                "Keep the scheduled paper cycle running until signals persist, "
                "recover, or complete."
            )
        elif ready:
            status = "owner_review_eligible"
            status_label = "Eligible for owner review"
            headline = (
                "The forward sample has cleared the minimum evidence gates."
            )
            next_action = (
                "Review the signal with the owner before considering any paper "
                "policy change."
            )
        else:
            status = "early_sample"
            status_label = "Early sample"
            headline = (
                f"{resolved} resolved signal"
                f"{'' if resolved == 1 else 's'} are not enough for a policy "
                "decision."
            )
            next_action = (
                "Continue collecting outcomes; do not change the paper policy."
            )
        return {
            "available": True,
            "activated": bool(tracker.get("activated")),
            "mode": "evidence_only",
            "policy_changed": False,
            "ready_for_owner_review": ready,
            "status": status,
            "status_label": status_label,
            "headline": headline,
            "detail": (
                "Confirmed weakness combines persistent signals and completed "
                "losses. False alarms combine recoveries and completed gains."
            ),
            "signal_count": len(signals),
            "resolved_signals": resolved,
            "confirmed_weakness": confirmed_weakness,
            "false_alarms": false_alarms,
            "completed_outcomes": completed,
            "confirmation_rate_pct": confirmation_rate,
            "false_alarm_rate_pct": false_alarm_rate,
            "outcome_comparison": outcome_comparison,
            "outcomes": outcome_rows,
            "evidence_progress_pct": evidence_progress,
            "minimum_resolved_signals": minimum_resolved,
            "minimum_completed_outcomes": minimum_completed,
            "gates": gates,
            "next_action": next_action,
        }

    def trade_statistics(self):
        events = self.ledger()
        trades = [event for event in events if event.get("event") == "paper_trade"]
        recommendations = [
            event for event in events if event.get("event") == "paper_recommendation"
        ]
        sell_executions = [
            event
            for event in trades
            if event.get("side") == "sell"
        ]
        partial_trims = [
            event
            for event in sell_executions
            if float(event.get("position_shares_after") or 0.0) > 0.0000001
        ]
        completed_outcomes = self._completed_position_outcomes(trades)
        wins = [
            outcome
            for outcome in completed_outcomes
            if outcome.get("realized_gain_loss", 0) > 0
        ]
        losses = [
            outcome
            for outcome in completed_outcomes
            if outcome.get("realized_gain_loss", 0) < 0
        ]
        profitable_sales = [
            event
            for event in sell_executions
            if event.get("realized_gain_loss", 0) > 0
        ]
        losing_sales = [
            event
            for event in sell_executions
            if event.get("realized_gain_loss", 0) < 0
        ]
        linked = [event for event in trades if event.get("recommendation_id")]
        proposal_linked = [event for event in trades if event.get("proposal_id")]
        total_buy_notional = sum(
            float(event.get("notional") or 0.0)
            for event in trades
            if event.get("side") == "buy"
        )
        total_sell_notional = sum(
            float(event.get("notional") or 0.0)
            for event in trades
            if event.get("side") == "sell"
        )
        feedback = self.proposal_feedback_summary()
        judged = int(feedback.get("judged") or 0)
        judged_working = int(feedback.get("verdict_counts", {}).get("working") or 0)
        judged_sells = int(feedback.get("judged_side_counts", {}).get("sell") or 0)
        judged_sell_working = int(feedback.get("working_side_counts", {}).get("sell") or 0)
        account = self.load()
        starting_cash = float(account.get("starting_cash") or 0.0)
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
            "sell_executions": len(sell_executions),
            "partial_trims": len(partial_trims),
            "realized_exits": len(completed_outcomes),
            "completed_positions": len(completed_outcomes),
            "completed_outcomes": completed_outcomes,
            "wins": len(wins),
            "losses": len(losses),
            "profitable_sales": len(profitable_sales),
            "losing_sales": len(losing_sales),
            "total_buy_notional": round(total_buy_notional, 2),
            "total_sell_notional": round(total_sell_notional, 2),
            "gross_turnover_notional": round(total_buy_notional + total_sell_notional, 2),
            "turnover_pct": (
                round(((total_buy_notional + total_sell_notional) / starting_cash) * 100.0, 1)
                if starting_cash
                else None
            ),
            "judged_trade_working_rate_pct": (
                round((judged_working / judged) * 100.0, 1)
                if judged
                else None
            ),
            "judged_sell_help_rate_pct": (
                round((judged_sell_working / judged_sells) * 100.0, 1)
                if judged_sells
                else None
            ),
            "win_rate_pct": (
                len(wins) / len(completed_outcomes) * 100
                if completed_outcomes
                else None
            ),
        }

    def render_performance_report(self):
        summary = self.performance_summary()
        validation = self.stage5_validation_summary()
        feedback = self.proposal_feedback_summary()
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

        lines.extend(
            [
                "",
                "## Stage 5 Validation",
                "",
                f"- **Status**: {validation['status_label']}",
                f"- **Headline**: {validation['headline']}",
                f"- **Evidence**: {validation['detail']}",
                "",
            ]
        )
        for card in validation.get("scorecards", []):
            lines.append(
                f"- **{card['label']}**: {card['value']} ({card['detail']})"
            )
        if validation.get("takeaways"):
            lines.extend(
                [
                    "",
                    "### Validation Takeaways",
                    "",
                ]
            )
            for takeaway in validation["takeaways"]:
                lines.append(f"- {takeaway}")

        lines.extend(
            [
                "",
                "## Adaptive Learning Profiles",
                "",
            ]
        )
        profile_sections = [
            ("Entry pacing", feedback.get("entry_strategy_profile") or {}),
            ("Projection tuning", feedback.get("projection_threshold_profile") or {}),
            ("Daily trade pressure", feedback.get("trade_pressure_profile") or {}),
            ("Benchmark trust", feedback.get("benchmark_preference_profile") or {}),
        ]
        for label, profile in profile_sections:
            status = "Active" if profile.get("active") else "Watching"
            lines.append(f"- **{label}**: {status}")
            if profile.get("headline"):
                lines.append(f"  - {profile['headline']}")
            for item in profile.get("adjustments") or []:
                lines.append(
                    f"  - {item.get('label', 'Adjustment')}: "
                    f"{item.get('from', '--')} -> {item.get('to', '--')} "
                    f"({item.get('reason', 'Atlas adjusted this from judged outcomes.')})"
                )
        lines.append("")
        benchmark_scorecard = feedback.get("benchmark_scorecard") or {}
        if benchmark_scorecard.get("enabled"):
            lines.extend(
                [
                    "## Benchmark-Specific Decision Scorecard",
                    "",
                    benchmark_scorecard.get(
                        "headline",
                        "Atlas is tracking benchmark-specific paper decision evidence.",
                    ),
                    "",
                    "| Benchmark | Judged | Working | Mixed | Lagging | Avg Decision Edge |",
                    "|-----------|--------|---------|-------|---------|-------------------|",
                ]
            )
            for item in benchmark_scorecard.get("scorecards") or []:
                edge = item.get("avg_decision_edge_pct")
                edge_text = "--" if edge is None else f"{edge:+.2f}%"
                lines.append(
                    f"| {item.get('benchmark', '--')} | {item.get('judged', 0)} | "
                    f"{item.get('working', 0)} | {item.get('mixed', 0)} | "
                    f"{item.get('lagging', 0)} | {edge_text} |"
                )
            lines.append("")

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
                f"- **Gross Buy Notional**: ${stats['total_buy_notional']:,.2f}",
                f"- **Gross Sell Notional**: ${stats['total_sell_notional']:,.2f}",
                (
                    f"- **Gross Turnover**: {stats['turnover_pct']:.1f}% of starting paper capital"
                    if stats["turnover_pct"] is not None
                    else "- **Gross Turnover**: N/A"
                ),
                (
                    f"- **Judged Trade Working Rate**: {stats['judged_trade_working_rate_pct']:.1f}%"
                    if stats["judged_trade_working_rate_pct"] is not None
                    else "- **Judged Trade Working Rate**: N/A"
                ),
                (
                    f"- **Judged Sell Help Rate**: {stats['judged_sell_help_rate_pct']:.1f}%"
                    if stats["judged_sell_help_rate_pct"] is not None
                    else "- **Judged Sell Help Rate**: N/A"
                ),
                "",
                "## Recent Execution Context",
                "",
            ]
        )
        activity = self.trade_activity(limit=6)
        if not activity:
            lines.extend(["No recent simulated trade activity is available.", ""])
        else:
            lines.extend(
                [
                    "| Time | Ticker | Action | Driver | News Event | Thesis |",
                    "|------|--------|--------|--------|------------|--------|",
                ]
            )
            for item in activity:
                timestamp = str(item.get("timestamp") or "").replace("T", " ")
                lines.append(
                    f"| {timestamp} | {item.get('ticker', '')} | "
                    f"{str(item.get('action_label') or '').title()} | "
                    f"{str(((item.get('decision_driver') or {}).get('label')) or 'None').replace('|', '/')} | "
                    f"{str(item.get('news_event_summary') or 'No specific news event recorded').replace('|', '/')} | "
                    f"{str(item.get('thesis') or 'N/A').replace('|', '/')} |"
                )
            lines.append("")

        lines.extend(
            [
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

    @staticmethod
    def _news_event_summary(*, thesis=None, rationale=None):
        sources = []
        if thesis:
            sources.append(str(thesis))
        for item in rationale or []:
            if item:
                sources.append(str(item))
        patterns = (
            r"dominant event(?: is| as)? ([a-z0-9 /-]+?)(?:\.|,|$)",
            r"main event read: ([a-z0-9 /-]+?)(?:\.|,|$)",
            r"led by ([a-z0-9 /-]+?)(?:\.|,|$)",
        )
        for text in sources:
            for pattern in patterns:
                match = re.search(pattern, str(text).strip(), flags=re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return ""

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
            self._ledger_cache_signature = None
            self._ledger_cache = []
            return []
        stat = self.ledger_file.stat()
        signature = (stat.st_mtime_ns, stat.st_size)
        if signature == self._ledger_cache_signature:
            return self._ledger_cache
        events = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        self._ledger_cache_signature = signature
        self._ledger_cache = events
        return self._ledger_cache

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
        ][:10]

    def _validate_order(self, account, order, now=None):
        errors = []
        warnings = []
        policy = dict(account.get("policy", self.policy))
        pressure_profile = self.trade_pressure_profile()
        policy.update(pressure_profile.get("policy_overrides", {}))
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
        self._ledger_cache_signature = None
