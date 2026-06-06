import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
