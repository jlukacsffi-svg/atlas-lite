import unittest

from app.report_generator import ReportGenerator


class ReportRankingTests(unittest.TestCase):
    def sample_market_data(self):
        return {
            "NVDA": {
                "status": "available",
                "company_name": "NVIDIA Corporation",
                "sector": "AI & Semiconductors",
                "category": "Core",
                "percent_change": 3.2,
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
                "sector": "Cloud Platforms / Software / AI Software",
                "category": "Core",
                "percent_change": 0.4,
                "scores": {
                    "growth": 85,
                    "quality": 92,
                    "moat": 92,
                    "momentum": 70,
                    "risk": 75,
                },
            },
            "SPY": {
                "status": "available",
                "company_name": "SPDR S&P 500 ETF Trust",
                "sector": "Benchmark ETF",
                "category": "Core",
                "percent_change": 0.1,
                "scores": {
                    "growth": 50,
                    "quality": 50,
                    "moat": 50,
                    "momentum": 50,
                    "risk": 50,
                },
            },
        }

    def test_sector_scorecard_excludes_benchmark_etfs(self):
        generator = ReportGenerator(self.sample_market_data(), market_summary={})

        section = generator._generate_sector_scorecard()

        self.assertIn("## Sector Scorecard", section)
        self.assertIn("AI & Semiconductors", section)
        self.assertIn("Cloud Platforms / Software / AI Software", section)
        self.assertNotIn("Benchmark ETF", section)
        self.assertIn("NVDA", section)

    def test_priority_ranking_combines_score_and_research_signals(self):
        generator = ReportGenerator(
            self.sample_market_data(),
            market_summary={},
            earnings_events=[{"ticker": "NVDA"}],
            analyst_actions=[{"ticker": "NVDA"}],
            insider_transactions=[{"ticker": "MSFT"}],
        )

        section = generator._generate_priority_ranking()
        priority_score, signals = generator._priority_score(
            "NVDA",
            self.sample_market_data()["NVDA"],
            89.0,
        )

        self.assertIn("## Atlas Priority Ranking", section)
        self.assertIn("earnings", signals)
        self.assertIn("analyst action", signals)
        self.assertIn("Core", signals)
        self.assertGreater(priority_score, 89.0)
        self.assertIn("| 1 | NVDA |", section)

    def test_priority_ranking_handles_missing_scores(self):
        generator = ReportGenerator({}, market_summary={})

        section = generator._generate_priority_ranking()

        self.assertIn("No priority ranking is available for this run.", section)


if __name__ == "__main__":
    unittest.main()
