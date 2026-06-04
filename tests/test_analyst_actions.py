import json
import tempfile
import unittest
from pathlib import Path

from app.analyst_actions import AnalystActionTracker


class AnalystActionTrackerTests(unittest.TestCase):
    def sample_headlines(self):
        return [
            {
                "title": "Nvidia price target raised by Wall Street firm",
                "publisher": "MarketWatch",
                "url": "https://example.com/nvda-target",
            },
            {
                "title": "Nvidia launches new AI chips",
                "publisher": "Reuters",
                "url": "https://example.com/nvda-chips",
            },
        ]

    def test_classifies_common_analyst_action_headlines(self):
        tracker = AnalystActionTracker(cache_dir=tempfile.mkdtemp())

        self.assertEqual(tracker._classify_action("AMD upgraded to Buy"), "Upgrade")
        self.assertEqual(tracker._classify_action("Meta downgraded by analyst"), "Downgrade")
        self.assertEqual(tracker._classify_action("Broadcom price target raised"), "Price target raised")
        self.assertEqual(tracker._classify_action("CrowdStrike price target cut"), "Price target cut")
        self.assertEqual(
            tracker._classify_action("Deutsche Bank Adjusts Intuitive Surgical PT to $366 From $440, Maintains Sell Rating"),
            "Price target cut",
        )
        self.assertEqual(
            tracker._classify_action("Goldman Sachs Adjusts Price Target on Palo Alto Networks to $330 From $224, Maintains Buy Rating"),
            "Price target raised",
        )
        self.assertEqual(tracker._classify_action("Analyst initiates coverage of Palantir"), "Initiated coverage")
        self.assertIsNone(tracker._classify_action("Nvidia launches new product"))

    def test_fetch_actions_filters_to_analyst_signals(self):
        tracker = AnalystActionTracker(cache_dir=tempfile.mkdtemp())
        tracker._fetch_ticker_headlines = lambda ticker, company_name: self.sample_headlines()
        market_data = {
            "NVDA": {
                "company_name": "NVIDIA Corporation",
                "sector": "AI & Semiconductors",
            },
            "SPY": {
                "company_name": "State Street SPDR S&P 500 ETF Trust",
                "sector": "Benchmark ETF",
            },
        }

        events = tracker.fetch_actions(market_data)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["ticker"], "NVDA")
        self.assertEqual(events[0]["action_type"], "Price target raised")
        self.assertEqual(events[0]["source"], "yahoo_finance_news_search")

    def test_fetch_ticker_headlines_uses_fresh_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = AnalystActionTracker(cache_dir=temp_dir)
            cache_path = Path(temp_dir) / "NVDA_analyst_actions.json"
            cache_path.write_text(json.dumps(self.sample_headlines()), encoding="utf-8")

            def fail_if_called(ticker, company_name):
                raise AssertionError("Fresh cache should avoid network fetch")

            tracker._fetch_ticker_headlines_uncached = fail_if_called

            headlines = tracker._fetch_ticker_headlines("NVDA", "NVIDIA Corporation")

        self.assertEqual(headlines[0]["title"], "Nvidia price target raised by Wall Street firm")

    def test_fetch_ticker_headlines_uses_stale_cache_when_network_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker = AnalystActionTracker(cache_dir=temp_dir)
            cache_path = Path(temp_dir) / "NVDA_analyst_actions.json"
            cache_path.write_text(json.dumps(self.sample_headlines()), encoding="utf-8")
            tracker._cache_is_fresh = lambda path: False
            tracker._fetch_ticker_headlines_uncached = lambda ticker, company_name: None

            headlines = tracker._fetch_ticker_headlines("NVDA", "NVIDIA Corporation")

        self.assertEqual(headlines[0]["publisher"], "MarketWatch")


if __name__ == "__main__":
    unittest.main()
