"""Tests for split-aware Atlas historical comparisons."""

import unittest

from app.corporate_actions import describe_splits, normalize_prior_price


class CorporateActionTests(unittest.TestCase):
    def test_forward_split_adjusts_pre_split_price(self):
        adjusted, splits = normalize_prior_price(
            2500.0,
            "2026-06-08T12:00:00",
            {
                "momentum_metrics": {
                    "recent_splits": [
                        {
                            "date": "2026-06-12T13:30:00+00:00",
                            "ratio": 10.0,
                            "split_ratio": "10:1",
                        }
                    ]
                }
            },
        )

        self.assertEqual(adjusted, 250.0)
        self.assertEqual(len(splits), 1)

    def test_split_before_prior_snapshot_is_not_reapplied(self):
        adjusted, splits = normalize_prior_price(
            250.0,
            "2026-06-13T12:00:00",
            {
                "momentum_metrics": {
                    "recent_splits": [
                        {
                            "date": "2026-06-12T13:30:00+00:00",
                            "ratio": 10.0,
                            "split_ratio": "10:1",
                        }
                    ]
                }
            },
        )

        self.assertEqual(adjusted, 250.0)
        self.assertEqual(splits, [])

    def test_description_preserves_ratio_and_date(self):
        descriptions = describe_splits(
            "KLAC",
            [
                {
                    "date": "2026-06-12T13:30:00+00:00",
                    "ratio": 10.0,
                    "split_ratio": "10:1",
                }
            ],
        )

        self.assertEqual(descriptions, ["KLAC 10:1 on 2026-06-12"])


if __name__ == "__main__":
    unittest.main()
