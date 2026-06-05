"""Tests for Atlas structured research memory."""

from datetime import datetime
import json
import tempfile
import unittest
from pathlib import Path

from app.research_memory import ResearchMemory


class ResearchMemoryTests(unittest.TestCase):
    def test_snapshot_save_and_load(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ResearchMemory(temp_dir)
            timestamp = datetime(2026, 6, 2, 8, 30, 0)

            path = memory.save_snapshot(
                market_data=self._market_data(),
                market_summary={"SPY": {"price": 500.0, "percent_change": 1.0}},
                universe_version="1.1",
                timestamp=timestamp,
            )
            loaded = memory.load_latest_snapshot()

            self.assertTrue(path.exists())
            self.assertEqual(loaded["generated_at"], "2026-06-02T08:30:00")
            self.assertEqual(loaded["universe_version"], "1.1")
            self.assertEqual(loaded["securities"]["AAA"]["total_score"], 50.0)
            self.assertEqual(
                loaded["securities"]["AAA"]["growth_metrics"]["source"],
                "sec_companyfacts",
            )
            self.assertEqual(
                loaded["securities"]["AAA"]["quality_metrics"]["source"],
                "sec_companyfacts",
            )

    def test_latest_snapshot_is_returned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ResearchMemory(temp_dir)

            memory.save_snapshot(
                self._market_data(price=10.0),
                {},
                "1.1",
                datetime(2026, 6, 1, 8, 0, 0),
            )
            memory.save_snapshot(
                self._market_data(price=20.0),
                {},
                "1.1",
                datetime(2026, 6, 2, 8, 0, 0),
            )

            loaded = memory.load_latest_snapshot()

            self.assertEqual(loaded["securities"]["AAA"]["price"], 20.0)

    def test_missing_archive_returns_none(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ResearchMemory(f"{temp_dir}/missing")
            self.assertIsNone(memory.load_latest_snapshot())

    def test_archive_index_is_written_with_report_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ResearchMemory(temp_dir)
            timestamp = datetime(2026, 6, 2, 8, 30, 0)
            snapshot_path = memory.save_snapshot(
                market_data=self._market_data(price=10.0),
                market_summary={},
                universe_version="1.1",
                timestamp=timestamp,
            )
            report_path = Path(temp_dir) / "morning_brief.md"
            html_path = Path(temp_dir) / "morning_brief.html"
            report_path.write_text("# Report", encoding="utf-8")
            html_path.write_text("<html></html>", encoding="utf-8")

            index_path = memory.update_archive_index(
                snapshot_path=snapshot_path,
                report_path=report_path,
                html_report_path=html_path,
            )
            markdown_path = Path(temp_dir) / "archive_index.md"

            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

            self.assertEqual(len(index_payload["entries"]), 1)
            self.assertEqual(index_payload["entries"][0]["securities"], 1)
            self.assertEqual(index_payload["entries"][0]["report_path"], "morning_brief.md")
            self.assertIn("AAA +11.11%", markdown)
            self.assertIn("[markdown](morning_brief.md)", markdown)
            self.assertIn("[html](morning_brief.html)", markdown)

    def test_archive_index_keeps_recent_entries_first_and_trims(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = ResearchMemory(temp_dir)

            first = memory.save_snapshot(
                self._market_data(price=10.0),
                {},
                "1.1",
                datetime(2026, 6, 1, 8, 0, 0),
            )
            second = memory.save_snapshot(
                self._market_data(price=20.0),
                {},
                "1.1",
                datetime(2026, 6, 2, 8, 0, 0),
            )

            memory.update_archive_index(first, max_entries=1)
            index_path = memory.update_archive_index(second, max_entries=1)
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))

            self.assertEqual(len(index_payload["entries"]), 1)
            self.assertEqual(index_payload["entries"][0]["generated_at"], "2026-06-02T08:00:00")

    def test_archive_index_uses_relative_paths_for_reports_outside_archive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir) / "research_archive"
            reports_dir = Path(temp_dir) / "reports"
            memory = ResearchMemory(archive_dir)
            reports_dir.mkdir()
            snapshot_path = memory.save_snapshot(
                market_data=self._market_data(price=10.0),
                market_summary={},
                universe_version="1.1",
                timestamp=datetime(2026, 6, 2, 8, 30, 0),
            )
            report_path = reports_dir / "morning_brief.md"
            report_path.write_text("# Report", encoding="utf-8")

            index_path = memory.update_archive_index(
                snapshot_path=snapshot_path,
                report_path=report_path,
            )
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))

            self.assertEqual(index_payload["entries"][0]["report_path"], "../reports/morning_brief.md")

    def test_archive_index_normalizes_existing_report_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_dir = Path(temp_dir)
            memory = ResearchMemory(archive_dir)
            index_path = archive_dir / "archive_index.json"
            index_path.write_text(
                json.dumps(
                    {
                        "index_version": "1.0",
                        "entries": [
                            {
                                "generated_at": "2026-06-01T08:00:00",
                                "snapshot_path": "snapshot_old.json",
                                "report_path": "reports/old.md",
                                "html_report_path": "reports/old.html",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            snapshot_path = memory.save_snapshot(
                market_data=self._market_data(price=10.0),
                market_summary={},
                universe_version="1.1",
                timestamp=datetime(2026, 6, 2, 8, 30, 0),
            )

            memory.update_archive_index(snapshot_path=snapshot_path)
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
            old_entry = [
                entry for entry in index_payload["entries"]
                if entry["snapshot_path"] == "snapshot_old.json"
            ][0]

            self.assertEqual(old_entry["report_path"], "../reports/old.md")
            self.assertEqual(old_entry["html_report_path"], "../reports/old.html")

    def _market_data(self, price=10.0):
        return {
            "AAA": {
                "company_name": "AAA Company",
                "sector": "Test",
                "category": "Watchlist",
                "notes": "Test notes",
                "price": price,
                "previous_close": 9.0,
                "change": 1.0,
                "percent_change": 11.11,
                "status": "available",
                "source": "test",
                "score_source": "hybrid_v3",
                "automated_scores": ["growth", "quality", "momentum"],
                "growth_metrics": {
                    "growth_score": 50.0,
                    "revenue_growth": 0.0,
                    "net_income_growth": 0.0,
                    "source": "sec_companyfacts",
                },
                "quality_metrics": {
                    "quality_score": 50.0,
                    "net_margin": 0.0,
                    "operating_cash_flow_margin": 0.0,
                    "free_cash_flow_margin": 0.0,
                    "source": "sec_companyfacts",
                },
                "scores": {
                    "growth": 50,
                    "quality": 50,
                    "moat": 50,
                    "momentum": 50,
                    "risk": 50,
                },
            }
        }


if __name__ == "__main__":
    unittest.main()
