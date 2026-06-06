import unittest

from app.report_generator import ReportGenerator


class _FakeQueue:
    def __init__(self, tasks):
        self.tasks = tasks

    def list_tasks(self, status=None):
        if status:
            return [task for task in self.tasks if task.get("status") == status]
        return self.tasks


class ReportResearchAgendaTests(unittest.TestCase):
    def test_research_agenda_renders_open_tasks(self):
        generator = ReportGenerator({}, {})
        generator.research_task_queue = _FakeQueue(
            [
                {
                    "status": "open",
                    "priority": "high",
                    "role": "CRO",
                    "subject": "ENPH",
                    "prompt": "Review downside risk.",
                    "created_at": "2026-06-05T08:00:00",
                },
                {
                    "status": "closed",
                    "priority": "medium",
                    "role": "CIO",
                    "subject": "NVDA",
                    "prompt": "Closed task.",
                    "created_at": "2026-06-05T08:00:00",
                },
            ]
        )

        section = generator._generate_research_agenda()

        self.assertIn("## Research Agenda", section)
        self.assertIn("| High | CRO | ENPH | Review downside risk. |", section)
        self.assertNotIn("Closed task", section)

    def test_research_agenda_handles_empty_queue(self):
        generator = ReportGenerator({}, {})
        generator.research_task_queue = _FakeQueue([])

        section = generator._generate_research_agenda()

        self.assertIn("No open research tasks", section)


if __name__ == "__main__":
    unittest.main()
