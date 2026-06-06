import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import paper_trading
from app.paper_trading import PaperTradingAccount


class PaperTradingCliTests(unittest.TestCase):
    def test_propose_research_requires_owner_approved_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
            )
            account.initialize(100000)
            task = {
                "id": "task_approved",
                "status": "closed",
                "subject": "NVDA",
                "result": {"conclusion": "Thesis remains intact."},
                "owner_decision": {"decision": "approve"},
            }

            with patch("paper_trading.PaperTradingAccount", return_value=account), patch(
                "paper_trading.ResearchTaskQueue"
            ) as queue_class:
                queue_class.return_value.list_tasks.return_value = [task]
                result = paper_trading.main(
                    [
                        "propose-research",
                        "task_approved",
                        "buy",
                        "10",
                        "--price",
                        "100",
                    ]
                )
                proposals = account.proposals()

        self.assertEqual(result, 0)
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0]["research_task_id"], "task_approved")
        self.assertEqual(proposals[0]["status"], "pending")

    def test_propose_research_rejects_unapproved_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
            )
            account.initialize(100000)
            task = {
                "id": "task_open",
                "status": "awaiting_owner",
                "subject": "NVDA",
                "result": {"conclusion": "Review needed."},
            }

            with patch("paper_trading.PaperTradingAccount", return_value=account), patch(
                "paper_trading.ResearchTaskQueue"
            ) as queue_class:
                queue_class.return_value.list_tasks.return_value = [task]
                with self.assertRaisesRegex(ValueError, "owner approval"):
                    paper_trading.main(
                        [
                            "propose-research",
                            "task_open",
                            "buy",
                            "10",
                            "--price",
                            "100",
                        ]
                    )


if __name__ == "__main__":
    unittest.main()
