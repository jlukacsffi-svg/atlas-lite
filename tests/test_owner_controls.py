import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from app.owner_controls import OwnerControlService
from app.paper_trading import PaperTradingAccount
from app.research_tasks import ResearchTaskQueue


class StubDashboardService:
    def __init__(self, root):
        self.research_queue = ResearchTaskQueue(root / "research" / "tasks.json")
        self.paper_account = PaperTradingAccount(
            account_file=root / "paper" / "account.json",
            ledger_file=root / "paper" / "ledger.jsonl",
        )

    def _latest_snapshot(self):
        return {
            "generated_at": "2026-06-12T08:00:00",
            "securities": {
                "NVDA": {
                    "status": "available",
                    "price": 125.0,
                    "percent_change": 4.25,
                    "category": "Watchlist",
                    "sector": "AI & Semiconductors",
                    "total_score": 88.0,
                    "news_signal": {
                        "signal_label": "constructive",
                        "signal_score": 64.0,
                        "positive_count": 1,
                        "negative_count": 0,
                        "company_headline_count": 2,
                        "dominant_event_type": "product_launch",
                        "positive_examples": ["NVIDIA announced a new product launch."],
                    },
                    "scores": {
                        "growth": 92.0,
                        "quality": 84.0,
                        "moat": 90.0,
                        "momentum": 86.0,
                        "risk": 78.0,
                    },
                },
                "RISK": {
                    "status": "available",
                    "price": 125.0,
                    "percent_change": -3.5,
                    "category": "Watchlist",
                    "sector": "Cybersecurity",
                    "total_score": 62.0,
                    "scores": {
                        "growth": 60.0,
                        "quality": 58.0,
                        "moat": 64.0,
                        "momentum": 55.0,
                        "risk": 72.0,
                    },
                },
            },
        }


class OwnerControlServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.dashboard = StubDashboardService(self.root)
        self.dashboard.paper_account.initialize(100000)
        task, _ = self.dashboard.research_queue.add_task(
            role="CIO",
            subject="NVDA",
            prompt="Review the investment thesis.",
        )
        self.dashboard.research_queue.complete_research(
            task["id"],
            conclusion="The thesis remains intact.",
            recommendation="monitor",
            confidence="high",
        )
        self.task_id = task["id"]
        self.service = OwnerControlService(self.dashboard)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_model_exposes_only_owner_review_and_active_paper_items(self):
        proposal = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )

        model = self.service.model()

        self.assertTrue(model["enabled"])
        self.assertEqual(model["research_reviews"][0]["id"], self.task_id)
        self.assertEqual(
            model["paper_proposals"][0]["proposal_id"],
            proposal["proposal_id"],
        )
        self.assertEqual(model["paper_proposals"][0]["action_label"], "purchase")
        self.assertFalse(model["capabilities"]["real_trading"])
        self.assertFalse(model["capabilities"]["brokerage_connection"])
        self.assertIn("owner_outcomes", model)
        self.assertTrue(model["paper_proposals"][0]["rationale"])
        self.assertEqual(
            model["paper_proposals"][0]["news_summary"]["label"],
            "constructive",
        )
        self.assertIn(
            "Main event read: product launch.",
            model["paper_proposals"][0]["news_summary"]["event_detail"],
        )
        self.assertTrue(model["paper_strategy_policy"]["available"])
        self.assertIn("entry_experiment_review", model)
        self.assertIn(
            "strategy_maximum_new_proposals",
            model["paper_strategy_policy"]["values"],
        )
        self.assertEqual(
            model["paper_strategy_policy"]["adaptive_profiles"][0]["label"],
            "Adaptive trade pressure",
        )
        self.assertEqual(
            model["paper_strategy_policy"]["adaptive_profiles"][1]["label"],
            "Adaptive benchmark trust",
        )

    def test_apply_updates_paper_strategy_policy(self):
        result = self.service.apply(
            "paper-policy",
            {
                "auto_manage_enabled": True,
                "strategy_maximum_new_proposals": 5,
                "strategy_target_position_pct": 6.5,
                "strategy_minimum_buy_score": 84.0,
                "strategy_maximum_exit_score": 58.0,
                "strategy_benchmark_excess_weight": 2.4,
                "strategy_trend_quality_weight": 0.35,
                "strategy_sector_repeat_penalty": 1.5,
                "strategy_minimum_daily_move_pct": -6.0,
            },
        )
        policy = self.dashboard.paper_account.load()["policy"]

        self.assertEqual(result["action"], "paper-policy")
        self.assertTrue(result["auto_manage_enabled"])
        self.assertTrue(policy["auto_manage_enabled"])
        self.assertEqual(policy["strategy_maximum_new_proposals"], 5)
        self.assertEqual(policy["strategy_target_position_pct"], 6.5)
        self.assertEqual(policy["strategy_minimum_buy_score"], 84.0)
        self.assertEqual(policy["strategy_maximum_exit_score"], 58.0)
        self.assertEqual(policy["strategy_benchmark_excess_weight"], 2.4)
        self.assertEqual(policy["strategy_trend_quality_weight"], 0.35)
        self.assertEqual(policy["strategy_sector_repeat_penalty"], 1.5)
        self.assertEqual(policy["strategy_minimum_daily_move_pct"], -6.0)

    def test_apply_rejects_entry_experiment_before_evidence_gate(self):
        with self.assertRaisesRegex(ValueError, "evidence gate is not complete"):
            self.service.apply(
                "entry-experiment-decision",
                {"decision": "reject"},
            )
        with self.assertRaisesRegex(ValueError, "result is not ready"):
            self.service.apply(
                "entry-experiment-result",
                {
                    "decision": "retain",
                    "confirmation": "RETAIN PAPER EXPERIMENT",
                },
            )

    def test_model_backfills_structured_rationale_for_legacy_buy_proposals(self):
        proposal = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        prior, _ = self.dashboard.research_queue.add_task(
            role="CRO",
            subject="NVDA",
            prompt="Review downside catalyst.",
            priority="high",
        )
        self.dashboard.research_queue.complete_research(
            prior["id"],
            conclusion="Fresh risk review.",
            recommendation="risk_review",
            confidence="medium",
            catalyst_type="score_risk",
            thesis_alignment="risk_to_thesis",
            thesis_drift="new_risk",
            evidence=[
                {
                    "title": "NVDA thesis history",
                    "source": "Atlas research task memory",
                    "detail": "Prior risk review",
                }
            ],
        )

        model = self.service.model()
        item = next(
            proposal_item
            for proposal_item in model["paper_proposals"]
            if proposal_item["proposal_id"] == proposal["proposal_id"]
        )
        combined = " ".join(item["rationale"])

        self.assertIn("Atlas score 88.0 keeps NVDA", combined)
        self.assertIn("Strongest score inputs", combined)
        self.assertIn("starting simulated cash", combined)
        self.assertNotIn(
            "created before structured Why now rationale",
            combined,
        )
        objections = " ".join(item["objections"])
        self.assertIn("risk-to-thesis review", objections)
        self.assertIn("Latest stored Atlas review tagged NVDA as risk to thesis", objections)
        self.assertIn("Recent disconfirming evidence: NVDA thesis history.", objections)
        self.assertIn("highest-conviction tier", objections)

    def test_model_backfills_structured_rationale_for_legacy_sell_proposals(self):
        buy = self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            buy["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(buy["proposal_id"], "approve")
        self.dashboard.paper_account.execute_order(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
            proposal_id=buy["proposal_id"],
        )
        sell = self.dashboard.paper_account.create_proposal(
            "sell",
            "RISK",
            5,
            125,
            "Trim review.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            sell["proposal_id"],
            "caution",
            ["recurring thesis risk", "position above preferred size"],
        )
        prior, _ = self.dashboard.research_queue.add_task(
            role="CRO",
            subject="RISK",
            prompt="Review recurring risk.",
            priority="high",
        )
        self.dashboard.research_queue.complete_research(
            prior["id"],
            conclusion="Recurring risk review.",
            recommendation="risk_review",
            confidence="medium",
            catalyst_type="score_risk",
            thesis_alignment="risk_to_thesis",
            thesis_drift="recurring_risk",
            evidence=[
                {
                    "title": "RISK thesis history",
                    "source": "Atlas research task memory",
                    "detail": "Recurring risk",
                }
            ],
        )

        model = self.service.model()
        item = next(
            proposal_item
            for proposal_item in model["paper_proposals"]
            if proposal_item["proposal_id"] == sell["proposal_id"]
        )
        combined = " ".join(item["rationale"])

        self.assertIn("proposing a trim of 5", combined)
        self.assertIn("Risk review flags:", combined)
        self.assertIn("Paper learning context:", combined)
        self.assertIn("Trim trigger:", item["sell_trigger_summary"])
        self.assertTrue(
            any("risk to thesis" in row for row in item["sell_trigger_reasons"])
        )
        self.assertTrue(
            any("Risk review flags:" in row for row in item["sell_trigger_reasons"])
        )
        objections = " ".join(item["objections"])
        self.assertIn("Latest stored Atlas review tagged RISK as risk to thesis", objections)
        self.assertIn("Recent disconfirming evidence: RISK thesis history.", objections)
        self.assertIn("A trim would still leave 5", objections)

    def test_model_labels_partial_sell_as_trim(self):
        buy = self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            buy["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(buy["proposal_id"], "approve")
        self.dashboard.paper_account.execute_order(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
            proposal_id=buy["proposal_id"],
        )
        sell = self.dashboard.paper_account.create_proposal(
            "sell",
            "RISK",
            5,
            125,
            "Trim review.",
        )

        model = self.service.model()
        proposal = next(
            item
            for item in model["paper_proposals"]
            if item["proposal_id"] == sell["proposal_id"]
        )

        self.assertEqual(proposal["action_label"], "trim")
        self.assertEqual(proposal["position_shares"], 10.0)

    def test_model_adds_supportive_paper_calibration_to_buy_proposals(self):
        times = iter(
            [
                datetime(2026, 6, 12, 9, 0, 0),
                datetime(2026, 6, 12, 9, 1, 0),
                datetime(2026, 6, 12, 9, 2, 0),
                datetime(2026, 6, 12, 9, 3, 0),
                datetime(2026, 6, 12, 16, 0, 0),
                datetime(2026, 6, 13, 16, 0, 0),
                datetime(2026, 6, 14, 16, 0, 0),
                datetime(2026, 6, 15, 16, 0, 0),
                datetime(2026, 6, 15, 9, 0, 0),
                datetime(2026, 6, 15, 9, 1, 0),
            ]
        )
        self.dashboard.paper_account = PaperTradingAccount(
            account_file=self.root / "paper" / "calibration_buy_account.json",
            ledger_file=self.root / "paper" / "calibration_buy_ledger.jsonl",
            clock=lambda: next(times),
        )
        self.dashboard.paper_account.initialize(100000)
        self.service = OwnerControlService(self.dashboard)
        self.dashboard.paper_account.record_performance_snapshot(
            prices={},
            benchmark_prices={"SPY": 500, "QQQ": 400},
        )
        prior = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            100,
            "Prior paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            prior["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(prior["proposal_id"], "approve")
        self.dashboard.paper_account.execute_order(
            "buy",
            "NVDA",
            10,
            100,
            "Prior paper entry.",
            proposal_id=prior["proposal_id"],
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"NVDA": 130},
            benchmark_prices={"SPY": 505, "QQQ": 404},
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"NVDA": 132},
            benchmark_prices={"SPY": 506, "QQQ": 405},
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"NVDA": 135},
            benchmark_prices={"SPY": 507, "QQQ": 406},
        )
        current = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            5,
            125,
            "Current paper entry.",
        )

        model = self.service.model()
        proposal = next(
            item
            for item in model["paper_proposals"]
            if item["proposal_id"] == current["proposal_id"]
        )

        self.assertGreater(proposal["paper_calibration"]["adjustment"], 0)
        self.assertEqual(proposal["paper_calibration"]["label"], "supportive")
        self.assertIn(
            "latest judged NVDA buy ideas outcome was working",
            proposal["paper_calibration"]["reasons"],
        )
        self.assertIn(
            "latest judged NVDA buy ideas 3-snapshot persistence stayed working",
            proposal["paper_calibration"]["reasons"],
        )

    def test_model_adds_caution_paper_calibration_to_sell_proposals(self):
        times = iter(
            [
                datetime(2026, 6, 12, 9, 0, 0),
                datetime(2026, 6, 12, 9, 1, 0),
                datetime(2026, 6, 12, 9, 2, 0),
                datetime(2026, 6, 12, 9, 3, 0),
                datetime(2026, 6, 12, 16, 0, 0),
                datetime(2026, 6, 13, 9, 0, 0),
                datetime(2026, 6, 13, 9, 1, 0),
                datetime(2026, 6, 13, 9, 2, 0),
                datetime(2026, 6, 13, 16, 0, 0),
                datetime(2026, 6, 14, 16, 0, 0),
                datetime(2026, 6, 15, 16, 0, 0),
                datetime(2026, 6, 16, 9, 0, 0),
                datetime(2026, 6, 16, 9, 1, 0),
                datetime(2026, 6, 16, 9, 2, 0),
            ]
        )
        self.dashboard.paper_account = PaperTradingAccount(
            account_file=self.root / "paper" / "calibration_sell_account.json",
            ledger_file=self.root / "paper" / "calibration_sell_ledger.jsonl",
            clock=lambda: next(times),
        )
        self.dashboard.paper_account.initialize(100000)
        self.service = OwnerControlService(self.dashboard)
        buy = self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            buy["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(buy["proposal_id"], "approve")
        self.dashboard.paper_account.execute_order(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
            proposal_id=buy["proposal_id"],
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"RISK": 100},
            benchmark_prices={"SPY": 500, "QQQ": 400},
        )
        prior_sell = self.dashboard.paper_account.create_proposal(
            "sell",
            "RISK",
            5,
            100,
            "Prior trim review.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            prior_sell["proposal_id"],
            "caution",
            [],
        )
        self.dashboard.paper_account.decide_proposal(prior_sell["proposal_id"], "approve")
        self.dashboard.paper_account.execute_order(
            "sell",
            "RISK",
            5,
            100,
            "Prior trim review.",
            proposal_id=prior_sell["proposal_id"],
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"RISK": 120},
            benchmark_prices={"SPY": 503, "QQQ": 404},
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"RISK": 123},
            benchmark_prices={"SPY": 504, "QQQ": 405},
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"RISK": 126},
            benchmark_prices={"SPY": 505, "QQQ": 406},
        )
        current_sell = self.dashboard.paper_account.create_proposal(
            "sell",
            "RISK",
            2,
            125,
            "Current trim review.",
        )

        model = self.service.model()
        proposal = next(
            item
            for item in model["paper_proposals"]
            if item["proposal_id"] == current_sell["proposal_id"]
        )

        self.assertLess(proposal["paper_calibration"]["adjustment"], 0)
        self.assertEqual(proposal["paper_calibration"]["label"], "caution")
        self.assertIn(
            "lagging",
            " ".join(proposal["paper_calibration"]["reasons"]),
        )
        self.assertIn(
            "3-snapshot persistence stayed lagging",
            " ".join(proposal["paper_calibration"]["reasons"]),
        )

    def test_model_ranks_recurring_thesis_risks_first(self):
        proposal = self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            100,
            100,
            "Paper exposure for a recurring risk review.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            proposal["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(
            proposal["proposal_id"],
            "approve",
        )
        self.dashboard.paper_account.execute_order(
            "buy",
            "RISK",
            100,
            100,
            "Paper exposure for a recurring risk review.",
            proposal_id=proposal["proposal_id"],
        )
        self.dashboard.paper_account.record_performance_snapshot(
            prices={"RISK": 125},
            benchmark_prices={"SPY": 500, "QQQ": 400},
        )
        self.dashboard.paper_account.record_position_review(
            "RISK",
            "review",
            125,
            25,
            62,
            ["recurring thesis risk"],
            "Paper exposure needs owner review.",
        )
        low_task, _ = self.dashboard.research_queue.add_task(
            role="CIO",
            subject="LOW",
            prompt="Monitor.",
            priority="medium",
        )
        self.dashboard.research_queue.complete_research(
            low_task["id"],
            conclusion="Monitor only.",
            recommendation="monitor",
            confidence="medium",
            thesis_alignment="neutral_context",
            thesis_drift="stable_monitoring",
        )
        urgent_task, _ = self.dashboard.research_queue.add_task(
            role="CRO",
            subject="RISK",
            prompt="Review recurring risk.",
            priority="high",
        )
        self.dashboard.research_queue.complete_research(
            urgent_task["id"],
            conclusion="Recurring risk.",
            recommendation="risk_review",
            confidence="medium",
            catalyst_type="score_risk",
            thesis_alignment="risk_to_thesis",
            thesis_drift="recurring_risk",
            evidence=[
                {
                    "title": "RISK thesis history",
                    "source": "Atlas research task memory",
                    "detail": "2 prior reviews | 1 prior risk-to-thesis",
                }
            ],
        )

        model = self.service.model()

        self.assertEqual(model["research_reviews"][0]["subject"], "RISK")
        self.assertEqual(model["research_reviews"][0]["attention_label"], "Urgent")
        self.assertGreater(
            model["research_reviews"][0]["attention_score"],
            model["research_reviews"][-1]["attention_score"],
        )
        self.assertIn(
            "recurring thesis risk",
            model["research_reviews"][0]["attention_reasons"],
        )
        self.assertEqual(model["daily_action_list"][0]["subject"], "RISK")
        self.assertIn(
            "Review first",
            model["daily_action_list"][0]["suggested_disposition"],
        )
        self.assertIn("recurring thesis risk", model["daily_action_list"][0]["summary"])
        self.assertIn(
            "RISK thesis history",
            model["daily_action_list"][0]["evidence_anchor"],
        )
        self.assertIn(
            "Simulated position: 100 shares",
            model["daily_action_list"][0]["portfolio_context"],
        )
        self.assertIn(
            "Paper account return",
            model["daily_action_list"][0]["paper_context"],
        )
        self.assertIn(
            "latest RISK thesis review",
            model["daily_action_list"][0]["paper_context"],
        )
        self.assertIn(
            "adaptive daily trade pressure",
            model["daily_action_list"][0]["paper_context"],
        )
        self.assertIn(
            "adaptive benchmark trust",
            model["daily_action_list"][0]["paper_context"],
        )

    def test_model_summarizes_owner_outcome_history(self):
        second, _ = self.dashboard.research_queue.add_task(
            role="CRO",
            subject="AMD",
            prompt="Review downside risk.",
            priority="high",
        )
        self.dashboard.research_queue.complete_research(
            second["id"],
            conclusion="Risk needs more evidence.",
            recommendation="risk_review",
            confidence="medium",
        )
        self.service.apply(
            "research-decision",
            {"task_id": self.task_id, "decision": "approve"},
        )
        self.service.apply(
            "research-decision",
            {"task_id": second["id"], "decision": "defer"},
        )

        model = self.service.model()
        outcomes = model["owner_outcomes"]

        self.assertEqual(outcomes["research_decisions"], 2)
        self.assertEqual(outcomes["research_decision_counts"]["approve"], 1)
        self.assertEqual(outcomes["research_decision_counts"]["defer"], 1)
        self.assertEqual(outcomes["research_approval_rate_pct"], 50.0)
        self.assertIn("risk_review", outcomes["recommendation_counts"])
        recent_subjects = {
            item["subject"] for item in outcomes["recent_research_decisions"]
        }
        self.assertIn("AMD", recent_subjects)
        self.assertIn("NVDA", recent_subjects)
        self.assertIn("Owner decisions", outcomes["learning_signal"])

    def test_attention_score_uses_owner_outcome_calibration(self):
        for index in range(2):
            prior, _ = self.dashboard.research_queue.add_task(
                role="CRO",
                subject="CAL",
                prompt=f"Prior caution {index}.",
                priority="high",
            )
            self.dashboard.research_queue.complete_research(
                prior["id"],
                conclusion="Prior review needed more evidence.",
                recommendation="risk_review",
                confidence="medium",
            )
            self.dashboard.research_queue.record_owner_decision(
                prior["id"],
                "defer",
            )
        current, _ = self.dashboard.research_queue.add_task(
            role="CRO",
            subject="CAL",
            prompt="Current risk review.",
            priority="high",
        )
        self.dashboard.research_queue.complete_research(
            current["id"],
            conclusion="Current risk requires review.",
            recommendation="risk_review",
            confidence="medium",
            thesis_alignment="risk_to_thesis",
            thesis_drift="new_risk",
        )

        model = self.service.model()
        review = next(
            item for item in model["research_reviews"] if item["subject"] == "CAL"
        )

        self.assertEqual(review["outcome_calibration"]["adjustment"], -8)
        self.assertIn(
            "owner history: prior caution for this ticker",
            review["attention_reasons"],
        )
        self.assertIn(
            "outcome_calibration",
            next(
                item
                for item in model["daily_action_list"]
                if item["subject"] == "CAL"
            ),
        )

    def test_model_builds_ranked_portfolio_action_queue(self):
        buy_fill = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            buy_fill["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(
            buy_fill["proposal_id"],
            "approve",
        )
        self.dashboard.paper_account.execute_order(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
            proposal_id=buy_fill["proposal_id"],
        )
        self.dashboard.paper_account.record_position_review(
            "NVDA",
            "review",
            118,
            -1.6667,
            68,
            ["Atlas score 68.0 is below the 70.0 review threshold."],
            "Atlas wants a closer thesis review on this holding.",
        )
        self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            5,
            125,
            "Paper entry for risk review.",
        )

        model = self.service.model()
        queue = model["portfolio_action_queue"]

        self.assertEqual(len(queue), 2)
        self.assertEqual(queue[0]["kind"], "proposal")
        self.assertEqual(queue[0]["subject"], "RISK")
        self.assertEqual(queue[0]["status_label"], "Buy candidate")
        self.assertEqual(queue[1]["kind"], "position")
        self.assertEqual(queue[1]["subject"], "NVDA")
        self.assertEqual(queue[1]["status_label"], "Watch closely")
        self.assertIn("latest thesis signals", queue[1]["next_step"])

    def test_queue_surfaces_projection_caution_on_open_holding(self):
        entry = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            entry["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(
            entry["proposal_id"],
            "approve",
        )
        self.dashboard.paper_account.execute_order(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
            proposal_id=entry["proposal_id"],
        )
        self.dashboard.paper_account.record_position_review(
            "NVDA",
            "review",
            118,
            -1.6667,
            68,
            [
                "Projection caution triggered: Atlas wants more proof because benchmark leadership, sector participation, or news tone is no longer clearly supportive."
            ],
            (
                "Daily paper thesis review for NVDA: Atlas currently wants to review this simulated holding. "
                "Projection posture is needs proof with -0.80% excess return versus SPY since entry. "
                "Sector breadth is 40%."
            ),
        )

        model = self.service.model()
        queue_item = next(
            item for item in model["portfolio_action_queue"] if item["subject"] == "NVDA"
        )

        self.assertEqual(queue_item["decision_driver"]["label"], "Projection caution")
        self.assertIn("more proof", queue_item["decision_driver"]["summary"])
        self.assertIn("Projection caution triggered", queue_item["evidence_anchor"])

    def test_queue_surfaces_projection_supported_add_on_buy_proposal(self):
        self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            5,
            130,
            "Atlas winner add rule for NVDA remains constructive.",
            rationale=[
                "Winner add rule triggered: Atlas score 92.0 is at or above the 90.0 add threshold.",
                "Projection watch remains supportive with 75% sector breadth and a leadership trend posture.",
            ],
        )

        model = self.service.model()
        queue_item = next(
            item for item in model["portfolio_action_queue"] if item["subject"] == "NVDA"
        )

        self.assertEqual(queue_item["decision_driver"]["label"], "Projection-supported add")
        self.assertIn("support adding", queue_item["decision_driver"]["summary"])
        self.assertIn("Projection watch remains supportive", queue_item["evidence_anchor"])

    def test_active_sell_proposal_suppresses_duplicate_open_position_queue_item(self):
        entry = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            entry["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(
            entry["proposal_id"],
            "approve",
        )
        self.dashboard.paper_account.execute_order(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
            proposal_id=entry["proposal_id"],
        )
        self.dashboard.paper_account.record_position_review(
            "NVDA",
            "exit",
            95,
            -20.8333,
            55,
            ["Atlas score 55.0 is at or below the 60.0 exit threshold."],
            "Atlas wants to reduce or exit this holding.",
        )
        exit_proposal = self.dashboard.paper_account.create_proposal(
            "sell",
            "NVDA",
            10,
            95,
            "Atlas wants to exit the simulated holding.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            exit_proposal["proposal_id"],
            "clear",
            [],
        )

        model = self.service.model()
        queue = [
            item
            for item in model["portfolio_action_queue"]
            if item["subject"] == "NVDA"
        ]

        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["kind"], "proposal")
        self.assertEqual(queue[0]["status_label"], "Exit candidate")

    def test_model_explains_healthy_holdings_absent_from_queue(self):
        entry = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            entry["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(
            entry["proposal_id"],
            "approve",
        )
        self.dashboard.paper_account.execute_order(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
            proposal_id=entry["proposal_id"],
        )
        self.dashboard.paper_account.record_position_review(
            "NVDA",
            "maintain",
            126,
            5.0,
            88,
            ["Latest thesis review remains constructive."],
            "Atlas keeps the simulated position in hold mode.",
        )

        model = self.service.model()
        summary = model["healthy_holdings_summary"]

        self.assertEqual(summary["count"], 1)
        self.assertIn("intentionally absent", summary["headline"])
        self.assertEqual(summary["items"][0]["ticker"], "NVDA")
        self.assertIn("constructive", summary["items"][0]["summary"].lower())
        self.assertTrue(summary["items"][0]["journal"])
        self.assertIn("Current basis", summary["items"][0]["journal"][0])
        self.assertTrue(summary["items"][0]["is_freshest_shift"])
        self.assertIn("Freshest shift as of", summary["items"][0]["freshness_label"])
        self.assertEqual(summary["items"][0]["anchor_id"], "controls-healthy-nvda")

    def test_model_builds_controls_summary(self):
        entry = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            entry["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(
            entry["proposal_id"],
            "approve",
        )
        self.dashboard.paper_account.execute_order(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
            proposal_id=entry["proposal_id"],
        )
        self.dashboard.paper_account.record_position_review(
            "NVDA",
            "maintain",
            126,
            5.0,
            88,
            ["Latest thesis review remains constructive."],
            "Atlas keeps the simulated position in hold mode.",
        )
        self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            5,
            125,
            "Paper entry for risk review.",
        )

        model = self.service.model()
        summary = model["controls_summary"]

        self.assertEqual(summary["counts"]["open_positions"], 1)
        self.assertEqual(summary["counts"]["queue"], 1)
        self.assertEqual(summary["counts"]["healthy"], 1)
        self.assertEqual(summary["counts"]["buy_proposals"], 1)
        self.assertIn("remain steady", summary["headline"])
        self.assertIn("entry-led", summary["posture"])
        self.assertEqual(summary["freshest_change"]["bucket"], "queue")
        self.assertEqual(summary["freshest_change"]["bucket_label"], "Portfolio action queue")
        self.assertEqual(summary["freshest_change"]["subject"], "RISK")
        self.assertIn("newest buy candidate", summary["freshest_change"]["detail"].lower())
        self.assertTrue(summary["freshest_change"]["timestamp_label"])
        self.assertIn(" ", summary["freshest_change"]["timestamp_label"])
        self.assertEqual(summary["freshest_change"]["anchor_id"], "controls-queue-risk")
        self.assertTrue(model["portfolio_action_queue"][0]["is_freshest_shift"])
        self.assertIn(
            "Freshest shift as of",
            model["portfolio_action_queue"][0]["freshness_label"],
        )
        self.assertEqual(model["portfolio_action_queue"][0]["anchor_id"], "controls-queue-risk")
        self.assertFalse(model["healthy_holdings_summary"]["items"][0]["is_freshest_shift"])

    def test_research_decision_is_saved_and_persisted(self):
        persisted = []
        service = OwnerControlService(
            self.dashboard,
            persist=lambda paths: persisted.append(paths),
        )

        result = service.apply(
            "research-decision",
            {"task_id": self.task_id, "decision": "approve"},
        )

        self.assertEqual(result["status"], "closed")
        self.assertEqual(len(persisted), 1)
        self.assertIn(
            self.dashboard.research_queue.task_file,
            persisted[0],
        )
        self.assertTrue(
            (self.root / "research" / "owner_review.md").exists()
        )

    def test_paper_approval_requires_existing_risk_review(self):
        proposal = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )

        with self.assertRaisesRegex(ValueError, "requires a risk review"):
            self.service.apply(
                "paper-decision",
                {
                    "proposal_id": proposal["proposal_id"],
                    "decision": "approve",
                },
            )

        self.dashboard.paper_account.record_proposal_risk_review(
            proposal["proposal_id"],
            "clear",
            [],
        )
        result = self.service.apply(
            "paper-decision",
            {
                "proposal_id": proposal["proposal_id"],
                "decision": "approve",
            },
        )
        self.assertEqual(result["status"], "approved")

    def test_paper_fill_requires_exact_simulation_confirmation(self):
        proposal = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        proposal_id = proposal["proposal_id"]
        self.dashboard.paper_account.record_proposal_risk_review(
            proposal_id,
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(proposal_id, "approve")

        with self.assertRaisesRegex(ValueError, "Confirmation must be"):
            self.service.apply(
                "paper-fill",
                {
                    "proposal_id": proposal_id,
                    "confirmation": "BUY",
                },
            )

        result = self.service.apply(
            "paper-fill",
            {
                "proposal_id": proposal_id,
                "confirmation": f"SIMULATE {proposal_id}",
            },
        )
        self.assertTrue(result["simulation_only"])
        self.assertEqual(result["price"], 125.0)
        self.assertEqual(
            self.dashboard.paper_account.proposal_status(proposal_id),
            "executed",
        )

    def test_paper_fill_can_record_approved_simulated_exit(self):
        buy = self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            buy["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(buy["proposal_id"], "approve")
        self.dashboard.paper_account.execute_order(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
            proposal_id=buy["proposal_id"],
        )
        sell = self.dashboard.paper_account.create_proposal(
            "sell",
            "RISK",
            10,
            125,
            "Paper exit review.",
        )
        proposal_id = sell["proposal_id"]
        self.dashboard.paper_account.record_proposal_risk_review(
            proposal_id,
            "caution",
            ["Exit review."],
        )
        self.dashboard.paper_account.decide_proposal(proposal_id, "approve")

        result = self.service.apply(
            "paper-fill",
            {
                "proposal_id": proposal_id,
                "confirmation": f"SIMULATE {proposal_id}",
            },
        )
        state = self.dashboard.paper_account.load()

        self.assertTrue(result["simulation_only"])
        self.assertEqual(result["side"], "sell")
        self.assertEqual(result["action_label"], "exit")
        self.assertEqual(result["price"], 125.0)
        self.assertNotIn("RISK", state["positions"])
        self.assertEqual(
            self.dashboard.paper_account.proposal_status(proposal_id),
            "executed",
        )

    def test_paper_fill_can_record_approved_simulated_trim(self):
        buy = self.dashboard.paper_account.create_proposal(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            buy["proposal_id"],
            "clear",
            [],
        )
        self.dashboard.paper_account.decide_proposal(buy["proposal_id"], "approve")
        self.dashboard.paper_account.execute_order(
            "buy",
            "RISK",
            10,
            100,
            "Paper entry.",
            proposal_id=buy["proposal_id"],
        )
        sell = self.dashboard.paper_account.create_proposal(
            "sell",
            "RISK",
            5,
            125,
            "Paper trim review.",
        )
        proposal_id = sell["proposal_id"]
        self.dashboard.paper_account.record_proposal_risk_review(
            proposal_id,
            "caution",
            ["Trim review."],
        )
        self.dashboard.paper_account.decide_proposal(proposal_id, "approve")

        result = self.service.apply(
            "paper-fill",
            {
                "proposal_id": proposal_id,
                "confirmation": f"SIMULATE {proposal_id}",
            },
        )
        state = self.dashboard.paper_account.load()

        self.assertTrue(result["simulation_only"])
        self.assertEqual(result["side"], "sell")
        self.assertEqual(result["action_label"], "trim")
        self.assertEqual(state["positions"]["RISK"]["shares"], 5.0)

    def test_auto_manage_mode_clears_pending_paper_approval_work(self):
        self.dashboard.paper_account.update_policy(
            {"auto_manage_enabled": True},
            source="test",
        )
        proposal = self.dashboard.paper_account.create_proposal(
            "buy",
            "NVDA",
            10,
            120,
            "Paper entry.",
        )
        self.dashboard.paper_account.record_proposal_risk_review(
            proposal["proposal_id"],
            "clear",
            [],
        )

        model = self.service.model()

        self.assertTrue(model["paper_auto_manage_enabled"])
        self.assertFalse(model["capabilities"]["paper_proposal_decisions"])
        self.assertFalse(model["capabilities"]["simulated_fills"])
        self.assertEqual(model["paper_proposals"], [])
        self.assertEqual(model["autonomous_cycle"]["approved"], [proposal["proposal_id"]])
        self.assertEqual(len(model["autonomous_cycle"]["executed"]), 1)
        self.assertEqual(
            self.dashboard.paper_account.proposal_status(proposal["proposal_id"]),
            "executed",
        )

    def test_auto_manage_mode_auto_resolves_research_reviews(self):
        self.dashboard.paper_account.update_policy(
            {"auto_manage_enabled": True},
            source="test",
        )

        model = self.service.model()
        updated_task = next(
            item
            for item in self.dashboard.research_queue.load()["tasks"]
            if item["id"] == self.task_id
        )

        self.assertFalse(model["capabilities"]["research_decisions"])
        self.assertEqual(model["research_reviews"], [])
        self.assertEqual(
            model["autonomous_research_cycle"]["approved"],
            [self.task_id],
        )
        self.assertEqual(updated_task["status"], "closed")
        self.assertEqual(
            updated_task["owner_decision"]["decision"],
            "approve",
        )

    def test_persistence_failure_restores_local_artifacts(self):
        original = self.dashboard.research_queue.task_file.read_bytes()

        def fail(paths):
            raise RuntimeError("storage conflict")

        service = OwnerControlService(self.dashboard, persist=fail)
        with self.assertRaisesRegex(RuntimeError, "storage conflict"):
            service.apply(
                "research-decision",
                {"task_id": self.task_id, "decision": "approve"},
            )

        self.assertEqual(
            self.dashboard.research_queue.task_file.read_bytes(),
            original,
        )
        self.assertEqual(
            json.loads(original)["tasks"][0]["status"],
            "awaiting_owner",
        )


if __name__ == "__main__":
    unittest.main()
