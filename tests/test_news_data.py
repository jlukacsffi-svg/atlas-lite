import json
import tempfile
import unittest
from pathlib import Path

from app.news_data import NewsFetcher


class NewsFetcherTests(unittest.TestCase):
    def test_fetch_signal_classifies_supportive_and_adverse_company_news(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fetcher = NewsFetcher(cache_dir=temp_dir)
            fetcher.fetch_headlines = lambda ticker, company_name=None: [
                {
                    "title": "Nvidia beats expectations and raises guidance on strong AI demand",
                    "publisher": "Reuters",
                    "url": "https://example.com/good",
                    "relevance": "company",
                },
                {
                    "title": "Nvidia wins large cloud contract as partnership expands",
                    "publisher": "Bloomberg",
                    "url": "https://example.com/better",
                    "relevance": "company",
                },
            ]
            supportive = fetcher.fetch_signal("NVDA", "NVIDIA Corporation")

            fetcher.fetch_headlines = lambda ticker, company_name=None: [
                {
                    "title": "Nvidia cuts guidance after weak demand warning",
                    "publisher": "Reuters",
                    "url": "https://example.com/bad",
                    "relevance": "company",
                },
                {
                    "title": "Nvidia faces lawsuit as shipment delay deepens concerns",
                    "publisher": "Bloomberg",
                    "url": "https://example.com/worse",
                    "relevance": "company",
                },
            ]
            adverse = fetcher.fetch_signal("NVDA", "NVIDIA Corporation")

        self.assertEqual(supportive["signal_label"], "supportive")
        self.assertEqual(supportive["positive_count"], 2)
        self.assertGreater(supportive["signal_score"], 50.0)
        self.assertEqual(supportive["dominant_event_type"], "guidance_raise")
        self.assertGreaterEqual(supportive["high_impact_positive_count"], 1)
        self.assertEqual(adverse["signal_label"], "adverse")
        self.assertEqual(adverse["negative_count"], 2)
        self.assertLess(adverse["signal_score"], 50.0)
        self.assertIn(adverse["dominant_event_type"], {"guidance_cut", "legal_risk"})
        self.assertGreaterEqual(adverse["high_impact_negative_count"], 1)

    def test_fetch_headlines_uses_fresh_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fetcher = NewsFetcher(cache_dir=temp_dir)
            cache_path = Path(temp_dir) / "NVDA_news.json"
            cache_path.write_text(
                json.dumps(
                    [
                        {
                            "title": "Cached headline",
                            "publisher": "Reuters",
                            "url": "https://example.com",
                            "relevance": "company",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            original = fetcher._cache_is_fresh
            fetcher._cache_is_fresh = lambda path: True
            headlines = fetcher.fetch_headlines("NVDA", "NVIDIA Corporation")
            fetcher._cache_is_fresh = original

        self.assertEqual(headlines[0]["title"], "Cached headline")

    def test_fetch_signal_treats_single_high_impact_legal_headline_as_adverse(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fetcher = NewsFetcher(cache_dir=temp_dir)
            fetcher.fetch_headlines = lambda ticker, company_name=None: [
                {
                    "title": "Nvidia faces lawsuit after regulators open investigation",
                    "publisher": "Reuters",
                    "url": "https://example.com/legal",
                    "relevance": "company",
                }
            ]
            signal = fetcher.fetch_signal("NVDA", "NVIDIA Corporation")

        self.assertEqual(signal["signal_label"], "adverse")
        self.assertEqual(signal["dominant_event_type"], "legal_risk")
        self.assertEqual(signal["high_impact_negative_count"], 1)
        self.assertGreaterEqual(signal["negative_weight"], 3.0)


if __name__ == "__main__":
    unittest.main()
