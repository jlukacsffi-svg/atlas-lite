"""Tests for automated Atlas fundamental Quality measurement."""

import unittest

from app.growth import NET_INCOME_TAGS, REVENUE_TAGS
from app.quality import CAPEX_TAGS, OPERATING_CASH_FLOW_TAGS, QualityEngine


class QualityEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = QualityEngine()

    def test_score_uses_profitability_and_cash_generation(self):
        score = self.engine.calculate_score(
            net_margin=20.0,
            operating_cash_flow_margin=30.0,
            free_cash_flow_margin=20.0,
        )

        self.assertEqual(score, 91.8)

    def test_score_renormalizes_when_metrics_are_missing(self):
        self.assertEqual(self.engine.calculate_score(10.0, None, None), 70.0)
        self.assertIsNone(self.engine.calculate_score(None, None, None))

    def test_score_is_bounded_between_zero_and_one_hundred(self):
        self.assertEqual(self.engine.calculate_score(100.0, 100.0, 100.0), 100.0)
        self.assertEqual(self.engine.calculate_score(-100.0, -100.0, -100.0), 0.0)

    def test_metrics_use_the_same_annual_period_as_revenue(self):
        payload = self._company_facts(
            revenue_entries=[
                self._entry(2024, 100, "2025-01-01", "2024-12-31"),
                self._entry(2025, 200, "2026-01-01", "2025-12-31"),
            ],
            net_income_entries=[
                self._entry(2024, 10, "2025-01-01", "2024-12-31"),
                self._entry(2025, 40, "2026-01-01", "2025-12-31"),
            ],
            operating_cash_flow_entries=[
                self._entry(2024, 20, "2025-01-01", "2024-12-31"),
                self._entry(2025, 60, "2026-01-01", "2025-12-31"),
            ],
            capex_entries=[
                self._entry(2024, 5, "2025-01-01", "2024-12-31"),
                self._entry(2025, 20, "2026-01-01", "2025-12-31"),
            ],
        )

        metrics = self.engine.metrics_from_payload(payload)

        self.assertEqual(metrics["net_margin"], 20.0)
        self.assertEqual(metrics["operating_cash_flow_margin"], 30.0)
        self.assertEqual(metrics["free_cash_flow_margin"], 20.0)
        self.assertEqual(metrics["latest_fiscal_year"], 2025)
        self.assertEqual(metrics["period_end"], "2025-12-31")
        self.assertEqual(metrics["source"], "sec_companyfacts")

    def _company_facts(
        self,
        revenue_entries=None,
        net_income_entries=None,
        operating_cash_flow_entries=None,
        capex_entries=None,
    ):
        return {
            "facts": {
                "us-gaap": {
                    REVENUE_TAGS[0][1]: {"units": {"USD": revenue_entries or []}},
                    NET_INCOME_TAGS[0][1]: {"units": {"USD": net_income_entries or []}},
                    OPERATING_CASH_FLOW_TAGS[0][1]: {
                        "units": {"USD": operating_cash_flow_entries or []}
                    },
                    CAPEX_TAGS[0][1]: {"units": {"USD": capex_entries or []}},
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
