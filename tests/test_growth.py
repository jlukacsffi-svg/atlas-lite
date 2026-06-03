"""Tests for automated Atlas fundamental Growth measurement."""

import unittest

from app.growth import GrowthEngine, NET_INCOME_TAGS, REVENUE_TAGS


class GrowthEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = GrowthEngine()

    def test_score_uses_revenue_as_primary_input(self):
        score = self.engine.calculate_score(revenue_growth=20.0, net_income_growth=40.0)

        self.assertEqual(score, 90.0)

    def test_score_renormalizes_when_only_revenue_is_available(self):
        self.assertEqual(self.engine.calculate_score(10.0, None), 70.0)
        self.assertIsNone(self.engine.calculate_score(None, None))

    def test_score_is_bounded_between_zero_and_one_hundred(self):
        self.assertEqual(self.engine.calculate_score(100.0, 100.0), 100.0)
        self.assertEqual(self.engine.calculate_score(-100.0, -100.0), 0.0)

    def test_latest_annual_pair_uses_latest_filing_for_each_year(self):
        payload = self._company_facts(
            revenue_entries=[
                self._entry(2024, 100, "2025-01-01", "2024-12-31"),
                self._entry(2025, 105, "2025-02-01", "2024-12-31"),
                self._entry(2025, 120, "2026-02-01", "2025-12-31"),
            ]
        )

        current, prior = self.engine._latest_annual_pair(payload, REVENUE_TAGS)

        self.assertEqual(current["fy"], 2025)
        self.assertEqual(current["value"], 120)
        self.assertEqual(prior["value"], 105)

    def test_latest_annual_pair_prefers_most_recent_supported_tag(self):
        older_tag = REVENUE_TAGS[0][1]
        newer_tag = REVENUE_TAGS[1][1]
        payload = {
            "facts": {
                "us-gaap": {
                    older_tag: {
                        "units": {
                            "USD": [
                                self._entry(2022, 100, "2023-01-01", "2022-12-31"),
                                self._entry(2023, 110, "2024-01-01", "2023-12-31"),
                            ]
                        }
                    },
                    newer_tag: {
                        "units": {
                            "USD": [
                                self._entry(2024, 120, "2025-01-01", "2024-12-31"),
                                self._entry(2025, 140, "2026-01-01", "2025-12-31"),
                            ]
                        }
                    },
                }
            }
        }

        current, prior = self.engine._latest_annual_pair(payload, REVENUE_TAGS)

        self.assertEqual(current["tag"], newer_tag)
        self.assertEqual(current["value"], 140)
        self.assertEqual(prior["value"], 120)

    def test_growth_rate_rejects_non_positive_prior_net_income(self):
        pair = (
            {"value": 10},
            {"value": -5},
        )

        self.assertIsNone(self.engine._growth_rate(pair, require_positive_prior=True))

    def test_fetch_metrics_builds_auditable_result(self):
        self.engine._ticker_ciks = {"AAA": "0000000001"}
        self.engine._fetch_json = lambda url: self._company_facts(
            revenue_entries=[
                self._entry(2024, 100, "2025-01-01", "2024-12-31"),
                self._entry(2025, 120, "2026-01-01", "2025-12-31"),
            ],
            net_income_entries=[
                self._entry(2024, 10, "2025-01-01", "2024-12-31"),
                self._entry(2025, 14, "2026-01-01", "2025-12-31"),
            ],
        )

        metrics = self.engine.fetch_metrics("AAA")

        self.assertEqual(metrics["growth_score"], 90.0)
        self.assertEqual(metrics["revenue_growth"], 20.0)
        self.assertEqual(metrics["net_income_growth"], 40.0)
        self.assertEqual(metrics["latest_fiscal_year"], 2025)
        self.assertEqual(metrics["source"], "sec_companyfacts")

    def _company_facts(self, revenue_entries=None, net_income_entries=None):
        revenue_tag = REVENUE_TAGS[0][1]
        net_income_tag = NET_INCOME_TAGS[0][1]
        return {
            "facts": {
                "us-gaap": {
                    revenue_tag: {"units": {"USD": revenue_entries or []}},
                    net_income_tag: {"units": {"USD": net_income_entries or []}},
                }
            }
        }

    def _entry(self, fiscal_year, value, filed, end):
        return {
            "fy": fiscal_year,
            "fp": "FY",
            "form": "10-K",
            "filed": filed,
            "val": value,
            "start": f"{end[:4]}-01-01",
            "end": end,
        }


if __name__ == "__main__":
    unittest.main()
