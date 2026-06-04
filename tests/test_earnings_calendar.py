import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.earnings_calendar import EarningsCalendar


class EarningsCalendarTests(unittest.TestCase):
    def sample_payload(self):
        return {
            "data": {
                "rows": [
                    {
                        "symbol": "AVGO",
                        "name": "Broadcom Inc.",
                        "time": "time-after-hours",
                        "fiscalQuarterEnding": "Apr/2026",
                        "epsForecast": "$1.57",
                        "lastYearEPS": "$1.10",
                    },
                    {
                        "symbol": "UNWATCHED",
                        "name": "Unwatched Company",
                        "time": "time-pre-market",
                        "fiscalQuarterEnding": "Mar/2026",
                        "epsForecast": "$0.10",
                        "lastYearEPS": "$0.09",
                    },
                ]
            }
        }

    def test_fetch_upcoming_filters_and_normalizes_watchlist_events(self):
        calendar = EarningsCalendar(cache_dir=tempfile.mkdtemp())
        calendar._fetch_daily_calendar = lambda target_date: self.sample_payload()

        events = calendar.fetch_upcoming(
            ["avgo", "msft"],
            start_date=date(2026, 6, 3),
            days=1,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["date"], "2026-06-03")
        self.assertEqual(events[0]["ticker"], "AVGO")
        self.assertEqual(events[0]["company_name"], "Broadcom Inc.")
        self.assertEqual(events[0]["time"], "After hours")
        self.assertEqual(events[0]["fiscal_quarter_ending"], "Apr/2026")
        self.assertEqual(events[0]["eps_forecast"], "$1.57")
        self.assertEqual(events[0]["last_year_eps"], "$1.10")
        self.assertEqual(events[0]["source"], "nasdaq_earnings_calendar")

    def test_fetch_daily_calendar_uses_fresh_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            calendar = EarningsCalendar(cache_dir=temp_dir)
            cache_path = Path(temp_dir) / "nasdaq_earnings_2026-06-03.json"
            cache_path.write_text(json.dumps(self.sample_payload()), encoding="utf-8")

            def fail_if_called(target_date):
                raise AssertionError("Fresh cache should avoid network fetch")

            calendar._fetch_daily_calendar_uncached = fail_if_called

            payload = calendar._fetch_daily_calendar(date(2026, 6, 3))

        self.assertEqual(payload["data"]["rows"][0]["symbol"], "AVGO")

    def test_fetch_daily_calendar_uses_stale_cache_when_network_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            calendar = EarningsCalendar(cache_dir=temp_dir)
            cache_path = Path(temp_dir) / "nasdaq_earnings_2026-06-03.json"
            cache_path.write_text(json.dumps(self.sample_payload()), encoding="utf-8")
            calendar._cache_is_fresh = lambda path: False
            calendar._fetch_daily_calendar_uncached = lambda target_date: None

            payload = calendar._fetch_daily_calendar(date(2026, 6, 3))

        self.assertEqual(payload["data"]["rows"][0]["symbol"], "AVGO")

    def test_format_time_has_safe_default(self):
        calendar = EarningsCalendar(cache_dir=tempfile.mkdtemp())

        self.assertEqual(calendar._format_time("time-pre-market"), "Pre-market")
        self.assertEqual(calendar._format_time(None), "Time not supplied")
        self.assertEqual(calendar._format_time("custom-session"), "custom-session")


if __name__ == "__main__":
    unittest.main()
