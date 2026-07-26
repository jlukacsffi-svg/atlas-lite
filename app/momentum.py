"""Automated momentum measurement for Atlas Scoring Engine v1."""

import json
import logging
import math
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
        return_12m = self._return_from_period(closes, 252)
        sma_20 = self._simple_moving_average(closes, 20)
        sma_50 = self._simple_moving_average(closes, 50)
        sma_200 = self._simple_moving_average(closes, 200)
        ema_20 = self._exponential_moving_average(closes, 20)
        ema_20_slope = self._ema_slope_pct(closes, 20, lookback=10)
        rsi_14 = self._rsi(closes, 14)
        volatility_20d = self._volatility(closes, 20)
        distance_from_52w_high = self._distance_from_high(closes, 252)
        drawdown_63d = self._distance_from_high(closes, 63)
        price_vs_sma_20 = self._distance_from_average(current, sma_20)
        price_vs_sma_50 = self._distance_from_average(current, sma_50)
        price_vs_sma_200 = self._distance_from_average(current, sma_200)
        sma_50_vs_sma_200 = self._distance_between_averages(sma_50, sma_200)
        legacy_score = self.calculate_score(return_1m, return_3m)
        trend_quality_score = self._trend_quality_score(
            current=current,
            return_1m=return_1m,
            return_3m=return_3m,
            return_6m=return_6m,
            return_12m=return_12m,
            sma_20=sma_20,
            sma_50=sma_50,
            sma_200=sma_200,
            rsi_14=rsi_14,
            distance_from_52w_high=distance_from_52w_high,
            volatility_20d=volatility_20d,
        )
        trend_regime_score = self._trend_regime_score(
            trend_quality_score=trend_quality_score,
            ema_20_slope=ema_20_slope,
            price_vs_sma_50=price_vs_sma_50,
            price_vs_sma_200=price_vs_sma_200,
            sma_50_vs_sma_200=sma_50_vs_sma_200,
            drawdown_63d=drawdown_63d,
        )

        return {
            "current_price": round(current, 2),
            "return_1m": self._round_optional(return_1m),
            "return_3m": self._round_optional(return_3m),
            "return_6m": self._round_optional(return_6m),
            "return_12m": self._round_optional(return_12m),
            "sma_20": self._round_optional(sma_20),
            "sma_50": self._round_optional(sma_50),
            "sma_200": self._round_optional(sma_200),
            "ema_20": self._round_optional(ema_20),
            "ema_20_slope_pct": self._round_optional(ema_20_slope),
            "rsi_14": self._round_optional(rsi_14),
            "volatility_20d_pct": self._round_optional(volatility_20d),
            "distance_from_52w_high_pct": self._round_optional(distance_from_52w_high),
            "drawdown_63d_pct": self._round_optional(drawdown_63d),
            "price_vs_sma_20_pct": self._round_optional(price_vs_sma_20),
            "price_vs_sma_50_pct": self._round_optional(price_vs_sma_50),
            "price_vs_sma_200_pct": self._round_optional(price_vs_sma_200),
            "sma_50_vs_sma_200_pct": self._round_optional(sma_50_vs_sma_200),
            "legacy_momentum_score": legacy_score,
            "trend_quality_score": trend_quality_score,
            "trend_regime_score": trend_regime_score,
            "momentum_score": self._composite_momentum_score(legacy_score, trend_quality_score),
            "trend_state": self._trend_state(
                current=current,
                sma_20=sma_20,
                sma_50=sma_50,
                sma_200=sma_200,
                rsi_14=rsi_14,
            ),
            "trend_regime": self._trend_regime(trend_regime_score),
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

    def _simple_moving_average(self, closes, period):
        if len(closes) < period:
            return None
        window = closes[-period:]
        return sum(window) / period

    def _exponential_moving_average(self, closes, period):
        if len(closes) < period:
            return None
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        for close in closes[period:]:
            ema = ((close - ema) * multiplier) + ema
        return ema

    def _ema_slope_pct(self, closes, period, lookback):
        if len(closes) < period + lookback:
            return None
        end_ema = self._exponential_moving_average(closes, period)
        start_ema = self._exponential_moving_average(closes[:-lookback], period)
        if end_ema is None or start_ema in {None, 0}:
            return None
        return ((end_ema - start_ema) / start_ema) * 100

    def _rsi(self, closes, period):
        if len(closes) <= period:
            return None
        gains = 0.0
        losses = 0.0
        for index in range(len(closes) - period, len(closes)):
            change = closes[index] - closes[index - 1]
            if change >= 0:
                gains += change
            else:
                losses += abs(change)
        average_gain = gains / period
        average_loss = losses / period
        if average_loss == 0:
            return 100.0
        relative_strength = average_gain / average_loss
        return 100 - (100 / (1 + relative_strength))

    def _volatility(self, closes, period):
        if len(closes) <= period:
            return None
        returns = []
        for index in range(len(closes) - period, len(closes)):
            previous = closes[index - 1]
            current = closes[index]
            if previous == 0:
                continue
            returns.append(((current - previous) / previous) * 100)
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
        return math.sqrt(variance)

    def _distance_from_high(self, closes, period):
        if not closes:
            return None
        window = closes[-period:] if len(closes) >= period else closes
        high = max(window)
        if high == 0:
            return None
        return ((closes[-1] - high) / high) * 100

    def _distance_from_average(self, current, average):
        if average in {None, 0}:
            return None
        return ((current - average) / average) * 100

    def _distance_between_averages(self, first, second):
        if first is None or second in {None, 0}:
            return None
        return ((first - second) / second) * 100

    def _trend_quality_score(
        self,
        *,
        current,
        return_1m,
        return_3m,
        return_6m,
        return_12m,
        sma_20,
        sma_50,
        sma_200,
        rsi_14,
        distance_from_52w_high,
        volatility_20d,
    ):
        persistence = self._persistence_score(return_1m, return_3m, return_6m, return_12m)
        alignment = self._moving_average_alignment_score(current, sma_20, sma_50, sma_200)
        breakout = self._breakout_score(distance_from_52w_high)
        rsi_score = self._rsi_context_score(rsi_14)
        volatility_score = self._volatility_score(volatility_20d)
        weighted = (
            persistence * 0.40
            + alignment * 0.30
            + breakout * 0.15
            + rsi_score * 0.10
            + volatility_score * 0.05
        )
        return round(max(0, min(100, weighted)), 1)

    def _persistence_score(self, return_1m, return_3m, return_6m, return_12m):
        weights = (
            (return_1m, 0.20),
            (return_3m, 0.30),
            (return_6m, 0.30),
            (return_12m, 0.20),
        )
        total_weight = sum(weight for value, weight in weights if value is not None)
        if total_weight == 0:
            return 50.0
        scaled = 0.0
        for value, weight in weights:
            if value is None:
                continue
            normalized = max(0, min(100, 50 + value))
            scaled += normalized * weight
        return scaled / total_weight

    def _moving_average_alignment_score(self, current, sma_20, sma_50, sma_200):
        checks = []
        if sma_20 is not None:
            checks.append(100.0 if current >= sma_20 else 0.0)
        if sma_50 is not None:
            checks.append(100.0 if current >= sma_50 else 0.0)
        if sma_200 is not None:
            checks.append(100.0 if current >= sma_200 else 0.0)
        if sma_20 is not None and sma_50 is not None:
            checks.append(100.0 if sma_20 >= sma_50 else 0.0)
        if sma_50 is not None and sma_200 is not None:
            checks.append(100.0 if sma_50 >= sma_200 else 0.0)
        if not checks:
            return 50.0
        return sum(checks) / len(checks)

    def _breakout_score(self, distance_from_52w_high):
        if distance_from_52w_high is None:
            return 50.0
        return max(0, min(100, 100 + (distance_from_52w_high * 2.5)))

    def _rsi_context_score(self, rsi_14):
        if rsi_14 is None:
            return 50.0
        if 50 <= rsi_14 <= 68:
            return 85.0
        if 40 <= rsi_14 < 50 or 68 < rsi_14 <= 75:
            return 65.0
        if 30 <= rsi_14 < 40 or 75 < rsi_14 <= 82:
            return 45.0
        return 25.0

    def _volatility_score(self, volatility_20d):
        if volatility_20d is None:
            return 50.0
        return max(20.0, min(90.0, 90.0 - (volatility_20d * 6.0)))

    def _composite_momentum_score(self, legacy_score, trend_quality_score):
        if legacy_score is None and trend_quality_score is None:
            return None
        legacy = 50.0 if legacy_score is None else float(legacy_score)
        trend = 50.0 if trend_quality_score is None else float(trend_quality_score)
        return round(max(0, min(100, (legacy * 0.45) + (trend * 0.55))), 1)

    def _trend_regime_score(
        self,
        *,
        trend_quality_score,
        ema_20_slope,
        price_vs_sma_50,
        price_vs_sma_200,
        sma_50_vs_sma_200,
        drawdown_63d,
    ):
        score = 50.0 if trend_quality_score is None else float(trend_quality_score)
        if ema_20_slope is not None:
            score += max(-10.0, min(10.0, ema_20_slope * 3.0))
        if price_vs_sma_50 is not None:
            score += max(-8.0, min(8.0, price_vs_sma_50 * 1.2))
        if price_vs_sma_200 is not None:
            score += max(-12.0, min(12.0, price_vs_sma_200 * 0.9))
        if sma_50_vs_sma_200 is not None:
            score += max(-8.0, min(8.0, sma_50_vs_sma_200 * 0.8))
        if drawdown_63d is not None:
            if drawdown_63d >= -4.0:
                score += 6.0
            elif drawdown_63d >= -8.0:
                score += 2.0
            elif drawdown_63d <= -18.0:
                score -= 10.0
            elif drawdown_63d <= -12.0:
                score -= 5.0
        return round(max(0, min(100, score)), 1)

    def _trend_regime(self, regime_score):
        if regime_score is None:
            return "unknown"
        if regime_score >= 82:
            return "leadership"
        if regime_score >= 68:
            return "constructive"
        if regime_score >= 52:
            return "repair"
        if regime_score >= 38:
            return "fragile"
        return "breakdown"

    def _trend_state(self, *, current, sma_20, sma_50, sma_200, rsi_14):
        above_20 = sma_20 is not None and current >= sma_20
        above_50 = sma_50 is not None and current >= sma_50
        above_200 = sma_200 is not None and current >= sma_200
        overheated = rsi_14 is not None and rsi_14 >= 75
        if above_20 and above_50 and above_200:
            return "extended_uptrend" if overheated else "uptrend"
        if above_50 and above_200:
            return "improving"
        if not above_50 and not above_200:
            return "downtrend"
        return "mixed"
