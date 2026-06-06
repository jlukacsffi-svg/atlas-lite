import tempfile
import unittest
import json
from pathlib import Path

from app.research_tasks import ResearchTaskQueue


class ResearchTaskQueueTests(unittest.TestCase):
    def test_add_task_deduplicates_open_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")

            first, created_first = queue.add_task(
                role="CIO",
                subject="NVDA",
                prompt="Review thesis quality.",
                source="test",
            )
            second, created_second = queue.add_task(
                role="CIO",
                subject="NVDA",
                prompt="Review thesis quality.",
                source="test",
            )

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first["id"], second["id"])

    def test_update_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            task, _ = queue.add_task(role="CRO", prompt="Review concentration risk.")

            updated = queue.update_status(task["id"], "closed")

        self.assertEqual(updated["status"], "closed")

    def test_invalid_role_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")

            with self.assertRaisesRegex(ValueError, "invalid research role"):
                queue.add_task(role="Trader", prompt="Not allowed.")

    def test_generate_from_archive_creates_role_based_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / "archive"
            archive_dir.mkdir()
            snapshot_path = archive_dir / "snapshot.json"
            snapshot_path.write_text(
                json.dumps(
                    {
                        "securities": {
                            "NVDA": {"status": "available"},
                            "BAD": {"status": "unavailable"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            archive_path = archive_dir / "archive_index.json"
            archive_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "generated_at": "2026-06-05T08:00:00",
                                "snapshot_path": "snapshot.json",
                                "report_path": "../reports/morning.md",
                                "top_movers": [
                                    {"ticker": "AVGO", "percent_change": -6.0},
                                    {"ticker": "NVDA", "percent_change": 5.0},
                                ],
                                "score_leaders": [
                                    {"ticker": "KLAC", "total_score": 94.0}
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")

            created = queue.generate_from_archive(archive_index_path=archive_path)

        self.assertGreaterEqual(len(created), 4)
        roles = {task["role"] for task in created}
        self.assertIn("CRO", roles)
        self.assertIn("CIO", roles)
        self.assertIn("Reporting", roles)


if __name__ == "__main__":
    unittest.main()
