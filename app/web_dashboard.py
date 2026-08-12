"""Read-only local web dashboard for Atlas Web Phase 1."""

from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from datetime import datetime
from urllib.parse import urlparse

from app.data_quality import daily_movement_summary, has_reliable_daily_change
from app.decision_driver import infer_decision_driver
from app.paper_strategy import PaperStrategy
from app.paper_trading import PaperTradingAccount
from app.paths import data_path, project_path
from app.research_tasks import ResearchTaskQueue
from app.tenant_store import SCHEMA_VERSION


WEB_DIR = project_path("web")
DEFAULT_ARCHIVE_DIR = data_path("research_archive")
DEFAULT_REPORTS_DIR = data_path("reports")
REPORT_ID_PATTERN = re.compile(
    r"^(morning_brief|weekly_summary)_(\d{8})_(\d{6})$"
)
UNSAFE_REPORT_HTML = re.compile(
    r"<\s*(script|iframe|object|embed|form)\b|"
    r"<\s*meta\b[^>]*http-equiv|"
    r"\son[a-z]+\s*=|javascript\s*:",
    re.IGNORECASE,
)

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class DashboardDataService:
    """Build a browser-safe read model from local Atlas artifacts."""

    def __init__(
        self,
        archive_dir=DEFAULT_ARCHIVE_DIR,
        reports_dir=DEFAULT_REPORTS_DIR,
        paper_account=None,
        research_queue=None,
    ):
        self.archive_dir = Path(archive_dir)
        self.reports_dir = Path(reports_dir)
        self.paper_account = paper_account or PaperTradingAccount()
        self.research_queue = research_queue or ResearchTaskQueue()

    def build(self):
        snapshot = self._latest_snapshot()
        securities = snapshot.get("securities", {})
        available = {
            ticker: data
            for ticker, data in securities.items()
            if data.get("status") == "available"
        }
        return {
            "generated_at": snapshot.get("generated_at"),
            "market": self._market(snapshot.get("market_summary", {})),
            "overview": self._overview(securities, available),
            "movers": self._movers(available),
            "score_leaders": self._score_leaders(available),
            "watchlist": self._watchlist(available),
            "sectors": self._sectors(available),
            "corporate_actions": self._corporate_actions(available),
            "paper": self._paper(available, include_details=True),
            "research": self._research(),
            "reports": self._reports(),
            "history": self._history(),
            "access": self._access(),
            "workspace": self._workspace(),
        }

    def build_summary(self):
        snapshot = self._latest_snapshot()
        securities = snapshot.get("securities", {})
        available = {
            ticker: data
            for ticker, data in securities.items()
            if data.get("status") == "available"
        }
        return {
            "generated_at": snapshot.get("generated_at"),
            "market": self._market(snapshot.get("market_summary", {})),
            "overview": self._overview(securities, available),
            "paper": self._paper(available, include_details=False),
            "research": self._research(include_tasks=False),
            "reports": self._reports(),
            "history": self._history(),
            "workspace": self._workspace(),
        }

    def build_verification(self):
        """Build only the fields needed by the token-protected smoke contract."""
        snapshot = self._latest_snapshot()
        securities = snapshot.get("securities", {})
        available = {
            ticker: data
            for ticker, data in securities.items()
            if data.get("status") == "available"
        }
        paper = self._paper(available, include_details=False)
        if paper.get("configured"):
            prices = {
                ticker: data.get("price")
                for ticker, data in available.items()
                if data.get("price") is not None
            }
            feedback_rows = self.paper_account.proposal_feedback(latest_prices=prices)
            feedback_summary = dict(paper.get("feedback_summary") or {})
            benchmark_scorecard = self.paper_account._benchmark_scorecard_from_rows(
                feedback_rows
            )
            entry_profile = self.paper_account._entry_strategy_profile_from_rows(
                feedback_rows
            )
            projection_profile = (
                self.paper_account._projection_threshold_profile_from_rows(
                    feedback_rows
                )
            )
            scorecards = benchmark_scorecard.get("scorecards") or []
            entry_profile.setdefault(
                "benchmark_rotation_stats",
                self.paper_account._benchmark_rotation_bucket(scorecards),
            )
            projection_profile.setdefault(
                "benchmark_exit_stats",
                self.paper_account._benchmark_exit_bucket(scorecards),
            )
            feedback_summary["benchmark_scorecard"] = benchmark_scorecard
            feedback_summary["entry_strategy_profile"] = entry_profile
            feedback_summary["projection_threshold_profile"] = projection_profile
            feedback_summary["sector_learning_bridge"] = (
                PaperStrategy.sector_learning_summary_from_feedback(
                    feedback_rows,
                    available,
                )
            )
            feedback_summary["sector_gate_audit"] = PaperStrategy.sector_gate_audit(
                self.paper_account,
                available,
            )
            feedback_summary.setdefault(
                "sector_gate_outcomes",
                {
                    "enabled": True,
                    "active": False,
                    "headline": (
                        "Atlas is waiting for judged accepted sector-gate buys."
                    ),
                    "scorecards": [],
                    "leader": None,
                },
            )
            paper["feedback_summary"] = feedback_summary
            paper["feedback"] = feedback_rows[:12]
            paper["capital_rotation_scoreboard"] = self._capital_rotation_scoreboard(
                paper.get("positions") or [],
                available,
                feedback_summary,
                paper.get("equity"),
                feedback_rows,
            )
            paper["accountability_report"] = self.paper_account.accountability_report()
        return {
            "generated_at": snapshot.get("generated_at"),
            "paper": paper,
            "workspace": self._workspace(),
        }

    @staticmethod
    def _workspace():
        revision = os.getenv("K_REVISION", "").strip()
        service = os.getenv("K_SERVICE", "").strip()
        return {
            "deployment": {
                "revision": revision or "local-preview",
                "service": service or "local-dashboard",
                "mode": "cloud" if revision or service else "local",
            }
        }

    def _access(self):
        return {
            "mode": "owner_only",
            "public_registration": False,
            "roles": ["Owner"],
            "schema_version": SCHEMA_VERSION,
            "tenant_isolation": "Single-owner private workspace",
            "identity_binding": "Verified Google subject and email",
            "audit_log": "Research and paper decisions retained",
            "threat_model": "Documented control matrix",
            "recovery": "Integrity-checked restore drill",
            "privacy_export": "Secret-free tenant package",
            "account_deletion": "Future member accounts disabled",
            "production_review": (
                "Owner profile active; public release remains gated"
            ),
            "phase_completion": 78,
            "next_step": "Operate and validate the owner workspace",
            "owner_validation": [
                {
                    "id": "cross_device_owner_login",
                    "label": "Cross-device owner login",
                    "status": "pending",
                    "detail": (
                        "Confirm Joe can sign in from a second trusted device."
                    ),
                },
                {
                    "id": "non_owner_denial",
                    "label": "Non-owner account denial",
                    "status": "pending",
                    "detail": (
                        "Confirm a different Google account is denied access."
                    ),
                },
            ],
        }

    def _latest_snapshot(self):
        files = sorted(self.archive_dir.glob("snapshot_*.json"), reverse=True)
        if not files:
            return {"securities": {}, "market_summary": {}}
        return self._read_json(files[0]) or {"securities": {}, "market_summary": {}}

    def _market(self, market_summary):
        return [
            {
                "ticker": ticker,
                "price": data.get("price"),
                "change": data.get("change"),
                "percent_change": data.get("percent_change"),
            }
            for ticker, data in sorted(market_summary.items())
        ]

    def _overview(self, securities, available):
        positive = sum(
            1
            for data in available.values()
            if (data.get("percent_change") or 0) > 0
        )
        negative = sum(
            1
            for data in available.values()
            if (data.get("percent_change") or 0) < 0
        )
        return {
            "tracked": len(securities),
            "available": len(available),
            "advancing": positive,
            "declining": negative,
            "daily_change_quality": daily_movement_summary(available),
        }

    def _movers(self, available):
        rows = [
            {
                "ticker": ticker,
                "company_name": data.get("company_name", ticker),
                "sector": data.get("sector", "Unclassified"),
                "price": data.get("price"),
                "percent_change": data.get("percent_change"),
            }
            for ticker, data in available.items()
            if has_reliable_daily_change(data)
        ]
        return sorted(
            rows,
            key=lambda item: abs(item["percent_change"]),
            reverse=True,
        )[:8]

    def _score_leaders(self, available):
        rows = [
            self._score_model(ticker, data)
            for ticker, data in available.items()
            if data.get("total_score") is not None
            and data.get("sector") != "Benchmark ETF"
        ]
        return sorted(rows, key=lambda item: item["score"], reverse=True)[:8]

    def _watchlist(self, available):
        rows = [
            self._score_model(ticker, data)
            for ticker, data in available.items()
        ]
        return sorted(
            rows,
            key=lambda item: (
                str(item.get("category") or ""),
                str(item.get("sector") or ""),
                str(item.get("ticker") or ""),
            ),
        )

    @staticmethod
    def _score_model(ticker, data):
        profile = data.get("profile") or {}
        scores = data.get("scores") or {}
        return {
            "ticker": ticker,
            "company_name": data.get("company_name", ticker),
            "sector": data.get("sector", "Unclassified"),
            "category": data.get("category", "Watchlist"),
            "score": data.get("total_score"),
            "percent_change": data.get("percent_change"),
            "scores": {
                name: scores.get(name)
                for name in ("growth", "quality", "moat", "momentum", "risk")
            },
            "thesis": profile.get("thesis") or data.get("notes"),
            "key_driver": profile.get("key_driver"),
            "key_risk": profile.get("key_risk"),
            "score_source": data.get("score_source"),
            "score_horizon": "Research priority; not a return forecast",
        }

    def _sectors(self, available):
        grouped = defaultdict(list)
        for data in available.values():
            sector = data.get("sector")
            change = data.get("percent_change")
            if sector and sector != "Benchmark ETF" and change is not None:
                grouped[sector].append(float(change))
        rows = [
            {
                "sector": sector,
                "average_change": round(sum(changes) / len(changes), 2),
                "securities": len(changes),
            }
            for sector, changes in grouped.items()
        ]
        return sorted(rows, key=lambda item: item["average_change"], reverse=True)

    @staticmethod
    def _corporate_actions(available):
        rows = []
        for ticker, data in available.items():
            actions = data.get("corporate_actions") or {}
            for split in actions.get("splits") or []:
                rows.append(
                    {
                        "ticker": ticker,
                        "type": "Stock split",
                        "date": split.get("date"),
                        "ratio": split.get("split_ratio") or str(split.get("ratio")),
                        "source": split.get("source") or actions.get("source"),
                        "normalized": True,
                    }
                )
        return sorted(
            rows,
            key=lambda item: item.get("date") or "",
            reverse=True,
        )[:8]

    def _paper(self, available, include_details=True):
        if not self.paper_account.account_file.exists():
            return {"configured": False}
        prices = {
            ticker: data.get("price")
            for ticker, data in available.items()
            if data.get("price") is not None
        }
        status = self.paper_account.status(prices=prices)
        performance = self.paper_account.performance_summary()
        history = self.paper_account.performance_history()
        feedback_rows = self.paper_account.proposal_feedback(latest_prices=prices)
        feedback_summary = self.paper_account.proposal_feedback_summary(
            latest_prices=prices,
            rows=feedback_rows,
        )
        trade_pressure_profile = feedback_summary.get("trade_pressure_profile") or {}
        benchmark_preference_profile = (
            feedback_summary.get("benchmark_preference_profile") or {}
        )
        latest_reviews = self.paper_account.latest_position_reviews()
        proposals = self.paper_account.proposals()
        active_sell_proposals = {
            proposal["ticker"]: proposal
            for proposal in proposals
            if proposal["side"] == "sell"
            and proposal["status"] in {"pending", "approved"}
        }
        positions = []
        for position in status["positions"]:
            ticker = position["ticker"]
            security = available.get(ticker, {})
            review = latest_reviews.get(ticker)
            active_sell = active_sell_proposals.get(ticker)
            thesis_status = self._position_thesis_status(
                position,
                review,
                active_sell,
            )
            news_summary = self._news_signal_summary(security)
            item = {
                "ticker": ticker,
                "anchor_id": self._paper_position_anchor_id(ticker),
                "shares": position["shares"],
                "average_cost": position["average_cost"],
                "price": position["price"],
                "market_value": position["market_value"],
                "unrealized_gain_loss": position["unrealized_gain_loss"],
                "review": review,
                "thesis_status": thesis_status,
                "decision_driver": self._position_decision_driver(
                    review,
                    thesis_status,
                ),
                "news_summary": news_summary,
            }
            if include_details:
                trend_summary = self._trend_summary(security)
                confirmation_summary = self._confirmation_summary(
                    ticker,
                    available,
                )
                outcome_summary = self._position_outcome_summary(
                    position,
                    history,
                    available,
                )
                item.update(
                    {
                        "adaptive_context": self._adaptive_position_context(
                            trade_pressure_profile,
                            benchmark_preference_profile,
                        ),
                        "decision_journal": self._position_decision_journal(
                            position,
                            review,
                            active_sell,
                            history,
                        ),
                        "outcome_summary": outcome_summary,
                        "trend_summary": trend_summary,
                        "confirmation_summary": confirmation_summary,
                        "projection_summary": self._position_projection_summary(
                            position=position,
                            thesis_status=thesis_status,
                            trend_summary=trend_summary,
                            confirmation_summary=confirmation_summary,
                            news_summary=news_summary,
                            outcome_summary=outcome_summary,
                            history=history,
                            available=available,
                        ),
                        "research_memory": self._research_memory_summary(
                            ticker,
                        ),
                    }
                )
            positions.append(item)
        payload = {
            "configured": True,
            "name": status["name"],
            "cash": round(status["cash"], 2),
            "equity": round(status["equity"], 2),
            "market_value": round(status["market_value"], 2),
            "total_return_pct": (
                performance.get("latest", {}).get("total_return_pct")
                if performance.get("available")
                else None
            ),
            "excess_return_pct": performance.get("excess_return_pct", {}),
            "positions": positions,
            "thesis_overview": self._thesis_overview(positions),
            "portfolio_focus": self._portfolio_focus(positions),
            "position_ladder": self._position_ladder(positions),
            "validation_summary": self.paper_account.stage5_validation_summary(
                latest_prices=prices,
                feedback_summary=feedback_summary,
                feedback_rows=feedback_rows,
            ),
            "operating_mode": self._paper_operating_mode(),
            "proposals": {
                "pending": sum(1 for item in proposals if item["status"] == "pending"),
                "approved": sum(1 for item in proposals if item["status"] == "approved"),
                "rejected": sum(1 for item in proposals if item["status"] == "rejected"),
                "executed": sum(1 for item in proposals if item["status"] == "executed"),
            },
        }
        if include_details:
            feedback_summary = dict(feedback_summary)
            feedback_summary["sector_learning_bridge"] = (
                PaperStrategy.sector_learning_summary_from_feedback(
                    feedback_rows,
                    available,
                )
            )
            feedback_summary["sector_gate_audit"] = PaperStrategy.sector_gate_audit(
                self.paper_account,
                available,
            )
            payload.update(
                {
                    "activity": self._paper_activity_with_context(),
                    "trade_history": self._paper_trade_history(),
                    "accountability_report": self.paper_account.accountability_report(),
                    "capital_rotation_scoreboard": self._capital_rotation_scoreboard(
                        positions,
                        available,
                        feedback_summary,
                        status.get("equity"),
                        feedback_rows,
                    ),
                    "feedback_summary": feedback_summary,
                    "feedback": feedback_rows,
                }
            )
        return payload

    def _paper_operating_mode(self):
        auto_manage_enabled = False
        policy = dict(self.paper_account.policy)
        if self.paper_account.account_file.exists():
            try:
                auto_manage_enabled = self.paper_account.auto_manage_enabled()
                policy.update(self.paper_account.load().get("policy", {}))
            except ValueError:
                auto_manage_enabled = False
        return {
            "current": {
                "id": "paper_auto_manage" if auto_manage_enabled else "recommendation_only",
                "label": "Auto-manage paper portfolio" if auto_manage_enabled else "Recommendation mode",
                "description": (
                    "Atlas is currently allowed to auto-approve and auto-execute "
                    "simulated paper buys, trims, and exits after the normal risk-review "
                    "step."
                    if auto_manage_enabled
                    else "Atlas currently researches, proposes, and explains paper trades, "
                    "but it does not auto-execute them."
                ),
            },
            "strategy_settings": [
                {
                    "label": "Daily trade cap",
                    "value": str(int(policy.get("maximum_daily_trades", 5))),
                    "detail": "maximum simulated trades Atlas can record in one day",
                },
                {
                    "label": "Buy slots",
                    "value": str(int(policy.get("strategy_maximum_new_proposals", 3))),
                    "detail": "maximum concurrent new paper buy proposals",
                },
                {
                    "label": "Target size",
                    "value": f"{float(policy.get('strategy_target_position_pct', 5.0)):.1f}%",
                    "detail": "of starting simulated cash per new entry",
                },
                {
                    "label": "Buy threshold",
                    "value": f"{float(policy.get('strategy_minimum_buy_score', 88.0)):.1f}",
                    "detail": "minimum Atlas score for new paper entries",
                },
                {
                    "label": "Benchmark weight",
                    "value": f"{float(policy.get('strategy_benchmark_excess_weight', 1.5)):.1f}x",
                    "detail": "extra emphasis on outperforming SPY or QQQ",
                },
                {
                    "label": "Benchmark trust",
                    "value": str(policy.get("strategy_preferred_benchmark", "auto")).upper(),
                    "detail": "which benchmark bar Atlas currently trusts most for borderline entries",
                },
                {
                    "label": "Trend weight",
                    "value": f"{float(policy.get('strategy_trend_quality_weight', 0.2)):.2f}",
                    "detail": "extra emphasis on trend-quality leadership",
                },
                {
                    "label": "Sector diversity",
                    "value": f"{float(policy.get('strategy_sector_repeat_penalty', 3.0)):.1f}",
                    "detail": "penalty applied before Atlas doubles up in one sector",
                },
                {
                    "label": "Trim escalation",
                    "value": (
                        f"{int(policy.get('maximum_partial_trims_per_position', 2))} trims"
                    ),
                    "detail": (
                        "the next repeated risk signal closes the remaining paper "
                        "position instead of creating another fractional trim"
                    ),
                },
            ],
            "modes": [
                {
                    "id": "recommendation_only",
                    "label": "Recommendation mode",
                    "status": "available" if auto_manage_enabled else "active",
                    "description": (
                        "Atlas surfaces buys, trims, and exits for owner review before "
                        "anything is recorded."
                    ),
                },
                {
                    "id": "paper_auto_manage",
                    "label": "Auto-manage paper portfolio",
                    "status": "active" if auto_manage_enabled else "available",
                    "description": (
                        "Atlas can automatically maintain the simulated portfolio "
                        "using paper-only rules, risk review, and a full audit trail."
                    ),
                },
            ],
            "boundary": (
                "Real-money auto-trading remains disabled. Any automation remains "
                "paper-only until explicitly expanded."
            ),
        }

    def _paper_activity_with_context(self):
        rows = []
        for item in self.paper_account.trade_activity():
            rows.append(
                {
                    **item,
                    "decision_context": self._activity_decision_context(item),
                }
            )
        return rows

    def _paper_trade_history(self):
        rows = []
        for item in self.paper_account.trade_activity(limit=1000):
            rows.append(
                {
                    **item,
                    "decision_context": self._activity_decision_context(item),
                }
            )
        return self._group_trade_history(rows)

    @staticmethod
    def _group_trade_history(rows):
        grouped = defaultdict(list)
        for item in rows:
            ticker = str(item.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            grouped[ticker].append(item)

        tickers = []
        for ticker, items in grouped.items():
            buy_count = sum(
                1 for item in items if str(item.get("side") or "").lower() == "buy"
            )
            sell_count = sum(
                1 for item in items if str(item.get("side") or "").lower() == "sell"
            )
            latest = items[0]
            tickers.append(
                {
                    "ticker": ticker,
                    "trade_count": len(items),
                    "buy_count": buy_count,
                    "sell_count": sell_count,
                    "latest_timestamp": latest.get("timestamp"),
                    "latest_action": latest.get("action_label"),
                    "rows": [
                        {
                            "trade_id": item.get("trade_id"),
                            "timestamp": item.get("timestamp"),
                            "side": item.get("side"),
                            "action_label": item.get("action_label"),
                            "shares": item.get("shares"),
                            "fill_price": item.get("fill_price"),
                            "realized_gain_loss": item.get("realized_gain_loss"),
                            "summary": item.get("summary"),
                            "thesis": item.get("thesis"),
                            "decision_driver": item.get("decision_driver") or {},
                            "decision_context": item.get("decision_context") or [],
                        }
                        for item in items
                    ],
                }
            )
        tickers.sort(
            key=lambda item: (
                str(item.get("latest_timestamp") or ""),
                item.get("ticker") or "",
            ),
            reverse=True,
        )
        return {
            "total_trades": sum(len(item["rows"]) for item in tickers),
            "ticker_count": len(tickers),
            "tickers": tickers,
        }

    def _capital_rotation_scoreboard(
        self,
        positions,
        available,
        feedback_summary,
        equity,
        feedback_rows,
    ):
        """Summarize where simulated capital is concentrating and earning its keep."""
        sector_rows = {}
        equity = float(equity or 0.0)

        def sector_for(ticker):
            security = available.get(str(ticker or "").upper(), {}) or {}
            return str(security.get("sector") or "Unclassified").strip() or "Unclassified"

        def bucket(sector):
            return sector_rows.setdefault(
                sector,
                {
                    "sector": sector,
                    "open_positions": 0,
                    "open_market_value": 0.0,
                    "open_weight_pct": 0.0,
                    "buy_notional": 0.0,
                    "sell_notional": 0.0,
                    "net_notional": 0.0,
                    "realized_gain_loss": 0.0,
                    "unrealized_gain_loss": 0.0,
                    "judged_buys": 0,
                    "working_buys": 0,
                    "mixed_buys": 0,
                    "lagging_buys": 0,
                    "buy_working_rate_pct": None,
                    "avg_benchmark_edge_pct": None,
                    "posture": "watch",
                    "summary": "",
                },
            )

        for position in positions:
            row = bucket(sector_for(position.get("ticker")))
            row["open_positions"] += 1
            row["open_market_value"] += float(position.get("market_value") or 0.0)
            row["unrealized_gain_loss"] += float(
                position.get("unrealized_gain_loss") or 0.0
            )

        for trade in self.paper_account.trade_activity(limit=1000):
            row = bucket(sector_for(trade.get("ticker")))
            notional = round(
                float(trade.get("shares") or 0.0)
                * float(trade.get("fill_price") or 0.0),
                2,
            )
            if str(trade.get("side") or "").lower() == "sell":
                row["sell_notional"] += notional
                row["realized_gain_loss"] += float(trade.get("realized_gain_loss") or 0.0)
            else:
                row["buy_notional"] += notional

        edge_totals = defaultdict(list)
        for item in feedback_rows:
            if str(item.get("side") or "").lower() != "buy":
                continue
            verdict = str(item.get("verdict") or "").lower()
            if verdict not in {"working", "mixed", "lagging"}:
                continue
            row = bucket(sector_for(item.get("ticker")))
            row["judged_buys"] += 1
            row[f"{verdict}_buys"] += 1
            benchmark_returns = [
                float(value)
                for value in (item.get("benchmark_returns_pct") or {}).values()
                if value is not None
            ]
            security_return = item.get("security_return_pct")
            if benchmark_returns and security_return is not None:
                edge_totals[row["sector"]].append(
                    float(security_return) - max(benchmark_returns)
                )

        sectors = []
        for row in sector_rows.values():
            row["open_market_value"] = round(row["open_market_value"], 2)
            row["open_weight_pct"] = (
                round((row["open_market_value"] / equity) * 100.0, 1)
                if equity
                else 0.0
            )
            row["buy_notional"] = round(row["buy_notional"], 2)
            row["sell_notional"] = round(row["sell_notional"], 2)
            row["net_notional"] = round(row["buy_notional"] - row["sell_notional"], 2)
            row["realized_gain_loss"] = round(row["realized_gain_loss"], 2)
            row["unrealized_gain_loss"] = round(row["unrealized_gain_loss"], 2)
            if row["judged_buys"]:
                row["buy_working_rate_pct"] = round(
                    (row["working_buys"] / row["judged_buys"]) * 100.0,
                    1,
                )
            if edge_totals[row["sector"]]:
                row["avg_benchmark_edge_pct"] = round(
                    sum(edge_totals[row["sector"]]) / len(edge_totals[row["sector"]]),
                    2,
                )
            row["posture"] = self._capital_rotation_posture(row)
            row["summary"] = self._capital_rotation_summary(row)
            sectors.append(row)

        sectors.sort(
            key=lambda row: (
                row["open_market_value"],
                row["net_notional"],
                row["buy_notional"],
            ),
            reverse=True,
        )
        totals = {
            "open_market_value": round(sum(row["open_market_value"] for row in sectors), 2),
            "buy_notional": round(sum(row["buy_notional"] for row in sectors), 2),
            "sell_notional": round(sum(row["sell_notional"] for row in sectors), 2),
            "net_notional": round(sum(row["net_notional"] for row in sectors), 2),
            "realized_gain_loss": round(sum(row["realized_gain_loss"] for row in sectors), 2),
            "unrealized_gain_loss": round(sum(row["unrealized_gain_loss"] for row in sectors), 2),
            "judged_buys": sum(row["judged_buys"] for row in sectors),
            "working_buys": sum(row["working_buys"] for row in sectors),
        }
        totals["buy_working_rate_pct"] = (
            round((totals["working_buys"] / totals["judged_buys"]) * 100.0, 1)
            if totals["judged_buys"]
            else None
        )
        rotation_stats = (
            (feedback_summary.get("entry_strategy_profile") or {}).get(
                "benchmark_rotation_stats"
            )
            or {}
        )
        return {
            "available": bool(sectors),
            "headline": self._capital_rotation_headline(sectors),
            "benchmark_rotation_read": rotation_stats,
            "totals": totals,
            "sectors": sectors,
        }

    @staticmethod
    def _capital_rotation_posture(row):
        working_rate = row.get("buy_working_rate_pct")
        open_weight = float(row.get("open_weight_pct") or 0.0)
        total_gain = float(row.get("realized_gain_loss") or 0.0) + float(
            row.get("unrealized_gain_loss") or 0.0
        )
        if open_weight >= 35.0 or int(row.get("open_positions") or 0) >= 3:
            return "diversify"
        if working_rate is not None and working_rate >= 70.0 and total_gain >= 0:
            return "press"
        if working_rate is not None and working_rate < 40.0:
            return "review"
        if total_gain < 0 and int(row.get("judged_buys") or 0) > 0:
            return "review"
        return "watch"

    @staticmethod
    def _capital_rotation_summary(row):
        posture = row.get("posture")
        sector = row.get("sector") or "this sector"
        if posture == "press":
            return f"{sector} is earning simulated capital so far; Atlas can keep pressing only if benchmark-relative evidence stays constructive."
        if posture == "diversify":
            return f"{sector} is a large part of the open paper book, so Atlas should require stronger proof before adding more concentration."
        if posture == "review":
            return f"{sector} needs review because judged buys or current gains are not yet proving enough follow-through."
        return f"{sector} remains on watch while Atlas collects more judged buy and benchmark-relative evidence."

    @staticmethod
    def _capital_rotation_headline(sectors):
        if not sectors:
            return "Atlas has not recorded enough simulated sector activity to score capital rotation yet."
        press = [row for row in sectors if row.get("posture") == "press"]
        review = [row for row in sectors if row.get("posture") == "review"]
        diversify = [row for row in sectors if row.get("posture") == "diversify"]
        if press:
            names = ", ".join(row["sector"] for row in press[:2])
            return f"Atlas is seeing its clearest simulated capital support in {names}."
        if review:
            names = ", ".join(row["sector"] for row in review[:2])
            return f"Atlas should review capital committed to {names} before adding more."
        if diversify:
            names = ", ".join(row["sector"] for row in diversify[:2])
            return f"Atlas has concentration pressure in {names} and should protect diversification."
        return "Atlas is watching sector rotation while simulated evidence continues to build."

    @staticmethod
    def _trend_summary(security):
        metrics = (security or {}).get("momentum_metrics") or {}
        if not metrics:
            return None

        def value(name):
            current = metrics.get(name)
            if current in (None, ""):
                return None
            try:
                return float(current)
            except (TypeError, ValueError):
                return None

        trend_quality = value("trend_quality_score")
        trend_regime_score = value("trend_regime_score")
        if trend_quality is None and trend_regime_score is None:
            return None

        trend_regime = str(metrics.get("trend_regime") or "unknown").strip().lower()
        trend_state = str(metrics.get("trend_state") or "unknown").strip().lower()
        price_vs_sma_50 = value("price_vs_sma_50_pct")
        price_vs_sma_200 = value("price_vs_sma_200_pct")
        ema_slope = value("ema_20_slope_pct")
        rsi = value("rsi_14")
        distance_from_high = value("distance_from_52w_high_pct")

        if trend_regime in {"leadership", "constructive"}:
            headline = "Trend posture remains supportive for continued outperformance."
        elif trend_regime == "repair":
            headline = "Trend posture is improving, but Atlas still sees some repair work."
        elif trend_regime in {"fragile", "breakdown"}:
            headline = "Trend posture is weakening and Atlas will be more skeptical."
        else:
            headline = "Trend posture is mixed on the latest snapshot."

        stats = []
        if trend_quality is not None:
            stats.append(
                {
                    "label": "Trend quality",
                    "value": f"{trend_quality:.1f}",
                    "detail": "Composite persistence, alignment, breakout, RSI, and volatility score.",
                }
            )
        if trend_regime_score is not None:
            stats.append(
                {
                    "label": "Trend regime",
                    "value": f"{trend_regime.replace('_', ' ')} ({trend_regime_score:.1f})",
                    "detail": "Atlas regime read for leadership versus weakness.",
                }
            )
        if price_vs_sma_50 is not None:
            stats.append(
                {
                    "label": "Vs 50-day",
                    "value": f"{price_vs_sma_50:+.1f}%",
                    "detail": "Distance from the 50-day moving average.",
                }
            )
        if price_vs_sma_200 is not None:
            stats.append(
                {
                    "label": "Vs 200-day",
                    "value": f"{price_vs_sma_200:+.1f}%",
                    "detail": "Distance from the 200-day moving average.",
                }
            )
        if ema_slope is not None:
            stats.append(
                {
                    "label": "20-day slope",
                    "value": f"{ema_slope:+.1f}%",
                    "detail": "Recent slope of the 20-day exponential moving average.",
                }
            )
        if rsi is not None:
            stats.append(
                {
                    "label": "RSI(14)",
                    "value": f"{rsi:.1f}",
                    "detail": "Short-term momentum balance.",
                }
            )
        if distance_from_high is not None:
            stats.append(
                {
                    "label": "From 52-week high",
                    "value": f"{distance_from_high:+.1f}%",
                    "detail": "Current distance from the trailing 52-week high.",
                }
            )
        return {
            "headline": headline,
            "trend_regime": trend_regime,
            "trend_state": trend_state,
            "stats": stats[:6],
        }

    @staticmethod
    def _confirmation_summary(ticker, available):
        security = available.get(ticker, {}) or {}
        if security.get("status") != "available":
            return None

        def pct(data):
            value = (data or {}).get("percent_change")
            if value in (None, ""):
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        security_change = pct(security)
        if security_change is None:
            return None

        sector = str(security.get("sector") or "Unclassified")
        sector_changes = []
        for row in available.values():
            if row.get("status") != "available":
                continue
            if str(row.get("sector") or "Unclassified") != sector:
                continue
            change = pct(row)
            if change is not None:
                sector_changes.append(change)
        sector_average = (
            round(sum(sector_changes) / len(sector_changes), 2) if sector_changes else None
        )
        sector_breadth = (
            round((sum(1 for value in sector_changes if value > 0) / len(sector_changes)) * 100.0, 0)
            if sector_changes
            else None
        )

        benchmarks = []
        for label in ("SPY", "QQQ", "IWM", "RSP"):
            change = pct(available.get(label, {}))
            if change is not None:
                benchmarks.append((label, change))

        stronger = max(benchmarks, key=lambda item: item[1]) if benchmarks else None
        benchmark_breadth = (
            round((sum(1 for _label, change in benchmarks if change > 0) / len(benchmarks)) * 100.0, 0)
            if benchmarks
            else None
        )

        if stronger:
            benchmark_label, benchmark_change = stronger
            excess = round(security_change - benchmark_change, 2)
            if excess >= 1.0:
                headline = f"{ticker} is leading the strongest benchmark tape today."
            elif excess >= 0.0:
                headline = f"{ticker} is keeping up with the strongest benchmark tape today."
            else:
                headline = f"{ticker} is trailing the strongest benchmark tape today."
        else:
            benchmark_label, benchmark_change, excess = "", None, None
            headline = f"{ticker} has no benchmark confirmation read on this snapshot."

        stats = []
        stats.append(
            {
                "label": "Daily move",
                "value": f"{security_change:+.2f}%",
                "detail": "Latest one-day move for this holding.",
            }
        )
        if sector_average is not None:
            stats.append(
                {
                    "label": "Sector average",
                    "value": f"{sector_average:+.2f}%",
                    "detail": f"Average one-day move across {sector}.",
                }
            )
        if sector_breadth is not None:
            stats.append(
                {
                    "label": "Sector breadth",
                    "value": f"{sector_breadth:.0f}%",
                    "detail": "Share of same-sector tracked names that are up today.",
                }
            )
        if benchmark_label and benchmark_change is not None:
            stats.append(
                {
                    "label": f"Vs {benchmark_label}",
                    "value": f"{excess:+.2f}%",
                    "detail": f"Excess return versus the strongest major benchmark today ({benchmark_change:+.2f}%).",
                }
            )
        if benchmark_breadth is not None:
            stats.append(
                {
                    "label": "Benchmark breadth",
                    "value": f"{benchmark_breadth:.0f}%",
                    "detail": "Share of SPY, QQQ, IWM, and RSP that are up today.",
                }
            )

        return {
            "headline": headline,
            "sector": sector,
            "strongest_benchmark": benchmark_label,
            "stats": stats[:5],
        }

    def _activity_decision_context(self, item):
        ticker = item.get("ticker")
        side = str(item.get("side") or "").lower()
        action = str(item.get("action_label") or side or "trade")
        context = []
        review = item.get("risk_review") or {}
        flags = [
            str(flag).strip()
            for flag in review.get("flags") or []
            if str(flag).strip()
        ]
        if flags:
            context.append(
                "Execution risk review: " + "; ".join(flags[:2]) + "."
            )
        history = self.research_queue.thesis_history_summary(ticker)
        latest = self._latest_research_context(ticker)
        if latest:
            alignment = latest.get("thesis_alignment")
            catalyst = str(latest.get("catalyst_type") or "recent review").replace(
                "_", " "
            )
            if alignment == "risk_to_thesis":
                if side == "sell":
                    context.append(
                        f"Latest stored Atlas review marked {ticker} as risk to thesis via {catalyst}, which supports the simulated {action}."
                    )
                else:
                    context.append(
                        f"Latest stored Atlas review still marked {ticker} as risk to thesis via {catalyst}, so this simulated buy was taken with known downside context."
                    )
            elif alignment == "supports_driver":
                if side == "buy":
                    context.append(
                        f"Latest stored Atlas review supported the {ticker} thesis via {catalyst}, which aligned with the simulated buy."
                    )
                else:
                    context.append(
                        f"Latest stored Atlas review was supportive via {catalyst}, so the simulated {action} likely came from portfolio discipline rather than outright thesis damage."
                    )
            evidence_titles = latest.get("evidence_titles") or []
            if evidence_titles:
                context.append(
                    "Evidence on file at execution: "
                    + ", ".join(evidence_titles[:2])
                    + "."
                )
        if history and history.get("review_count"):
            context.append(
                self._research_memory_sentence(
                    ticker,
                    history,
                )
            )
        return context[:4]

    def _research_memory_summary(self, ticker):
        history = self.research_queue.thesis_history_summary(ticker)
        if not history:
            return None
        summary = self._research_memory_sentence(ticker, history)
        latest = self._latest_research_context(ticker)
        detail = ""
        if latest and latest.get("thesis_alignment") == "risk_to_thesis":
            catalyst = str(latest.get("catalyst_type") or "recent review").replace(
                "_", " "
            )
            detail = f"Latest stored review leaned risk to thesis via {catalyst}."
        elif latest and latest.get("thesis_alignment") == "supports_driver":
            catalyst = str(latest.get("catalyst_type") or "recent review").replace(
                "_", " "
            )
            detail = f"Latest stored review supported the thesis via {catalyst}."
        return {
            "summary": summary,
            "detail": detail,
        }

    def _position_decision_journal(self, position, review, active_sell, history):
        ticker = position.get("ticker")
        basis = position.get("average_cost")
        price = position.get("price")
        rows = []
        if basis not in (None, 0) and price is not None:
            change = (float(price) / float(basis) - 1) * 100
            rows.append(
                f"Current basis is ${float(basis):,.2f}; latest price is ${float(price):,.2f}, for a {change:+.2f}% open return."
            )
        benchmark_line = self._position_benchmark_line(ticker, history, price)
        if benchmark_line:
            rows.append(benchmark_line)
        if review:
            flags = review.get("flags") or []
            verdict = str(review.get("verdict") or "maintain").replace("_", " ")
            review_date = self._friendly_timestamp(review.get("timestamp"))
            review_line = f"Latest thesis review ({review_date}): {verdict}."
            if flags:
                review_line += f" Main flag: {flags[0]}"
            rows.append(review_line)
        rows.append(self._position_escalation_line(position, review, active_sell))
        return rows[:4]

    def _position_decision_driver(self, review, thesis_status):
        review = review or {}
        texts = list(review.get("flags") or [])
        thesis = str(review.get("thesis") or "").strip()
        if thesis:
            texts.append(thesis)
        return infer_decision_driver(
            texts,
            side="hold",
            action_label=(thesis_status or {}).get("label"),
        )

    def _position_benchmark_line(self, ticker, history, latest_price):
        if latest_price is None:
            return ""
        entry_trade = self._latest_open_buy_trade(ticker)
        if not entry_trade:
            return ""
        start = self.paper_account._first_snapshot_after(history, entry_trade.get("timestamp"))
        latest = history[-1] if history else None
        if not start or not latest or start.get("timestamp") == latest.get("timestamp"):
            return ""
        security_return = self.paper_account._pct_return(
            entry_trade.get("fill_price"),
            latest_price,
        )
        if security_return is None:
            return ""
        spy_return = self.paper_account._pct_return(
            start.get("benchmark_prices", {}).get("SPY"),
            latest.get("benchmark_prices", {}).get("SPY"),
        )
        qqq_return = self.paper_account._pct_return(
            start.get("benchmark_prices", {}).get("QQQ"),
            latest.get("benchmark_prices", {}).get("QQQ"),
        )
        benchmarks = []
        if spy_return is not None:
            benchmarks.append(f"SPY {spy_return:+.2f}%")
        if qqq_return is not None:
            benchmarks.append(f"QQQ {qqq_return:+.2f}%")
        if not benchmarks:
            return ""
        return (
            f"Since the latest buy fill, {ticker} is {security_return:+.2f}% versus "
            + " and ".join(benchmarks)
            + "."
        )

    def _position_outcome_summary(self, position, history, available):
        ticker = str(position.get("ticker") or "").strip().upper()
        latest_price = position.get("price")
        entry_trade = self._latest_open_buy_trade(ticker)
        if not ticker or latest_price is None or not entry_trade:
            return None

        security_return = self.paper_account._pct_return(
            entry_trade.get("fill_price"),
            latest_price,
        )
        if security_return is None:
            return None

        start = self.paper_account._first_snapshot_after(history, entry_trade.get("timestamp"))
        latest = history[-1] if history else None
        spy_return = None
        qqq_return = None
        if start and latest and start.get("timestamp") != latest.get("timestamp"):
            spy_return = self.paper_account._pct_return(
                start.get("benchmark_prices", {}).get("SPY"),
                latest.get("benchmark_prices", {}).get("SPY"),
            )
            qqq_return = self.paper_account._pct_return(
                start.get("benchmark_prices", {}).get("QQQ"),
                latest.get("benchmark_prices", {}).get("QQQ"),
            )

        benchmark_candidates = [
            ("SPY", spy_return),
            ("QQQ", qqq_return),
        ]
        benchmark_candidates = [
            (label, value)
            for label, value in benchmark_candidates
            if value is not None
        ]
        best_benchmark = max(benchmark_candidates, key=lambda item: item[1]) if benchmark_candidates else None
        benchmark_excess = (
            round(security_return - best_benchmark[1], 2)
            if best_benchmark
            else None
        )

        confirmation = self._confirmation_summary(ticker, available) or {}
        sector_average = None
        strongest_daily = None
        for item in confirmation.get("stats") or []:
            label = str(item.get("label") or "").strip().lower()
            value = str(item.get("value") or "").strip()
            if label == "sector average":
                sector_average = value
            elif label.startswith("vs "):
                strongest_daily = value

        if benchmark_excess is None:
            headline = f"{ticker} is up {security_return:+.2f}% since entry."
            detail = "Atlas does not yet have enough post-entry benchmark history to judge whether this is leadership or just market lift."
        elif benchmark_excess >= 3.0:
            headline = f"{ticker} is acting like a genuine leader since entry."
            detail = (
                f"It is up {security_return:+.2f}% since entry, beating the stronger "
                f"benchmark by {benchmark_excess:+.2f}%."
            )
        elif benchmark_excess >= 0.0:
            headline = f"{ticker} is modestly ahead of the market since entry."
            detail = (
                f"It is up {security_return:+.2f}% since entry, ahead of the stronger "
                f"benchmark by {benchmark_excess:+.2f}%."
            )
        else:
            headline = f"{ticker} is rising less than the market since entry."
            detail = (
                f"It is up {security_return:+.2f}% since entry, but trails the stronger "
                f"benchmark by {abs(benchmark_excess):.2f}%."
            )

        if sector_average is not None or strongest_daily is not None:
            extras = []
            if sector_average is not None:
                extras.append(f"Current sector average is {sector_average}.")
            if strongest_daily is not None:
                extras.append(f"Today's daily confirmation versus the strongest benchmark is {strongest_daily}.")
            detail += " " + " ".join(extras)

        return {
            "headline": headline,
            "detail": detail.strip(),
        }

    def _position_projection_summary(
        self,
        position,
        thesis_status,
        trend_summary,
        confirmation_summary,
        news_summary,
        outcome_summary,
        history,
        available,
    ):
        ticker = str(position.get("ticker") or "").strip().upper()
        if not ticker:
            return None

        trend_regime = str((trend_summary or {}).get("trend_regime") or "unknown")
        news_label = str((news_summary or {}).get("label") or "neutral")
        thesis_label = str((thesis_status or {}).get("label") or "healthy")
        benchmark_excess = self._position_benchmark_excess_since_entry(
            ticker,
            position.get("price"),
            history,
        )
        strongest_daily = self._summary_stat_value(
            confirmation_summary,
            prefix="vs ",
        )
        sector_breadth = self._summary_stat_value(
            confirmation_summary,
            label="sector breadth",
        )
        price_vs_sma_50 = self._summary_stat_value(
            trend_summary,
            label="vs 50-day",
        )

        watchpoints = []
        if price_vs_sma_50 is not None:
            if price_vs_sma_50 >= 0:
                watchpoints.append(
                    f"Hold the 50-day trend cushion, currently {price_vs_sma_50:+.2f}% above it."
                )
            else:
                watchpoints.append(
                    f"Reclaim the 50-day trend line, currently {abs(price_vs_sma_50):.2f}% below it."
                )
        if strongest_daily is not None:
            if strongest_daily >= 0:
                watchpoints.append(
                    f"Keep daily confirmation positive versus the strongest benchmark, now {strongest_daily:+.2f}%."
                )
            else:
                watchpoints.append(
                    f"Reverse the current daily benchmark lag of {abs(strongest_daily):.2f}% before it compounds."
                )
        if sector_breadth is not None:
            if sector_breadth >= 60:
                watchpoints.append(
                    f"Sector participation remains healthy with {sector_breadth:.0f}% breadth."
                )
            else:
                watchpoints.append(
                    f"Sector participation is thin at {sector_breadth:.0f}% breadth, so follow-through needs extra caution."
                )
        if news_label in {"adverse", "cautious"}:
            watchpoints.append(
                "Watch company-specific headlines closely because the current news tone is no longer cleanly supportive."
            )
        else:
            watchpoints.append(
                "A shift toward adverse company-specific news would weaken the projection quickly."
            )

        if thesis_label in {"exit", "trim"} or trend_regime in {"breakdown", "fragile"} or news_label == "adverse":
            headline = "Atlas projection: trim or exit risk is elevated if weakness persists."
            detail = "The forward read is defensive because the holding is already showing enough damage that further lag would strengthen the case to reduce exposure."
        elif benchmark_excess is not None and benchmark_excess >= 3.0 and trend_regime in {"leadership", "constructive"} and news_label not in {"adverse", "cautious"}:
            headline = "Atlas projection: continued leadership is favored while confirmation holds."
            detail = (
                f"The current read combines a {trend_regime.replace('_', ' ')} trend, "
                f"{benchmark_excess:+.2f}% excess return since entry, and a clean news tone."
            )
        elif benchmark_excess is not None and benchmark_excess >= 0.0:
            headline = "Atlas projection: upside can continue, but Atlas wants more proof."
            detail = (
                f"The holding is still ahead of the market by {benchmark_excess:+.2f}% since entry, "
                "yet Atlas is looking for continued daily and sector confirmation before treating it as a stronger leader."
            )
        else:
            headline = "Atlas projection: stall risk is higher until leadership improves."
            if outcome_summary and outcome_summary.get("detail"):
                detail = str(outcome_summary.get("detail"))
            else:
                detail = (
                    "Atlas does not yet see enough benchmark-relative evidence to assume that the current move will keep extending."
                )

        return {
            "headline": headline,
            "detail": detail,
            "watchpoints": watchpoints[:3],
        }

    @staticmethod
    def _adaptive_position_context(trade_pressure_profile, benchmark_preference_profile):
        notes = []
        trade_cap = (trade_pressure_profile or {}).get("policy_overrides", {}).get(
            "maximum_daily_trades",
            (trade_pressure_profile or {}).get("baseline", {}).get(
                "maximum_daily_trades"
            ),
        )
        if trade_cap is not None:
            notes.append(
                f"Atlas is currently pacing the paper book around {trade_cap} daily trades."
            )
        benchmark_bar = str(
            (benchmark_preference_profile or {}).get("strategy_overrides", {}).get(
                "strategy_preferred_benchmark",
                (benchmark_preference_profile or {}).get("baseline", {}).get(
                    "strategy_preferred_benchmark",
                    "auto",
                ),
            )
        ).upper()
        if benchmark_bar == "AUTO":
            notes.append(
                "Atlas is still auto-picking the stronger benchmark tape for borderline entry confirmation."
            )
        else:
            notes.append(
                f"Atlas currently trusts {benchmark_bar} as the stronger benchmark bar for borderline entries."
            )
        return notes

    def _latest_open_buy_trade(self, ticker):
        ticker = str(ticker or "").strip().upper()
        if not ticker:
            return None
        for trade in reversed(self.paper_account.trade_activity(limit=1000)):
            if str(trade.get("ticker") or "").strip().upper() != ticker:
                continue
            if str(trade.get("side") or "").lower() != "buy":
                continue
            return trade
        return None

    @staticmethod
    def _friendly_timestamp(value):
        text = str(value or "").strip()
        if not text:
            return "recently"
        return text.replace("T", " ")

    def _position_benchmark_excess_since_entry(self, ticker, latest_price, history):
        if latest_price is None:
            return None
        entry_trade = self._latest_open_buy_trade(ticker)
        if not entry_trade:
            return None
        start = self.paper_account._first_snapshot_after(history, entry_trade.get("timestamp"))
        latest = history[-1] if history else None
        if not start or not latest or start.get("timestamp") == latest.get("timestamp"):
            return None
        security_return = self.paper_account._pct_return(
            entry_trade.get("fill_price"),
            latest_price,
        )
        if security_return is None:
            return None
        benchmarks = []
        for label in ("SPY", "QQQ"):
            value = self.paper_account._pct_return(
                start.get("benchmark_prices", {}).get(label),
                latest.get("benchmark_prices", {}).get(label),
            )
            if value is not None:
                benchmarks.append(value)
        if not benchmarks:
            return None
        return round(security_return - max(benchmarks), 2)

    @staticmethod
    def _summary_stat_value(summary, label=None, prefix=None):
        rows = (summary or {}).get("stats") or []
        for item in rows:
            current_label = str(item.get("label") or "").strip().lower()
            if label and current_label != label:
                continue
            if prefix and not current_label.startswith(prefix):
                continue
            text = str(item.get("value") or "").strip().replace("%", "")
            if not text:
                return None
            try:
                return float(text)
            except ValueError:
                return None
        return None

    @staticmethod
    def _news_signal_summary(security):
        signal = (security or {}).get("news_signal") or {}
        label = str(signal.get("signal_label") or "").strip().lower()
        if not label:
            return None
        positive = int(signal.get("positive_count") or 0)
        negative = int(signal.get("negative_count") or 0)
        company_headlines = int(signal.get("company_headline_count") or 0)
        score = float(signal.get("signal_score") or 50.0)
        dominant_event = DashboardDataService._friendly_news_event(
            signal.get("dominant_event_type")
        )
        high_impact_negative = int(signal.get("high_impact_negative_count") or 0)
        high_impact_positive = int(signal.get("high_impact_positive_count") or 0)
        examples = []
        for text in signal.get("negative_examples") or []:
            cleaned = str(text).strip()
            if cleaned:
                examples.append(cleaned)
        if not examples:
            for text in signal.get("positive_examples") or []:
                cleaned = str(text).strip()
                if cleaned:
                    examples.append(cleaned)

        tone = label.replace("_", " ")
        headline = (
            f"News tone is {tone} with {positive} positive and {negative} negative "
            f"company headline{'s' if company_headlines != 1 else ''} in the latest scan."
        )
        detail = (
            f"Signal score {score:.0f} across {company_headlines} company-specific "
            f"headline{'s' if company_headlines != 1 else ''}."
        )
        event_detail = f"Main event read: {dominant_event}."
        if high_impact_negative > 0:
            event_detail += " Atlas currently treats this as high-impact downside news."
        elif high_impact_positive > 0:
            event_detail += " Atlas currently treats this as high-impact supportive news."
        return {
            "label": label,
            "headline": headline,
            "detail": detail,
            "event_detail": event_detail,
            "score": score,
            "positive_count": positive,
            "negative_count": negative,
            "company_headline_count": company_headlines,
            "dominant_event_type": str(signal.get("dominant_event_type") or "routine"),
            "example": examples[0] if examples else "",
        }

    @staticmethod
    def _friendly_news_event(value):
        text = str(value or "").strip().lower()
        if not text or text == "routine":
            return "routine mention"
        return text.replace("_", " ")

    @staticmethod
    def _position_escalation_line(position, review, active_sell):
        ticker = position.get("ticker") or "This holding"
        if active_sell:
            shares = float(position.get("shares") or 0.0)
            sell_shares = float(active_sell.get("shares") or 0.0)
            if shares and sell_shares < shares:
                return (
                    f"Escalation state: Atlas already wants to trim {sell_shares:g} of {shares:g} simulated shares."
                )
            return "Escalation state: Atlas already has an exit path active for this holding."
        if review:
            verdict = str(review.get("verdict") or "").lower()
            if verdict == "exit":
                return f"Escalation cue: {ticker} has already crossed Atlas's exit threshold on the latest review."
            if verdict == "review":
                return (
                    f"Escalation cue: move from hold toward trim or exit if the next thesis review repeats weakness or adds new risk flags."
                )
        return (
            f"Escalation cue: stay in hold mode unless a future thesis review downgrades the position or Atlas opens a trim/exit proposal."
        )

    @staticmethod
    def _research_memory_sentence(ticker, history):
        review_count = int(history.get("review_count") or 0)
        risk_count = int(history.get("risk_to_thesis_count") or 0)
        support_count = int(history.get("supports_driver_count") or 0)
        parts = [f"{review_count} stored review{'s' if review_count != 1 else ''}"]
        if risk_count:
            parts.append(
                f"{risk_count} risk-to-thesis signal{'s' if risk_count != 1 else ''}"
            )
        if support_count:
            parts.append(
                f"{support_count} supportive signal{'s' if support_count != 1 else ''}"
            )
        return f"Atlas memory for {ticker}: " + "; ".join(parts) + "."

    def _latest_research_context(self, ticker):
        ticker = str(ticker or "").strip().upper()
        if not ticker:
            return None
        latest = None
        for task in reversed(self.research_queue.load().get("tasks", [])):
            if str(task.get("subject") or "").strip().upper() != ticker:
                continue
            if not task.get("result"):
                continue
            latest = task
            break
        if not latest:
            return None
        result = latest.get("result", {})
        evidence_titles = []
        for item in result.get("evidence", []) or []:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    evidence_titles.append(text[:90])
            else:
                title = str(item.get("title") or item.get("detail") or "").strip()
                if title:
                    evidence_titles.append(title[:90])
        return {
            "catalyst_type": result.get("catalyst_type"),
            "thesis_alignment": result.get("thesis_alignment"),
            "thesis_drift": result.get("thesis_drift"),
            "evidence_titles": evidence_titles[:2],
        }

    @staticmethod
    def _position_thesis_status(position, review, active_sell):
        shares = float(position.get("shares") or 0.0)
        if active_sell:
            sell_shares = float(active_sell.get("shares") or 0.0)
            if shares and sell_shares < shares:
                return {
                    "label": "trim",
                    "summary": (
                        f"Atlas has an active simulated trim proposal for "
                        f"{sell_shares:g} of {shares:g} shares."
                    ),
                }
            return {
                "label": "exit",
                "summary": "Atlas has an active simulated exit proposal for this holding.",
            }
        if not review:
            return {
                "label": "healthy",
                "summary": "Awaiting the next daily thesis review.",
            }

        verdict = str(review.get("verdict") or "maintain").lower()
        flags = review.get("flags") or []
        score = review.get("atlas_score")
        score_text = f" Atlas score {score:.1f}." if score is not None else ""
        if verdict == "exit":
            return {
                "label": "exit",
                "summary": (
                    (flags[0] if flags else "Atlas marked this holding for simulated exit.")
                    + score_text
                ).strip(),
            }
        if verdict == "review":
            return {
                "label": "watch",
                "summary": (
                    (flags[0] if flags else "Atlas wants a closer thesis review on this holding.")
                    + score_text
                ).strip(),
            }
        return {
            "label": "healthy",
            "summary": (
                (flags[0] if flags else "Latest thesis review remains constructive.")
                + score_text
            ).strip(),
        }

    @staticmethod
    def _thesis_overview(positions):
        counts = {label: 0 for label in ("healthy", "watch", "trim", "exit")}
        priority = {"exit": 0, "trim": 1, "watch": 2, "healthy": 3}
        attention = []
        for position in positions:
            thesis = position.get("thesis_status") or {}
            label = thesis.get("label", "healthy")
            counts[label] = counts.get(label, 0) + 1
            attention.append(
                {
                    "ticker": position.get("ticker"),
                    "label": label,
                    "summary": thesis.get("summary", ""),
                    "news_summary": position.get("news_summary") or {},
                    "market_value": position.get("market_value") or 0.0,
                }
            )
        attention.sort(
            key=lambda item: (
                priority.get(item["label"], 99),
                -(float(item["market_value"]) if item["market_value"] is not None else 0.0),
                item.get("ticker") or "",
            )
        )
        return {
            "counts": counts,
            "attention": attention[:4],
        }

    @staticmethod
    def _position_ladder(positions):
        buckets = [
            ("healthy", "Hold steady", "Constructive thesis and no active reduction path."),
            ("watch", "Watch closely", "Needs closer monitoring before Atlas escalates."),
            ("trim", "Trim candidate", "Atlas already wants to reduce exposure."),
            ("exit", "Exit candidate", "Atlas already has an exit path or exit-level thesis concern."),
        ]
        ladder = []
        for key, label, detail in buckets:
            items = [
                {
                    "ticker": position.get("ticker"),
                    "summary": (position.get("thesis_status") or {}).get("summary", ""),
                    "news_summary": position.get("news_summary") or {},
                    "market_value": position.get("market_value"),
                    "unrealized_gain_loss": position.get("unrealized_gain_loss"),
                }
                for position in positions
                if (position.get("thesis_status") or {}).get("label") == key
            ]
            items.sort(
                key=lambda item: (
                    -(float(item.get("market_value") or 0.0)),
                    str(item.get("ticker") or ""),
                )
            )
            ladder.append(
                {
                    "id": key,
                    "label": label,
                    "detail": detail,
                    "count": len(items),
                    "items": items[:6],
                }
            )
        return ladder

    @staticmethod
    def _portfolio_focus(positions):
        counts = {"healthy": 0, "watch": 0, "trim": 0, "exit": 0}
        priority = {"exit": 0, "trim": 1, "watch": 2, "healthy": 3}
        highlights = []
        for position in positions:
            thesis = position.get("thesis_status") or {}
            label = thesis.get("label") or "healthy"
            counts[label] = counts.get(label, 0) + 1
            highlights.append(
                {
                    "ticker": position.get("ticker"),
                    "anchor_id": position.get("anchor_id") or "",
                    "label": label,
                    "summary": thesis.get("summary", ""),
                    "decision_driver": position.get("decision_driver"),
                    "news_summary": position.get("news_summary") or {},
                    "market_value": position.get("market_value") or 0.0,
                    "unrealized_gain_loss": position.get("unrealized_gain_loss") or 0.0,
                }
            )
        highlights.sort(
            key=lambda item: (
                priority.get(item["label"], 99),
                -(float(item["market_value"]) if item["market_value"] is not None else 0.0),
                item.get("ticker") or "",
            )
        )
        headline = "No open simulated positions."
        if counts.get("exit"):
            headline = "Exit-level paper review is the top portfolio priority."
        elif counts.get("trim"):
            headline = "Atlas wants to reduce exposure in part of the paper book."
        elif counts.get("watch"):
            headline = "Some paper holdings need closer monitoring before escalation."
        elif counts.get("healthy"):
            headline = "Open paper holdings remain constructive right now."
        return {
            "counts": counts,
            "headline": headline,
            "highlights": highlights[:4],
        }

    @staticmethod
    def _paper_position_anchor_id(ticker):
        subject = str(ticker or "").strip().lower()
        if not subject:
            return ""
        clean = "".join(
            char if char.isalnum() else "-"
            for char in subject
        ).strip("-")
        return f"paper-position-{clean}" if clean else ""

    def _research(self, include_tasks=True):
        summary = self.research_queue.summary()
        tasks = self.research_queue.list_tasks(status="open")
        awaiting_owner = self.research_queue.list_tasks(status="awaiting_owner")
        payload = {
            "open": summary["by_status"].get("open", 0),
            "high_priority": len(summary["open_high_priority"]),
            "awaiting_owner": len(awaiting_owner),
        }
        if include_tasks:
            payload["tasks"] = [
                {
                    "id": task.get("id"),
                    "role": task.get("role"),
                    "priority": task.get("priority"),
                    "subject": task.get("subject"),
                    "prompt": task.get("prompt"),
                    "created_at": task.get("created_at"),
                    "updated_at": task.get("updated_at"),
                    "last_seen_at": task.get("last_seen_at"),
                }
                for task in self.research_queue._sorted_tasks(tasks)[:6]
            ]
        return payload

    def _reports(self, limit=12):
        reports = []
        if not self.reports_dir.exists():
            return reports
        evidence_by_report = self._report_evidence_index()
        for path in self.reports_dir.glob("*.html"):
            match = REPORT_ID_PATTERN.fullmatch(path.stem)
            if (
                not match
                or path.is_symlink()
                or self.report_document(path.stem) is None
            ):
                continue
            generated = datetime.strptime(
                f"{match.group(2)}{match.group(3)}",
                "%Y%m%d%H%M%S",
            )
            report_type = match.group(1)
            evidence = evidence_by_report.get(path.stem, {})
            leaders = evidence.get("score_leaders") or []
            leader = leaders[0] if leaders else {}
            reports.append(
                {
                    "id": path.stem,
                    "type": "Morning brief" if report_type == "morning_brief" else "Weekly summary",
                    "title": (
                        "Morning Executive Brief"
                        if report_type == "morning_brief"
                        else "Weekly Research Summary"
                    ),
                    "generated_at": generated.isoformat(timespec="seconds"),
                    "url": f"/reports/{path.stem}",
                    "coverage": evidence.get("available_securities"),
                    "leader": (
                        {
                            "ticker": leader.get("ticker"),
                            "score": leader.get("total_score"),
                        }
                        if leader.get("ticker")
                        else None
                    ),
                }
            )
        return sorted(
            reports,
            key=lambda item: item["generated_at"],
            reverse=True,
        )[:limit]

    def _report_evidence_index(self):
        payload = self._read_json(self.archive_dir / "archive_index.json") or {}
        entries = payload.get("entries")
        if not isinstance(entries, list):
            return {}
        evidence = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            report_path = Path(str(entry.get("html_report_path") or ""))
            if REPORT_ID_PATTERN.fullmatch(report_path.stem):
                evidence[report_path.stem] = entry
        return evidence

    def report_document(self, report_id):
        if not REPORT_ID_PATTERN.fullmatch(str(report_id or "")):
            return None
        path = (self.reports_dir / f"{report_id}.html").resolve()
        try:
            path.relative_to(self.reports_dir.resolve())
        except ValueError:
            return None
        if not path.is_file() or path.is_symlink():
            return None
        body = path.read_bytes()
        text = body.decode("utf-8", errors="strict")
        if UNSAFE_REPORT_HTML.search(text):
            return None
        return body

    def _history(self):
        if not self.paper_account.account_file.exists():
            return []
        return [
            {
                "timestamp": item.get("timestamp"),
                "equity": item.get("equity"),
                "atlas_return": item.get("total_return_pct"),
                "spy_return": item.get("benchmark_returns_pct", {}).get("SPY"),
                "qqq_return": item.get("benchmark_returns_pct", {}).get("QQQ"),
            }
            for item in self.paper_account.performance_history()[-30:]
        ]

    def _read_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None


def create_handler(data_service=None, web_dir=WEB_DIR):
    service = data_service or DashboardDataService()
    static_root = Path(web_dir)

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "AtlasDashboard/1.0"

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/dashboard/summary":
                self._send_json(service.build_summary())
                return
            if path == "/api/dashboard":
                self._send_json(service.build())
                return
            static_file = STATIC_FILES.get(path)
            if static_file:
                filename, content_type = static_file
                self._send_file(static_root / filename, content_type)
                return
            self.send_error(404)

        def do_POST(self):
            self.send_error(405, "Read-only dashboard")

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
            )
            super().end_headers()

        def log_message(self, format, *args):
            return

        def _send_json(self, payload):
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path, content_type):
            try:
                body = path.read_bytes()
            except FileNotFoundError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler


def run_server(host="127.0.0.1", port=8765):
    server = ThreadingHTTPServer((host, int(port)), create_handler())
    print(f"[web] Atlas owner dashboard: http://{host}:{port}")
    print("[web] Read-only local server. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
