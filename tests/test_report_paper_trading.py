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
        self.assertIn("Simulated performance only", section)


if __name__ == "__main__":
    unittest.main()
