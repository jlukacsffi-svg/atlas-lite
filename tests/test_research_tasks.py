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

            updated = queue.update_status(task["id"], "closed", notes="Risk reviewed.")

        self.assertEqual(updated["status"], "closed")
        self.assertEqual(updated["notes"], "Risk reviewed.")

    def test_update_status_appends_notes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            task, _ = queue.add_task(role="CIO", prompt="Review thesis.", notes="Initial note.")

            updated = queue.update_status(task["id"], "in_progress", notes="Started review.")

        self.assertIn("Initial note.", updated["notes"])
        self.assertIn("Started review.", updated["notes"])

    def test_summary_counts_tasks_by_status_role_and_priority(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(role="CRO", priority="high", subject="ENPH", prompt="Review downside risk.")
            task, _ = queue.add_task(role="CIO", priority="medium", subject="NVDA", prompt="Review thesis.")
            queue.update_status(task["id"], "closed")

            summary = queue.summary()

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_status"]["open"], 1)
        self.assertEqual(summary["by_status"]["closed"], 1)
        self.assertEqual(summary["by_role"]["CRO"], 1)
        self.assertEqual(len(summary["open_high_priority"]), 1)

    def test_render_agenda_groups_tasks_for_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(role="CRO", priority="high", subject="ENPH", prompt="Review downside risk.")
            queue.add_task(role="CIO", priority="medium", subject="NVDA", prompt="Review thesis.")

            agenda = queue.render_agenda()

        self.assertIn("# Atlas Research Task Agenda", agenda)
        self.assertIn("## High Priority", agenda)
        self.assertIn("### CRO", agenda)
        self.assertIn("### CIO", agenda)
        self.assertIn("Review downside risk.", agenda)

    def test_save_agenda_writes_markdown_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "agenda.md"
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(role="CIO", subject="NVDA", prompt="Review thesis.")

            saved_path = queue.save_agenda(output_path=output_path)
            saved_text = output_path.read_text(encoding="utf-8")

        self.assertEqual(saved_path, output_path)
        self.assertIn("Review thesis.", saved_text)

    def test_render_role_brief_filters_non_ceo_assignments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(role="CRO", priority="high", subject="ENPH", prompt="Review downside risk.")
            queue.add_task(role="CIO", priority="medium", subject="NVDA", prompt="Review thesis.")

            brief = queue.render_role_brief("CRO")

        self.assertIn("# Atlas CRO Research Brief", brief)
        self.assertIn("Review downside risk.", brief)
        self.assertNotIn("Review thesis.", brief)
        self.assertIn("does not authorize trades", brief)

    def test_render_ceo_brief_includes_all_roles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(role="CRO", subject="Risk", prompt="Review downside risk.")
            queue.add_task(role="CIO", subject="Thesis", prompt="Review thesis.")

            brief = queue.render_role_brief("CEO")

        self.assertIn("Review downside risk.", brief)
        self.assertIn("Review thesis.", brief)

    def test_save_role_brief_uses_role_specific_default_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(role="CIO", subject="NVDA", prompt="Review thesis.")

            saved_path = queue.save_role_brief("CIO")
            saved_text = saved_path.read_text(encoding="utf-8")

        self.assertEqual(saved_path.name, "cio_brief.md")
        self.assertIn("Review thesis.", saved_text)

    def test_save_review_outputs_writes_agenda_and_all_role_briefs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(role="CIO", subject="NVDA", prompt="Review thesis.")

            paths = queue.save_review_outputs()

            self.assertEqual(
                set(paths),
                {"agenda", "CEO", "CIO", "CRO", "Reporting"},
            )
            self.assertTrue(all(path.exists() for path in paths.values()))

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

    def test_generate_from_market_data_creates_current_run_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            market_data = {
                "LOSS": {
                    "status": "available",
                    "percent_change": -6.0,
                    "sector": "Software",
                    "scores": {
                        "growth": 70,
                        "quality": 70,
                        "moat": 70,
                        "momentum": 60,
                        "risk": 50,
                    },
                },
                "GAIN": {
                    "status": "available",
                    "percent_change": 5.0,
                    "sector": "Semiconductors",
                    "scores": {
                        "growth": 95,
                        "quality": 90,
                        "moat": 90,
                        "momentum": 95,
                        "risk": 80,
                    },
                },
                "BAD": {
                    "status": "unavailable",
                    "percent_change": None,
                    "sector": "Software",
                    "scores": {},
                },
            }

            created = queue.generate_from_market_data(
                market_data,
                source="test_daily_run",
            )

        roles = {task["role"] for task in created}
        subjects = {task["subject"] for task in created}
        self.assertIn("CRO", roles)
        self.assertIn("CIO", roles)
        self.assertIn("Reporting", roles)
        self.assertIn("LOSS", subjects)
        self.assertIn("GAIN", subjects)
        self.assertTrue(all(task["source"] == "test_daily_run" for task in created))

    def test_generate_from_market_data_deduplicates_repeated_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            market_data = {
                "NVDA": {
                    "status": "available",
                    "percent_change": 5.0,
                    "sector": "Semiconductors",
                    "scores": {
                        "growth": 95,
                        "quality": 90,
                        "moat": 95,
                        "momentum": 90,
                        "risk": 80,
                    },
                }
            }

            first = queue.generate_from_market_data(market_data)
            second = queue.generate_from_market_data(market_data)

        self.assertGreaterEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_generate_from_portfolio_summary_assigns_risk_and_data_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            summary = {
                "configured": True,
                "risk_alerts": [
                    {
                        "type": "position_concentration",
                        "severity": "high",
                        "message": "NVDA is 40.0% of tracked portfolio value.",
                    },
                    {
                        "type": "missing_data",
                        "severity": "medium",
                        "message": "Missing market data for holdings: TEST.",
                    },
                ],
            }

            created = queue.generate_from_portfolio_summary(summary, source="test_portfolio")

        self.assertEqual(len(created), 2)
        self.assertEqual({task["role"] for task in created}, {"CRO", "Reporting"})
        self.assertTrue(all(task["source"] == "test_portfolio" for task in created))

    def test_generate_from_portfolio_summary_skips_unconfigured_portfolio(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")

            created = queue.generate_from_portfolio_summary({"configured": False})

        self.assertEqual(created, [])


if __name__ == "__main__":
    unittest.main()
