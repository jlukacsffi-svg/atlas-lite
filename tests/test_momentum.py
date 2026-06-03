"""Tests for automated Atlas momentum measurement."""

import unittest

from app.momentum import MomentumEngine


class MomentumEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = MomentumEngine()

    def test_score_uses_one_and_three_month_returns(self):
        score = self.engine.calculate_score(return_1m=10.0, return_3m=20.0)

        self.assertEqual(score, 80.0)

    def test_score_is_bounded_between_zero_and_one_hundred(self):
        self.assertEqual(self.engine.calculate_score(100.0, 100.0), 100)
        self.assertEqual(self.engine.calculate_score(-100.0, -100.0), 0)

    def test_missing_return_is_treated_as_neutral(self):
        self.assertEqual(self.engine.calculate_score(10.0, None), 65.0)
        self.assertIsNone(self.engine.calculate_score(None, None))

    def test_extract_closes_ignores_missing_values(self):
        closes = self.engine._extract_closes(
            {
                "chart": {
                    "result": [
                        {
                            "indicators": {
                                "quote": [{"close": [10.0, None, 12.5]}]
                            }
                        }
                    ]
                }
            }
        )

        self.assertEqual(closes, [10.0, 12.5])

    def test_return_from_period_uses_trading_day_lookback(self):
        closes = [100.0] * 21 + [110.0]

        self.assertAlmostEqual(self.engine._return_from_period(closes, 21), 10.0)


if __name__ == "__main__":
    unittest.main()
