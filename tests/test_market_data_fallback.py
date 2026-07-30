"""Tests for reliable Yahoo fallback daily-change calculations."""

import json
import unittest

from app.market_data import MarketDataFetcher, YAHOO_CHART_URL
from app.report_generator import ReportGenerator


def yahoo_payload(closes, meta=None):
    return json.dumps(
        {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "symbol": "AAA",
                            **(meta or {}),
                        },
                        "indicators": {
                            "quote": [
                                {
                                    "close": closes,
                                    "open": closes,
                                    "high": closes,
                                    "low": closes,
                                    "volume": [100 for _ in closes],
                                }
                            ],
                            "adjclose": [{"adjclose": closes}],
                        },
                    }
                ],
                "error": None,
            }
        }
    )


class YahooFallbackDailyChangeTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = MarketDataFetcher(["AAA"])

    def test_five_day_window_is_used_to_cross_weekends(self):
        self.assertIn("range=5d", YAHOO_CHART_URL)

    def test_two_valid_closes_use_daily_history(self):
        record = self.fetcher._parse_yahoo_chart_json(
            yahoo_payload([100.0, 105.0]),
            "AAA",
        )

        self.assertEqual(record["price"], 105.0)
        self.assertEqual(record["previous_close"], 100.0)
        self.assertEqual(record["percent_change"], 5.0)
        self.assertEqual(record["daily_change_quality"], "complete")
        self.assertEqual(record["daily_change_source"], "daily_history")

    def test_single_close_uses_valid_meta_previous_close(self):
        record = self.fetcher._parse_yahoo_chart_json(
            yahoo_payload([105.0], {"chartPreviousClose": 100.0}),
            "AAA",
        )

        self.assertEqual(record["previous_close"], 100.0)
        self.assertEqual(record["percent_change"], 5.0)
        self.assertEqual(record["daily_change_quality"], "complete")
        self.assertEqual(record["daily_change_source"], "meta_previous_close")

    def test_single_close_without_prior_is_explicitly_limited(self):
        record = self.fetcher._parse_yahoo_chart_json(
            yahoo_payload([105.0]),
            "AAA",
        )

        self.assertEqual(record["price"], 105.0)
        self.assertEqual(record["percent_change"], 0.0)
        self.assertEqual(record["daily_change_quality"], "limited")
        self.assertEqual(record["daily_change_source"], "single_close_no_prior")

    def test_invalid_close_values_are_ignored(self):
        record = self.fetcher._parse_yahoo_chart_json(
            yahoo_payload([None, 100.0, float("nan"), 102.0]),
            "AAA",
        )

        self.assertEqual(record["previous_close"], 100.0)
        self.assertEqual(record["price"], 102.0)
        self.assertEqual(record["percent_change"], 2.0)

    def test_report_discloses_limited_daily_change_coverage(self):
        report = ReportGenerator(
            {
                "AAA": {
                    "status": "available",
                    "source": "yahoo_fallback",
                    "daily_change_quality": "complete",
                },
                "BBB": {
                    "status": "available",
                    "source": "yahoo_fallback",
                    "daily_change_quality": "limited",
                },
            },
            {},
        )._generate_data_quality()

        self.assertIn("Daily Change Coverage**: 1/2", report)
        self.assertIn("Daily Change Warning**: 1", report)


if __name__ == "__main__":
    unittest.main()
