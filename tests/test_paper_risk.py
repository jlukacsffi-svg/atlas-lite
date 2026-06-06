import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.paper_risk import PaperRiskReviewer
from app.paper_trading import PaperTradingAccount


def security(change, score=90, sector="AI & Semiconductors"):
    return {
        "status": "available",
        "price": 100,
        "percent_change": change,
        "sector": sector,
        "category": "Watchlist",
        "scores": {
            "growth": score,
            "quality": score,
            "moat": score,
            "momentum": score,
            "risk": score,
        },
    }


class PaperRiskReviewerTests(unittest.TestCase):
    def make_account(self, temp_dir):
        account = PaperTradingAccount(
            account_file=Path(temp_dir) / "account.json",
            ledger_file=Path(temp_dir) / "ledger.jsonl",
            clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
        )
        account.initialize(100000)
        return account

    def test_sharp_downside_produces_hold_verdict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")

            reviews = PaperRiskReviewer().review_pending(
                account,
                {"AAA": security(-9.0)},
            )
            status = account.proposal_status(proposal["proposal_id"])

        self.assertEqual(reviews[0]["verdict"], "hold")
        self.assertTrue(any("Sharp downside move" in flag for flag in reviews[0]["flags"]))
        self.assertEqual(status, "rejected")

    def test_sector_concentration_produces_caution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            for ticker in ["AAA", "BBB", "CCC"]:
                account.create_proposal("buy", ticker, 40, 100, "Entry.")

            reviews = PaperRiskReviewer().review_pending(
                account,
                {
                    "AAA": security(1.0),
                    "BBB": security(1.0),
                    "CCC": security(1.0),
                },
            )

        self.assertTrue(all(review["verdict"] == "caution" for review in reviews))
        self.assertTrue(
            any("Proposal concentration" in flag for flag in reviews[0]["flags"])
        )

    def test_clear_review_allows_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            PaperRiskReviewer().review_pending(
                account,
                {"AAA": security(1.0, sector="Software")},
            )

            decision = account.decide_proposal(proposal["proposal_id"], "approve")

        self.assertEqual(decision["decision"], "approve")

    def test_hold_enforcement_can_be_disabled_for_review_testing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")

            PaperRiskReviewer().review_pending(
                account,
                {"AAA": security(-9.0)},
                enforce_holds=False,
            )
            status = account.proposal_status(proposal["proposal_id"])

        self.assertEqual(status, "pending")


if __name__ == "__main__":
    unittest.main()
