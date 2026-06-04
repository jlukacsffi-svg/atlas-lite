import unittest

from app.report_generator import ReportGenerator


class ReportEarningsTests(unittest.TestCase):
    def test_report_includes_upcoming_earnings_section(self):
        generator = ReportGenerator(
            market_data={},
            market_summary={},
            earnings_events=[
                {
                    "date": "2026-06-03",
                    "ticker": "AVGO",
                    "company_name": "Broadcom Inc.",
                    "time": "After hours",
                    "fiscal_quarter_ending": "Apr/2026",
                    "eps_forecast": "$1.57",
                    "last_year_eps": "$1.10",
                }
            ],
        )

        section = generator._generate_upcoming_earnings()

        self.assertIn("## Upcoming Earnings", section)
        self.assertIn("| 2026-06-03 | AVGO | Broadcom Inc. | After hours |", section)

    def test_report_handles_empty_earnings_calendar(self):
        generator = ReportGenerator(market_data={}, market_summary={})

        section = generator._generate_upcoming_earnings()

        self.assertIn("No Atlas universe earnings events found in the next 7 days.", section)


if __name__ == "__main__":
    unittest.main()
