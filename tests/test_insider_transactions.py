import tempfile
import unittest
from datetime import date

from app.insider_transactions import InsiderTransactionTracker


class InsiderTransactionTrackerTests(unittest.TestCase):
    def sample_submissions(self):
        return {
            "filings": {
                "recent": {
                    "form": ["4", "10-Q", "4"],
                    "accessionNumber": [
                        "0001818224-26-000004",
                        "0000000000-26-000001",
                        "0001818224-26-000001",
                    ],
                    "filingDate": ["2026-05-29", "2026-05-28", "2026-05-01"],
                    "reportDate": ["2026-05-27", "2026-05-28", "2026-04-29"],
                    "primaryDocument": [
                        "xslF345X06/wk-form4_1780087807.xml",
                        "nvda-20260528.htm",
                        "old-form4.xml",
                    ],
                }
            }
        }

    def sample_form4_xml(self):
        return """<?xml version="1.0"?>
<ownershipDocument>
  <issuer>
    <issuerTradingSymbol>NVDA</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerName>Dabiri John</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <officerTitle>Director</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <transactionDate><value>2026-05-27</value></transactionDate>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>625</value></transactionShares>
        <transactionPricePerShare><value>214</value></transactionPricePerShare>
        <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""

    def test_recent_form4_filings_filters_by_form_and_lookback(self):
        tracker = InsiderTransactionTracker(cache_dir=tempfile.mkdtemp())

        filings = tracker._recent_form4_filings(
            self.sample_submissions(),
            cutoff=date(2026, 5, 20),
        )

        self.assertEqual(len(filings), 1)
        self.assertEqual(filings[0]["accession_number"], "0001818224-26-000004")
        self.assertEqual(filings[0]["report_date"], "2026-05-27")

    def test_parse_form4_xml_extracts_transaction_details(self):
        tracker = InsiderTransactionTracker(cache_dir=tempfile.mkdtemp())
        filing = {
            "accession_number": "0001818224-26-000004",
            "filing_date": "2026-05-29",
            "report_date": "2026-05-27",
        }

        transactions = tracker._parse_form4_xml(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            cik="0001045810",
            filing=filing,
            xml_text=self.sample_form4_xml(),
        )

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["owner_name"], "Dabiri John")
        self.assertEqual(transactions[0]["owner_title"], "Director")
        self.assertEqual(transactions[0]["transaction_label"], "Sale")
        self.assertEqual(transactions[0]["shares"], 625)
        self.assertEqual(transactions[0]["price"], 214)
        self.assertEqual(transactions[0]["total_value"], 133750)
        self.assertEqual(transactions[0]["source"], "sec_form4")

    def test_fetch_transactions_skips_etfs_and_sorts_recent_events(self):
        tracker = InsiderTransactionTracker(cache_dir=tempfile.mkdtemp())
        tracker.growth_engine._get_cik = lambda ticker: "0001045810"
        tracker._fetch_submissions = lambda cik: self.sample_submissions()
        tracker._fetch_filing_transactions = lambda ticker, company_name, cik, filing: [
            {
                "ticker": ticker,
                "transaction_date": filing["report_date"],
                "transaction_label": "Sale",
            }
        ]
        market_data = {
            "NVDA": {"company_name": "NVIDIA Corporation", "sector": "AI & Semiconductors"},
            "SPY": {"company_name": "SPDR S&P 500 ETF Trust", "sector": "Benchmark ETF"},
        }

        transactions = tracker.fetch_transactions(
            market_data,
            today=date(2026, 6, 3),
            lookback_days=14,
        )

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["ticker"], "NVDA")


if __name__ == "__main__":
    unittest.main()
