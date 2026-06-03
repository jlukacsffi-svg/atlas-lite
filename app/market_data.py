"""Market data fetching module using yfinance"""

import contextlib
import io
import json
import logging
import os
import time
import urllib.request
from pathlib import Path

import yfinance as yf

from app.growth import GrowthEngine
from app.momentum import MomentumEngine

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_FILE = LOG_DIR / "atlas_diagnostics.log"
YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    "?range=2d&interval=1d&includePrePost=false"
)
YFINANCE_TIMEOUT_SECONDS = 1
YFINANCE_INFO_TIMEOUT_SECONDS = 1
YFINANCE_FAILURE_LIMIT = 2
YAHOO_FALLBACK_TIMEOUT_SECONDS = 6


def _configure_logger():
    logger = logging.getLogger(__name__)
    if logger.handlers:
        return logger
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger

logger = _configure_logger()


class MarketDataFetcher:
    """Fetch market data for stocks using yfinance"""

    def __init__(self, watchlist, universe=None):
        """
        Initialize the fetcher with a watchlist

        Args:
            watchlist (list): List of stock ticker symbols
        """
        self.watchlist = watchlist
        self.universe = universe
        self.logger = logger
        self.growth_engine = GrowthEngine()
        self.momentum_engine = MomentumEngine()
        self.yfinance_failures = 0
        self.yfinance_disabled = False

    def _apply_universe_metadata(self, ticker, record):
        if not self.universe:
            return record

        security = self.universe.get(ticker)
        if not security:
            return record

        record["company_name"] = record.get("company_name") or security["company_name"]
        record["sector"] = security["sector"]
        record["category"] = security["category"]
        record["notes"] = security["notes"]
        record["scores"] = dict(security["scores"])
        record["score_source"] = security["score_source"]
        record["profile"] = dict(security.get("profile", {}))
        automated_scores = []

        if security["sector"] != "Benchmark ETF":
            growth_metrics = self.growth_engine.fetch_metrics(ticker)
            if growth_metrics and growth_metrics.get("growth_score") is not None:
                record["growth_metrics"] = growth_metrics
                record["scores"]["growth"] = growth_metrics["growth_score"]
                automated_scores.append("growth")

        momentum_metrics = self.momentum_engine.fetch_metrics(ticker)
        if momentum_metrics and momentum_metrics.get("momentum_score") is not None:
            record["momentum_metrics"] = momentum_metrics
            record["scores"]["momentum"] = momentum_metrics["momentum_score"]
            automated_scores.append("momentum")

        if automated_scores:
            record["automated_scores"] = automated_scores
            record["score_source"] = (
                "hybrid_v2"
                if set(automated_scores) == {"growth", "momentum"}
                else "hybrid_v1"
            )
        return record

    def _note_yfinance_failure(self, ticker, reason):
        self.yfinance_failures += 1
        self.logger.warning("yfinance failed for %s: %s", ticker, reason)

        if self.yfinance_failures >= YFINANCE_FAILURE_LIMIT:
            self.yfinance_disabled = True
            self.logger.warning(
                "Disabling yfinance for the rest of this run after %d failures",
                self.yfinance_failures,
            )

    def _placeholder_record(self, status='unavailable'):
        return {
            'price': None,
            'previous_close': None,
            'change': 0.0,
            'percent_change': 0.0,
            'status': status,
            'source': 'placeholder',
        }

    def _placeholder_summary(self, status='unavailable'):
        return {
            'price': None,
            'change': 0.0,
            'percent_change': 0.0,
            'status': status,
            'source': 'placeholder',
        }

    def _run_yfinance_history(self, ticker):
        start = time.monotonic()
        stderr_buffer = io.StringIO()
        with contextlib.redirect_stderr(stderr_buffer):
            stock = yf.Ticker(ticker)
            hist = stock.history(period='2d', timeout=YFINANCE_TIMEOUT_SECONDS)

        elapsed = time.monotonic() - start
        self.logger.info("yfinance history completed for %s in %.2fs", ticker, elapsed)

        stderr_text = stderr_buffer.getvalue().strip()
        if stderr_text:
            self.logger.warning("yfinance stderr for %s: %s", ticker, stderr_text.replace('\n', ' | '))
        return hist

    def _run_yfinance_info(self, ticker):
        start = time.monotonic()
        stock_info = yf.Ticker(ticker).get_info(timeout=YFINANCE_INFO_TIMEOUT_SECONDS)
        elapsed = time.monotonic() - start
        self.logger.info("yfinance info completed for %s in %.2fs", ticker, elapsed)
        return stock_info

    def _fetch_yahoo_fallback_record(self, ticker):
        raw = self._fetch_yahoo_raw_response(ticker)
        if raw is not None:
            parsed = self._parse_yahoo_chart_json(raw, ticker)
            if parsed is not None:
                return parsed
        return self._placeholder_record()

    def _fetch_yahoo_fallback_summary(self, idx):
        raw = self._fetch_yahoo_raw_response(idx)
        if raw is not None:
            parsed = self._parse_yahoo_chart_json(raw, idx)
            if parsed is not None:
                return parsed
        return self._placeholder_summary()

    def _fetch_yahoo_raw_response(self, ticker):
        url = YAHOO_CHART_URL.format(ticker=ticker)
        self.logger.debug("Fetching raw Yahoo response for %s from %s", ticker, url)
        request = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
        )

        try:
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=YAHOO_FALLBACK_TIMEOUT_SECONDS) as response:
                raw = response.read().decode('utf-8', errors='replace')
                elapsed = time.monotonic() - start
                self.logger.info("Yahoo fallback completed for %s in %.2fs", ticker, elapsed)
                self.logger.debug("Raw response body for %s: %s", ticker, raw)
                return raw
        except Exception as exc:
            self.logger.warning(
                "Unable to retrieve raw Yahoo response for %s: %s",
                ticker,
                exc,
                exc_info=True,
            )
            return None

    def _parse_yahoo_chart_json(self, raw, ticker):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.logger.warning("Unable to parse raw Yahoo JSON for %s: %s", ticker, exc)
            return None

        chart = payload.get('chart', {})
        results = chart.get('result')
        if not results:
            self.logger.warning("No chart result in Yahoo response for %s", ticker)
            return None

        result = results[0]
        meta = result.get('meta', {})
        indicators = result.get('indicators', {}).get('quote', [])
        if not indicators:
            self.logger.warning("No quote indicators in Yahoo response for %s", ticker)
            return None

        quote = indicators[0]
        closes = quote.get('close') or []
        opens = quote.get('open') or []
        highs = quote.get('high') or []
        lows = quote.get('low') or []
        volumes = quote.get('volume') or []

        if not closes:
            self.logger.warning("No close prices in Yahoo response for %s", ticker)
            return None

        # Find last valid close and previous valid close
        last_close = None
        prev_close = None
        for value in reversed(closes):
            if value is not None:
                if last_close is None:
                    last_close = value
                elif prev_close is None:
                    prev_close = value
                    break

        if last_close is None:
            self.logger.warning("No valid close price in Yahoo response for %s", ticker)
            return None

        if prev_close is None:
            prev_close = last_close

        change = last_close - prev_close
        percent_change = (change / prev_close * 100) if prev_close != 0 else 0

        last_open = None
        for value in reversed(opens):
            if value is not None:
                last_open = value
                break

        last_high = None
        for value in reversed(highs):
            if value is not None:
                last_high = value
                break

        last_low = None
        for value in reversed(lows):
            if value is not None:
                last_low = value
                break

        last_volume = None
        for value in reversed(volumes):
            if value is not None:
                last_volume = value
                break

        company_name = meta.get('longName') or meta.get('shortName') or meta.get('symbol') or ticker

        parsed = {
            'ticker': ticker,
            'price': round(last_close, 2),
            'previous_close': round(prev_close, 2),
            'change': round(change, 2),
            'percent_change': round(percent_change, 2),
            'volume': int(last_volume) if last_volume is not None else None,
            'open': round(last_open, 2) if last_open is not None else None,
            'high': round(last_high, 2) if last_high is not None else None,
            'low': round(last_low, 2) if last_low is not None else None,
            'company_name': company_name,
            'status': 'available',
            'source': 'yahoo_fallback',
        }

        self.logger.debug("Parsed Yahoo fallback data for %s: %s", ticker, parsed)
        return parsed

    def _fetch_data_for_ticker(self, ticker):
        self.logger.info("Fetching data for ticker %s", ticker)
        self.logger.debug("Calling yfinance: yf.Ticker(%r).history(period='2d')", ticker)

        if self.yfinance_disabled:
            self.logger.info("Skipping yfinance for %s because it is disabled for this run", ticker)
            return self._apply_universe_metadata(ticker, self._fetch_yahoo_fallback_record(ticker))

        try:
            hist = self._run_yfinance_history(ticker)
            self.logger.debug("yfinance history rows for %s: %s", ticker, len(hist))

            if len(hist) < 1:
                self._note_yfinance_failure(ticker, "empty history")
                return self._apply_universe_metadata(ticker, self._fetch_yahoo_fallback_record(ticker))

            current_price = hist['Close'].iloc[-1]
            previous_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            price_change = current_price - previous_close
            percent_change = (price_change / previous_close * 100) if previous_close != 0 else 0

            # Try to get company name from yfinance info
            company_name = ticker
            try:
                stock_info = self._run_yfinance_info(ticker) or {}
                company_name = (
                    stock_info.get('longName')
                    or stock_info.get('shortName')
                    or stock_info.get('symbol')
                    or ticker
                )
            except Exception:
                pass

            return self._apply_universe_metadata(ticker, {
                'price': round(current_price, 2),
                'previous_close': round(previous_close, 2),
                'change': round(price_change, 2),
                'percent_change': round(percent_change, 2),
                'company_name': company_name,
                'status': 'available',
                'source': 'yfinance',
            })
        except Exception as exc:
            self.logger.error(
                "Error fetching data for %s: %s",
                ticker,
                exc,
                exc_info=True,
            )
            return self._apply_universe_metadata(ticker, self._fetch_yahoo_fallback_record(ticker))

    def fetch_current_data(self):
        """
        Fetch current price data for all stocks in the watchlist

        Returns:
            dict: Dictionary with stock data
        """
        self.logger.info("Fetching current data for %d tickers", len(self.watchlist))
        data = {}

        for ticker in self.watchlist:
            data[ticker] = self._fetch_data_for_ticker(ticker)

        return data

    def _fetch_summary_for_index(self, idx):
        self.logger.info("Fetching market summary for index %s", idx)
        self.logger.debug("Calling yfinance: yf.Ticker(%r).history(period='2d')", idx)

        if self.yfinance_disabled:
            self.logger.info("Skipping yfinance for index %s because it is disabled for this run", idx)
            return self._fetch_yahoo_fallback_summary(idx)

        try:
            hist = self._run_yfinance_history(idx)
            self.logger.debug("yfinance history rows for %s: %s", idx, len(hist))

            if len(hist) < 1:
                self._note_yfinance_failure(idx, "empty history")
                return self._fetch_yahoo_fallback_summary(idx)

            current_price = hist['Close'].iloc[-1]
            previous_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            price_change = current_price - previous_close
            percent_change = (price_change / previous_close * 100) if previous_close != 0 else 0

            return {
                'price': round(current_price, 2),
                'change': round(price_change, 2),
                'percent_change': round(percent_change, 2),
                'status': 'available',
            }
        except Exception as exc:
            self.logger.error(
                "Error fetching index data for %s: %s",
                idx,
                exc,
                exc_info=True,
            )
            return self._fetch_yahoo_fallback_summary(idx)

    def get_market_summary(self):
        """
        Get summary of major market indices

        Returns:
            dict: Dictionary with index data (SPY, QQQ, etc.)
        """
        indices = ['SPY', 'QQQ']
        summary = {}

        for idx in indices:
            summary[idx] = self._fetch_summary_for_index(idx)

        return summary
