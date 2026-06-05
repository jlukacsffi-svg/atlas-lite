import unittest

from app.report_generator import ReportGenerator


class ReportExecutiveSummaryTests(unittest.TestCase):
    def sample_market_data(self):
        return {
            "NVDA": {
                "status": "available",
                "company_name": "NVIDIA Corporation",
                "sector": "AI & Semiconductors",
                "category": "Core",
                "price": 200,
                "change": 7,
                "percent_change": 3.5,
                "scores": {
                    "growth": 95,
                    "quality": 90,
                    "moat": 95,
                    "momentum": 90,
                    "risk": 65,
                },
            },
            "MSFT": {
                "status": "available",
                "company_name": "Microsoft Corporation",
                "sector": "Cloud Platforms",
                "category": "Core",
                "price": 450,
                "change": -5,
                "percent_change": -1.1,
                "scores": {
                    "growth": 85,
                    "quality": 92,
                    "moat": 92,
                    "momentum": 70,
                    "risk": 75,
                },
            },
            "FTNT": {
                "status": "available",
                "company_name": "Fortinet, Inc.",
                "sector": "Cybersecurity",
                "category": "Watchlist",
                "price": 80,
                "change": -4,
                "percent_change": -4.8,
                "scores": {
                    "growth": 70,
                    "quality": 75,
                    "moat": 70,
                    "momentum": 60,
                    "risk": 65,
                },
            },
        }

    def test_executive_summary_interprets_rankings_and_catalysts(self):
        generator = ReportGenerator(
            self.sample_market_data(),
            market_summary={
                "SPY": {"percent_change": 0.3, "status": "available"},
                "QQQ": {"percent_change": 0.4, "status": "available"},
            },
            earnings_events=[{"ticker": "NVDA"}],
            analyst_actions=[{"ticker": "NVDA"}, {"ticker": "FTNT"}],
            insider_transactions=[{"ticker": "MSFT"}],
        )

        section = generator._generate_executive_summary()

        self.assertIn("## Executive Summary", section)
        self.assertIn("Sector read", section)
        self.assertIn("AI & Semiconductors", section)
        self.assertIn("Priority review", section)
        self.assertIn("NVDA", section)
        self.assertIn("Catalyst load", section)
        self.assertIn("1 earnings", section)
        self.assertIn("2 analyst actions", section)
        self.assertIn("1 insider activity", section)

    def test_executive_summary_still_handles_missing_market_data(self):
        generator = ReportGenerator({}, market_summary={})

        section = generator._generate_executive_summary()

        self.assertIn("Market data was unavailable", section)


if __name__ == "__main__":
    unittest.main()
