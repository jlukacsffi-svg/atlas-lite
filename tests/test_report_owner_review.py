import unittest

from app.report_generator import ReportGenerator


class StubTaskQueue:
    def __init__(self, tasks):
        self.tasks = tasks

    def list_tasks(self, status=None):
        return [task for task in self.tasks if not status or task.get("status") == status]

    def _sorted_tasks(self, tasks):
        return tasks


class ReportOwnerReviewTests(unittest.TestCase):
    def test_owner_review_section_lists_pending_recommendations(self):
        generator = ReportGenerator({}, {})
        generator.research_task_queue = StubTaskQueue(
            [
                {
                    "status": "awaiting_owner",
                    "priority": "high",
                    "role": "CRO",
                    "subject": "NVDA",
                    "result": {
                        "recommendation": "risk_review",
                        "confidence": "high",
                        "conclusion": "Risk increased.",
                    },
                }
            ]
        )

        section = generator._generate_owner_review()

        self.assertIn("## Research Recommendations Awaiting Owner Review", section)
        self.assertIn("Risk Review", section)
        self.assertIn("Risk increased.", section)
        self.assertIn("does not authorize a trade", section)

    def test_owner_review_section_handles_empty_queue(self):
        generator = ReportGenerator({}, {})
        generator.research_task_queue = StubTaskQueue([])

        section = generator._generate_owner_review()

        self.assertIn("No completed research recommendations", section)


if __name__ == "__main__":
    unittest.main()
