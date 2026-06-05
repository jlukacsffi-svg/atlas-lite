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
            },
        )

        section = generator._generate_portfolio_intelligence()

        self.assertIn("Test Portfolio", section)
        self.assertIn("$550.00", section)
        self.assertIn("| NVDA |", section)
        self.assertIn("AI & Semiconductors", section)
        self.assertIn("Concentration", section)


if __name__ == "__main__":
    unittest.main()
