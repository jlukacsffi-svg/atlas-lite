import unittest

from app.report_generator import ReportGenerator


class ReportPaperTradingTests(unittest.TestCase):
    def test_paper_section_explains_dormant_account(self):
        generator = ReportGenerator({}, {}, paper_summary={"configured": False})

        section = generator._generate_paper_performance()

        self.assertIn("## Paper Trading Performance", section)
        self.assertIn("No simulated paper account", section)
        self.assertIn("No brokerage connection exists", section)

    def test_paper_section_renders_benchmark_comparison(self):
        generator = ReportGenerator(
            {},
            {},
            paper_summary={
                "configured": True,
                "available": True,
                "snapshots": 3,
                "latest": {
                    "equity": 101000,
                    "total_return_pct": 1.0,
                    "realized_gain_loss": 200,
                    "unrealized_gain_loss": 800,
                    "benchmark_returns_pct": {"QQQ": 2.0, "SPY": 0.5},
                },
                "excess_return_pct": {"QQQ": -1.0, "SPY": 0.5},
                "trade_statistics": {
                    "recommendations": 3,
                    "trades": 2,
                    "wins": 1,
                    "losses": 0,
                    "proposal_statuses": {"pending": 1},
                },
                "pending_proposals": [
                    {
                        "proposal_id": "proposal_test",
                        "side": "buy",
                        "ticker": "NVDA",
                        "shares": 10,
                        "price": 150,
                        "source": "paper_strategy_v1",
                        "thesis": "High Atlas score.",
                        "risk_review": {
                            "verdict": "caution",
                            "flags": ["Elevated daily volatility."],
                        },
                    }
                ],
                "position_reviews": {
                    "NVDA": {
                        "verdict": "maintain",
                        "return_pct": 2.5,
                        "atlas_score": 89.7,
                        "flags": [],
                        "thesis": "NVDA thesis remains intact.",
                    }
                },
            },
        )

        section = generator._generate_paper_performance()

        self.assertIn("$101,000.00", section)
        self.assertIn("| QQQ | +2.00% | -1.00% |", section)
        self.assertIn("| SPY | +0.50% | +0.50% |", section)
        self.assertIn("Recommendations / Simulated Trades", section)
        self.assertIn("Pending Paper Proposals", section)
        self.assertIn("| proposal_test | Buy | NVDA | 10 | $150.00 | Caution |", section)
        self.assertIn("Elevated daily volatility.", section)
        self.assertIn("cannot execute without a separate simulation approval", section)
        self.assertIn("Open Position Thesis Reviews", section)
        self.assertIn("| NVDA | Maintain | +2.50% | 89.7 |", section)
        self.assertIn("Simulated performance only", section)

    def test_defensive_review_section_renders_recent_transition_digest(self):
        generator = ReportGenerator(
            {},
            {},
            paper_summary={
                "prospective_review_tracker": {
                    "available": True,
                    "activated": True,
                    "recent_transitions": [
                        {
                            "ticker": "TSM",
                            "status": "persistent_weakness",
                            "status_label": "Weakness persists",
                            "latest_return_pct": -4.25,
                            "latest_lag_pct": -5.75,
                            "snapshots_observed": 3,
                        },
                        {
                            "ticker": "AMD",
                            "status": "recovered",
                            "status_label": "Recovered above trigger",
                            "latest_return_pct": -1.25,
                            "latest_lag_pct": -2.0,
                            "snapshots_observed": 4,
                        },
                    ],
                }
            },
        )

        section = generator._generate_paper_review_evidence()

        self.assertIn("## Defensive Review Evidence", section)
        self.assertIn(
            "| TSM | Weakness persists | -4.25% | -5.75% | 3 |",
            section,
        )
        self.assertIn(
            "| AMD | Recovered above trigger | -1.25% | -2.00% | 4 |",
            section,
        )
        self.assertIn("do not change policy", section)
        self.assertIn("only the latest state", section)

    def test_defensive_review_section_explains_forward_start(self):
        generator = ReportGenerator(
            {},
            {},
            paper_summary={
                "prospective_review_tracker": {
                    "available": True,
                    "activated": False,
                    "recent_transitions": [],
                }
            },
        )

        section = generator._generate_paper_review_evidence()

        self.assertIn("starts with the next scheduled paper snapshot", section)
        self.assertNotIn("| Ticker |", section)


if __name__ == "__main__":
    unittest.main()
