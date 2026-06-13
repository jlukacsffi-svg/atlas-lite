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
