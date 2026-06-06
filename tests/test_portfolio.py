import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.portfolio import Portfolio


class PortfolioTests(unittest.TestCase):
    def test_missing_portfolio_file_is_not_configured(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            portfolio = Portfolio(Path(temp_dir) / "portfolio.json")

            summary = portfolio.analyze({})

        self.assertFalse(summary["configured"])

    def test_analyze_calculates_position_and_sector_exposure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "portfolio.json"
            path.write_text(
                json.dumps(
                    {
                        "name": "Test Portfolio",
                        "positions": [
                            {"ticker": "NVDA", "shares": 2, "cost_basis": 100},
                            {"ticker": "MSFT", "shares": 1, "cost_basis": 200},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            market_data = {
                "NVDA": {
                    "status": "available",
                    "price": 150,
                    "percent_change": 2.5,
                    "sector": "AI & Semiconductors",
                },
                "MSFT": {
                    "status": "available",
                    "price": 250,
                    "percent_change": -1.0,
                    "sector": "Cloud Platforms",
                },
            }

            summary = Portfolio(path).analyze(market_data)

        self.assertTrue(summary["configured"])
        self.assertEqual(summary["name"], "Test Portfolio")
        self.assertEqual(summary["total_value"], 550)
        self.assertEqual(summary["positions"][0]["market_value"], 300)
        self.assertEqual(summary["positions"][0]["gain_loss"], 100)
        self.assertAlmostEqual(summary["positions"][0]["allocation_pct"], 54.5454, places=3)
        self.assertGreater(summary["day_change_value"], 0)
        self.assertGreater(summary["day_change_pct"], 0)
        self.assertEqual(summary["sector_allocations"][0]["sector"], "AI & Semiconductors")
        self.assertTrue(summary["risk_alerts"])

    def test_validate_flags_duplicate_tickers_and_unknown_universe_names(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "portfolio.json"
            path.write_text(
                json.dumps(
                    {
                        "positions": [
                            {"ticker": "NVDA", "shares": 1},
                            {"ticker": "NVDA", "shares": 2},
                            {"ticker": "UNKNOWN", "shares": 1},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = Portfolio(path).validate(allowed_tickers=["NVDA"])

        self.assertTrue(result["configured"])
        self.assertIn("Duplicate portfolio tickers: NVDA", result["errors"])
        self.assertIn("UNKNOWN", result["warnings"][0])

    def test_history_snapshot_and_comparison_are_local(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_dir = Path(temp_dir) / "history"
            portfolio = Portfolio(Path(temp_dir) / "missing.json", history_dir=history_dir)
            prior = {
                "configured": True,
                "name": "Test Portfolio",
                "total_value": 500,
                "day_change_value": 0,
                "day_change_pct": 0,
                "positions": [],
                "sector_allocations": [],
                "risk_alerts": [],
            }
            portfolio.save_history(prior, timestamp=datetime(2026, 6, 1, 8, 0, 0))
            current = {"configured": True, "name": "Test Portfolio", "total_value": 550}

            portfolio.add_history_comparison(current)

        self.assertEqual(current["previous_snapshot"]["total_value"], 500)
        self.assertEqual(current["previous_snapshot"]["change_value"], 50)
        self.assertEqual(current["previous_snapshot"]["change_pct"], 10)


if __name__ == "__main__":
    unittest.main()
