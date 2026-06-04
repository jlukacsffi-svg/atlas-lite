import unittest

from app.report_generator import ReportGenerator


class ReportInsiderTransactionsTests(unittest.TestCase):
    def test_report_includes_insider_transactions_section(self):
        generator = ReportGenerator(
            market_data={},
            market_summary={},
            insider_transactions=[
                {
                    "transaction_date": "2026-05-27",
                    "ticker": "NVDA",
                    "owner_name": "Dabiri John",
                    "owner_title": "Director",
                    "transaction_label": "Sale",
                    "acquired_disposed": "D",
                    "shares": 625,
                    "price": 214,
                    "total_value": 133750,
                    "filing_url": "https://www.sec.gov/example",
                }
            ],
        )

        section = generator._generate_insider_transactions()

        self.assertIn("## Insider Transactions", section)
        self.assertIn("| 2026-05-27 | NVDA | Dabiri John (Director) | Sale | D | 625 | $214.00 | $133,750 |", section)
        self.assertIn("[SEC filing](https://www.sec.gov/example)", section)

    def test_report_handles_empty_insider_transactions(self):
        generator = ReportGenerator(market_data={}, market_summary={})

        section = generator._generate_insider_transactions()

        self.assertIn("No recent SEC Form 4 transactions found for the Atlas universe.", section)


if __name__ == "__main__":
    unittest.main()
