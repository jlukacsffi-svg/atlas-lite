import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.paper_monitor import PaperPositionMonitor
from app.paper_trading import PaperTradingAccount


def steady_clock(*times):
    dates = list(times)
    last = dates[-1]

    def clock():
        return dates.pop(0) if dates else last

    return clock


def security(score=90, price=100, category="Core", **extra):
    data = {
        "status": "available",
        "price": price,
        "percent_change": 1.0,
        "sector": "AI & Semiconductors",
        "category": category,
        "scores": {
            "growth": score,
            "quality": score,
            "moat": score,
            "momentum": score,
            "risk": score,
        },
    }
    data.update(extra)
    return data


class PaperPositionMonitorTests(unittest.TestCase):
    def make_account_with_position(self, temp_dir):
        account = PaperTradingAccount(
            account_file=Path(temp_dir) / "account.json",
            ledger_file=Path(temp_dir) / "ledger.jsonl",
            clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
        )
        account.initialize(100000)
        proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
        account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
        account.decide_proposal(proposal["proposal_id"], "approve")
        account.execute_order(
            "buy",
            "NVDA",
            10,
            100,
            "Entry.",
            proposal_id=proposal["proposal_id"],
        )
        return account

    def test_healthy_position_receives_maintain_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=105)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "maintain")
        self.assertEqual(result["exit_proposals"], [])

    def test_from_account_applies_projection_learning_overrides(self):
        class StubAccount:
            def effective_policy(self):
                return {"maximum_partial_trims_per_position": 3}

            def projection_threshold_profile(self, latest_prices=None):
                return {
                    "monitor_overrides": {
                        "projection_add_sector_breadth_pct": 65.0,
                        "projection_add_trend_quality": 75.0,
                    }
                }

        monitor = PaperPositionMonitor.from_account(
            StubAccount(),
            latest_prices={"NVDA": 100},
        )

        self.assertEqual(monitor.projection_add_sector_breadth_pct, 65.0)
        self.assertEqual(monitor.projection_add_trend_quality, 75.0)
        self.assertEqual(monitor.maximum_partial_trims_per_position, 3)

    def test_weak_score_creates_exit_proposal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=55, price=95)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertIn("exit threshold", result["reviews"][0]["flags"][0])
        self.assertIn("reduce or exit", result["reviews"][0]["thesis"])
        self.assertEqual(result["exit_proposals"][0]["side"], "sell")
        self.assertEqual(result["exit_proposals"][0]["shares"], 10)
        self.assertEqual(
            result["exit_proposals"][0]["source"],
            "paper_monitor_v1",
        )
        self.assertIn(
            "Atlas score 55.0 is at or below the 60.0 exit threshold",
            result["exit_proposals"][0]["rationale"][0],
        )

    def test_drawdown_creates_review_without_exit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=85)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "review")
        self.assertIn("review threshold", result["reviews"][0]["flags"][0])
        self.assertEqual(result["exit_proposals"], [])

    def test_position_is_reviewed_only_once_per_day(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)
            monitor = PaperPositionMonitor()
            market_data = {"NVDA": security(score=90, price=105)}

            first = monitor.review(account, market_data)
            second = monitor.review(account, market_data)

        self.assertEqual(len(first["reviews"]), 1)
        self.assertEqual(second["reviews"], [])

    def test_benchmark_lag_creates_review_without_trim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 7, 0, 0),
                ),
            )
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 99},
                benchmark_prices={"SPY": 520, "QQQ": 416},
            )

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=99)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "review")
        self.assertIn("Benchmark review triggered", result["reviews"][0]["flags"][0])
        self.assertEqual(result["exit_proposals"], [])

    def test_severe_benchmark_lag_creates_trim_proposal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 7, 0, 0),
                    datetime(2026, 6, 3, 7, 1, 0),
                ),
            )
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 94},
                benchmark_prices={"SPY": 525, "QQQ": 420},
            )

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=94)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertIn("Trim rule triggered", result["reviews"][0]["flags"][0])
        self.assertIn("Benchmark lag is 11.00 percentage points", result["reviews"][0]["thesis"])
        self.assertEqual(result["exit_proposals"][0]["side"], "sell")
        self.assertEqual(result["exit_proposals"][0]["shares"], 5)

    def test_third_partial_trim_escalates_to_full_exit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)
            for shares in (5, 2.5):
                proposal = account.create_proposal(
                    "sell",
                    "NVDA",
                    shares,
                    90,
                    "Paper trim.",
                )
                account.record_proposal_risk_review(
                    proposal["proposal_id"],
                    "clear",
                    [],
                )
                account.decide_proposal(proposal["proposal_id"], "approve")
                account.execute_order(
                    "sell",
                    "NVDA",
                    shares,
                    90,
                    "Paper trim.",
                    proposal_id=proposal["proposal_id"],
                )

            verdict, flags, sell_shares = PaperPositionMonitor()._review_decision(
                category="Core",
                score=90,
                score_text="90.0",
                return_pct=-10.0,
                lag={
                    "lag_pct": -9.0,
                    "snapshots": 5,
                    "security_return_pct": -8.0,
                    "weakest_benchmark": "SPY",
                    "weakest_benchmark_return_pct": 1.0,
                },
                current_shares=2.5,
                account=account,
                ticker="NVDA",
                news_signal={},
                projection={},
            )

        self.assertEqual(verdict, "exit")
        self.assertEqual(sell_shares, 2.5)
        self.assertIn("Trim escalation exit triggered", flags[-1])

    def test_new_entry_resets_partial_trim_escalation_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)
            for shares in (5, 5):
                proposal = account.create_proposal(
                    "sell",
                    "NVDA",
                    shares,
                    90,
                    "Paper sale.",
                )
                account.record_proposal_risk_review(
                    proposal["proposal_id"],
                    "clear",
                    [],
                )
                account.decide_proposal(proposal["proposal_id"], "approve")
                account.execute_order(
                    "sell",
                    "NVDA",
                    shares,
                    90,
                    "Paper sale.",
                    proposal_id=proposal["proposal_id"],
                )
            proposal = account.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "New entry.",
            )
            account.record_proposal_risk_review(
                proposal["proposal_id"],
                "clear",
                [],
            )
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "New entry.",
                proposal_id=proposal["proposal_id"],
            )

            trim_count = PaperPositionMonitor._partial_trims_since_entry(
                account,
                "NVDA",
            )

        self.assertEqual(trim_count, 0)

    def test_review_can_include_multiple_reasons(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=68, price=85)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "review")
        self.assertEqual(len(result["reviews"][0]["flags"]), 2)
        self.assertIn("Atlas score 68.0 is below the 70.0 review threshold.", result["reviews"][0]["flags"])
        self.assertIn(
            "Position return -15.00% is below the -10.00% review threshold.",
            result["reviews"][0]["flags"],
        )

    def test_strong_winner_can_create_add_on_buy_proposal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                    datetime(2026, 6, 4, 7, 0, 0),
                ),
            )
            account.initialize(100000)
            account.update_policy(
                {"strategy_target_position_pct": 6.0},
                source="test",
            )
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 108},
                benchmark_prices={"SPY": 504, "QQQ": 404},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            result = PaperPositionMonitor().review(
                account,
                {
                    "NVDA": security(
                        score=94,
                        price=115,
                        percent_change=1.2,
                        momentum_metrics={
                            "trend_regime": "leadership",
                            "trend_quality_score": 79.0,
                        },
                    ),
                    "AMD": security(score=88, price=101, percent_change=0.7),
                    "AVGO": security(score=89, price=102, percent_change=0.9),
                    "SPY": {
                        "status": "available",
                        "price": 506,
                        "percent_change": 0.4,
                        "sector": "Benchmark ETF",
                    },
                    "QQQ": {
                        "status": "available",
                        "price": 406,
                        "percent_change": 0.5,
                        "sector": "Benchmark ETF",
                    },
                },
            )

        self.assertEqual(result["reviews"][0]["verdict"], "maintain")
        self.assertEqual(len(result["exit_proposals"]), 1)
        self.assertEqual(result["exit_proposals"][0]["side"], "buy")
        self.assertIn("winner add rule", result["exit_proposals"][0]["thesis"].lower())
        self.assertIn("Winner add rule triggered", result["exit_proposals"][0]["rationale"][0])

    def test_repeated_review_weakness_escalates_to_trim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 7, 0, 0),
                    datetime(2026, 6, 4, 7, 0, 0),
                    datetime(2026, 6, 5, 7, 0, 0),
                ),
            )
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_position_review(
                "NVDA",
                "review",
                97,
                -3.0,
                69.0,
                ["Prior review weakness."],
                "Prior review.",
            )
            account.record_position_review(
                "NVDA",
                "review",
                96,
                -4.0,
                68.0,
                ["Second review weakness."],
                "Second review.",
            )

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=69, price=95)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertIn("Repeated review trim triggered", result["reviews"][0]["flags"][-1])
        self.assertEqual(result["exit_proposals"][0]["side"], "sell")
        self.assertEqual(result["exit_proposals"][0]["shares"], 5)

    def test_negative_company_news_can_trigger_trim_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {
                    "NVDA": security(score=88, price=97)
                    | {
                        "news_signal": {
                            "signal_label": "adverse",
                            "negative_count": 2,
                            "positive_count": 0,
                            "signal_score": 18.0,
                        }
                    }
                },
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertIn("News risk trim triggered", " ".join(result["reviews"][0]["flags"]))
        self.assertEqual(result["exit_proposals"][0]["shares"], 5)

    def test_single_high_impact_negative_news_event_can_trigger_trim_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {
                    "NVDA": security(score=88, price=97)
                    | {
                        "news_signal": {
                            "signal_label": "adverse",
                            "negative_count": 1,
                            "positive_count": 0,
                            "negative_weight": 3.3,
                            "high_impact_negative_count": 1,
                            "dominant_event_type": "legal_risk",
                            "signal_score": 24.0,
                        }
                    }
                },
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertIn("News risk trim triggered", " ".join(result["reviews"][0]["flags"]))
        self.assertIn("legal risk", " ".join(result["reviews"][0]["flags"]))
        self.assertEqual(result["exit_proposals"][0]["shares"], 5)

    def test_projection_de_risk_can_trigger_trim_before_harder_exit_rules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 7, 0, 0),
                    datetime(2026, 6, 3, 7, 1, 0),
                ),
            )
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 97},
                benchmark_prices={"SPY": 510, "QQQ": 408},
            )

            result = PaperPositionMonitor().review(
                account,
                {
                    "NVDA": security(
                        score=88,
                        price=97,
                        percent_change=-0.5,
                        momentum_metrics={
                            "trend_regime": "fragile",
                            "trend_quality_score": 58.0,
                        },
                    ),
                    "AMD": security(score=90, price=101, percent_change=-1.0),
                    "AVGO": security(score=91, price=102, percent_change=-0.8),
                    "SPY": {
                        "status": "available",
                        "price": 510,
                        "percent_change": 1.8,
                        "sector": "Benchmark ETF",
                    },
                    "QQQ": {
                        "status": "available",
                        "price": 408,
                        "percent_change": 1.5,
                        "sector": "Benchmark ETF",
                    },
                },
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertIn(
            "Projection de-risk triggered",
            " ".join(result["reviews"][0]["flags"]),
        )
        self.assertIn("Projection posture is de risk", result["reviews"][0]["thesis"])
        self.assertEqual(result["exit_proposals"][0]["shares"], 5)

    def test_winner_add_is_blocked_when_projection_confirmation_is_not_supportive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                    datetime(2026, 6, 4, 7, 0, 0),
                ),
            )
            account.initialize(100000)
            account.update_policy(
                {"strategy_target_position_pct": 6.0},
                source="test",
            )
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 108},
                benchmark_prices={"SPY": 504, "QQQ": 404},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            result = PaperPositionMonitor().review(
                account,
                {
                    "NVDA": security(
                        score=94,
                        price=115,
                        percent_change=0.6,
                        momentum_metrics={
                            "trend_regime": "leadership",
                            "trend_quality_score": 78.0,
                        },
                    ),
                    "AMD": security(score=88, price=99, percent_change=-0.4),
                    "AVGO": security(score=89, price=98, percent_change=-0.2),
                    "SPY": {
                        "status": "available",
                        "price": 506,
                        "percent_change": 0.4,
                        "sector": "Benchmark ETF",
                    },
                    "QQQ": {
                        "status": "available",
                        "price": 406,
                        "percent_change": 0.5,
                        "sector": "Benchmark ETF",
                    },
                },
            )

        self.assertEqual(result["reviews"][0]["verdict"], "review")
        self.assertIn(
            "Projection caution triggered",
            " ".join(result["reviews"][0]["flags"]),
        )
        self.assertEqual(result["exit_proposals"], [])


if __name__ == "__main__":
    unittest.main()
