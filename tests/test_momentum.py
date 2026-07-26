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

    def test_extract_closes_prefers_split_adjusted_history(self):
        closes = self.engine._extract_closes(
            {
                "chart": {
                    "result": [
                        {
                            "indicators": {
                                "quote": [{"close": [1000.0, 110.0]}],
                                "adjclose": [{"adjclose": [100.0, 110.0]}],
                            }
                        }
                    ]
                }
            }
        )

        self.assertEqual(closes, [100.0, 110.0])

    def test_extract_splits_returns_dated_auditable_ratios(self):
        splits = self.engine._extract_splits(
            {
                "chart": {
                    "result": [
                        {
                            "events": {
                                "splits": {
                                    "1781271000": {
                                        "date": 1781271000,
                                        "numerator": 10.0,
                                        "denominator": 1.0,
                                        "splitRatio": "10:1",
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        )

        self.assertEqual(splits[0]["ratio"], 10.0)
        self.assertEqual(splits[0]["split_ratio"], "10:1")
        self.assertEqual(splits[0]["source"], "yahoo_chart_event")

    def test_return_from_period_uses_trading_day_lookback(self):
        closes = [100.0] * 21 + [110.0]

        self.assertAlmostEqual(self.engine._return_from_period(closes, 21), 10.0)

    def test_trend_quality_score_rewards_persistent_uptrend(self):
        closes = [100 + index for index in range(260)]

        trend_quality = self.engine._trend_quality_score(
            current=closes[-1],
            return_1m=self.engine._return_from_period(closes, 21),
            return_3m=self.engine._return_from_period(closes, 63),
            return_6m=self.engine._return_from_period(closes, 126),
            return_12m=self.engine._return_from_period(closes, 252),
            sma_20=self.engine._simple_moving_average(closes, 20),
            sma_50=self.engine._simple_moving_average(closes, 50),
            sma_200=self.engine._simple_moving_average(closes, 200),
            rsi_14=self.engine._rsi(closes, 14),
            distance_from_52w_high=self.engine._distance_from_high(closes, 252),
            volatility_20d=self.engine._volatility(closes, 20),
        )

        self.assertGreaterEqual(trend_quality, 75.0)

    def test_composite_momentum_blends_legacy_and_trend_scores(self):
        self.assertEqual(self.engine._composite_momentum_score(60.0, 80.0), 71.0)

    def test_trend_state_marks_downtrend_when_price_loses_key_averages(self):
        state = self.engine._trend_state(
            current=90.0,
            sma_20=95.0,
            sma_50=100.0,
            sma_200=110.0,
            rsi_14=35.0,
        )

        self.assertEqual(state, "downtrend")

    def test_trend_regime_score_rewards_constructive_structure(self):
        regime_score = self.engine._trend_regime_score(
            trend_quality_score=78.0,
            ema_20_slope=2.0,
            price_vs_sma_50=4.0,
            price_vs_sma_200=10.0,
            sma_50_vs_sma_200=6.0,
            drawdown_63d=-3.0,
        )

        self.assertGreaterEqual(regime_score, 82.0)
        self.assertEqual(self.engine._trend_regime(regime_score), "leadership")

    def test_trend_regime_marks_breakdown_when_structure_is_weak(self):
        regime_score = self.engine._trend_regime_score(
            trend_quality_score=35.0,
            ema_20_slope=-2.0,
            price_vs_sma_50=-6.0,
            price_vs_sma_200=-15.0,
            sma_50_vs_sma_200=-8.0,
            drawdown_63d=-20.0,
        )

        self.assertLess(regime_score, 38.0)
        self.assertEqual(self.engine._trend_regime(regime_score), "breakdown")


if __name__ == "__main__":
    unittest.main()
