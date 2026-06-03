"""Tests for Atlas structured research memory."""

from datetime import datetime
import tempfile
import unittest

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
                "score_source": "hybrid_v2",
                "automated_scores": ["growth", "momentum"],
                "growth_metrics": {
                    "growth_score": 50.0,
                    "revenue_growth": 0.0,
                    "net_income_growth": 0.0,
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
