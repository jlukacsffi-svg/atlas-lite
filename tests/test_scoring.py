"""Tests for Atlas Scoring Engine v1."""

import unittest

from app.scoring import ScoringEngine


class ScoringEngineTests(unittest.TestCase):
    def test_weighted_score_uses_v1_weights(self):
        engine = ScoringEngine()

        total = engine.score(
            {
                "growth": 100,
                "quality": 80,
                "moat": 60,
                "momentum": 40,
                "risk": 20,
            }
        )

        self.assertEqual(total, 73.0)

    def test_missing_component_is_rejected(self):
        engine = ScoringEngine()

        with self.assertRaisesRegex(ValueError, "Missing scoring components"):
            engine.score(
                {
                    "growth": 50,
                    "quality": 50,
                    "moat": 50,
                    "momentum": 50,
                }
            )

    def test_weights_must_sum_to_one(self):
        with self.assertRaisesRegex(ValueError, "sum to 1.0"):
            ScoringEngine({"growth": 0.5, "quality": 0.5, "risk": 0.5})


if __name__ == "__main__":
    unittest.main()
