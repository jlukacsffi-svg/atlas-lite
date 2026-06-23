import json
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
                "NVDA": {"status": "available", "price": 125.0},
                "RISK": {"status": "available", "price": 125.0},
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
        self.assertFalse(model["capabilities"]["real_trading"])
        self.assertFalse(model["capabilities"]["brokerage_connection"])

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
