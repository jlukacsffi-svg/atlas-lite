"""Tests for applying Atlas universe and automated score metadata."""

import unittest

from app.market_data import MarketDataFetcher


class _Universe:
    def get(self, ticker):
        return {
            "company_name": "AAA Company",
            "sector": "Test Sector",
            "category": "Watchlist",
            "notes": "Test notes",
            "profile": {
                "thesis": "Test thesis",
                "key_driver": "Test driver",
                "key_risk": "Test risk",
            },
            "score_source": "manual_v1",
            "scores": {
                "growth": 50,
                "quality": 60,
                "moat": 70,
                "momentum": 50,
                "risk": 80,
            },
        }


class _MetricsEngine:
    def __init__(self, metrics):
        self.metrics = metrics

    def fetch_metrics(self, ticker):
        return dict(self.metrics)


class MarketDataMetadataTests(unittest.TestCase):
    def test_growth_and_momentum_create_hybrid_v2_score(self):
        fetcher = MarketDataFetcher(["AAA"], universe=_Universe())
        fetcher.growth_engine = _MetricsEngine({"growth_score": 75.0})
        fetcher.momentum_engine = _MetricsEngine({"momentum_score": 65.0})

        record = fetcher._apply_universe_metadata("AAA", {"company_name": "AAA"})

        self.assertEqual(record["scores"]["growth"], 75.0)
        self.assertEqual(record["scores"]["momentum"], 65.0)
        self.assertEqual(record["automated_scores"], ["growth", "momentum"])
        self.assertEqual(record["score_source"], "hybrid_v2")

    def test_manual_growth_is_retained_when_growth_data_is_unavailable(self):
        fetcher = MarketDataFetcher(["AAA"], universe=_Universe())
        fetcher.growth_engine = _MetricsEngine({})
        fetcher.momentum_engine = _MetricsEngine({"momentum_score": 65.0})

        record = fetcher._apply_universe_metadata("AAA", {})

        self.assertEqual(record["scores"]["growth"], 50)
        self.assertEqual(record["scores"]["momentum"], 65.0)
        self.assertEqual(record["score_source"], "hybrid_v1")


if __name__ == "__main__":
    unittest.main()
