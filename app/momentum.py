"""Automated momentum measurement for Atlas Scoring Engine v1."""

import json
import logging
import time
import urllib.request
from datetime import datetime, timezone


YAHOO_MOMENTUM_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?range=1y&interval=1d&includePrePost=false&events=div%2Csplits"
)
MOMENTUM_TIMEOUT_SECONDS = 6


class MomentumEngine:
    """Fetch recent returns and convert them into a 0-100 momentum score."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def fetch_metrics(self, ticker):
        request = urllib.request.Request(
            YAHOO_MOMENTUM_URL.format(ticker=ticker),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )

        try:
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=MOMENTUM_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            self.logger.info("Momentum history completed for %s in %.2fs", ticker, time.monotonic() - start)
        except Exception as exc:
            self.logger.warning("Unable to retrieve momentum history for %s: %s", ticker, exc)
            return None

        closes = self._extract_closes(payload)
        if len(closes) < 2:
            return None

        current = closes[-1]
        return_1m = self._return_from_period(closes, 21)
        return_3m = self._return_from_period(closes, 63)
        return_6m = self._return_from_period(closes, 126)

        return {
            "current_price": round(current, 2),
            "return_1m": self._round_optional(return_1m),
            "return_3m": self._round_optional(return_3m),
            "return_6m": self._round_optional(return_6m),
            "momentum_score": self.calculate_score(return_1m, return_3m),
            "recent_splits": self._extract_splits(payload),
            "source": "yahoo_chart_1y",
        }

    def calculate_score(self, return_1m, return_3m):
        """Map recent returns to a bounded score centered on 50."""
        if return_1m is None and return_3m is None:
            return None

        one_month = return_1m or 0.0
        three_month = return_3m or 0.0
        raw_score = 50 + (one_month * 1.5) + (three_month * 0.75)
        return round(max(0, min(100, raw_score)), 1)

    def _extract_closes(self, payload):
        results = payload.get("chart", {}).get("result") or []
        if not results:
            return []
        indicators = results[0].get("indicators", {})
        adjusted = indicators.get("adjclose") or []
        quotes = indicators.get("quote") or []
        values = (
            adjusted[0].get("adjclose")
            if adjusted and adjusted[0].get("adjclose")
            else quotes[0].get("close") if quotes else []
        )
        if not values:
            return []
        return [
            float(value)
            for value in values
            if value is not None
        ]

    def _extract_splits(self, payload):
        results = payload.get("chart", {}).get("result") or []
        if not results:
            return []
        events = results[0].get("events", {}).get("splits", {})
        splits = []
        for event in events.values():
            numerator = self._positive_float(event.get("numerator"))
            denominator = self._positive_float(event.get("denominator"))
            timestamp = event.get("date")
            if numerator is None or denominator is None or timestamp is None:
                continue
            splits.append(
                {
                    "date": datetime.fromtimestamp(
                        int(timestamp),
                        tz=timezone.utc,
                    ).isoformat(),
                    "ratio": round(numerator / denominator, 8),
                    "split_ratio": event.get(
                        "splitRatio",
                        f"{numerator:g}:{denominator:g}",
                    ),
                    "source": "yahoo_chart_event",
                }
            )
        return sorted(splits, key=lambda item: item["date"])

    def _return_from_period(self, closes, trading_days):
        if len(closes) <= trading_days:
            return None
        prior = closes[-(trading_days + 1)]
        if prior == 0:
            return None
        return ((closes[-1] - prior) / prior) * 100

    def _round_optional(self, value):
        return round(value, 2) if value is not None else None

    @staticmethod
    def _positive_float(value):
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None
