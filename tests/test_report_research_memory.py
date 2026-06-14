"""Tests for split-aware research-memory reporting."""

import unittest

from app.report_generator import ReportGenerator


class ReportResearchMemoryTests(unittest.TestCase):
    def test_split_is_normalized_and_disclosed(self):
        generator = ReportGenerator(
            {
                "KLAC": {
                    "status": "available",
                    "price": 254.54,
                    "momentum_metrics": {
                        "recent_splits": [
                            {
                                "date": "2026-06-12T13:30:00+00:00",
                                "ratio": 10.0,
                                "split_ratio": "10:1",
                            }
                        ]
                    },
                }
            },
            market_summary={},
            previous_snapshot={
                "generated_at": "2026-06-08T12:00:00",
                "securities": {
                    "KLAC": {
                        "price": 2500.0,
                        "total_score": None,
                    }
                },
            },
        )

        section = generator._generate_research_memory()

        self.assertIn("Corporate-action normalization applied", section)
        self.assertIn("KLAC 10:1 on 2026-06-12", section)
        self.assertIn("KLAC**: +1.82%", section)
        self.assertNotIn("-89.82%", section)


if __name__ == "__main__":
    unittest.main()
