"""Upcoming earnings calendar retrieval for Atlas Lite."""

from datetime import date, datetime, timedelta
import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EARNINGS_CACHE_DIR = PROJECT_ROOT / "data_cache" / "earnings"
NASDAQ_EARNINGS_URL = "https://api.nasdaq.com/api/calendar/earnings?date={date}"
EARNINGS_LOOKAHEAD_DAYS = 7
EARNINGS_TIMEOUT_SECONDS = 10
EARNINGS_CACHE_HOURS = 18


class EarningsCalendar:
    """Fetch and cache upcoming earnings events for Atlas securities."""

    def __init__(self, cache_dir=DEFAULT_EARNINGS_CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.logger = logging.getLogger(__name__)

    def fetch_upcoming(self, tickers, start_date=None, days=EARNINGS_LOOKAHEAD_DAYS):
        watchlist = {str(ticker).upper() for ticker in tickers}
        start_date = start_date or date.today()
        events = []

        for offset in range(days):
            target_date = start_date + timedelta(days=offset)
            payload = self._fetch_daily_calendar(target_date)
            for row in self._extract_rows(payload):
                symbol = str(row.get("symbol", "")).upper()
                if symbol not in watchlist:
                    continue
                events.append(self._normalize_event(row, target_date))

        return sorted(events, key=lambda item: (item["date"], item["ticker"]))

    def _fetch_daily_calendar(self, target_date):
        cache_path = self.cache_dir / f"nasdaq_earnings_{target_date.isoformat()}.json"
        cached_payload = self._read_cached_json(cache_path)

        if cached_payload is not None and self._cache_is_fresh(cache_path):
            self.logger.info("Earnings cache hit: %s", cache_path)
            return cached_payload

        payload = self._fetch_daily_calendar_uncached(target_date)
        if payload is not None:
            self._write_cached_json(cache_path, payload)
            return payload

        if cached_payload is not None:
            self.logger.warning("Using stale earnings cache after fetch failure: %s", cache_path)
            return cached_payload
        return None

    def _fetch_daily_calendar_uncached(self, target_date):
        url = NASDAQ_EARNINGS_URL.format(date=urllib.parse.quote(target_date.isoformat()))
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/market-activity/earnings",
            },
        )

        try:
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=EARNINGS_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            self.logger.info(
                "Nasdaq earnings calendar completed for %s in %.2fs",
                target_date,
                time.monotonic() - start,
            )
            return payload
        except Exception as exc:
            self.logger.warning("Unable to retrieve earnings calendar for %s: %s", target_date, exc)
            return None

    def _extract_rows(self, payload):
        if not payload:
            return []
        rows = payload.get("data", {}).get("rows") or []
        return rows if isinstance(rows, list) else []

    def _normalize_event(self, row, target_date):
        return {
            "date": target_date.isoformat(),
            "ticker": str(row.get("symbol", "")).upper(),
            "company_name": row.get("name") or "",
            "time": self._format_time(row.get("time")),
            "fiscal_quarter_ending": row.get("fiscalQuarterEnding") or "N/A",
            "eps_forecast": row.get("epsForecast") or "N/A",
            "last_year_eps": row.get("lastYearEPS") or "N/A",
            "source": "nasdaq_earnings_calendar",
        }

    def _format_time(self, value):
        labels = {
            "time-pre-market": "Pre-market",
            "time-after-hours": "After hours",
            "time-not-supplied": "Time not supplied",
            "time-during-market": "During market",
        }
        if not value:
            return "Time not supplied"
        return labels.get(value, str(value))

    def _read_cached_json(self, cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.logger.warning("Unable to read earnings cache %s: %s", cache_path, exc)
            return None

    def _write_cached_json(self, cache_path, payload):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            self.logger.warning("Unable to write earnings cache %s: %s", cache_path, exc)

    def _cache_is_fresh(self, cache_path):
        try:
            age_seconds = time.time() - cache_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return age_seconds <= EARNINGS_CACHE_HOURS * 60 * 60
