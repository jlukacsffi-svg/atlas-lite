"""Analyst rating and price-target action tracking for Atlas Lite."""

from datetime import datetime
import json
import logging
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ANALYST_CACHE_DIR = PROJECT_ROOT / "data_cache" / "analyst_actions"
YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
ANALYST_ACTION_CACHE_HOURS = 12
ANALYST_ACTION_TIMEOUT_SECONDS = 5
ANALYST_ACTION_SEARCH_HEADLINES = 12


ACTION_PATTERNS = [
    ("Upgrade", re.compile(r"\b(upgrade|upgraded|raises rating|raised rating)\b", re.IGNORECASE)),
    ("Downgrade", re.compile(r"\b(downgrade|downgraded|cuts rating|cut rating|lowered rating)\b", re.IGNORECASE)),
    (
        "Price target raised",
        re.compile(
            r"(\b(raises|raised|boosts|boosted|lifts|lifted|increases|increased)\b.*\b(price target|pt)\b)"
            r"|(\b(price target|pt)\b.*\b(raises|raised|boosts|boosted|lifted|increased)\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "Price target cut",
        re.compile(
            r"(\b(cuts|cut|lowers|lowered|trims|trimmed|reduces|reduced)\b.*\b(price target|pt)\b)"
            r"|(\b(price target|pt)\b.*\b(cut|lowered|trimmed|reduced)\b)",
            re.IGNORECASE,
        ),
    ),
    ("Initiated coverage", re.compile(r"\b(initiate|initiates|initiated|starts coverage|started coverage)\b", re.IGNORECASE)),
    ("Reiterated", re.compile(r"\b(reiterate|reiterates|reiterated|maintains|maintained)\b", re.IGNORECASE)),
]


class AnalystActionTracker:
    """Fetch and cache analyst-action headlines for Atlas securities."""

    def __init__(
        self,
        cache_dir=DEFAULT_ANALYST_CACHE_DIR,
        max_headlines=2,
        search_headlines=ANALYST_ACTION_SEARCH_HEADLINES,
        timeout=ANALYST_ACTION_TIMEOUT_SECONDS,
    ):
        self.cache_dir = Path(cache_dir)
        self.max_headlines = max_headlines
        self.search_headlines = search_headlines
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def fetch_actions(self, market_data, max_events=12):
        """Fetch recent analyst-action headlines for the current Atlas universe."""
        events = []

        for ticker, data in sorted(market_data.items()):
            if data.get("sector") == "Benchmark ETF":
                continue

            company_name = data.get("company_name") or ticker
            headlines = self._fetch_ticker_headlines(ticker, company_name)
            for headline in headlines:
                action_type = self._classify_action(headline.get("title", ""))
                if not action_type:
                    continue
                events.append(
                    {
                        "ticker": ticker,
                        "company_name": company_name,
                        "action_type": action_type,
                        "title": headline.get("title", ""),
                        "publisher": headline.get("publisher", "Unknown publisher"),
                        "url": headline.get("url", ""),
                        "source": "yahoo_finance_news_search",
                    }
                )

        unique_events = self._dedupe_events(events)
        return unique_events[:max_events]

    def _fetch_ticker_headlines(self, ticker, company_name):
        cache_path = self.cache_dir / f"{ticker.upper()}_analyst_actions.json"
        cached_payload = self._read_cached_json(cache_path)

        if cached_payload is not None and self._cache_is_fresh(cache_path):
            return cached_payload

        payload = self._fetch_ticker_headlines_uncached(ticker, company_name)
        if payload is not None:
            self._write_cached_json(cache_path, payload)
            return payload

        if cached_payload is not None:
            self.logger.warning("Using stale analyst-action cache after fetch failure: %s", cache_path)
            return cached_payload
        return []

    def _fetch_ticker_headlines_uncached(self, ticker, company_name):
        query = f"{company_name} {ticker} analyst upgrade downgrade price target"
        params = urllib.parse.urlencode(
            {
                "q": query,
                "quotesCount": 0,
                "newsCount": self.search_headlines,
            }
        )
        request = urllib.request.Request(
            f"{YAHOO_SEARCH_URL}?{params}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )

        try:
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            self.logger.info(
                "Analyst-action headline search completed for %s in %.2fs",
                ticker,
                time.monotonic() - start,
            )
        except Exception as exc:
            self.logger.warning("Unable to retrieve analyst-action headlines for %s: %s", ticker, exc)
            return None

        headlines = []
        seen_titles = set()
        for item in payload.get("news", []):
            title = (item.get("title") or "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            if not self._classify_action(title):
                continue
            headlines.append(
                {
                    "title": title,
                    "publisher": item.get("publisher") or "Unknown publisher",
                    "url": item.get("link") or "",
                    "fetched_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            if len(headlines) >= self.max_headlines:
                break

        return headlines

    def _classify_action(self, title):
        price_target_adjustment = self._classify_price_target_adjustment(title)
        if price_target_adjustment:
            return price_target_adjustment

        for label, pattern in ACTION_PATTERNS:
            if pattern.search(title or ""):
                return label
        return None

    def _classify_price_target_adjustment(self, title):
        match = re.search(
            r"\b(?:price target|pt)\b.*?\bto\b\s*\$?([0-9,.]+).*?\bfrom\b\s*\$?([0-9,.]+)",
            title or "",
            re.IGNORECASE,
        )
        if not match:
            return None

        try:
            new_target = float(match.group(1).replace(",", ""))
            old_target = float(match.group(2).replace(",", ""))
        except ValueError:
            return None

        if new_target > old_target:
            return "Price target raised"
        if new_target < old_target:
            return "Price target cut"
        return None

    def _dedupe_events(self, events):
        deduped = []
        seen = set()
        for event in events:
            key = (event.get("ticker"), event.get("title"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(event)
        return deduped

    def _read_cached_json(self, cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.logger.warning("Unable to read analyst-action cache %s: %s", cache_path, exc)
            return None

    def _write_cached_json(self, cache_path, payload):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            self.logger.warning("Unable to write analyst-action cache %s: %s", cache_path, exc)

    def _cache_is_fresh(self, cache_path):
        try:
            age_seconds = time.time() - cache_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return age_seconds <= ANALYST_ACTION_CACHE_HOURS * 60 * 60
