import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.paper_trading import PaperTradingAccount


class PaperTradingAccountTests(unittest.TestCase):
    def make_account(self, temp_dir, policy=None):
        return PaperTradingAccount(
            account_file=Path(temp_dir) / "account.json",
            ledger_file=Path(temp_dir) / "ledger.jsonl",
            policy=policy,
            clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
        )

    def test_initialize_creates_account_and_ledger_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)

            state = account.initialize(100000)
            ledger = account.ledger()

        self.assertEqual(state["cash"], 100000)
        self.assertEqual(ledger[0]["event"], "account_initialized")

    def test_buy_and_sell_update_average_cost_and_realized_gain(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 50.0},
            )
            account.initialize(100000)

            account.execute_order("buy", "NVDA", 100, 100, "Initial thesis.")
            account.execute_order("buy", "NVDA", 50, 120, "Add after confirmation.")
            sell = account.execute_order("sell", "NVDA", 50, 130, "Trim after target.")
            state = account.load()

        self.assertAlmostEqual(state["positions"]["NVDA"]["average_cost"], 106.666666, places=5)
        self.assertEqual(state["positions"]["NVDA"]["shares"], 100)
        self.assertAlmostEqual(sell["realized_gain_loss"], 1166.67, places=2)
        self.assertAlmostEqual(state["realized_gain_loss"], 1166.666666, places=5)

    def test_rejects_margin_short_and_position_limit_violations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.initialize(100000)

            position_limit = account.preview_order("buy", "NVDA", 250, 100, "Too large.")
            margin = account.preview_order("buy", "NVDA", 1100, 100, "Too expensive.")
            short = account.preview_order("sell", "NVDA", 1, 100, "No holding.")

        self.assertFalse(position_limit["valid"])
        self.assertTrue(any("position limit" in error for error in position_limit["errors"]))
        self.assertTrue(any("margin is disabled" in error for error in margin["errors"]))
        self.assertTrue(any("short selling is disabled" in error for error in short["errors"]))

    def test_rejects_cash_reserve_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 100.0},
            )
            account.initialize(100000)

            result = account.preview_order("buy", "SPY", 950, 100, "Reserve breach.")

        self.assertFalse(result["valid"])
        self.assertTrue(any("cash reserve" in error for error in result["errors"]))

    def test_daily_trade_limit_uses_append_only_ledger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(
                temp_dir,
                policy={"maximum_position_pct": 100.0, "maximum_daily_trades": 2},
            )
            account.initialize(100000)
            account.execute_order("buy", "AAA", 1, 100, "One.")
            account.execute_order("buy", "BBB", 1, 100, "Two.")

            result = account.preview_order("buy", "CCC", 1, 100, "Three.")

        self.assertFalse(result["valid"])
        self.assertIn("maximum daily paper-trade count reached", result["errors"])

    def test_status_marks_positions_without_prices_as_unvalued(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir, policy={"maximum_position_pct": 50.0})
            account.initialize(100000)
            account.execute_order("buy", "NVDA", 10, 100, "Test.")

            status = account.status()

        self.assertEqual(status["market_value"], 0)
        self.assertIsNone(status["positions"][0]["market_value"])


if __name__ == "__main__":
    unittest.main()
