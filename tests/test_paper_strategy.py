import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.paper_strategy import PaperStrategy
from app.paper_trading import PaperTradingAccount


def market_security(score, price=100, category="Watchlist", change=1.0):
    return {
        "status": "available",
        "price": price,
        "percent_change": change,
        "sector": "Software",
        "category": category,
        "scores": {
            "growth": score,
            "quality": score,
            "moat": score,
            "momentum": score,
            "risk": score,
        },
    }


class PaperStrategyTests(unittest.TestCase):
    def make_account(self, temp_dir):
        account = PaperTradingAccount(
            account_file=Path(temp_dir) / "account.json",
            ledger_file=Path(temp_dir) / "ledger.jsonl",
            clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
        )
        account.initialize(100000)
        return account

    def test_generates_top_three_pending_buy_proposals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy()
            market_data = {
                "AAA": market_security(95),
                "BBB": market_security(93, price=200),
                "CCC": market_security(91, price=250),
                "DDD": market_security(89),
                "LOW": market_security(70),
                "SPY": {
                    **market_security(99),
                    "sector": "Benchmark ETF",
                },
            }

            created = strategy.generate(account, market_data)
            proposals = account.proposals()

        self.assertEqual([item["ticker"] for item in created], ["AAA", "BBB", "CCC"])
        self.assertTrue(all(item["status"] == "pending" for item in proposals))
        self.assertEqual(created[0]["shares"], 50)

    def test_deduplicates_pending_proposals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy()
            market_data = {"AAA": market_security(95)}

            first = strategy.generate(account, market_data)
            second = strategy.generate(account, market_data)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_generates_exit_for_held_name_below_threshold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "AAA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            strategy = PaperStrategy()

            created = strategy.generate(
                account,
                {"AAA": market_security(55, price=90)},
            )

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["side"], "sell")
        self.assertEqual(created[0]["shares"], 10)

    def test_avoid_category_never_creates_buy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy()

            created = strategy.generate(
                account,
                {"AAA": market_security(99, category="Avoid")},
            )

        self.assertEqual(created, [])


if __name__ == "__main__":
    unittest.main()
