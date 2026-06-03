"""Security universe loading and validation for Atlas Lite."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_UNIVERSE_PATH = PROJECT_ROOT / "data" / "security_universe.json"
ALLOWED_CATEGORIES = {"Core", "Watchlist", "Emerging", "Avoid"}
SCORE_COMPONENTS = {"growth", "quality", "moat", "momentum", "risk"}
REQUIRED_FIELDS = {"ticker", "company_name", "sector", "category", "notes", "scores"}
PROFILE_FIELDS = {"thesis", "key_driver", "key_risk"}


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
            scores = security["scores"]
            profile = security.get("profile", {})

            if not ticker:
                raise ValueError(f"Security universe entry {index} has an empty ticker")
            if ticker in seen_tickers:
                raise ValueError(f"Duplicate ticker in security universe: {ticker}")
            if category not in ALLOWED_CATEGORIES:
                raise ValueError(
                    f"Invalid category for {ticker}: {category}. "
                    f"Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}"
                )
            if not isinstance(scores, dict):
                raise ValueError(f"Scores for {ticker} must be an object")
            if not isinstance(profile, dict):
                raise ValueError(f"Profile for {ticker} must be an object")

            missing_profile_fields = PROFILE_FIELDS - profile.keys()
            if missing_profile_fields:
                raise ValueError(
                    f"Profile for {ticker} is missing: "
                    f"{', '.join(sorted(missing_profile_fields))}"
                )

            missing_scores = SCORE_COMPONENTS - scores.keys()
            if missing_scores:
                raise ValueError(
                    f"Scores for {ticker} are missing: {', '.join(sorted(missing_scores))}"
                )

            normalized_scores = {}
            for component in sorted(SCORE_COMPONENTS):
                value = scores[component]
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise ValueError(f"Score {component} for {ticker} must be numeric")
                if not 0 <= value <= 100:
                    raise ValueError(f"Score {component} for {ticker} must be between 0 and 100")
                normalized_scores[component] = float(value)

            normalized_security = {
                "ticker": ticker,
                "company_name": str(security["company_name"]).strip(),
                "sector": str(security["sector"]).strip(),
                "category": category,
                "notes": str(security["notes"]).strip(),
                "profile": {
                    field: str(profile[field]).strip()
                    for field in sorted(PROFILE_FIELDS)
                },
                "scores": normalized_scores,
                "score_source": str(security.get("score_source", "manual_v1")).strip() or "manual_v1",
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
