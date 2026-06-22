import tempfile
import unittest
import json
from datetime import datetime
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
                {
                    "agenda",
                    "owner_review",
                    "CEO",
                    "CIO",
                    "CRO",
                    "Reporting",
                    "Sector Analyst",
                },
            )
            self.assertTrue(all(path.exists() for path in paths.values()))

    def test_sector_analyst_role_uses_safe_brief_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.add_task(
                role="Sector Analyst",
                subject="Cybersecurity",
                prompt="Review sector weakness.",
            )

            saved_path = queue.save_role_brief("Sector Analyst")

        self.assertEqual(saved_path.name, "sector_analyst_brief.md")

    def test_complete_research_routes_task_to_owner_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            task, _ = queue.add_task(role="CRO", subject="NVDA", prompt="Review risk.")

            completed = queue.complete_research(
                task["id"],
                conclusion="The move appears event-driven.",
                recommendation="monitor",
                confidence="high",
                evidence=["Earnings release"],
            )
            review = queue.render_owner_review()

        self.assertEqual(completed["status"], "awaiting_owner")
        self.assertEqual(completed["result"]["recommendation"], "monitor")
        self.assertIn("The move appears event-driven.", review)
        self.assertIn("does not authorize or execute", review)

    def test_owner_decision_closes_or_defers_recommendation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            task, _ = queue.add_task(role="CIO", subject="NVDA", prompt="Review thesis.")
            queue.complete_research(
                task["id"],
                conclusion="Thesis remains intact.",
                recommendation="watchlist_review",
            )

            decided = queue.record_owner_decision(task["id"], "approve", notes="Reviewed.")

        self.assertEqual(decided["status"], "closed")
        self.assertEqual(decided["owner_decision"]["decision"], "approve")
        self.assertEqual(decided["owner_decision"]["notes"], "Reviewed.")

    def test_thesis_history_summary_counts_prior_reviews(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            first, _ = queue.add_task(role="CRO", subject="NVDA", prompt="Review risk.")
            queue.complete_research(
                first["id"],
                conclusion="Risk reviewed.",
                recommendation="risk_review",
                thesis_alignment="risk_to_thesis",
                thesis_drift="new_risk",
            )
            queue.record_owner_decision(first["id"], "defer", notes="Watch closely.")
            second, _ = queue.add_task(role="CIO", subject="NVDA", prompt="Review upside.")
            queue.complete_research(
                second["id"],
                conclusion="Driver reviewed.",
                recommendation="monitor",
                thesis_alignment="supports_driver",
                thesis_drift="new_support",
            )

            summary = queue.thesis_history_summary("nvda")

        self.assertEqual(summary["subject"], "NVDA")
        self.assertEqual(summary["review_count"], 2)
        self.assertEqual(summary["risk_to_thesis_count"], 1)
        self.assertEqual(summary["supports_driver_count"], 1)
        self.assertEqual(summary["decision_counts"]["defer"], 1)

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
            open_tasks = queue.list_tasks(status="open")

        self.assertGreaterEqual(len(first), 1)
        self.assertEqual(len(second), len(first))
        self.assertEqual(len(open_tasks), len(first))

    def test_generated_signal_refresh_updates_existing_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            first = queue.refresh_generated_tasks(
                [
                    {
                        "role": "CRO",
                        "subject": "MU",
                        "priority": "high",
                        "signal_type": "downside_move",
                        "prompt": "Review downside risk after a -6.00% move.",
                    }
                ],
                source="daily_run",
                generated_scope="daily_market",
                now=datetime(2026, 6, 10, 8, 0, 0),
            )
            second = queue.refresh_generated_tasks(
                [
                    {
                        "role": "CRO",
                        "subject": "MU",
                        "priority": "medium",
                        "signal_type": "downside_move",
                        "prompt": "Review downside risk after a -4.10% move.",
                    }
                ],
                source="daily_run",
                generated_scope="daily_market",
                now=datetime(2026, 6, 11, 8, 0, 0),
            )
            open_tasks = queue.list_tasks(status="open")

        self.assertEqual(first[0]["id"], second[0]["id"])
        self.assertEqual(second[0]["priority"], "medium")
        self.assertIn("-4.10%", second[0]["prompt"])
        self.assertEqual(len(open_tasks), 1)

    def test_generated_signal_refresh_preserves_pending_owner_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            task = queue.refresh_generated_tasks(
                [
                    {
                        "role": "CRO",
                        "subject": "MU",
                        "priority": "high",
                        "signal_type": "downside_move",
                        "prompt": "Review downside risk after a -6.00% move.",
                    }
                ],
                source="daily_run",
                generated_scope="daily_market",
                now=datetime(2026, 6, 10, 8, 0, 0),
            )[0]
            queue.complete_research(
                task["id"],
                conclusion="The catalyst remains uncertain.",
                recommendation="research_further",
                confidence="low",
            )

            refreshed = queue.refresh_generated_tasks(
                [
                    {
                        "role": "CRO",
                        "subject": "MU",
                        "priority": "high",
                        "signal_type": "downside_move",
                        "prompt": "Review downside risk after a -4.50% move.",
                    }
                ],
                source="new_daily_run",
                generated_scope="daily_market",
                now=datetime(2026, 6, 11, 8, 0, 0),
            )
            tasks = queue.list_tasks()

        self.assertEqual(len(tasks), 1)
        self.assertEqual(refreshed[0]["status"], "awaiting_owner")
        self.assertEqual(
            refreshed[0]["result"]["conclusion"],
            "The catalyst remains uncertain.",
        )
        self.assertEqual(refreshed[0]["source"], "new_daily_run")

    def test_complete_research_preserves_structured_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            task, _ = queue.add_task(
                role="CRO",
                subject="MU",
                prompt="Review risk.",
            )

            completed = queue.complete_research(
                task["id"],
                conclusion="Evidence reviewed.",
                recommendation="risk_review",
                catalyst_type="score_risk",
                thesis_action="Recheck thesis quality.",
                thesis_alignment="risk_to_thesis",
                thesis_drift="recurring_risk",
                evidence=[
                    {
                        "title": "Company update",
                        "source": "Example News",
                        "url": "https://example.com/update",
                        "detail": "Company-specific headline",
                    }
                ],
            )

        self.assertEqual(
            completed["result"]["evidence"][0]["url"],
            "https://example.com/update",
        )
        self.assertEqual(completed["result"]["catalyst_type"], "score_risk")
        self.assertEqual(
            completed["result"]["thesis_action"],
            "Recheck thesis quality.",
        )
        self.assertEqual(completed["result"]["thesis_alignment"], "risk_to_thesis")
        self.assertEqual(completed["result"]["thesis_drift"], "recurring_risk")

    def test_generated_signals_expire_without_refresh(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            queue.refresh_generated_tasks(
                [
                    {
                        "role": "CRO",
                        "subject": "MU",
                        "priority": "high",
                        "signal_type": "downside_move",
                        "prompt": "Review downside risk.",
                    }
                ],
                source="daily_run",
                generated_scope="daily_market",
                now=datetime(2026, 6, 5, 8, 0, 0),
            )

            closed = queue.maintain_generated_tasks(
                now=datetime(2026, 6, 9, 8, 0, 0)
            )
            tasks = queue.list_tasks()

        self.assertEqual(len(closed), 1)
        self.assertEqual(tasks[0]["status"], "closed")
        self.assertIn("expired after 3 days", tasks[0]["close_reason"])

    def test_legacy_weekly_duplicates_are_closed_but_newest_is_retained(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            task_file = Path(temp_dir) / "tasks.json"
            task_file.write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "id": "old",
                                "created_at": "2026-06-05T08:00:00",
                                "role": "CRO",
                                "priority": "high",
                                "status": "open",
                                "subject": "MU",
                                "source": "weekly_summary_20260605.md",
                                "prompt": (
                                    "Investigate MU: appeared as a top mover 11 times; "
                                    "review catalysts behind the -13.25% largest move."
                                ),
                            },
                            {
                                "id": "new",
                                "created_at": "2026-06-08T08:00:00",
                                "role": "CRO",
                                "priority": "high",
                                "status": "open",
                                "subject": "MU",
                                "source": "weekly_summary_20260608.md",
                                "prompt": (
                                    "Investigate MU: appeared as a top mover 24 times; "
                                    "review catalysts behind the -13.25% largest move."
                                ),
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            queue = ResearchTaskQueue(task_file)

            closed = queue.maintain_generated_tasks(
                now=datetime(2026, 6, 10, 8, 0, 0)
            )
            open_tasks = queue.list_tasks(status="open")

        self.assertEqual(len(closed), 1)
        self.assertEqual(open_tasks[0]["id"], "new")
        self.assertIn("Superseded", closed[0]["close_reason"])

    def test_manual_and_owner_review_tasks_are_never_auto_closed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue = ResearchTaskQueue(Path(temp_dir) / "tasks.json")
            manual, _ = queue.add_task(
                role="CIO",
                subject="NVDA",
                prompt="Owner-requested thesis review.",
                created_at="2026-01-01T08:00:00",
            )
            owner, _ = queue.add_task(
                role="CRO",
                subject="Risk",
                prompt="Review risk.",
                created_at="2026-01-01T08:00:00",
            )
            queue.complete_research(
                owner["id"],
                conclusion="Review complete.",
                recommendation="monitor",
            )

            closed = queue.maintain_generated_tasks(
                now=datetime(2026, 6, 10, 8, 0, 0)
            )
            task_statuses = {
                task["id"]: task["status"] for task in queue.list_tasks()
            }

        self.assertEqual(closed, [])
        self.assertEqual(
            task_statuses,
            {manual["id"]: "open", owner["id"]: "awaiting_owner"},
        )

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
