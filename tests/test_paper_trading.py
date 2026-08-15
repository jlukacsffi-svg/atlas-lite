import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.paper_trading import PaperTradingAccount


def stepped_clock(*times):
    dates = list(times)
    last = dates[-1]

    def clock():
        return dates.pop(0) if dates else last

    return clock


def incremental_clock(start):
    current = start

    def clock():
        nonlocal current
        value = current
        current = current + timedelta(minutes=1)
        return value

    return clock


class PaperTradingAccountTests(unittest.TestCase):
    def make_account(self, temp_dir, policy=None):
        return PaperTradingAccount(
            account_file=Path(temp_dir) / "account.json",
            ledger_file=Path(temp_dir) / "ledger.jsonl",
            policy=policy,
            clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
        )

    def test_feedback_summary_accepts_precomputed_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)

            def unexpected_feedback(**_kwargs):
                self.fail("proposal feedback should not be recalculated")

            account.proposal_feedback = unexpected_feedback
            summary = account.proposal_feedback_summary(rows=[])

        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["judged"], 0)

    def test_ledger_cache_reuses_reads_and_invalidates_after_append(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)

            first = account.ledger()
            second = account.ledger()
            account._append_event(
                {
                    "event": "test_event",
                    "timestamp": "2026-06-06T09:31:00",
                }
            )
            third = account.ledger()

        self.assertIs(first, second)
        self.assertIsNot(second, third)
        self.assertEqual(len(third), len(first) + 1)
        self.assertEqual(third[-1]["event"], "test_event")

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

    def test_trade_pressure_profile_can_raise_daily_trade_limit_after_constructive_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 3},
                clock=incremental_clock(datetime(2026, 6, 1, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("AAA", "BBB", "CCC"):
                self.execute_approved(account, "buy", ticker, 10, 100, f"{ticker} entry.")
            account.record_performance_snapshot(
                prices={"AAA": 100, "BBB": 100, "CCC": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"AAA": 108, "BBB": 107, "CCC": 106},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"AAA": 111, "BBB": 110, "CCC": 109},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"AAA": 112, "BBB": 111, "CCC": 110},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            profile = account.trade_pressure_profile(
                latest_prices={"AAA": 112, "BBB": 111, "CCC": 110}
            )

        self.assertTrue(profile["active"])
        self.assertEqual(profile["policy_overrides"]["maximum_daily_trades"], 6)

    def test_trade_pressure_profile_can_lower_daily_trade_limit_after_lagging_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 3},
                clock=incremental_clock(datetime(2026, 6, 1, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("AAA", "BBB", "CCC"):
                self.execute_approved(account, "buy", ticker, 10, 100, f"{ticker} entry.")
            account.record_performance_snapshot(
                prices={"AAA": 100, "BBB": 100, "CCC": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"AAA": 95, "BBB": 94, "CCC": 93},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"AAA": 91, "BBB": 90, "CCC": 89},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"AAA": 90, "BBB": 89, "CCC": 88},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            profile = account.trade_pressure_profile(
                latest_prices={"AAA": 90, "BBB": 89, "CCC": 88}
            )

        self.assertTrue(profile["active"])
        self.assertEqual(profile["policy_overrides"]["maximum_daily_trades"], 4)

    def test_validate_order_uses_adaptive_daily_trade_limit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 100.0, "maximum_daily_trades": 2},
            )
            account.initialize(100000)
            account.trade_pressure_profile = lambda latest_prices=None: {
                "policy_overrides": {"maximum_daily_trades": 3}
            }
            self.execute_approved(account, "buy", "AAA", 1, 100, "One.")
            self.execute_approved(account, "buy", "BBB", 1, 100, "Two.")

            result = account.preview_order("buy", "CCC", 1, 100, "Three.")

        self.assertTrue(result["valid"])

    def test_benchmark_preference_profile_can_prefer_qqq_when_it_separates_results_better(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 3},
                clock=incremental_clock(datetime(2026, 6, 1, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("AAA", "BBB", "CCC"):
                self.execute_approved(account, "buy", ticker, 10, 100, f"{ticker} entry.")
            account.record_performance_snapshot(
                prices={"AAA": 100, "BBB": 100, "CCC": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"AAA": 108, "BBB": 103.5, "CCC": 100},
                benchmark_prices={"SPY": 505, "QQQ": 420},
            )

            profile = account.benchmark_preference_profile(
                latest_prices={"AAA": 108, "BBB": 103.5, "CCC": 100}
            )

        self.assertTrue(profile["active"])
        self.assertEqual(
            profile["strategy_overrides"]["strategy_preferred_benchmark"], "QQQ"
        )

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

    def test_auto_managed_cycle_approves_and_executes_clear_proposal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 50.0},
            )
            account.initialize(100000)
            account.update_policy({"auto_manage_enabled": True}, source="test")
            proposal = account.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "Auto-manage entry.",
            )
            account.record_proposal_risk_review(
                proposal["proposal_id"],
                verdict="clear",
                flags=[],
                source="test",
            )

            result = account.run_autonomous_cycle({"NVDA": 101}, source="test_auto")
            state = account.load()
            self.assertTrue(result["enabled"])
            self.assertEqual(result["approved"], [proposal["proposal_id"]])
            self.assertEqual(len(result["executed"]), 1)
            self.assertEqual(state["positions"]["NVDA"]["shares"], 10)
            self.assertEqual(account.proposal_status(proposal["proposal_id"]), "executed")

    def test_auto_managed_cycle_rejects_hold_risk_proposal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            account.update_policy({"auto_manage_enabled": True}, source="test")
            proposal = account.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "Auto-manage entry.",
            )
            account.record_proposal_risk_review(
                proposal["proposal_id"],
                verdict="hold",
                flags=["too much risk"],
                source="test",
            )

            result = account.run_autonomous_cycle({"NVDA": 101}, source="test_auto")
            self.assertEqual(result["rejected"], [proposal["proposal_id"]])
            self.assertEqual(result["executed"], [])
            self.assertEqual(account.proposal_status(proposal["proposal_id"]), "rejected")

    def test_auto_managed_cycle_pauses_pending_and_approved_buys_on_limited_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 50.0},
            )
            account.initialize(100000)
            account.update_policy({"auto_manage_enabled": True}, source="test")
            pending = account.create_proposal(
                "buy", "NVDA", 10, 100, "Pending entry."
            )
            account.record_proposal_risk_review(
                pending["proposal_id"],
                verdict="clear",
                flags=[],
                source="test",
            )
            approved = account.create_proposal(
                "buy", "AMD", 10, 100, "Approved entry."
            )
            account.record_proposal_risk_review(
                approved["proposal_id"],
                verdict="clear",
                flags=[],
                source="test",
            )
            account.decide_proposal(approved["proposal_id"], "approve")
            market_data = {
                ticker: {
                    "status": "available",
                    "price": 100,
                    "percent_change": 0,
                    "daily_change_quality": "complete",
                }
                for ticker in ("NVDA", "AMD", "SPY", "QQQ", "MSFT")
            }

            result = account.run_autonomous_cycle(
                {"NVDA": 101, "AMD": 99},
                source="test_auto",
                market_data=market_data,
            )

            self.assertEqual(result["entry_evidence"]["status"], "limited")
            self.assertEqual(result["approved"], [])
            self.assertEqual(result["executed"], [])
            self.assertEqual(len(result["skipped"]), 2)
            self.assertEqual(account.proposal_status(pending["proposal_id"]), "pending")
            self.assertEqual(account.proposal_status(approved["proposal_id"]), "approved")
            self.assertEqual(account.load()["positions"], {})

    def test_auto_managed_cycle_keeps_risk_exit_active_on_limited_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            buy = account.create_proposal("buy", "NVDA", 10, 100, "Initial entry.")
            account.record_proposal_risk_review(
                buy["proposal_id"],
                verdict="clear",
                flags=[],
                source="test",
            )
            account.decide_proposal(buy["proposal_id"], "approve")
            account.execute_order(
                "buy", "NVDA", 10, 100, "Initial entry.", proposal_id=buy["proposal_id"]
            )
            account.update_policy({"auto_manage_enabled": True}, source="test")
            sell = account.create_proposal("sell", "NVDA", 10, 95, "Risk exit.")
            account.record_proposal_risk_review(
                sell["proposal_id"],
                verdict="clear",
                flags=[],
                source="test",
            )
            market_data = {
                ticker: {
                    "status": "available",
                    "price": 95,
                    "percent_change": 0,
                    "daily_change_quality": "complete",
                }
                for ticker in ("NVDA", "AMD", "SPY", "QQQ", "MSFT")
            }

            result = account.run_autonomous_cycle(
                {"NVDA": 95},
                source="test_auto",
                market_data=market_data,
            )

            self.assertEqual(result["entry_evidence"]["status"], "limited")
            self.assertEqual(result["approved"], [sell["proposal_id"]])
            self.assertEqual(len(result["executed"]), 1)
            self.assertNotIn("NVDA", account.load()["positions"])

    def test_update_policy_accepts_strategy_tuning_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)

            policy = account.update_policy(
                {
                    "strategy_minimum_buy_score": 90.0,
                    "strategy_maximum_exit_score": 58.0,
                    "strategy_target_position_pct": 6.0,
                    "strategy_maximum_new_proposals": 5,
                    "strategy_benchmark_excess_weight": 2.5,
                    "strategy_preferred_benchmark": "qqq",
                    "strategy_trend_quality_weight": 0.35,
                    "strategy_sector_repeat_penalty": 1.5,
                },
                source="test",
            )

        self.assertEqual(policy["strategy_minimum_buy_score"], 90.0)
        self.assertEqual(policy["strategy_maximum_exit_score"], 58.0)
        self.assertEqual(policy["strategy_target_position_pct"], 6.0)
        self.assertEqual(policy["strategy_maximum_new_proposals"], 5)
        self.assertEqual(policy["strategy_benchmark_excess_weight"], 2.5)
        self.assertEqual(policy["strategy_preferred_benchmark"], "QQQ")
        self.assertEqual(policy["strategy_trend_quality_weight"], 0.35)
        self.assertEqual(policy["strategy_sector_repeat_penalty"], 1.5)

    def test_projection_threshold_profile_tightens_winner_add_gates_after_lagging_buys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 2},
                clock=incremental_clock(datetime(2026, 6, 6, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("NVDA", "AMD"):
                proposal = account.create_proposal(
                    "buy",
                    ticker,
                    10,
                    100,
                    "Projection-led entry.",
                    rationale=[
                        "Projection watch remains supportive with 72% sector breadth and a leadership trend posture."
                    ],
                )
                account.record_proposal_risk_review(
                    proposal["proposal_id"],
                    "clear",
                    [],
                    source="test",
                )
                account.decide_proposal(proposal["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    "Projection-led entry.",
                    proposal_id=proposal["proposal_id"],
                )

            account.record_performance_snapshot(
                prices={"NVDA": 100, "AMD": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 94, "AMD": 95},
                benchmark_prices={"SPY": 505, "QQQ": 404},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 88, "AMD": 90},
                benchmark_prices={"SPY": 510, "QQQ": 408},
            )

            profile = account.projection_threshold_profile(
                latest_prices={"NVDA": 88, "AMD": 90}
            )

        self.assertTrue(profile["enabled"])
        self.assertTrue(profile["active"])
        self.assertEqual(
            profile["monitor_overrides"]["projection_add_sector_breadth_pct"], 65.0
        )
        self.assertEqual(
            profile["monitor_overrides"]["projection_add_trend_quality"], 75.0
        )

    def test_projection_threshold_profile_makes_caution_sells_earlier_after_helpful_trims(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 2},
                clock=incremental_clock(datetime(2026, 6, 6, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("NVDA", "AMD"):
                buy = account.create_proposal("buy", ticker, 10, 100, "Entry.")
                account.record_proposal_risk_review(
                    buy["proposal_id"], "clear", [], source="test"
                )
                account.decide_proposal(buy["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    "Entry.",
                    proposal_id=buy["proposal_id"],
                )
                sell = account.create_proposal(
                    "sell",
                    ticker,
                    10,
                    100,
                    "Projection caution exit.",
                    rationale=[
                        "Projection caution triggered: Atlas wants more proof because benchmark leadership, sector participation, or news tone is no longer clearly supportive."
                    ],
                )
                account.record_proposal_risk_review(
                    sell["proposal_id"], "clear", [], source="test"
                )
                account.decide_proposal(sell["proposal_id"], "approve")
                account.execute_order(
                    "sell",
                    ticker,
                    10,
                    100,
                    "Projection caution exit.",
                    proposal_id=sell["proposal_id"],
                )

            account.record_performance_snapshot(
                prices={"NVDA": 100, "AMD": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 94, "AMD": 95},
                benchmark_prices={"SPY": 505, "QQQ": 404},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 88, "AMD": 90},
                benchmark_prices={"SPY": 510, "QQQ": 408},
            )

            profile = account.projection_threshold_profile(
                latest_prices={"NVDA": 88, "AMD": 90}
            )

        self.assertTrue(profile["active"])
        self.assertEqual(
            profile["monitor_overrides"]["projection_trim_excess_pct"], -2.0
        )
        self.assertEqual(
            profile["monitor_overrides"]["projection_review_excess_pct"], 0.5
        )

    def test_entry_constraint_study_aggregates_forward_observations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
            )
            account.initialize(100000)
            account.record_entry_constraint_observation(
                {
                    "event": "entry_constraint_observation",
                    "candidate_universe": 5,
                    "unheld_candidates": 4,
                    "score_pass_candidates": 2,
                    "confirmation_blocked_candidates": 1,
                    "available_buy_slots": 2,
                    "target_position_pct": 5.0,
                    "scenarios": [
                        {
                            "label": "Current entry rules",
                            "minimum_buy_score": 88.0,
                            "eligible_ideas": 1,
                            "selected_ideas": 1,
                            "estimated_deployable_pct": 5.0,
                        }
                    ],
                }
            )
            study = account.entry_constraint_study()

        self.assertTrue(study["activated"])
        self.assertFalse(study["policy_changed"])
        self.assertEqual(study["observations"], 1)
        self.assertEqual(study["scenarios"][0]["average_eligible_ideas"], 1.0)

    def test_entry_strategy_profile_loosens_buy_threshold_after_constructive_buys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 2},
                clock=incremental_clock(datetime(2026, 6, 6, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("NVDA", "AMD"):
                buy = account.create_proposal("buy", ticker, 10, 100, "Constructive entry.")
                account.record_proposal_risk_review(buy["proposal_id"], "clear", [], source="test")
                account.decide_proposal(buy["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    "Constructive entry.",
                    proposal_id=buy["proposal_id"],
                )
            account.record_performance_snapshot(
                prices={"NVDA": 100, "AMD": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 108, "AMD": 107},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 111, "AMD": 110},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112, "AMD": 111},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            profile = account.entry_strategy_profile(
                latest_prices={"NVDA": 112, "AMD": 111}
            )

        self.assertTrue(profile["active"])
        self.assertEqual(profile["buy_stats"]["working"], 2)
        self.assertEqual(profile["persistence_stats"]["working"], 2)
        self.assertEqual(profile["strategy_overrides"]["strategy_minimum_buy_score"], 87.0)
        self.assertEqual(profile["strategy_overrides"]["strategy_target_position_pct"], 5.5)
        self.assertEqual(profile["strategy_overrides"]["strategy_maximum_new_proposals"], 4)
        self.assertEqual(profile["strategy_overrides"]["strategy_sector_repeat_penalty"], 2.0)

    def test_entry_strategy_profile_tightens_buy_threshold_after_lagging_buys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 2},
                clock=incremental_clock(datetime(2026, 6, 6, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("NVDA", "AMD"):
                buy = account.create_proposal("buy", ticker, 10, 100, "Lagging entry.")
                account.record_proposal_risk_review(buy["proposal_id"], "clear", [], source="test")
                account.decide_proposal(buy["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    "Lagging entry.",
                    proposal_id=buy["proposal_id"],
                )
            account.record_performance_snapshot(
                prices={"NVDA": 100, "AMD": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 95, "AMD": 94},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 91, "AMD": 90},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 90, "AMD": 89},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            profile = account.entry_strategy_profile(
                latest_prices={"NVDA": 90, "AMD": 89}
            )

        self.assertTrue(profile["active"])
        self.assertEqual(profile["buy_stats"]["lagging"], 2)
        self.assertEqual(profile["persistence_stats"]["lagging"], 2)
        self.assertEqual(profile["strategy_overrides"]["strategy_minimum_buy_score"], 90.0)
        self.assertEqual(profile["strategy_overrides"]["strategy_target_position_pct"], 4.5)
        self.assertEqual(profile["strategy_overrides"]["strategy_maximum_new_proposals"], 2)
        self.assertEqual(profile["strategy_overrides"]["strategy_benchmark_excess_weight"], 2.0)
        self.assertEqual(profile["strategy_overrides"]["strategy_trend_quality_weight"], 0.3)
        self.assertEqual(profile["strategy_overrides"]["strategy_sector_repeat_penalty"], 4.0)

    def test_entry_strategy_profile_uses_benchmark_scorecard_for_sector_pacing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"projection_learning_min_judged_trades": 2},
            )
            account.initialize(100000)
            rows = [
                {
                    "side": "buy",
                    "verdict": "working",
                    "security_return_pct": 8.0,
                    "benchmark_returns_pct": {"SPY": 1.0, "QQQ": 2.0},
                },
                {
                    "side": "buy",
                    "verdict": "working",
                    "security_return_pct": 7.0,
                    "benchmark_returns_pct": {"SPY": 1.0, "QQQ": 2.0},
                },
            ]

            profile = account._entry_strategy_profile_from_rows(rows)

        self.assertTrue(profile["active"])
        self.assertEqual(profile["benchmark_rotation_stats"]["benchmark"], "SPY")
        self.assertEqual(profile["benchmark_rotation_stats"]["working_rate_pct"], 100.0)
        self.assertEqual(profile["strategy_overrides"]["strategy_target_position_pct"], 5.5)
        self.assertEqual(profile["strategy_overrides"]["strategy_maximum_new_proposals"], 4)
        self.assertEqual(profile["strategy_overrides"]["strategy_sector_repeat_penalty"], 2.5)
        self.assertEqual(profile["adjustments"][0]["label"], "Benchmark-led target size")

    def test_entry_strategy_profile_tightens_sector_pacing_when_benchmark_buys_lag(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"projection_learning_min_judged_trades": 2},
            )
            account.initialize(100000)
            rows = [
                {
                    "side": "buy",
                    "verdict": "lagging",
                    "security_return_pct": -6.0,
                    "benchmark_returns_pct": {"SPY": 1.0, "QQQ": 2.0},
                },
                {
                    "side": "buy",
                    "verdict": "lagging",
                    "security_return_pct": -5.0,
                    "benchmark_returns_pct": {"SPY": 1.0, "QQQ": 2.0},
                },
            ]

            profile = account._entry_strategy_profile_from_rows(rows)

        self.assertTrue(profile["active"])
        self.assertEqual(profile["benchmark_rotation_stats"]["benchmark"], "QQQ")
        self.assertEqual(profile["benchmark_rotation_stats"]["working_rate_pct"], 0.0)
        self.assertEqual(profile["strategy_overrides"]["strategy_target_position_pct"], 4.5)
        self.assertEqual(profile["strategy_overrides"]["strategy_maximum_new_proposals"], 2)
        self.assertEqual(profile["strategy_overrides"]["strategy_sector_repeat_penalty"], 3.5)
        self.assertEqual(profile["adjustments"][0]["direction"], "smaller")

    def test_projection_threshold_profile_can_retune_from_confirmation_weakness_sell_learning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"projection_learning_min_judged_trades": 2},
                clock=incremental_clock(datetime(2026, 6, 6, 9, 30, 0)),
            )
            account.initialize(100000)
            for ticker in ("NVDA", "AMD"):
                buy = account.create_proposal("buy", ticker, 10, 100, "Entry.")
                account.record_proposal_risk_review(
                    buy["proposal_id"], "clear", [], source="test"
                )
                account.decide_proposal(buy["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    "Entry.",
                    proposal_id=buy["proposal_id"],
                )
                sell = account.create_proposal(
                    "sell",
                    ticker,
                    10,
                    100,
                    "Trim trigger: Atlas sees enough thesis or confirmation weakness to reduce exposure.",
                    rationale=[
                        "Latest move is -3.50%, which supports a more defensive posture.",
                        "Risk review flags: recurring thesis risk, position above preferred size.",
                    ],
                )
                account.record_proposal_risk_review(
                    sell["proposal_id"], "clear", ["recurring thesis risk"], source="test"
                )
                account.decide_proposal(sell["proposal_id"], "approve")
                account.execute_order(
                    "sell",
                    ticker,
                    10,
                    100,
                    "Trim trigger: Atlas sees enough thesis or confirmation weakness to reduce exposure.",
                    proposal_id=sell["proposal_id"],
                )

            account.record_performance_snapshot(
                prices={"NVDA": 100, "AMD": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 94, "AMD": 95},
                benchmark_prices={"SPY": 505, "QQQ": 404},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 88, "AMD": 90},
                benchmark_prices={"SPY": 510, "QQQ": 408},
            )

            profile = account.projection_threshold_profile(
                latest_prices={"NVDA": 88, "AMD": 90}
            )

        self.assertTrue(profile["active"])
        self.assertEqual(profile["protective_stats"]["judged"], 0)
        self.assertEqual(profile["sell_trigger_stats"]["judged"], 2)
        self.assertEqual(profile["sell_trigger_stats"]["working"], 2)
        self.assertEqual(
            profile["monitor_overrides"]["projection_trim_excess_pct"], -2.0
        )
        self.assertEqual(
            profile["monitor_overrides"]["projection_review_excess_pct"], 0.5
        )

    def test_projection_threshold_profile_uses_benchmark_scorecard_for_exit_strictness(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"projection_learning_min_judged_trades": 2},
            )
            account.initialize(100000)
            rows = [
                {
                    "side": "sell",
                    "verdict": "working",
                    "security_return_pct": -8.0,
                    "benchmark_returns_pct": {"SPY": 0.0, "QQQ": 1.0},
                },
                {
                    "side": "sell",
                    "verdict": "working",
                    "security_return_pct": -6.0,
                    "benchmark_returns_pct": {"SPY": 0.0, "QQQ": 2.0},
                },
            ]

            profile = account._projection_threshold_profile_from_rows(rows)

        self.assertTrue(profile["active"])
        self.assertEqual(profile["benchmark_exit_stats"]["benchmark"], "QQQ")
        self.assertEqual(profile["benchmark_exit_stats"]["working_rate_pct"], 100.0)
        self.assertEqual(
            profile["monitor_overrides"]["projection_trim_excess_pct"], -2.0
        )
        self.assertEqual(
            profile["monitor_overrides"]["projection_review_excess_pct"], 0.5
        )
        self.assertEqual(
            profile["adjustments"][0]["label"],
            "Benchmark-scorecard trim trigger",
        )

    def test_projection_threshold_profile_slows_exits_when_benchmark_scorecard_lags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"projection_learning_min_judged_trades": 2},
            )
            account.initialize(100000)
            rows = [
                {
                    "side": "sell",
                    "verdict": "lagging",
                    "security_return_pct": 8.0,
                    "benchmark_returns_pct": {"SPY": 0.0, "QQQ": 1.0},
                },
                {
                    "side": "sell",
                    "verdict": "lagging",
                    "security_return_pct": 7.0,
                    "benchmark_returns_pct": {"SPY": 0.0, "QQQ": 2.0},
                },
            ]

            profile = account._projection_threshold_profile_from_rows(rows)

        self.assertTrue(profile["active"])
        self.assertEqual(profile["benchmark_exit_stats"]["benchmark"], "QQQ")
        self.assertEqual(profile["benchmark_exit_stats"]["working_rate_pct"], 0.0)
        self.assertEqual(
            profile["monitor_overrides"]["projection_trim_excess_pct"], -3.0
        )
        self.assertEqual(
            profile["monitor_overrides"]["projection_review_excess_pct"], -0.5
        )
        self.assertEqual(profile["adjustments"][0]["direction"], "slower")

    def test_performance_snapshots_compare_account_with_benchmarks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                datetime(2026, 6, 1, 9, minute, 0)
                for minute in range(30, 60)
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
                datetime(2026, 6, 1, 9, minute, 0)
                for minute in range(30, 60)
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
        self.assertIsNone(feedback[0]["decision_driver"])

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
            buy = account.create_proposal(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                rationale=[
                    "Projection watch remains supportive with 70% sector breadth and a leadership trend posture.",
                ],
            )
            account.record_proposal_risk_review(buy["proposal_id"], "clear", [])
            account.decide_proposal(buy["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                proposal_id=buy["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 505, "QQQ": 408},
            )
            sell = account.create_proposal(
                "sell",
                "NVDA",
                50,
                112,
                "Trim thesis.",
                rationale=[
                    "Projection caution triggered: Atlas wants more proof because benchmark leadership, sector participation, or news tone is no longer clearly supportive.",
                ],
            )
            account.record_proposal_risk_review(sell["proposal_id"], "clear", [])
            account.decide_proposal(sell["proposal_id"], "approve")
            account.execute_order(
                "sell",
                "NVDA",
                50,
                112,
                "Trim thesis.",
                proposal_id=sell["proposal_id"],
            )
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
        self.assertEqual(
            summary["decision_driver_learning"][0]["label"],
            "Projection caution",
        )
        self.assertEqual(
            summary["decision_driver_learning"][1]["label"],
            "Projection-supported add",
        )
        self.assertEqual(
            summary["sell_trigger_learning"][0]["label"],
            "Confirmation weakness",
        )
        self.assertEqual(summary["sell_trigger_learning"][0]["working"], 1)
        self.assertEqual(summary["horizon_learning"][0]["label"], "1-snapshot persistence")
        self.assertEqual(summary["horizon_learning"][1]["label"], "3-snapshot persistence")
        self.assertEqual(summary["horizon_learning"][1]["working_rate_pct"], 100.0)
        self.assertEqual(summary["benchmark_scorecard"]["leader"]["benchmark"], "SPY")
        spy_scorecard = summary["benchmark_scorecard"]["scorecards"][0]
        self.assertEqual(spy_scorecard["benchmark"], "SPY")
        self.assertEqual(spy_scorecard["judged"], 2)
        self.assertEqual(spy_scorecard["working"], 1)
        self.assertEqual(spy_scorecard["lagging"], 1)
        self.assertEqual(spy_scorecard["working_rate_pct"], 50.0)
        self.assertGreater(spy_scorecard["avg_decision_edge_pct"], 4.0)
        self.assertTrue(
            any("Best projection read so far" in item for item in summary["takeaways"])
        )
        self.assertTrue(
            any("Best sell trigger so far" in item for item in summary["takeaways"])
        )
        self.assertTrue(
            any("Longest persistence read so far" in item for item in summary["takeaways"])
        )
        self.assertTrue(
            any("Benchmark scorecard leader" in item for item in summary["takeaways"])
        )

    def test_proposal_feedback_summary_scores_sector_gate_outcomes_from_recommendations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                datetime(2026, 6, 1, 9, minute, 0)
                for minute in range(30, 60)
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            recommendation = account.record_recommendation(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                rationale=[
                    "Sector learning gate: Cleared stronger lagging-sector confirmation. 6 of 6 stronger confirmation checks passed.",
                ],
            )
            buy = account.create_proposal(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                recommendation_id=recommendation["recommendation_id"],
            )
            account.record_proposal_risk_review(buy["proposal_id"], "clear", [])
            account.decide_proposal(buy["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                proposal_id=buy["proposal_id"],
                recommendation_id=recommendation["recommendation_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 112},
                benchmark_prices={"SPY": 505, "QQQ": 408},
            )

            feedback = account.proposal_feedback(latest_prices={"NVDA": 112})
            summary = account.proposal_feedback_summary(latest_prices={"NVDA": 112})

        self.assertEqual(feedback[0]["sector_gate"]["status"], "cleared")
        outcomes = summary["sector_gate_outcomes"]
        self.assertTrue(outcomes["active"])
        self.assertEqual(outcomes["leader"]["status"], "cleared")
        self.assertEqual(outcomes["leader"]["working"], 1)
        self.assertEqual(outcomes["leader"]["working_rate_pct"], 100.0)
        self.assertGreater(outcomes["leader"]["avg_edge_pct"], 8.0)
        self.assertTrue(
            any("Sector gate outcome leader" in item for item in summary["takeaways"])
        )

    def test_stage5_validation_summary_reports_benchmark_progress(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 9, 30, 0),
                    datetime(2026, 6, 3, 9, 31, 0),
                    datetime(2026, 6, 3, 9, 32, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                    datetime(2026, 6, 4, 16, 0, 0),
                    datetime(2026, 6, 5, 16, 0, 0),
                    datetime(2026, 6, 6, 16, 0, 0),
                    datetime(2026, 6, 7, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            buy = account.create_proposal(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                rationale=[
                    "Projection watch remains supportive with 70% sector breadth and a leadership trend posture.",
                ],
            )
            account.record_proposal_risk_review(buy["proposal_id"], "clear", [])
            account.decide_proposal(buy["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                proposal_id=buy["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 118},
                benchmark_prices={"SPY": 505, "QQQ": 408},
            )
            sell = account.create_proposal(
                "sell",
                "NVDA",
                50,
                118,
                "Trim thesis.",
                rationale=[
                    "Projection caution triggered: Atlas wants more proof because benchmark leadership, sector participation, or news tone is no longer clearly supportive.",
                ],
            )
            account.record_proposal_risk_review(sell["proposal_id"], "clear", [])
            account.decide_proposal(sell["proposal_id"], "approve")
            account.execute_order(
                "sell",
                "NVDA",
                50,
                118,
                "Trim thesis.",
                proposal_id=sell["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 118},
                benchmark_prices={"SPY": 507, "QQQ": 410},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 115},
                benchmark_prices={"SPY": 509, "QQQ": 412},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 114},
                benchmark_prices={"SPY": 510, "QQQ": 413},
            )

            summary = account.stage5_validation_summary(latest_prices={"NVDA": 114})

        self.assertTrue(summary["available"])
        self.assertEqual(summary["status"], "building")
        self.assertEqual(summary["status_label"], "Evidence building")
        self.assertEqual(summary["judged_trades"], 2)
        self.assertEqual(summary["realized_exits"], 0)
        pipeline = summary["evidence_pipeline"]
        self.assertEqual(pipeline["source"], "Active paper ledger")
        self.assertEqual(pipeline["snapshot_count"], 5)
        self.assertEqual(pipeline["executed_decisions"], 2)
        self.assertEqual(pipeline["judged_decisions"], 2)
        self.assertEqual(pipeline["awaiting_judgment"], 0)
        self.assertEqual(pipeline["judgment_coverage_pct"], 100.0)
        self.assertEqual(pipeline["realized_exits"], 0)
        self.assertEqual(pipeline["completed_positions"], 0)
        self.assertEqual(pipeline["partial_trims"], 1)
        self.assertEqual(pipeline["sell_executions"], 1)
        self.assertEqual(pipeline["latest_snapshot_at"], "2026-06-07T16:00:00")
        integrity = summary["evaluation_integrity"]
        self.assertTrue(integrity["available"])
        self.assertEqual(integrity["snapshot_count"], 5)
        self.assertEqual(integrity["judged_decisions"], 2)
        self.assertFalse(integrity["policy_changed"])
        self.assertFalse(summary["completed_position_diagnostics"]["available"])
        self.assertTrue(summary["prospective_review_tracker"]["activated"])
        self.assertFalse(
            summary["prospective_review_tracker"]["policy_changed"]
        )

        self.assertFalse(
            summary["prospective_review_effectiveness"][
                "ready_for_owner_review"
            ]
        )
        readiness = summary["capital_readiness"]
        self.assertFalse(readiness["ready_for_owner_review"])
        self.assertEqual(readiness["status"], "paper_only")
        self.assertEqual(readiness["total"], 9)
        self.assertGreater(readiness["progress_pct"], 0)
        self.assertLess(readiness["progress_pct"], 100)
        self.assertEqual(len(readiness["next_milestones"]), 3)
        self.assertEqual(
            [item["id"] for item in readiness["next_milestones"]],
            ["observation_depth", "judged_decisions", "realized_exits"],
        )
        self.assertTrue(
            all("next_step" in item for item in readiness["next_milestones"])
        )
        self.assertTrue(
            all("progress_pct" in item for item in readiness["criteria"])
        )
        self.assertEqual(
            {item["id"] for item in readiness["criteria"]},
            {
                "observation_depth",
                "judged_decisions",
                "realized_exits",
                "benchmark_outperformance",
                "decision_quality",
                "exit_quality",
                "realized_win_rate",
                "persistence",
                "turnover_discipline",
            },
        )
        scorecards = {
            item["label"]: item
            for item in summary["scorecards"]
        }
        self.assertIn("Judged trade outcomes", scorecards)
        self.assertEqual(scorecards["Judged trade working rate"]["value"], "100.0%")
        self.assertEqual(scorecards["Judged sell help rate"]["value"], "100.0%")
        self.assertEqual(scorecards["Gross turnover"]["value"], "15.9%")
        self.assertEqual(scorecards["3-snapshot persistence"]["value"], "100.0%")
        self.assertIn("Exit quality is 100.0% on judged trims and exits.", summary["takeaways"])
        self.assertIn("Gross turnover has reached 15.9% of starting paper capital.", summary["takeaways"])
        self.assertIn("100.0% of judged trades are still working by the 3-snapshot checkpoint.", summary["takeaways"])
        self.assertIn(
            "Atlas is not yet ahead of the tracked benchmarks on total paper return.",
            summary["takeaways"],
        )

    def test_stage5_evaluation_integrity_starts_a_new_policy_epoch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 0, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 9, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: next(times),
            )
            account.initialize(100000)
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.update_policy(
                {"strategy_minimum_buy_score": 90.0},
                source="owner_test",
            )
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 501, "QQQ": 402},
            )
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 503, "QQQ": 405},
            )

            integrity = account.stage5_evaluation_integrity(feedback_rows=[])

        self.assertTrue(integrity["available"])
        self.assertTrue(integrity["policy_changed"])
        self.assertEqual(integrity["policy_update_count"], 1)
        self.assertEqual(integrity["snapshot_count"], 2)
        self.assertEqual(integrity["trade_count"], 0)
        self.assertEqual(integrity["judged_decisions"], 0)
        self.assertEqual(
            integrity["changed_fields"],
            ["strategy_minimum_buy_score"],
        )
        performance = integrity["performance"]
        self.assertTrue(performance["available"])
        self.assertEqual(performance["atlas_return_pct"], 0.0)
        self.assertEqual(performance["benchmark_returns_pct"]["SPY"], 0.3992)
        self.assertEqual(performance["benchmark_returns_pct"]["QQQ"], 0.7463)
        self.assertEqual(performance["excess_returns_pct"]["SPY"], -0.3992)
        self.assertEqual(performance["excess_returns_pct"]["QQQ"], -0.7463)
        self.assertEqual(performance["maximum_drawdown_pct"], 0.0)
        self.assertEqual(performance["sample_label"], "2 current-policy snapshots")
        self.assertFalse(integrity["comparable"])

    def test_policy_epoch_performance_measures_drawdown_from_epoch_peak(self):
        snapshots = [
            {
                "timestamp": "2026-06-01T16:00:00",
                "equity": 100000,
                "benchmark_prices": {"SPY": 500, "QQQ": 400},
            },
            {
                "timestamp": "2026-06-02T16:00:00",
                "equity": 105000,
                "benchmark_prices": {"SPY": 510, "QQQ": 404},
            },
            {
                "timestamp": "2026-06-03T16:00:00",
                "equity": 102000,
                "benchmark_prices": {"SPY": 505, "QQQ": 408},
            },
        ]

        performance = PaperTradingAccount._policy_epoch_performance(snapshots)

        self.assertTrue(performance["available"])
        self.assertEqual(performance["atlas_return_pct"], 2.0)
        self.assertEqual(performance["benchmark_returns_pct"]["SPY"], 1.0)
        self.assertEqual(performance["benchmark_returns_pct"]["QQQ"], 2.0)
        self.assertEqual(performance["excess_returns_pct"]["SPY"], 1.0)
        self.assertEqual(performance["excess_returns_pct"]["QQQ"], 0.0)
        self.assertEqual(performance["maximum_drawdown_pct"], -2.8571)

    def test_policy_epoch_performance_requires_two_snapshots(self):
        performance = PaperTradingAccount._policy_epoch_performance(
            [{"equity": 100000, "benchmark_prices": {"SPY": 500, "QQQ": 400}}]
        )

        self.assertFalse(performance["available"])
        self.assertIn("two current-policy snapshots", performance["detail"])

    def test_policy_epoch_attribution_explains_cash_decisions_and_holdings(self):
        snapshots = [
            {
                "timestamp": "2026-06-01T16:00:00",
                "equity": 100000,
                "cash": 40000,
                "benchmark_prices": {"SPY": 500, "QQQ": 400},
                "positions": [
                    {"ticker": "NVDA", "shares": 10, "price": 100},
                    {"ticker": "MSFT", "shares": 20, "price": 200},
                ],
            },
            {
                "timestamp": "2026-06-02T16:00:00",
                "equity": 102000,
                "cash": 30000,
                "benchmark_prices": {"SPY": 525, "QQQ": 410},
                "positions": [],
            },
            {
                "timestamp": "2026-06-03T16:00:00",
                "equity": 105000,
                "cash": 20000,
                "benchmark_prices": {"SPY": 550, "QQQ": 420},
                "positions": [
                    {"ticker": "NVDA", "shares": 8, "price": 110},
                    {"ticker": "MSFT", "shares": 20, "price": 190},
                    {"ticker": "PLTR", "shares": 10, "price": 150},
                ],
            },
        ]
        feedback = [
            {
                "side": "buy",
                "verdict": "working",
                "security_return_pct": 8,
                "benchmark_returns_pct": {"SPY": 5, "QQQ": 6},
            },
            {
                "side": "sell",
                "verdict": "working",
                "security_return_pct": -2,
                "benchmark_returns_pct": {"SPY": 3, "QQQ": 4},
            },
        ]

        attribution = PaperTradingAccount._policy_epoch_attribution(
            snapshots,
            feedback,
            sector_map={"NVDA": "AI & Semiconductors", "MSFT": "Cloud & Software"},
        )

        self.assertTrue(attribution["available"])
        self.assertEqual(attribution["average_cash_pct"], 29.49)
        self.assertEqual(attribution["estimated_cash_drag_pct"]["SPY"], -2.9486)
        self.assertEqual(attribution["estimated_cash_drag_pct"]["QQQ"], -1.4743)
        self.assertEqual(
            attribution["decision_quality"]["buy"]["average_decision_edge_pct"],
            2.0,
        )
        self.assertEqual(
            attribution["decision_quality"]["sell"]["average_decision_edge_pct"],
            6.0,
        )
        self.assertEqual(attribution["top_contributor"]["ticker"], "NVDA")
        self.assertEqual(attribution["top_contributor"]["contribution_pct"], 0.08)
        self.assertEqual(attribution["largest_detractor"]["ticker"], "MSFT")
        self.assertEqual(attribution["largest_detractor"]["contribution_pct"], -0.2)
        self.assertEqual(
            attribution["sector_contributions"][0]["sector"],
            "AI & Semiconductors",
        )
        self.assertEqual(
            attribution["sector_contributions"][-1]["sector"],
            "Cloud & Software",
        )
        scenarios = attribution["exposure_scenarios"]
        self.assertEqual(len(scenarios), 3)
        self.assertEqual(scenarios[0]["idle_cash_deployed_pct"], 25.0)
        self.assertEqual(scenarios[0]["added_portfolio_exposure_pct"], 7.37)
        self.assertEqual(scenarios[0]["estimated_return_uplift_pct"], 0.7372)
        self.assertEqual(scenarios[0]["estimated_policy_return_pct"], 5.7372)
        self.assertEqual(scenarios[0]["modeled_sleeve_drawdown_pct"], 0.0)

    def test_proposal_feedback_tracks_snapshot_persistence_horizons(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 16, 0, 0),
                    datetime(2026, 6, 4, 16, 0, 0),
                    datetime(2026, 6, 5, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                policy={"maximum_position_pct": 50.0},
                clock=lambda: next(times),
            )
            account.initialize(100000)
            buy = account.create_proposal("buy", "NVDA", 100, 100, "Paper thesis.")
            account.record_proposal_risk_review(buy["proposal_id"], "clear", [])
            account.decide_proposal(buy["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                100,
                100,
                "Paper thesis.",
                proposal_id=buy["proposal_id"],
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
                prices={"NVDA": 111},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 109},
                benchmark_prices={"SPY": 507, "QQQ": 407},
            )

            feedback = account.proposal_feedback(latest_prices={"NVDA": 109})

        horizons = feedback[0]["horizon_outcomes"]
        self.assertEqual(horizons[0]["label"], "1-snapshot")
        self.assertTrue(horizons[0]["available"])
        self.assertEqual(horizons[0]["verdict"], "working")
        self.assertEqual(horizons[1]["label"], "3-snapshot")
        self.assertTrue(horizons[1]["available"])
        self.assertEqual(horizons[1]["security_return_pct"], 11.0)
        self.assertEqual(horizons[1]["benchmark_returns_pct"]["SPY"], 1.2)
        self.assertEqual(horizons[2]["label"], "5-snapshot")
        self.assertFalse(horizons[2]["available"])

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
                rationale=[
                    "Atlas score is above the buy threshold.",
                    "Projection watch remains supportive with 72% sector breadth and a leadership trend posture.",
                ],
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
        self.assertEqual(activity[0]["proposal_id"], sell["proposal_id"])
        self.assertEqual(activity[0]["risk_review"]["verdict"], "clear")
        self.assertEqual(activity[1]["action_label"], "purchase")
        self.assertEqual(activity[1]["title"], "Atlas purchased NVDA")
        self.assertEqual(activity[1]["proposal_id"], buy["proposal_id"])
        self.assertEqual(activity[1]["risk_review"]["verdict"], "clear")
        self.assertEqual(
            activity[1]["rationale"][0],
            "Atlas score is above the buy threshold.",
        )
        self.assertEqual(
            activity[1]["decision_driver"]["label"],
            "Projection-supported add",
        )

    def test_accountability_report_tracks_basis_and_open_positions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            buy_one = account.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "Entry one with product launch context.",
                rationale=[
                    "News tone is constructive.",
                    "Atlas classifies the dominant event as product launch.",
                    "Projection watch remains supportive with 75% sector breadth and a leadership trend posture.",
                ],
            )
            account.record_proposal_risk_review(buy_one["proposal_id"], "clear", [])
            account.decide_proposal(buy_one["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry one with product launch context.",
                proposal_id=buy_one["proposal_id"],
            )
            self.execute_approved(account, "buy", "NVDA", 5, 120, "Entry two.")
            self.execute_approved(account, "sell", "NVDA", 6, 130, "Partial exit.")

            report = account.accountability_report()

        self.assertEqual(report["accounting_method"], "weighted_average_cost")
        self.assertEqual(report["summary"]["tickers"], 1)
        self.assertEqual(report["summary"]["transactions"], 3)
        self.assertEqual(report["summary"]["open_positions"], 1)
        nvda = report["tickers"][0]
        self.assertEqual(nvda["ticker"], "NVDA")
        self.assertEqual(nvda["open_shares"], 9.0)
        self.assertAlmostEqual(nvda["average_cost"], 106.6667, places=4)
        self.assertAlmostEqual(nvda["open_basis"], 960.0, places=2)
        self.assertEqual(nvda["transactions"][0]["basis_amount"], 1000.0)
        self.assertEqual(
            nvda["transactions"][0]["news_event_summary"],
            "product launch",
        )
        self.assertEqual(
            nvda["transactions"][0]["decision_driver"]["label"],
            "Projection-supported add",
        )
        self.assertIn("daily trade cap", nvda["transactions"][0]["adaptive_regime"])
        self.assertIn("benchmark trust", nvda["transactions"][0]["adaptive_regime"])
        self.assertEqual(nvda["transactions"][1]["basis_amount"], 600.0)
        self.assertAlmostEqual(nvda["transactions"][2]["basis_per_share"], 106.6667, places=4)
        self.assertEqual(nvda["transactions"][2]["proceeds"], 780.0)

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
        self.assertEqual(stats["total_buy_notional"], 1000.0)
        self.assertEqual(stats["total_sell_notional"], 1100.0)
        self.assertEqual(stats["gross_turnover_notional"], 2100.0)
        self.assertEqual(stats["turnover_pct"], 2.1)
        self.assertIn("## Stage 5 Validation", report)
        self.assertIn("**Status**: Evidence building", report)
        self.assertIn("### Validation Takeaways", report)
        self.assertIn("## Adaptive Learning Profiles", report)
        self.assertIn("**Daily trade pressure**: Watching", report)
        self.assertIn("**Benchmark trust**: Watching", report)
        self.assertIn("## Benchmark-Specific Decision Scorecard", report)
        self.assertIn("| Benchmark | Judged | Working | Mixed | Lagging | Avg Decision Edge |", report)
        self.assertIn("## Decision Audit", report)
        self.assertIn("**Gross Turnover**: 2.1% of starting paper capital", report)
        self.assertIn("**Judged Trade Working Rate**: N/A", report)
        self.assertIn("**Judged Sell Help Rate**: N/A", report)
        self.assertIn("## Recent Execution Context", report)
        self.assertIn("| Time | Ticker | Action | Driver | News Event | Thesis |", report)
        self.assertIn("This report evaluates a simulation", report)

    def test_trade_statistics_separates_partial_trims_from_completed_positions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            self.execute_approved(account, "buy", "NVDA", 10, 100, "Paper thesis.")
            self.execute_approved(account, "sell", "NVDA", 4, 90, "Partial trim.")

            trim_stats = account.trade_statistics()

            self.execute_approved(account, "sell", "NVDA", 6, 110, "Full exit.")
            exit_stats = account.trade_statistics()

        self.assertEqual(trim_stats["sell_executions"], 1)
        self.assertEqual(trim_stats["partial_trims"], 1)
        self.assertEqual(trim_stats["completed_positions"], 0)
        self.assertIsNone(trim_stats["win_rate_pct"])
        self.assertEqual(exit_stats["sell_executions"], 2)
        self.assertEqual(exit_stats["partial_trims"], 1)
        self.assertEqual(exit_stats["completed_positions"], 1)
        self.assertEqual(exit_stats["wins"], 1)
        self.assertEqual(exit_stats["losses"], 0)
        self.assertEqual(exit_stats["win_rate_pct"], 100)
        self.assertEqual(
            exit_stats["completed_outcomes"][0]["realized_gain_loss"],
            20.0,
        )

    def test_completed_position_diagnostics_separates_entry_response_and_execution(self):
        diagnostics = PaperTradingAccount.completed_position_diagnostics(
            [
                {
                    "event": "paper_trade",
                    "timestamp": "2026-07-01T09:30:00",
                    "ticker": "NVDA",
                    "side": "buy",
                    "shares": 10,
                    "price": 100,
                    "notional": 1000,
                    "position_shares_before": 0,
                    "position_shares_after": 10,
                    "thesis": "Atlas paper entry rule with a -6.20% current move.",
                },
                {
                    "event": "paper_trade",
                    "timestamp": "2026-07-06T09:30:00",
                    "ticker": "NVDA",
                    "side": "sell",
                    "shares": 5,
                    "price": 95,
                    "notional": 475,
                    "realized_gain_loss": -25,
                    "position_shares_before": 10,
                    "position_shares_after": 5,
                },
                {
                    "event": "paper_trade",
                    "timestamp": "2026-07-07T09:30:00",
                    "ticker": "NVDA",
                    "side": "sell",
                    "shares": 2.5,
                    "price": 94,
                    "notional": 235,
                    "realized_gain_loss": -15,
                    "position_shares_before": 5,
                    "position_shares_after": 2.5,
                },
                {
                    "event": "paper_trade",
                    "timestamp": "2026-07-08T09:30:00",
                    "ticker": "NVDA",
                    "side": "sell",
                    "shares": 2.5,
                    "price": 93,
                    "notional": 232.5,
                    "realized_gain_loss": -17.5,
                    "position_shares_before": 2.5,
                    "position_shares_after": 0,
                },
            ]
        )

        self.assertTrue(diagnostics["available"])
        self.assertEqual(diagnostics["sample_size"], 1)
        self.assertEqual(diagnostics["late_risk_responses"], 1)
        self.assertEqual(diagnostics["sharp_decline_entries"], 1)
        self.assertEqual(diagnostics["fragmented_exits"], 1)
        self.assertEqual(diagnostics["cycles"][0]["holding_days"], 7.0)
        self.assertEqual(
            diagnostics["cycles"][0]["days_to_first_risk_action"],
            5.0,
        )
        self.assertEqual(
            diagnostics["cycles"][0]["first_risk_action_return_pct"],
            -5.0,
        )
        self.assertIn(
            "sharp -6.2% daily decline",
            diagnostics["cycles"][0]["entry"]["finding"],
        )
        self.assertIn(
            "fragmented across 3",
            diagnostics["cycles"][0]["execution"]["finding"],
        )

    def test_shadow_defensive_trigger_analysis_rejects_unhelpful_auto_exit(self):
        trades = [
            {
                "event": "paper_trade",
                "timestamp": "2026-07-01T09:30:00",
                "ticker": "NVDA",
                "side": "buy",
                "shares": 10,
                "price": 100,
                "notional": 1000,
                "position_shares_before": 0,
                "position_shares_after": 10,
            },
            {
                "event": "paper_trade",
                "timestamp": "2026-07-01T09:31:00",
                "ticker": "AMD",
                "side": "buy",
                "shares": 10,
                "price": 100,
                "notional": 1000,
                "position_shares_before": 0,
                "position_shares_after": 10,
            },
            {
                "event": "paper_trade",
                "timestamp": "2026-07-03T09:30:00",
                "ticker": "NVDA",
                "side": "sell",
                "shares": 10,
                "price": 98,
                "notional": 980,
                "realized_gain_loss": -20,
                "position_shares_before": 10,
                "position_shares_after": 0,
            },
        ]
        snapshots = [
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:00:00",
                "security_prices": {"NVDA": 100, "AMD": 100},
                "benchmark_prices": {"SPY": 100, "QQQ": 100},
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-02T10:00:00",
                "security_prices": {"NVDA": 96, "AMD": 96},
                "benchmark_prices": {"SPY": 100, "QQQ": 100},
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-03T09:00:00",
                "security_prices": {"NVDA": 98, "AMD": 105},
                "benchmark_prices": {"SPY": 101, "QQQ": 101},
            },
        ]

        analysis = PaperTradingAccount.shadow_defensive_trigger_analysis(
            trades,
            snapshots,
        )
        candidates = {
            item["id"]: item for item in analysis["candidates"]
        }
        automatic = candidates["automatic_full_exit"]

        self.assertTrue(analysis["available"])
        self.assertFalse(analysis["policy_changed"])
        self.assertEqual(analysis["decision"], "No live strategy change")
        self.assertEqual(automatic["decision"], "reject")
        self.assertEqual(automatic["triggered_cycles"], 2)
        self.assertEqual(automatic["completed_cycles"], 1)
        self.assertEqual(automatic["recovered_cycles"], 2)
        self.assertEqual(automatic["actual_completed_gain_loss"], -20)
        self.assertEqual(automatic["shadow_completed_gain_loss"], -40)
        self.assertEqual(automatic["completed_improvement"], -20)

    def test_prospective_review_tracker_classifies_forward_outcomes(self):
        events = [
            {
                "event": "paper_trade",
                "timestamp": "2026-07-01T09:30:00",
                "ticker": "NVDA",
                "side": "buy",
                "shares": 10,
                "price": 100,
                "notional": 1000,
                "position_shares_before": 0,
                "position_shares_after": 10,
            },
            {
                "event": "paper_trade",
                "timestamp": "2026-07-01T09:31:00",
                "ticker": "AMD",
                "side": "buy",
                "shares": 10,
                "price": 100,
                "notional": 1000,
                "position_shares_before": 0,
                "position_shares_after": 10,
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T09:45:00",
                "benchmark_prices": {"SPY": 100, "QQQ": 100},
                "security_prices": {"NVDA": 100, "AMD": 100},
            },
            {
                "event": "defensive_review_tracking_started",
                "timestamp": "2026-07-01T10:00:00",
                "mode": "review_only",
                "policy_changed": False,
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:00:00",
                "benchmark_prices": {"SPY": 101, "QQQ": 101},
                "security_prices": {"NVDA": 97, "AMD": 97},
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:01:00",
                "benchmark_prices": {"SPY": 102, "QQQ": 102},
                "security_prices": {"NVDA": 96, "AMD": 99},
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:02:00",
                "benchmark_prices": {"SPY": 103, "QQQ": 103},
                "security_prices": {"NVDA": 95, "AMD": 98},
            },
            {
                "event": "paper_trade",
                "timestamp": "2026-07-01T10:03:00",
                "ticker": "NVDA",
                "side": "sell",
                "shares": 10,
                "price": 95,
                "notional": 950,
                "realized_gain_loss": -50,
                "position_shares_before": 10,
                "position_shares_after": 0,
            },
            {
                "event": "defensive_review_signal",
                "signal_id": "review_amd",
                "timestamp": "2026-07-01T10:00:00",
                "ticker": "AMD",
                "status": "active",
                "status_label": "New review",
                "latest_return_pct": -3.0,
                "latest_lag_pct": -4.0,
                "snapshots_observed": 1,
            },
            {
                "event": "defensive_review_signal",
                "signal_id": "review_amd",
                "timestamp": "2026-07-01T10:02:00",
                "ticker": "AMD",
                "status": "recovered",
                "status_label": "Recovered above trigger",
                "latest_return_pct": -2.0,
                "latest_lag_pct": -5.0,
                "snapshots_observed": 3,
                "priority_changed": True,
                "meaningful_priority_escalation": True,
                "previous_review_priority": "low",
                "previous_review_priority_label": "Low priority",
                "previous_review_priority_score": 25,
                "review_priority": "monitor",
                "review_priority_label": "Monitor closely",
                "review_priority_score": 65,
                "priority_score_change": 40,
            },
            {
                "event": "defensive_review_signal",
                "signal_id": "review_nvda",
                "timestamp": "2026-07-01T10:02:00",
                "ticker": "NVDA",
                "status": "completed_loss",
                "status_label": "Completed loss",
                "latest_return_pct": -5.0,
                "latest_lag_pct": -8.0,
                "snapshots_observed": 3,
            },
        ]

        tracker = PaperTradingAccount.prospective_defensive_review_tracker(
            events
        )

        self.assertTrue(tracker["activated"])
        self.assertFalse(tracker["policy_changed"])
        self.assertEqual(tracker["counts"]["total"], 2)
        self.assertEqual(tracker["counts"]["completed_loss"], 1)
        self.assertEqual(tracker["counts"]["recovered"], 1)
        by_ticker = {item["ticker"]: item for item in tracker["signals"]}
        self.assertEqual(by_ticker["NVDA"]["status"], "completed_loss")
        self.assertEqual(by_ticker["NVDA"]["snapshots_observed"], 3)
        self.assertEqual(
            by_ticker["NVDA"]["post_trigger_move_pct"],
            -2.0619,
        )
        self.assertEqual(
            by_ticker["NVDA"]["worst_post_trigger_move_pct"],
            -2.0619,
        )
        self.assertEqual(
            by_ticker["NVDA"]["best_post_trigger_move_pct"],
            0.0,
        )
        self.assertEqual(by_ticker["NVDA"]["comparison_benchmark"], "SPY")
        self.assertEqual(
            by_ticker["NVDA"]["comparison_benchmark_move_pct"],
            1.9802,
        )
        self.assertEqual(
            by_ticker["NVDA"]["benchmark_relative_move_pct"],
            -4.0421,
        )
        self.assertEqual(
            by_ticker["NVDA"]["benchmark_attribution_label"],
            "Lagged stronger benchmark",
        )
        self.assertIsNone(
            by_ticker["NVDA"]["snapshots_to_first_recovery"]
        )
        self.assertIsNone(by_ticker["NVDA"]["days_to_first_recovery"])
        self.assertEqual(by_ticker["NVDA"]["warning_span_days"], 0.0)
        self.assertEqual(by_ticker["NVDA"]["recovery_durability_pct"], 0.0)
        self.assertEqual(by_ticker["NVDA"]["relapse_count"], 0)
        self.assertEqual(
            by_ticker["NVDA"]["recovery_quality_label"],
            "No recovery observed",
        )
        self.assertEqual(by_ticker["AMD"]["status"], "recovered")
        self.assertEqual(by_ticker["AMD"]["latest_return_pct"], -2.0)
        self.assertEqual(
            by_ticker["AMD"]["post_trigger_move_pct"],
            1.0309,
        )
        self.assertEqual(
            by_ticker["AMD"]["best_post_trigger_move_pct"],
            2.0619,
        )
        self.assertEqual(
            by_ticker["AMD"]["benchmark_relative_move_pct"],
            -0.9493,
        )
        self.assertEqual(
            by_ticker["AMD"]["best_benchmark_relative_move_pct"],
            1.0718,
        )
        self.assertEqual(
            by_ticker["AMD"]["benchmark_attribution_label"],
            "Moved near stronger benchmark",
        )
        self.assertEqual(
            by_ticker["AMD"]["snapshots_to_first_recovery"],
            1,
        )
        self.assertEqual(by_ticker["AMD"]["days_to_first_recovery"], 0.0)
        self.assertEqual(
            by_ticker["AMD"]["first_recovered_at"],
            "2026-07-01T10:01:00",
        )
        self.assertEqual(by_ticker["AMD"]["recovery_durability_pct"], 100.0)
        self.assertEqual(by_ticker["AMD"]["relapse_count"], 0)
        self.assertEqual(
            by_ticker["AMD"]["longest_recovery_streak_snapshots"],
            2,
        )
        self.assertEqual(
            by_ticker["AMD"]["current_recovery_streak_snapshots"],
            2,
        )
        self.assertTrue(by_ticker["AMD"]["currently_above_trigger"])
        self.assertEqual(
            by_ticker["AMD"]["recovery_quality_label"],
            "Recovery remains above trigger",
        )
        self.assertEqual(tracker["transition_count"], 3)
        self.assertEqual(tracker["recent_transition_count"], 2)
        self.assertEqual(
            [item["ticker"] for item in tracker["recent_transitions"]],
            ["NVDA", "AMD"],
        )
        self.assertEqual(
            tracker["recent_transitions"][1]["status"],
            "recovered",
        )
        self.assertEqual(tracker["priority_transition_count"], 1)
        self.assertEqual(tracker["latest_priority_escalation_count"], 1)
        self.assertEqual(
            tracker["latest_priority_escalations"][0]["ticker"],
            "AMD",
        )
        self.assertEqual(
            tracker["latest_priority_escalations"][0][
                "previous_review_priority_label"
            ],
            "Low priority",
        )

        scorecard = PaperTradingAccount.prospective_review_effectiveness(
            tracker
        )
        outcomes = {
            item["ticker"]: item for item in scorecard["outcomes"]
        }
        self.assertEqual(
            outcomes["NVDA"]["classification"],
            "confirmed_weakness",
        )
        self.assertEqual(
            outcomes["AMD"]["classification"],
            "false_alarm",
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "confirmed_avg_post_trigger_move_pct"
            ],
            -2.06,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "false_alarm_avg_post_trigger_move_pct"
            ],
            1.03,
        )
        self.assertEqual(
            scorecard["outcome_comparison"]["outcome_separation_pct"],
            3.09,
        )
        self.assertEqual(
            outcomes["NVDA"]["benchmark_relative_move_pct"],
            -4.0421,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "confirmed_avg_benchmark_relative_move_pct"
            ],
            -4.04,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "false_alarm_avg_benchmark_relative_move_pct"
            ],
            -0.95,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "benchmark_adjusted_separation_pct"
            ],
            3.09,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "confirmed_avg_warning_span_snapshots"
            ],
            3.0,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "false_alarm_avg_snapshots_to_recovery"
            ],
            1.0,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "confirmed_avg_recovery_durability_pct"
            ],
            0.0,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "false_alarm_avg_recovery_durability_pct"
            ],
            100.0,
        )
        self.assertEqual(
            scorecard["outcome_comparison"][
                "recovery_durability_separation_pct"
            ],
            100.0,
        )
        nvda_signal = next(
            signal for signal in tracker["signals"] if signal["ticker"] == "NVDA"
        )
        amd_signal = next(
            signal for signal in tracker["signals"] if signal["ticker"] == "AMD"
        )
        self.assertEqual(nvda_signal["review_priority"], "recorded")
        self.assertEqual(nvda_signal["review_priority_score"], 0)
        self.assertFalse(nvda_signal["requires_owner_attention"])
        self.assertEqual(amd_signal["review_priority"], "low")
        self.assertEqual(amd_signal["review_priority_score"], 25)
        self.assertEqual([item["ticker"] for item in tracker["review_queue"]], ["AMD"])
        self.assertEqual(tracker["review_priority_counts"]["recorded"], 1)
        self.assertEqual(tracker["review_priority_mode"], "evidence_only")
        self.assertFalse(tracker["review_priority_policy_changed"])

    def test_prospective_review_tracker_counts_recovery_relapses(self):
        events = [
            {
                "event": "paper_trade",
                "timestamp": "2026-07-01T09:30:00",
                "ticker": "MSFT",
                "side": "buy",
                "shares": 10,
                "price": 100,
                "notional": 1000,
                "position_shares_before": 0,
                "position_shares_after": 10,
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T09:45:00",
                "benchmark_prices": {"SPY": 100, "QQQ": 100},
                "security_prices": {"MSFT": 100},
            },
            {
                "event": "defensive_review_tracking_started",
                "timestamp": "2026-07-01T10:00:00",
                "mode": "review_only",
                "policy_changed": False,
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:00:00",
                "benchmark_prices": {"SPY": 101, "QQQ": 101},
                "security_prices": {"MSFT": 97},
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:01:00",
                "benchmark_prices": {"SPY": 102, "QQQ": 102},
                "security_prices": {"MSFT": 99},
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:02:00",
                "benchmark_prices": {"SPY": 103, "QQQ": 103},
                "security_prices": {"MSFT": 96},
            },
            {
                "event": "performance_snapshot",
                "timestamp": "2026-07-01T10:03:00",
                "benchmark_prices": {"SPY": 104, "QQQ": 104},
                "security_prices": {"MSFT": 100},
            },
        ]

        tracker = PaperTradingAccount.prospective_defensive_review_tracker(
            events
        )
        signal = tracker["signals"][0]

        self.assertEqual(signal["status"], "recovered")
        self.assertEqual(signal["recovery_durability_pct"], 66.7)
        self.assertEqual(signal["relapse_count"], 1)
        self.assertEqual(
            signal["first_relapsed_at"],
            "2026-07-01T10:02:00",
        )
        self.assertEqual(signal["days_to_first_relapse"], 0.0)
        self.assertEqual(signal["longest_recovery_streak_snapshots"], 1)
        self.assertEqual(signal["current_recovery_streak_snapshots"], 1)
        self.assertTrue(signal["currently_above_trigger"])
        self.assertEqual(
            signal["recovery_quality_label"],
            "Recovered again after relapse",
        )
        self.assertEqual(signal["review_priority"], "watch")
        self.assertEqual(signal["review_priority_label"], "Watch")
        self.assertEqual(signal["review_priority_score"], 40)
        self.assertFalse(signal["requires_owner_attention"])
        self.assertIn("relapsed 1 time", " ".join(signal["review_priority_rationale"]))

    def test_performance_snapshot_starts_review_tracking_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 7, 1, 9, 0, 0),
                    datetime(2026, 7, 1, 16, 0, 0),
                    datetime(2026, 7, 2, 16, 0, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: next(times),
            )
            account.initialize(100000)
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            events = account.ledger()

        markers = [
            event
            for event in events
            if event.get("event") == "defensive_review_tracking_started"
        ]
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0]["mode"], "review_only")
        self.assertFalse(markers[0]["policy_changed"])

    def test_review_priority_sync_records_only_band_changes_and_escalations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
            )
            account.initialize(100000)
            states = [
                {
                    "ticker": "MSFT",
                    "signal_id": "review_msft",
                    "status": "recovered",
                    "status_label": "Recovered above trigger",
                    "latest_at": "2026-07-01T10:00:00",
                    "review_priority": "watch",
                    "review_priority_label": "Watch",
                    "review_priority_score": 40,
                    "review_priority_rationale": ["Recovery relapsed once."],
                },
                {
                    "ticker": "MSFT",
                    "signal_id": "review_msft",
                    "status": "persistent_weakness",
                    "status_label": "Weakness persists",
                    "latest_at": "2026-07-02T10:00:00",
                    "review_priority": "monitor",
                    "review_priority_label": "Monitor closely",
                    "review_priority_score": 70,
                    "review_priority_rationale": ["Weakness persisted."],
                },
                {
                    "ticker": "MSFT",
                    "signal_id": "review_msft",
                    "status": "persistent_weakness",
                    "status_label": "Weakness persists",
                    "latest_at": "2026-07-03T10:00:00",
                    "review_priority": "monitor",
                    "review_priority_label": "Monitor closely",
                    "review_priority_score": 75,
                    "review_priority_rationale": ["Weakness persisted."],
                },
            ]
            account.prospective_defensive_review_tracker = lambda events: {
                "signals": [states.pop(0)]
            }

            account._sync_prospective_defensive_review_events()
            account._sync_prospective_defensive_review_events()
            account._sync_prospective_defensive_review_events()
            transitions = [
                event
                for event in account.ledger()
                if event.get("event") == "defensive_review_signal"
            ]

        self.assertEqual(len(transitions), 2)
        self.assertEqual(transitions[0]["transition_kind"], "initial_signal")
        self.assertFalse(transitions[0]["meaningful_priority_escalation"])
        self.assertEqual(
            transitions[1]["transition_kind"],
            "priority_escalation",
        )
        self.assertTrue(transitions[1]["meaningful_priority_escalation"])
        self.assertEqual(transitions[1]["previous_review_priority"], "watch")
        self.assertEqual(transitions[1]["review_priority"], "monitor")
        self.assertEqual(transitions[1]["priority_score_change"], 30)

    def test_priority_escalation_episodes_measure_duration_peak_and_resolution(self):
        snapshots = [
            {"timestamp": f"2026-07-0{day}T10:00:00"}
            for day in range(1, 8)
        ]
        transitions = [
            {
                "signal_id": "review_msft",
                "ticker": "MSFT",
                "timestamp": "2026-07-01T10:00:00",
                "meaningful_priority_escalation": True,
                "review_priority": "monitor",
                "review_priority_label": "Monitor closely",
                "review_priority_score": 65,
                "status": "persistent_weakness",
                "status_label": "Weakness persists",
            },
            {
                "signal_id": "review_msft",
                "ticker": "MSFT",
                "timestamp": "2026-07-02T10:00:00",
                "meaningful_priority_escalation": True,
                "review_priority": "urgent",
                "review_priority_label": "Review now",
                "review_priority_score": 90,
                "status": "persistent_weakness",
                "status_label": "Weakness persists",
            },
            {
                "signal_id": "review_msft",
                "ticker": "MSFT",
                "timestamp": "2026-07-04T10:00:00",
                "priority_changed": True,
                "review_priority": "watch",
                "review_priority_label": "Watch",
                "review_priority_score": 45,
                "status": "recovered",
                "status_label": "Recovered above trigger",
            },
            {
                "signal_id": "review_msft",
                "ticker": "MSFT",
                "timestamp": "2026-07-05T10:00:00",
                "meaningful_priority_escalation": True,
                "review_priority": "monitor",
                "review_priority_label": "Monitor closely",
                "review_priority_score": 70,
                "status": "persistent_weakness",
                "status_label": "Weakness persists",
            },
        ]

        evidence = PaperTradingAccount.prospective_priority_escalation_episodes(
            transitions,
            snapshots,
        )

        self.assertEqual(evidence["episode_count"], 2)
        self.assertEqual(evidence["open_episode_count"], 1)
        self.assertEqual(evidence["resolved_episode_count"], 1)
        self.assertEqual(evidence["average_resolved_duration_days"], 3.0)
        self.assertEqual(evidence["resolution_counts"]["deescalated"], 1)
        by_start = {item["started_at"]: item for item in evidence["episodes"]}
        resolved = by_start["2026-07-01T10:00:00"]
        self.assertFalse(resolved["open"])
        self.assertEqual(resolved["resolution"], "deescalated")
        self.assertEqual(resolved["duration_days"], 3.0)
        self.assertEqual(resolved["snapshots_open"], 4)
        self.assertEqual(resolved["peak_review_priority"], "urgent")
        self.assertEqual(resolved["peak_review_priority_score"], 90)
        open_episode = by_start["2026-07-05T10:00:00"]
        self.assertTrue(open_episode["open"])
        self.assertEqual(open_episode["duration_days"], 2.0)
        self.assertEqual(open_episode["snapshots_open"], 3)
        self.assertFalse(evidence["policy_changed"])

    def test_prospective_review_effectiveness_requires_forward_sample(self):
        scorecard = (
            PaperTradingAccount.prospective_review_effectiveness(
                {
                    "activated": True,
                    "signals": [],
                    "counts": {
                        "persistent_weakness": 0,
                        "completed_loss": 0,
                        "recovered": 0,
                        "completed_gain": 0,
                    },
                }
            )
        )

        self.assertEqual(scorecard["status"], "collecting")
        self.assertEqual(scorecard["resolved_signals"], 0)
        self.assertIsNone(scorecard["confirmation_rate_pct"])
        self.assertFalse(scorecard["ready_for_owner_review"])
        self.assertFalse(scorecard["policy_changed"])
        self.assertEqual(scorecard["minimum_resolved_signals"], 10)
        self.assertEqual(scorecard["minimum_completed_outcomes"], 5)
        self.assertEqual(scorecard["outcomes"], [])
        self.assertIsNone(
            scorecard["outcome_comparison"][
                "outcome_separation_pct"
            ]
        )
        self.assertIsNone(
            scorecard["outcome_comparison"][
                "benchmark_adjusted_separation_pct"
            ]
        )
        self.assertIsNone(
            scorecard["outcome_comparison"][
                "false_alarm_avg_snapshots_to_recovery"
            ]
        )
        self.assertIsNone(
            scorecard["outcome_comparison"][
                "recovery_durability_separation_pct"
            ]
        )

    def test_prospective_review_effectiveness_can_clear_owner_review_gates(self):
        signals = (
            [{"status": "persistent_weakness"} for _ in range(4)]
            + [{"status": "completed_loss"} for _ in range(5)]
            + [{"status": "recovered"} for _ in range(2)]
            + [{"status": "completed_gain"}]
        )
        scorecard = (
            PaperTradingAccount.prospective_review_effectiveness(
                {
                    "activated": True,
                    "signals": signals,
                    "counts": {
                        "persistent_weakness": 4,
                        "completed_loss": 5,
                        "recovered": 2,
                        "completed_gain": 1,
                    },
                }
            )
        )

        self.assertEqual(scorecard["resolved_signals"], 12)
        self.assertEqual(scorecard["confirmed_weakness"], 9)
        self.assertEqual(scorecard["false_alarms"], 3)
        self.assertEqual(scorecard["completed_outcomes"], 6)
        self.assertEqual(scorecard["confirmation_rate_pct"], 75.0)
        self.assertEqual(scorecard["false_alarm_rate_pct"], 25.0)
        self.assertTrue(scorecard["ready_for_owner_review"])
        self.assertEqual(scorecard["status"], "owner_review_eligible")
        self.assertTrue(all(gate["passed"] for gate in scorecard["gates"]))
        self.assertFalse(scorecard["policy_changed"])

    def test_performance_report_includes_news_event_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)
            proposal = account.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "Atlas paper entry rule with dominant event product launch.",
                rationale=[
                    "Atlas score is above the buy threshold.",
                    "News tone is constructive with Atlas classifies the dominant event as product launch.",
                    "Projection watch remains supportive with 74% sector breadth and a leadership trend posture.",
                ],
            )
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Atlas paper entry rule with dominant event product launch.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 101},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )

            report = account.render_performance_report()

        self.assertIn("Recent Execution Context", report)
        self.assertIn("product launch", report)
        self.assertIn("Projection-supported add", report)

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
