import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.paper_trading import PaperTradingAccount
from app.weekly_summary import WeeklySummaryGenerator


class WeeklySummaryGeneratorTests(unittest.TestCase):
    def write_index(self, archive_dir):
        self.write_snapshot(
            archive_dir,
            "snapshot_1.json",
            {
                "NVDA": {
                    "sector": "AI & Semiconductors",
                    "status": "available",
                    "percent_change": 5.5,
                    "total_score": 90.0,
                },
                "AVGO": {
                    "sector": "AI & Semiconductors",
                    "status": "available",
                    "percent_change": -4.2,
                    "total_score": 88.0,
                },
                "MSFT": {
                    "sector": "Cloud Platforms",
                    "status": "available",
                    "percent_change": 1.0,
                    "total_score": 86.0,
                },
            },
        )
        self.write_snapshot(
            archive_dir,
            "snapshot_2.json",
            {
                "NVDA": {
                    "sector": "AI & Semiconductors",
                    "status": "available",
                    "percent_change": -6.5,
                    "total_score": 93.0,
                },
                "AVGO": {
                    "sector": "AI & Semiconductors",
                    "status": "available",
                    "percent_change": 2.0,
                    "total_score": 87.0,
                },
                "MSFT": {
                    "sector": "Cloud Platforms",
                    "status": "available",
                    "percent_change": 3.1,
                    "total_score": 88.0,
                },
            },
        )
        payload = {
            "entries": [
                {
                    "generated_at": "2026-06-01T08:00:00",
                    "universe_version": "1.3",
                    "securities": 56,
                    "available_securities": 56,
                    "snapshot_path": "snapshot_1.json",
                    "report_path": "../reports/morning_1.md",
                    "html_report_path": "../reports/morning_1.html",
                    "top_movers": [
                        {"ticker": "NVDA", "percent_change": 5.5},
                        {"ticker": "AVGO", "percent_change": -4.2},
                    ],
                    "score_leaders": [
                        {"ticker": "NVDA", "total_score": 93.0},
                        {"ticker": "KLAC", "total_score": 94.0},
                    ],
                },
                {
                    "generated_at": "2026-06-03T08:00:00",
                    "universe_version": "1.3",
                    "securities": 56,
                    "available_securities": 55,
                    "snapshot_path": "snapshot_2.json",
                    "report_path": "../reports/morning_2.md",
                    "html_report_path": "../reports/morning_2.html",
                    "top_movers": [
                        {"ticker": "NVDA", "percent_change": -6.5},
                        {"ticker": "MSFT", "percent_change": 3.1},
                    ],
                    "score_leaders": [
                        {"ticker": "NVDA", "total_score": 93.0},
                        {"ticker": "TSM", "total_score": 91.0},
                    ],
                },
                {
                    "generated_at": "2026-05-01T08:00:00",
                    "universe_version": "1.2",
                    "securities": 40,
                    "available_securities": 40,
                    "top_movers": [{"ticker": "OLD", "percent_change": 9.0}],
                    "score_leaders": [{"ticker": "OLD", "total_score": 80.0}],
                },
            ]
        }
        (Path(archive_dir) / "archive_index.json").write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def write_snapshot(self, archive_dir, filename, securities):
        payload = {
            "generated_at": "2026-06-01T08:00:00",
            "securities": securities,
        }
        (Path(archive_dir) / filename).write_text(
            json.dumps(payload),
            encoding="utf-8",
        )

    def test_generate_summary_uses_recent_archive_entries(self):
        with tempfile.TemporaryDirectory() as archive_dir:
            self.write_index(archive_dir)
            generator = WeeklySummaryGenerator(archive_dir=archive_dir)
            generator.timestamp = datetime(2026, 6, 4, 8, 0, 0)

            summary = generator.generate_summary(days=7)

        self.assertIn("Runs indexed**: 2", summary)
        self.assertIn("| NVDA | 2 | -6.50% |", summary)
        self.assertIn("| NVDA | 2 | 93.0 |", summary)
        self.assertIn("## What Changed This Week", summary)
        self.assertIn("Atlas ended the week with 55/56 securities available", summary)
        self.assertIn("Largest score improvement: NVDA rose from 90.0 to 93.0 (+3.0).", summary)
        self.assertIn("Most persistent top mover: NVDA appeared 2 times", summary)
        self.assertIn("## Research Action Prompts", summary)
        self.assertIn("Review NVDA: score improved +3.0 points", summary)
        self.assertIn("Challenge AVGO: score declined -1.0 points", summary)
        self.assertIn("Investigate NVDA: appeared as a top mover 2 times", summary)
        self.assertIn("| NVDA | 90.0 | 93.0 | +3.0 |", summary)
        self.assertIn("| AI & Semiconductors |", summary)
        self.assertIn("[markdown](morning_2.md)", summary)
        self.assertNotIn("OLD", summary)

    def test_save_summary_writes_markdown_and_html(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / "archive"
            reports_dir = Path(temp_dir) / "reports"
            archive_dir.mkdir()
            self.write_index(archive_dir)
            generator = WeeklySummaryGenerator(
                archive_dir=archive_dir,
                reports_dir=reports_dir,
            )
            generator.timestamp = datetime(2026, 6, 4, 8, 0, 0)

            markdown_path = generator.save_summary(days=7)

            self.assertTrue(markdown_path.exists())
            self.assertTrue(generator.last_html_path.exists())
            self.assertIn("Atlas Weekly Research Summary", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("<html", generator.last_html_path.read_text(encoding="utf-8"))

    def test_research_task_suggestions_assign_weekly_signals_to_roles(self):
        with tempfile.TemporaryDirectory() as archive_dir:
            self.write_index(archive_dir)
            generator = WeeklySummaryGenerator(archive_dir=archive_dir)
            generator.timestamp = datetime(2026, 6, 4, 8, 0, 0)

            suggestions = generator.research_task_suggestions(days=7)

        roles = {item["role"] for item in suggestions}
        subjects = {item["subject"] for item in suggestions}
        self.assertIn("CIO", roles)
        self.assertIn("CRO", roles)
        self.assertIn("Sector Analyst", roles)
        self.assertIn("NVDA", subjects)
        self.assertIn("AVGO", subjects)
        self.assertTrue(all(item.get("priority") for item in suggestions))

    def test_generate_summary_handles_empty_archive(self):
        with tempfile.TemporaryDirectory() as archive_dir:
            generator = WeeklySummaryGenerator(archive_dir=archive_dir)
            generator.timestamp = datetime(2026, 6, 4, 8, 0, 0)

            summary = generator.generate_summary(days=7)

        self.assertIn("No archive entries are available", summary)

    def test_weekly_summary_deduplicates_recent_paper_review_transitions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_dir = root / "archive"
            archive_dir.mkdir()
            self.write_index(archive_dir)
            paper_account = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
            )
            paper_account.initialize(100000)
            paper_account._append_event(
                {
                    "event": "defensive_review_tracking_started",
                    "timestamp": "2026-06-01T08:00:00",
                    "mode": "review_only",
                    "policy_changed": False,
                }
            )
            paper_account._append_event(
                {
                    "event": "defensive_review_signal",
                    "signal_id": "review_tsm",
                    "ticker": "TSM",
                    "status": "active",
                    "status_label": "New review",
                    "timestamp": "2026-06-02T08:00:00",
                    "latest_return_pct": -2.5,
                    "latest_lag_pct": -3.5,
                    "snapshots_observed": 1,
                }
            )
            paper_account._append_event(
                {
                    "event": "defensive_review_signal",
                    "signal_id": "review_tsm",
                    "ticker": "TSM",
                    "status": "persistent_weakness",
                    "status_label": "Weakness persists",
                    "timestamp": "2026-06-04T07:30:00",
                    "latest_return_pct": -4.25,
                    "latest_lag_pct": -5.75,
                    "snapshots_observed": 3,
                }
            )
            paper_account._append_event(
                {
                    "event": "defensive_review_signal",
                    "signal_id": "review_old",
                    "ticker": "OLD",
                    "status": "completed_loss",
                    "status_label": "Completed loss",
                    "timestamp": "2026-05-01T08:00:00",
                    "latest_return_pct": -8.0,
                    "latest_lag_pct": -9.0,
                    "snapshots_observed": 5,
                }
            )
            generator = WeeklySummaryGenerator(
                archive_dir=archive_dir,
                paper_account=paper_account,
            )
            generator.timestamp = datetime(2026, 6, 4, 8, 0, 0)

            summary = generator.generate_summary(days=7)

        self.assertIn("## Paper Defensive Review Evidence", summary)
        self.assertIn("1 persistent weakness", summary)
        self.assertIn(
            "| TSM | Weakness persists | -4.25% | -5.75% | 3 |",
            summary,
        )
        self.assertNotIn("| TSM | New review |", summary)
        self.assertNotIn("OLD", summary)
        self.assertIn("cannot change paper policy", summary)


if __name__ == "__main__":
    unittest.main()
