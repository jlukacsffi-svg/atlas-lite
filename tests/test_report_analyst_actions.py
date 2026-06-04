import unittest

from app.report_generator import ReportGenerator


class ReportAnalystActionsTests(unittest.TestCase):
    def test_report_includes_analyst_actions_section(self):
        generator = ReportGenerator(
            market_data={},
            market_summary={},
            analyst_actions=[
                {
                    "ticker": "NVDA",
                    "action_type": "Price target raised",
                    "title": "Nvidia price target raised | by analyst",
                    "publisher": "MarketWatch",
                    "url": "https://example.com/nvda-target",
                }
            ],
        )

        section = generator._generate_analyst_actions()

        self.assertIn("## Analyst Actions", section)
        self.assertIn("Price target raised", section)
        self.assertIn("[Nvidia price target raised / by analyst](https://example.com/nvda-target)", section)

    def test_report_handles_empty_analyst_actions(self):
        generator = ReportGenerator(market_data={}, market_summary={})

        section = generator._generate_analyst_actions()

        self.assertIn("No recent analyst-action headlines found for the Atlas universe.", section)


if __name__ == "__main__":
    unittest.main()
