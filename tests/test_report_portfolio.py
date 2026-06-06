import unittest

from app.report_generator import ReportGenerator


class ReportPortfolioTests(unittest.TestCase):
    def test_portfolio_section_explains_missing_local_file(self):
        generator = ReportGenerator({}, {}, portfolio_summary={"configured": False})

        section = generator._generate_portfolio_intelligence()

        self.assertIn("## Portfolio Intelligence", section)
        self.assertIn("No local portfolio is configured", section)
        self.assertIn("data/portfolio.json", section)

    def test_portfolio_section_renders_positions_and_sector_exposure(self):
        generator = ReportGenerator(
            {},
            {},
            portfolio_summary={
                "configured": True,
                "name": "Test Portfolio",
                "total_value": 550,
                "day_change_value": 5,
                "day_change_pct": 0.92,
                "previous_snapshot": {
                    "generated_at": "2026-06-01T08:00:00",
                    "total_value": 500,
                    "change_value": 50,
                    "change_pct": 10,
                },
                "positions": [
                    {
                        "ticker": "NVDA",
                        "shares": 2,
                        "market_value": 300,
                        "allocation_pct": 54.545,
                        "day_change_pct": 2.5,
                        "gain_loss": 100,
                        "gain_loss_pct": 50,
                    }
                ],
                "sector_allocations": [
                    {
                        "sector": "AI & Semiconductors",
                        "market_value": 300,
                        "allocation_pct": 54.545,
                    }
                ],
                "unavailable_tickers": [],
                "risk_alerts": [
                    {
                        "severity": "medium",
                        "message": "NVDA is 54.5% of tracked portfolio value.",
                    }
                ],
            },
        )

        section = generator._generate_portfolio_intelligence()

        self.assertIn("Test Portfolio", section)
        self.assertIn("$550.00", section)
        self.assertIn("Estimated Daily Change", section)
        self.assertIn("Benchmark Context", section)
        self.assertIn("Change Since Previous Portfolio Snapshot", section)
        self.assertIn("| NVDA |", section)
        self.assertIn("AI & Semiconductors", section)
        self.assertIn("NVDA is 54.5% of tracked portfolio value", section)


if __name__ == "__main__":
    unittest.main()
