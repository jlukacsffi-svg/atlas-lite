"""News headline fetching for Atlas Lite."""

from datetime import datetime
import json
import logging
import time
import urllib.parse
import urllib.request
from pathlib import Path

from app.paths import data_path


YAHOO_SEARCH_URL = "https://query1.finance.yahoo.com/v1/finance/search"
DEFAULT_NEWS_CACHE_DIR = data_path("data_cache", "news")
NEWS_CACHE_HOURS = 6
DEFAULT_SOURCE_WEIGHT = 1.0


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

POSITIVE_NEWS_PATTERNS = (
    "beats",
    "beat",
    "raised guidance",
    "raises guidance",
    "guidance raise",
    "guidance boosted",
    "upgrade",
    "upgraded",
    "price target raised",
    "record",
    "surge",
    "surges",
    "wins",
    "win",
    "contract",
    "approval",
    "approved",
    "partnership",
    "expands",
    "strong demand",
)

NEGATIVE_NEWS_PATTERNS = (
    "misses",
    "miss",
    "cuts guidance",
    "cut guidance",
    "lowers guidance",
    "lowered guidance",
    "downgrade",
    "downgraded",
    "price target cut",
    "lawsuit",
    "probe",
    "investigation",
    "recall",
    "delay",
    "delayed",
    "fraud",
    "warning",
    "warns",
    "weak demand",
    "offering",
)

SOURCE_WEIGHT_RULES = (
    ("reuters", 1.3),
    ("bloomberg", 1.3),
    ("associated press", 1.2),
    ("ap ", 1.2),
    ("wall street journal", 1.25),
    ("dow jones", 1.2),
    ("financial times", 1.2),
    ("barron", 1.15),
    ("marketwatch", 1.1),
    ("cnbc", 1.05),
    ("seeking alpha", 0.95),
    ("benzinga", 0.9),
    ("investorplace", 0.8),
    ("motley fool", 0.8),
)

NEWS_EVENT_RULES = (
    {
        "event_type": "legal_risk",
        "sentiment": "negative",
        "weight": 3.3,
        "severity": "high",
        "patterns": ("lawsuit", "probe", "investigation", "fraud", "sec investigation", "doj"),
    },
    {
        "event_type": "guidance_cut",
        "sentiment": "negative",
        "weight": 3.0,
        "severity": "high",
        "patterns": ("cuts guidance", "cut guidance", "lowers guidance", "lowered guidance"),
    },
    {
        "event_type": "earnings_miss",
        "sentiment": "negative",
        "weight": 2.8,
        "severity": "high",
        "patterns": ("misses expectations", "misses estimates", "earnings miss", "revenue miss"),
    },
    {
        "event_type": "analyst_downgrade",
        "sentiment": "negative",
        "weight": 2.2,
        "severity": "medium",
        "patterns": ("downgrade", "downgraded", "price target cut"),
    },
    {
        "event_type": "product_delay",
        "sentiment": "negative",
        "weight": 2.0,
        "severity": "medium",
        "patterns": ("delay", "delayed", "recall"),
    },
    {
        "event_type": "demand_weakness",
        "sentiment": "negative",
        "weight": 2.0,
        "severity": "medium",
        "patterns": ("weak demand", "demand warning", "warning", "warns"),
    },
    {
        "event_type": "offering_or_dilution",
        "sentiment": "negative",
        "weight": 1.8,
        "severity": "medium",
        "patterns": ("offering", "share sale", "secondary offering"),
    },
    {
        "event_type": "guidance_raise",
        "sentiment": "positive",
        "weight": 3.0,
        "severity": "high",
        "patterns": ("raised guidance", "raises guidance", "guidance raise", "guidance boosted"),
    },
    {
        "event_type": "earnings_beat",
        "sentiment": "positive",
        "weight": 2.8,
        "severity": "high",
        "patterns": ("beats expectations", "beats estimates", "beat estimates", "earnings beat"),
    },
    {
        "event_type": "analyst_upgrade",
        "sentiment": "positive",
        "weight": 2.2,
        "severity": "medium",
        "patterns": ("upgrade", "upgraded", "price target raised"),
    },
    {
        "event_type": "contract_win",
        "sentiment": "positive",
        "weight": 2.0,
        "severity": "medium",
        "patterns": ("wins contract", "large contract", "contract win", "award"),
    },
    {
        "event_type": "approval",
        "sentiment": "positive",
        "weight": 2.0,
        "severity": "medium",
        "patterns": ("approval", "approved", "cleared by fda"),
    },
    {
        "event_type": "product_launch",
        "sentiment": "positive",
        "weight": 1.7,
        "severity": "medium",
        "patterns": ("launch", "launches", "product release", "announces new"),
    },
    {
        "event_type": "partnership",
        "sentiment": "positive",
        "weight": 1.6,
        "severity": "medium",
        "patterns": ("partnership", "partner", "expands alliance"),
    },
)


class NewsFetcher:
    """Fetch recent public finance headlines for watchlist tickers."""

    def __init__(
        self,
        cache_dir=DEFAULT_NEWS_CACHE_DIR,
        max_headlines=3,
        search_headlines=10,
        timeout=5,
    ):
        self.cache_dir = Path(cache_dir)
        self.max_headlines = max_headlines
        self.search_headlines = search_headlines
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)

    def fetch_headlines(self, ticker, company_name=None):
        cache_path = self.cache_dir / f"{str(ticker).upper()}_news.json"
        cached_payload = self._read_cached_json(cache_path)

        if cached_payload is not None and self._cache_is_fresh(cache_path):
            return cached_payload[: self.max_headlines]

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
            if cached_payload is not None:
                self.logger.warning("Using stale news cache after fetch failure: %s", cache_path)
                return cached_payload[: self.max_headlines]
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
                    "published_at": self._normalize_published_at(
                        item.get("providerPublishTime")
                    ),
                    "source_weight": self._source_weight(item.get("publisher")),
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

        payload = (company_headlines + sector_headlines + broad_headlines)[:self.max_headlines]
        self._write_cached_json(cache_path, payload)
        return payload

    def fetch_signal(self, ticker, company_name=None):
        headlines = self.fetch_headlines(ticker, company_name)
        company_headlines = [
            headline for headline in headlines if headline.get("relevance") == "company"
        ]
        positive = []
        negative = []
        analyzed = []
        positive_weight = 0.0
        negative_weight = 0.0
        high_impact_positive_count = 0
        high_impact_negative_count = 0

        for headline in company_headlines:
            title = str(headline.get("title") or "")
            publisher = str(headline.get("publisher") or "")
            event = self._classify_event(title)
            impact = round(float(event["weight"]) * self._source_weight(publisher), 2)
            analyzed.append(
                {
                    "title": title,
                    "publisher": publisher,
                    "event_type": event["event_type"],
                    "sentiment": event["sentiment"],
                    "severity": event["severity"],
                    "impact": impact,
                }
            )
            classification = event["sentiment"]
            if classification == "positive":
                positive.append(title)
                positive_weight += impact
                if event["severity"] == "high":
                    high_impact_positive_count += 1
            elif classification == "negative":
                negative.append(title)
                negative_weight += impact
                if event["severity"] == "high":
                    high_impact_negative_count += 1

        net_weight = positive_weight - negative_weight
        score = max(0, min(100, 50 + (net_weight * 10.0)))
        if high_impact_negative_count >= 1 or negative_weight >= 3.0:
            label = "adverse"
            score = min(score, 32.0)
        elif high_impact_positive_count >= 1 and positive_weight >= 2.5:
            label = "supportive"
            score = max(score, 68.0)
        elif net_weight < -0.8:
            label = "cautious"
        elif net_weight > 0.8:
            label = "constructive"
        else:
            label = "neutral"

        dominant_event_type = "routine"
        if analyzed:
            dominant = max(analyzed, key=lambda item: (item["impact"], item["title"]))
            dominant_event_type = dominant["event_type"]

        return {
            "ticker": str(ticker).upper(),
            "headline_count": len(headlines),
            "company_headline_count": len(company_headlines),
            "positive_count": len(positive),
            "negative_count": len(negative),
            "positive_weight": round(positive_weight, 2),
            "negative_weight": round(negative_weight, 2),
            "net_weight": round(net_weight, 2),
            "high_impact_positive_count": high_impact_positive_count,
            "high_impact_negative_count": high_impact_negative_count,
            "dominant_event_type": dominant_event_type,
            "headline_events": analyzed[:3],
            "signal_score": float(score),
            "signal_label": label,
            "positive_examples": positive[:2],
            "negative_examples": negative[:2],
        }

    def enrich_market_data(self, market_data, tickers):
        for ticker in sorted({str(value).strip().upper() for value in tickers if str(value).strip()}):
            data = market_data.get(ticker)
            if not data or data.get("status") != "available":
                continue
            data["news_signal"] = self.fetch_signal(
                ticker,
                company_name=data.get("company_name") or ticker,
            )
        return market_data

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

    def _classify_sentiment(self, title):
        normalized = str(title or "").lower()
        if any(pattern in normalized for pattern in NEGATIVE_NEWS_PATTERNS):
            return "negative"
        if any(pattern in normalized for pattern in POSITIVE_NEWS_PATTERNS):
            return "positive"
        return "neutral"

    def _classify_event(self, title):
        normalized = str(title or "").lower()
        for rule in NEWS_EVENT_RULES:
            if any(pattern in normalized for pattern in rule["patterns"]):
                return {
                    "event_type": rule["event_type"],
                    "sentiment": rule["sentiment"],
                    "weight": rule["weight"],
                    "severity": rule["severity"],
                }
        return {
            "event_type": "routine",
            "sentiment": self._classify_sentiment(title),
            "weight": 1.2 if self._classify_sentiment(title) != "neutral" else 0.4,
            "severity": "low",
        }

    @staticmethod
    def _source_weight(publisher):
        normalized = str(publisher or "").strip().lower()
        for token, weight in SOURCE_WEIGHT_RULES:
            if token in normalized:
                return float(weight)
        return DEFAULT_SOURCE_WEIGHT

    @staticmethod
    def _normalize_published_at(timestamp):
        try:
            if timestamp is None:
                return None
            return datetime.utcfromtimestamp(int(timestamp)).isoformat() + "Z"
        except (TypeError, ValueError, OSError):
            return None

    def _read_cached_json(self, cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.logger.warning("Unable to read news cache %s: %s", cache_path, exc)
            return None

    def _write_cached_json(self, cache_path, payload):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        except Exception as exc:
            self.logger.warning("Unable to write news cache %s: %s", cache_path, exc)

    def _cache_is_fresh(self, cache_path):
        try:
            age_seconds = time.time() - cache_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return age_seconds <= NEWS_CACHE_HOURS * 60 * 60
