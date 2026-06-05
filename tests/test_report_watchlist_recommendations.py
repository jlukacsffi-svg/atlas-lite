import unittest

from app.report_generator import ReportGenerator


class ReportWatchlistRecommendationsTests(unittest.TestCase):
    def test_recommends_core_review_for_high_scoring_watchlist_name(self):
        market_data = {
            "MRVL": {
                "status": "available",
                "sector": "AI & Semiconductors",
                "category": "Watchlist",
                "percent_change": 3.0,
                "scores": {
                    "growth": 92,
                    "quality": 88,
                    "moat": 88,
                    "momentum": 90,
                    "risk": 78,
                },
            }
        }
        generator = ReportGenerator(
            market_data,
            market_summary={},
            analyst_actions=[{"ticker": "MRVL"}],
        )

        recommendations = generator._watchlist_recommendations()
        section = generator._generate_watchlist_recommendations()

        self.assertEqual(recommendations[0]["ticker"], "MRVL")
        self.assertEqual(recommendations[0]["recommendation"], "Review for Core")
        self.assertIn("## Watchlist Change Recommendations", section)
        self.assertIn("Review for Core", section)

    def test_recommends_watchlist_review_for_strong_emerging_name(self):
        market_data = {
            "SYM": {
                "status": "available",
                "sector": "Robotics & Automation",
                "category": "Emerging",
                "percent_change": 0.5,
                "scores": {
                    "growth": 82,
                    "quality": 80,
                    "moat": 76,
                    "momentum": 78,
                    "risk": 72,
                },
            }
        }
        generator = ReportGenerator(market_data, market_summary={})

        recommendations = generator._watchlist_recommendations()

        self.assertEqual(recommendations[0]["ticker"], "SYM")
        self.assertEqual(recommendations[0]["recommendation"], "Review for Watchlist")

    def test_recommends_risk_review_for_large_negative_move_with_catalyst(self):
        market_data = {
            "AVGO": {
                "status": "available",
                "sector": "AI & Semiconductors",
                "category": "Core",
                "percent_change": -8.0,
                "scores": {
                    "growth": 82,
                    "quality": 82,
                    "moat": 86,
                    "momentum": 70,
                    "risk": 70,
                },
            }
        }
        generator = ReportGenerator(
            market_data,
            market_summary={},
            earnings_events=[{"ticker": "AVGO"}],
        )

        recommendations = generator._watchlist_recommendations()

        self.assertEqual(recommendations[0]["recommendation"], "Review risk status")
        self.assertIn("-8.0% move", recommendations[0]["evidence"])

    def test_handles_no_recommendations(self):
        generator = ReportGenerator({}, market_summary={})

        section = generator._generate_watchlist_recommendations()

        self.assertIn("No watchlist category changes require review today.", section)


if __name__ == "__main__":
    unittest.main()
