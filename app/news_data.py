"""News headline fetching for Atlas Lite."""

import json
import logging
import time
import urllib.parse
import urllib.request


YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"


SECTOR_KEYWORDS = {
    "AI",
    "chip",
    "chips",
    "semiconductor",
    "software",
    "cybersecurity",
    "cloud",
    "defense",
    "aerospace",
    "missile",
    "market",
    "earnings",
    "analyst",
}


class NewsFetcher:
    """Fetch recent public finance headlines for watchlist tickers."""

    def __init__(self, max_headlines=3, search_headlines=10, timeout=5):
        self.max_headlines = max_headlines
        self.search_headlines = search_headlines
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def fetch_headlines(self, ticker, company_name=None):
        query = company_name or ticker
        params = urllib.parse.urlencode(
            {
                "q": query,
                "quotesCount": 0,
                "newsCount": self.search_headlines,
            }
        )
        url = f"{YAHOO_SEARCH_URL}?{params}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )

        try:
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
                elapsed = time.monotonic() - start
                self.logger.info("News fetch completed for %s in %.2fs", ticker, elapsed)
        except Exception as exc:
            self.logger.warning("Unable to retrieve news for %s: %s", ticker, exc)
            return []

        candidates = []
        seen_titles = set()
        for item in payload.get("news", []):
            title = (item.get("title") or "").strip()
            if not title or title in seen_titles:
                continue

            seen_titles.add(title)
            relevance = self._classify_relevance(title, ticker, company_name)
            candidates.append(
                {
                    "title": title,
                    "publisher": item.get("publisher") or "Unknown publisher",
                    "url": item.get("link") or "",
                    "relevance": relevance,
                }
            )

        company_headlines = [
            headline for headline in candidates
            if headline["relevance"] == "company"
        ]
        sector_headlines = [
            headline for headline in candidates
            if headline["relevance"] == "sector"
        ]
        broad_headlines = [
            headline for headline in candidates
            if headline["relevance"] == "broad"
        ]

        return (company_headlines + sector_headlines + broad_headlines)[:self.max_headlines]

    def _classify_relevance(self, title, ticker, company_name):
        normalized_title = title.lower()
        company_tokens = [
            token.strip(".,()").lower()
            for token in (company_name or "").split()
            if len(token.strip(".,()")) >= 4
        ]

        if ticker.lower() in normalized_title:
            return "company"

        if any(token in normalized_title for token in company_tokens):
            return "company"

        if any(keyword.lower() in normalized_title for keyword in SECTOR_KEYWORDS):
            return "sector"

        return "broad"
