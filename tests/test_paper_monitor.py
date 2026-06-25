import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from app.paper_monitor import PaperPositionMonitor
from app.paper_trading import PaperTradingAccount


def steady_clock(*times):
    dates = list(times)
    last = dates[-1]

    def clock():
        return dates.pop(0) if dates else last

    return clock


def security(score=90, price=100, category="Core"):
    return {
        "status": "available",
        "price": price,
        "percent_change": 1.0,
        "sector": "AI & Semiconductors",
        "category": category,
        "scores": {
            "growth": score,
            "quality": score,
            "moat": score,
            "momentum": score,
            "risk": score,
        },
    }


class PaperPositionMonitorTests(unittest.TestCase):
    def make_account_with_position(self, temp_dir):
        account = PaperTradingAccount(
            account_file=Path(temp_dir) / "account.json",
            ledger_file=Path(temp_dir) / "ledger.jsonl",
            clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
        )
        account.initialize(100000)
        proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
        account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
        account.decide_proposal(proposal["proposal_id"], "approve")
        account.execute_order(
            "buy",
            "NVDA",
            10,
            100,
            "Entry.",
            proposal_id=proposal["proposal_id"],
        )
        return account

    def test_healthy_position_receives_maintain_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=105)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "maintain")
        self.assertEqual(result["exit_proposals"], [])

    def test_weak_score_creates_exit_proposal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=55, price=95)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertEqual(result["exit_proposals"][0]["side"], "sell")
        self.assertEqual(result["exit_proposals"][0]["shares"], 10)
        self.assertEqual(
            result["exit_proposals"][0]["source"],
            "paper_monitor_v1",
        )

    def test_drawdown_creates_review_without_exit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=85)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "review")
        self.assertEqual(result["exit_proposals"], [])

    def test_position_is_reviewed_only_once_per_day(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account_with_position(temp_dir)
            monitor = PaperPositionMonitor()
            market_data = {"NVDA": security(score=90, price=105)}

            first = monitor.review(account, market_data)
            second = monitor.review(account, market_data)

        self.assertEqual(len(first["reviews"]), 1)
        self.assertEqual(second["reviews"], [])

    def test_benchmark_lag_creates_review_without_trim(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 7, 0, 0),
                ),
            )
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 99},
                benchmark_prices={"SPY": 520, "QQQ": 416},
            )

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=99)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "review")
        self.assertIn("Benchmark review triggered", result["reviews"][0]["flags"][0])
        self.assertEqual(result["exit_proposals"], [])

    def test_severe_benchmark_lag_creates_trim_proposal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=steady_clock(
                    datetime(2026, 6, 1, 9, 30, 0),
                    datetime(2026, 6, 1, 9, 31, 0),
                    datetime(2026, 6, 1, 9, 32, 0),
                    datetime(2026, 6, 1, 9, 33, 0),
                    datetime(2026, 6, 1, 9, 34, 0),
                    datetime(2026, 6, 1, 16, 0, 0),
                    datetime(2026, 6, 2, 16, 0, 0),
                    datetime(2026, 6, 3, 7, 0, 0),
                    datetime(2026, 6, 3, 7, 1, 0),
                ),
            )
            account.initialize(100000)
            proposal = account.create_proposal("buy", "NVDA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"NVDA": 94},
                benchmark_prices={"SPY": 525, "QQQ": 420},
            )

            result = PaperPositionMonitor().review(
                account,
                {"NVDA": security(score=90, price=94)},
            )

        self.assertEqual(result["reviews"][0]["verdict"], "exit")
        self.assertIn("Trim rule triggered", result["reviews"][0]["flags"][0])
        self.assertEqual(result["exit_proposals"][0]["side"], "sell")
        self.assertEqual(result["exit_proposals"][0]["shares"], 5)


if __name__ == "__main__":
    unittest.main()
