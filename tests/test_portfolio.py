import json
import tempfile
import unittest
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
        self.assertEqual(summary["sector_allocations"][0]["sector"], "AI & Semiconductors")


if __name__ == "__main__":
    unittest.main()
