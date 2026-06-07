"""Automated fundamental growth measurement using SEC Company Facts."""

import json
import logging
import os
import time
import urllib.request
from datetime import date
from pathlib import Path

from app.paths import data_path

DEFAULT_SEC_CACHE_DIR = data_path("data_cache", "sec")
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_TIMEOUT_SECONDS = 10
SEC_REQUEST_DELAY_SECONDS = 0.12
TICKER_MAP_CACHE_DAYS = 30
COMPANY_FACTS_CACHE_DAYS = 7
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
REVENUE_TAGS = (
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
    ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax"),
    ("us-gaap", "Revenues"),
    ("ifrs-full", "Revenue"),
)
NET_INCOME_TAGS = (
    ("us-gaap", "NetIncomeLoss"),
    ("ifrs-full", "ProfitLoss"),
)


class GrowthEngine:
    """Fetch annual filing metrics and convert them into a 0-100 Growth score."""

    def __init__(self, cache_dir=DEFAULT_SEC_CACHE_DIR):
        self.logger = logging.getLogger(__name__)
        self.user_agent = os.getenv(
            "ATLAS_SEC_USER_AGENT",
            "Atlas Capital Research atlas.capital.reports@gmail.com",
        )
        self.cache_dir = Path(cache_dir)
        self._ticker_ciks = None

    def fetch_metrics(self, ticker):
        payload = self.fetch_company_facts(ticker)
        if not payload:
            return None

        return self.metrics_from_payload(payload)

    def fetch_company_facts(self, ticker):
        cik = self._get_cik(ticker)
        if not cik:
            return None
        return self._fetch_json_cached(
            SEC_COMPANY_FACTS_URL.format(cik=cik),
            f"companyfacts_{cik}.json",
            COMPANY_FACTS_CACHE_DAYS,
        )

    def metrics_from_payload(self, payload):
        """Build Growth metrics from an already retrieved SEC Company Facts payload."""
        revenue = self._latest_annual_pair(payload, REVENUE_TAGS)
        net_income = self._latest_annual_pair(payload, NET_INCOME_TAGS)
        revenue_growth = self._growth_rate(revenue)
        net_income_growth = self._growth_rate(net_income, require_positive_prior=True)
        growth_score = self.calculate_score(revenue_growth, net_income_growth)

        if growth_score is None:
            return None

        latest_fiscal_year = None
        fiscal_years = [
            pair[0]["fy"]
            for pair in (revenue, net_income)
            if pair and pair[0].get("fy") is not None
        ]
        if fiscal_years:
            latest_fiscal_year = max(fiscal_years)

        return {
            "growth_score": growth_score,
            "revenue_growth": self._round_optional(revenue_growth),
            "net_income_growth": self._round_optional(net_income_growth),
            "latest_fiscal_year": latest_fiscal_year,
            "revenue_tag": revenue[0]["tag"] if revenue else None,
            "net_income_tag": net_income[0]["tag"] if net_income else None,
            "source": "sec_companyfacts",
        }

    def calculate_score(self, revenue_growth, net_income_growth):
        """Calculate a bounded score with revenue growth as the primary input."""
        components = []
        if revenue_growth is not None:
            components.append((self._metric_score(revenue_growth, multiplier=2.0), 0.7))
        if net_income_growth is not None:
            components.append((self._metric_score(net_income_growth, multiplier=1.0), 0.3))

        if not components:
            return None

        total_weight = sum(weight for _, weight in components)
        weighted_score = sum(score * weight for score, weight in components) / total_weight
        return round(weighted_score, 1)

    def _get_cik(self, ticker):
        if self._ticker_ciks is None:
            payload = self._fetch_json_cached(
                SEC_TICKERS_URL,
                "company_tickers.json",
                TICKER_MAP_CACHE_DAYS,
            )
            if not payload:
                self._ticker_ciks = {}
            else:
                self._ticker_ciks = {
                    str(item["ticker"]).upper(): f"{int(item['cik_str']):010d}"
                    for item in payload.values()
                }
        return self._ticker_ciks.get(str(ticker).upper())

    def _fetch_json_cached(self, url, cache_filename, max_age_days):
        cache_path = self.cache_dir / cache_filename
        cached_payload = self._read_cached_json(cache_path)

        if cached_payload is not None and self._cache_is_fresh(cache_path, max_age_days):
            self.logger.info("SEC cache hit: %s", cache_path)
            return cached_payload

        payload = self._fetch_json_uncached(url)
        if payload is not None:
            self._write_cached_json(cache_path, payload)
            return payload

        if cached_payload is not None:
            self.logger.warning("Using stale SEC cache after fetch failure: %s", cache_path)
            return cached_payload
        return None

    def _fetch_json_uncached(self, url):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        try:
            time.sleep(SEC_REQUEST_DELAY_SECONDS)
            start = time.monotonic()
            with urllib.request.urlopen(request, timeout=SEC_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            self.logger.info("SEC request completed in %.2fs: %s", time.monotonic() - start, url)
            return payload
        except Exception as exc:
            self.logger.warning("Unable to retrieve SEC data from %s: %s", url, exc)
            return None

    def _read_cached_json(self, cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as exc:
            self.logger.warning("Unable to read SEC cache %s: %s", cache_path, exc)
            return None

    def _write_cached_json(self, cache_path, payload):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            self.logger.warning("Unable to write SEC cache %s: %s", cache_path, exc)

    def _cache_is_fresh(self, cache_path, max_age_days):
        try:
            age_seconds = time.time() - cache_path.stat().st_mtime
        except FileNotFoundError:
            return False
        return age_seconds <= max_age_days * 24 * 60 * 60

    def _latest_annual_pair(self, payload, tag_candidates):
        candidate_pairs = []
        for namespace, tag in tag_candidates:
            annual_entries = self._annual_entries(payload, namespace, tag)
            if len(annual_entries) >= 2:
                candidate_pairs.append((annual_entries[0], annual_entries[1]))
        if not candidate_pairs:
            return None
        return max(candidate_pairs, key=lambda pair: pair[0]["end"])

    def _latest_annual_value(self, payload, tag_candidates, period_end=None):
        candidates = []
        for namespace, tag in tag_candidates:
            annual_entries = self._annual_entries(payload, namespace, tag)
            for entry in annual_entries:
                if period_end is None or entry["end"] == period_end:
                    candidates.append(entry)
        if not candidates:
            return None
        return max(candidates, key=lambda entry: (entry["end"], entry["filed"]))

    def _annual_entries(self, payload, namespace, tag):
        facts = payload.get("facts", {})
        fact = facts.get(namespace, {}).get(tag)
        if not fact:
            return []

        units = fact.get("units", {})
        entries = units.get("USD") or units.get("USD/shares") or []
        annual_entries = [
            {
                "fy": entry.get("fy"),
                "value": entry.get("val"),
                "filed": entry.get("filed", ""),
                "form": entry.get("form"),
                "start": entry.get("start"),
                "end": entry.get("end"),
                "tag": tag,
            }
            for entry in entries
            if entry.get("form") in ANNUAL_FORMS
            and entry.get("fp") == "FY"
            and isinstance(entry.get("fy"), int)
            and isinstance(entry.get("val"), (int, float))
            and self._is_annual_duration(entry)
        ]

        by_period_end = {}
        for entry in annual_entries:
            current = by_period_end.get(entry["end"])
            if current is None or entry["filed"] > current["filed"]:
                by_period_end[entry["end"]] = entry

        return [
            by_period_end[period_end]
            for period_end in sorted(by_period_end, reverse=True)
        ]

    def _is_annual_duration(self, entry):
        start = entry.get("start")
        end = entry.get("end")
        if not start or not end:
            return False
        try:
            return (date.fromisoformat(end) - date.fromisoformat(start)).days >= 300
        except ValueError:
            return False

    def _growth_rate(self, pair, require_positive_prior=False):
        if not pair:
            return None
        current, prior = pair
        prior_value = prior["value"]
        if prior_value == 0 or (require_positive_prior and prior_value <= 0):
            return None
        return ((current["value"] - prior_value) / abs(prior_value)) * 100

    def _metric_score(self, growth_rate, multiplier):
        return max(0, min(100, 50 + (growth_rate * multiplier)))

    def _round_optional(self, value):
        return round(value, 2) if value is not None else None
