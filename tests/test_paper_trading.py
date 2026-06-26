import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.paper_trading import PaperTradingAccount


class PaperTradingAccountTests(unittest.TestCase):
    def make_account(self, temp_dir, policy=None):
        return PaperTradingAccount(
            account_file=Path(temp_dir) / "account.json",
            ledger_file=Path(temp_dir) / "ledger.jsonl",
            policy=policy,
            clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
        )

    def execute_approved(
        self,
        account,
        side,
        ticker,
        shares,
        price,
        thesis,
        recommendation_id=None,
    ):
        proposal = account.create_proposal(
            side,
            ticker,
            shares,
            price,
            thesis,
            recommendation_id=recommendation_id,
        )
        account.record_proposal_risk_review(
            proposal["proposal_id"],
            verdict="clear",
            flags=[],
            source="test",
        )
        account.decide_proposal(proposal["proposal_id"], "approve")
        return account.execute_order(
            side,
            ticker,
            shares,
            price,
            thesis,
            recommendation_id=recommendation_id,
            proposal_id=proposal["proposal_id"],
        )

    def test_initialize_creates_account_and_ledger_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)

            state = account.initialize(100000)
            ledger = account.ledger()

        self.assertEqual(state["cash"], 100000)
        self.assertEqual(ledger[0]["event"], "account_initialized")

    def test_buy_and_sell_update_average_cost_and_realized_gain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 50.0},
            )
            account.initialize(100000)

            self.execute_approved(account, "buy", "NVDA", 100, 100, "Initial thesis.")
            self.execute_approved(account, "buy", "NVDA", 50, 120, "Add after confirmation.")
            sell = self.execute_approved(account, "sell", "NVDA", 50, 130, "Trim after target.")
            state = account.load()

        self.assertAlmostEqual(state["positions"]["NVDA"]["average_cost"], 106.666666, places=5)
        self.assertEqual(state["positions"]["NVDA"]["shares"], 100)
        self.assertAlmostEqual(sell["realized_gain_loss"], 1166.67, places=2)
        self.assertAlmostEqual(state["realized_gain_loss"], 1166.666666, places=5)

    def test_rejects_margin_short_and_position_limit_violations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)

            position_limit = account.preview_order("buy", "NVDA", 250, 100, "Too large.")
            margin = account.preview_order("buy", "NVDA", 1100, 100, "Too expensive.")
            short = account.preview_order("sell", "NVDA", 1, 100, "No holding.")

        self.assertFalse(position_limit["valid"])
        self.assertTrue(any("position limit" in error for error in position_limit["errors"]))
        self.assertTrue(any("margin is disabled" in error for error in margin["errors"]))
        self.assertTrue(any("short selling is disabled" in error for error in short["errors"]))

    def test_rejects_cash_reserve_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 100.0},
            )
            account.initialize(100000)

            result = account.preview_order("buy", "SPY", 950, 100, "Reserve breach.")

        self.assertFalse(result["valid"])
        self.assertTrue(any("cash reserve" in error for error in result["errors"]))

    def test_daily_trade_limit_uses_append_only_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 100.0, "maximum_daily_trades": 2},
            )
            account.initialize(100000)
            self.execute_approved(account, "buy", "AAA", 1, 100, "One.")
            self.execute_approved(account, "buy", "BBB", 1, 100, "Two.")

            result = account.preview_order("buy", "CCC", 1, 100, "Three.")

        self.assertFalse(result["valid"])
        self.assertIn("maximum daily paper-trade count reached", result["errors"])

    def test_status_marks_positions_without_prices_as_unvalued(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir, policy={"maximum_position_pct": 50.0})
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 10, 100, "Test.")

            status = account.status()

        self.assertEqual(status["market_value"], 0)
        self.assertIsNone(status["positions"][0]["market_value"])

    def test_recommendation_is_logged_without_changing_account(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)

            recommendation = account.record_recommendation(
                "buy",
                "NVDA",
                10,
                100,
                "Paper thesis.",
                confidence="high",
            )
            state = account.load()

        self.assertTrue(recommendation["recommendation_id"].startswith("recommendation_"))
        self.assertEqual(state["cash"], 100000)
        self.assertEqual(state["positions"], {})

    def test_trade_can_link_to_matching_recommendation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            recommendation = account.record_recommendation(
                "buy",
                "NVDA",
                10,
                100,
                "Paper thesis.",
            )

            trade = self.execute_approved(
                account,
                "buy",
                "NVDA",
                10,
                101,
                "Paper thesis.",
                recommendation_id=recommendation["recommendation_id"],
            )

        self.assertEqual(
            trade["recommendation_id"],
            recommendation["recommendation_id"],
        )

    def test_trade_rejects_mismatched_recommendation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            recommendation = account.record_recommendation(
                "buy",
                "NVDA",
                10,
                100,
                "Paper thesis.",
            )

            with self.assertRaisesRegex(ValueError, "does not match"):
                proposal = account.create_proposal(
                    "sell",
                    "NVDA",
                    1,
                    100,
                    "Different action.",
                    recommendation_id=recommendation["recommendation_id"],
                )

    def test_performance_snapshots_compare_account_with_benchmarks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 100, 100, "Paper thesis.")
            first = account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            second = account.record_performance_snapshot(
                prices={"NVDA": 110},
                benchmark_prices={"SPY": 505, "QQQ": 408},
            )
            summary = account.performance_summary()

        self.assertEqual(first["total_return_pct"], 0)
        self.assertEqual(second["total_return_pct"], 1.0)
        self.assertEqual(second["benchmark_returns_pct"]["SPY"], 1.0)
        self.assertEqual(second["benchmark_returns_pct"]["QQQ"], 2.0)
        self.assertEqual(summary["excess_return_pct"]["SPY"], 0.0)
        self.assertEqual(summary["excess_return_pct"]["QQQ"], -1.0)

    def test_proposal_feedback_compares_simulated_buy_with_benchmarks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 100, 100, "Paper thesis.")
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 505, "QQQ": 408},
            )

            feedback = account.proposal_feedback(latest_prices={"NVDA": 112})

        self.assertEqual(feedback[0]["ticker"], "NVDA")
        self.assertEqual(feedback[0]["verdict"], "working")
        self.assertEqual(feedback[0]["action_label"], "purchase")
        self.assertEqual(feedback[0]["security_return_pct"], 12.0)
        self.assertEqual(feedback[0]["benchmark_returns_pct"]["SPY"], 1.0)
        self.assertEqual(feedback[0]["benchmark_returns_pct"]["QQQ"], 2.0)

    def test_proposal_feedback_can_score_simulated_exit_as_working(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 9, 30, 0),
                    datetime(2026, 6, 2, 9, 31, 0),
                    datetime(2026, 6, 2, 9, 32, 0),
                    datetime(2026, 6, 2, 9, 33, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 100, 100, "Paper thesis.")
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            self.execute_approved(account, "sell", "NVDA", 100, 90, "Exit thesis.")
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 498, "QQQ": 397},
            )
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 497, "QQQ": 396},
            )

            feedback = account.proposal_feedback(latest_prices={"NVDA": 80})

        self.assertEqual(feedback[0]["side"], "sell")
        self.assertEqual(feedback[0]["action_label"], "exit")
        self.assertEqual(feedback[0]["verdict"], "working")
        self.assertEqual(feedback[0]["security_return_pct"], -11.1111)
        self.assertIn("sell is helping so far", feedback[0]["summary"])

    def test_proposal_feedback_can_score_simulated_trim_as_lagging(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 9, 30, 0),
                    datetime(2026, 6, 2, 9, 31, 0),
                    datetime(2026, 6, 2, 9, 32, 0),
                    datetime(2026, 6, 2, 9, 33, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 100, 100, "Paper thesis.")
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            self.execute_approved(account, "sell", "NVDA", 50, 100, "Trim thesis.")
            account.record_performance_snapshot(
                prices={"NVDA": 110},
                benchmark_prices={"SPY": 503, "QQQ": 404},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 504, "QQQ": 405},
            )

            feedback = account.proposal_feedback(latest_prices={"NVDA": 115})

        sell_feedback = next(item for item in feedback if item["side"] == "sell")
        self.assertEqual(sell_feedback["action_label"], "trim")
        self.assertEqual(sell_feedback["verdict"], "lagging")
        self.assertEqual(sell_feedback["security_return_pct"], 15.0)
        self.assertIn("looks early", sell_feedback["summary"])

    def test_proposal_feedback_summary_counts_buy_and_sell_learning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 9, 30, 0),
                    datetime(2026, 6, 3, 9, 31, 0),
                    datetime(2026, 6, 3, 9, 32, 0),
                    datetime(2026, 6, 3, 9, 33, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                    datetime(2026, 6, 4, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 100, 100, "Paper thesis.")
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 505, "QQQ": 408},
            )
            self.execute_approved(account, "sell", "NVDA", 50, 112, "Trim thesis.")
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 506, "QQQ": 409},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 90},
                benchmark_prices={"SPY": 507, "QQQ": 410},
            )

            summary = account.proposal_feedback_summary(latest_prices={"NVDA": 90})

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["judged"], 2)
        self.assertEqual(summary["verdict_counts"]["working"], 1)
        self.assertEqual(summary["verdict_counts"]["lagging"], 1)
        self.assertEqual(summary["judged_side_counts"]["buy"], 1)
        self.assertEqual(summary["judged_side_counts"]["sell"], 1)
        self.assertEqual(summary["working_side_counts"]["sell"], 1)
        self.assertEqual(summary["lagging_side_counts"]["buy"], 1)
        self.assertIn("Judged outcomes", summary["takeaways"][0])

    def test_trade_activity_describes_buys_and_sells_with_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            buy = account.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "NVDA remains a high-conviction paper entry.",
                rationale=["Atlas score is above the buy threshold."],
            )
            account.record_proposal_risk_review(
                buy["proposal_id"],
                "clear",
                [],
            )
            account.decide_proposal(buy["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "NVDA remains a high-conviction paper entry.",
                proposal_id=buy["proposal_id"],
            )
            sell = account.create_proposal(
                "sell",
                "NVDA",
                10,
                110,
                "Atlas wants to close the paper position after thesis deterioration.",
                rationale=["Thesis drift triggered an exit review."],
            )
            account.record_proposal_risk_review(
                sell["proposal_id"],
                "clear",
                [],
            )
            account.decide_proposal(sell["proposal_id"], "approve")
            account.execute_order(
                "sell",
                "NVDA",
                10,
                110,
                "Atlas wants to close the paper position after thesis deterioration.",
                proposal_id=sell["proposal_id"],
            )

            activity = account.trade_activity()

        self.assertEqual(activity[0]["action_label"], "exit")
        self.assertEqual(activity[0]["title"], "Atlas sold NVDA")
        self.assertIn("closed the simulated position", activity[0]["summary"])
        self.assertEqual(activity[1]["action_label"], "purchase")
        self.assertEqual(activity[1]["title"], "Atlas purchased NVDA")
        self.assertEqual(
            activity[1]["rationale"][0],
            "Atlas score is above the buy threshold.",
        )

    def test_performance_snapshot_requires_all_position_prices(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 10, 100, "Paper thesis.")

            with self.assertRaisesRegex(ValueError, "missing paper position prices"):
                account.record_performance_snapshot(
                    prices={},
                    benchmark_prices={"SPY": 500, "QQQ": 400},
                )

    def test_trade_statistics_and_performance_report_track_decisions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            recommendation = account.record_recommendation(
                "buy",
                "NVDA",
                10,
                100,
                "Paper thesis.",
            )
            self.execute_approved(
                account,
                "buy",
                "NVDA",
                10,
                100,
                "Paper thesis.",
                recommendation_id=recommendation["recommendation_id"],
            )
            self.execute_approved(account, "sell", "NVDA", 10, 110, "Exit thesis.")
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )

            stats = account.trade_statistics()
            report = account.render_performance_report()

        self.assertEqual(stats["recommendations"], 1)
        self.assertEqual(stats["trades"], 2)
        self.assertEqual(stats["linked_trades"], 1)
        self.assertEqual(stats["wins"], 1)
        self.assertEqual(stats["losses"], 0)
        self.assertEqual(stats["win_rate_pct"], 100)
        self.assertIn("## Decision Audit", report)
        self.assertIn("This report evaluates a simulation", report)

    def test_pending_or_rejected_proposal_cannot_execute(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            pending = account.create_proposal("buy", "NVDA", 10, 100, "Pending.")

            with self.assertRaisesRegex(ValueError, "not approved"):
                account.execute_order(
                    "buy",
                    "NVDA",
                    10,
                    100,
                    "Pending.",
                    proposal_id=pending["proposal_id"],
                )

            account.decide_proposal(pending["proposal_id"], "reject")
            with self.assertRaisesRegex(ValueError, "not approved"):
                account.execute_order(
                    "buy",
                    "NVDA",
                    10,
                    100,
                    "Pending.",
                    proposal_id=pending["proposal_id"],
                )

    def test_approved_proposal_must_match_order_size_and_security(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Approved.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
            account.decide_proposal(proposal["proposal_id"], "approve")

            with self.assertRaisesRegex(ValueError, "does not match"):
                account.execute_order(
                    "buy",
                    "NVDA",
                    11,
                    100,
                    "Approved.",
                    proposal_id=proposal["proposal_id"],
                )

    def test_approved_proposal_executes_and_is_audited(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Approved.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
            account.decide_proposal(proposal["proposal_id"], "approve")

            trade = account.execute_order(
                "buy",
                "NVDA",
                10,
                101,
                "Approved.",
                proposal_id=proposal["proposal_id"],
            )
            stats = account.trade_statistics()

        self.assertEqual(trade["proposal_id"], proposal["proposal_id"])
        self.assertEqual(stats["proposals"], 1)
        self.assertEqual(stats["proposal_linked_trades"], 1)
        self.assertEqual(stats["proposal_statuses"]["executed"], 1)

    def test_executed_proposal_cannot_be_reused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Approved.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Approved.",
                proposal_id=proposal["proposal_id"],
            )

            with self.assertRaisesRegex(ValueError, "not approved"):
                account.execute_order(
                    "buy",
                    "NVDA",
                    10,
                    100,
                    "Approved.",
                    proposal_id=proposal["proposal_id"],
                )

            status = account.proposal_status(proposal["proposal_id"])

        self.assertEqual(status, "executed")

    def test_approval_requires_non_hold_risk_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Review.")

            with self.assertRaisesRegex(ValueError, "requires a risk review"):
                account.decide_proposal(proposal["proposal_id"], "approve")

            account.record_proposal_risk_review(
                proposal["proposal_id"],
                verdict="hold",
                flags=["Sharp downside."],
            )
            with self.assertRaisesRegex(ValueError, "hold risk verdict"):
                account.decide_proposal(proposal["proposal_id"], "approve")


if __name__ == "__main__":
    unittest.main()
