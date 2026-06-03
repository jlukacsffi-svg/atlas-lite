"""Tests for the structured Atlas security universe."""

import json
import tempfile
import unittest
from pathlib import Path

from app.security_universe import SecurityUniverse


class SecurityUniverseTests(unittest.TestCase):
    def test_default_universe_loads_current_watchlist(self):
        universe = SecurityUniverse()

        self.assertEqual(universe.version, "1.0")
        self.assertEqual(len(universe.tickers()), 17)
        self.assertIn("NVDA", universe.tickers())
        self.assertEqual(universe.get("NVDA")["category"], "Core")
        self.assertEqual(universe.get("CRWD")["sector"], "Cybersecurity")

    def test_avoid_securities_are_excluded_by_default(self):
        universe = self._load_temp_universe(
            [
                self._security("AAA", "Core"),
                self._security("BBB", "Avoid"),
            ]
        )

        self.assertEqual(universe.tickers(), ["AAA"])
        self.assertEqual(universe.tickers(include_avoid=True), ["AAA", "BBB"])

    def test_duplicate_tickers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate ticker"):
            self._load_temp_universe(
                [
                    self._security("AAA", "Core"),
                    self._security("aaa", "Watchlist"),
                ]
            )

    def test_invalid_category_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid category"):
            self._load_temp_universe([self._security("AAA", "Unknown")])

    def _load_temp_universe(self, securities):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "security_universe.json"
        path.write_text(
            json.dumps({"version": "test", "securities": securities}),
            encoding="utf-8",
        )
        return SecurityUniverse(path)

    def _security(self, ticker, category):
        return {
            "ticker": ticker,
            "company_name": f"{ticker} Company",
            "sector": "Test Sector",
            "category": category,
            "notes": "Test notes",
        }


if __name__ == "__main__":
    unittest.main()
