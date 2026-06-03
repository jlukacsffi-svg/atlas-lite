"""Security universe loading and validation for Atlas Lite."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNIVERSE_PATH = PROJECT_ROOT / "data" / "security_universe.json"
ALLOWED_CATEGORIES = {"Core", "Watchlist", "Emerging", "Avoid"}
REQUIRED_FIELDS = {"ticker", "company_name", "sector", "category", "notes"}


class SecurityUniverse:
    """Load the structured Atlas security universe."""

    def __init__(self, path=DEFAULT_UNIVERSE_PATH):
        self.path = Path(path)
        self.version = None
        self.securities = []
        self._by_ticker = {}
        self._load()

    def _load(self):
        with open(self.path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        securities = payload.get("securities")
        if not isinstance(securities, list) or not securities:
            raise ValueError("Security universe must contain a non-empty 'securities' list")

        normalized = []
        seen_tickers = set()

        for index, security in enumerate(securities, start=1):
            if not isinstance(security, dict):
                raise ValueError(f"Security universe entry {index} must be an object")

            missing = REQUIRED_FIELDS - security.keys()
            if missing:
                raise ValueError(
                    f"Security universe entry {index} is missing: {', '.join(sorted(missing))}"
                )

            ticker = str(security["ticker"]).strip().upper()
            category = str(security["category"]).strip()

            if not ticker:
                raise ValueError(f"Security universe entry {index} has an empty ticker")
            if ticker in seen_tickers:
                raise ValueError(f"Duplicate ticker in security universe: {ticker}")
            if category not in ALLOWED_CATEGORIES:
                raise ValueError(
                    f"Invalid category for {ticker}: {category}. "
                    f"Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}"
                )

            normalized_security = {
                "ticker": ticker,
                "company_name": str(security["company_name"]).strip(),
                "sector": str(security["sector"]).strip(),
                "category": category,
                "notes": str(security["notes"]).strip(),
            }
            normalized.append(normalized_security)
            seen_tickers.add(ticker)

        self.version = str(payload.get("version", "")).strip() or "unversioned"
        self.securities = normalized
        self._by_ticker = {
            security["ticker"]: security
            for security in self.securities
        }

    def tickers(self, include_avoid=False):
        return [
            security["ticker"]
            for security in self.securities
            if include_avoid or security["category"] != "Avoid"
        ]

    def get(self, ticker):
        return self._by_ticker.get(str(ticker).strip().upper())

