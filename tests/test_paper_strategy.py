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


def market_security_with_trend(
    score,
    *,
    price=100,
    category="Watchlist",
    change=1.0,
    trend_quality_score=50.0,
    trend_state="unknown",
    trend_regime="unknown",
    trend_regime_score=50.0,
    return_1m=2.0,
    return_3m=6.0,
    return_6m=12.0,
    ema_20_slope_pct=1.0,
    price_vs_sma_20_pct=2.0,
    price_vs_sma_50_pct=3.0,
    drawdown_63d_pct=-4.0,
):
    return market_security(score, price=price, category=category, change=change) | {
        "momentum_metrics": {
            "trend_quality_score": trend_quality_score,
            "trend_state": trend_state,
            "trend_regime": trend_regime,
            "trend_regime_score": trend_regime_score,
            "return_1m": return_1m,
            "return_3m": return_3m,
            "return_6m": return_6m,
            "ema_20_slope_pct": ema_20_slope_pct,
            "price_vs_sma_20_pct": price_vs_sma_20_pct,
            "price_vs_sma_50_pct": price_vs_sma_50_pct,
            "drawdown_63d_pct": drawdown_63d_pct,
            "momentum_score": score,
        }
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
            recommendations = account.recommendations()

        self.assertEqual([item["ticker"] for item in created], ["AAA", "BBB", "CCC"])
        self.assertTrue(all(item["status"] == "pending" for item in proposals))
        self.assertEqual(created[0]["shares"], 50)
        self.assertEqual(len(recommendations), 3)
        self.assertTrue(all(item.get("recommendation_id") for item in created))
        self.assertIn("Atlas score 95.0", created[0]["rationale"][0])
        self.assertIn("versus SPY", recommendations[0]["thesis"])
        self.assertTrue(any("Why" not in item for item in created[0]["rationale"]))
        self.assertIn("buy threshold", recommendations[0]["rationale"][0])
        self.assertTrue(
            any(
                "outperforming the stronger benchmark" in line
                for line in recommendations[0]["rationale"]
            )
        )
        self.assertIn("routine mention", recommendations[0]["thesis"])

    def test_deduplicates_pending_proposals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy()
            market_data = {"AAA": market_security(95)}

            first = strategy.generate(account, market_data)
            second = strategy.generate(account, market_data)

        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])

    def test_existing_pending_proposals_count_against_daily_cap(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=3)
            account.create_proposal("buy", "AAA", 10, 100, "Existing.")
            account.create_proposal("buy", "BBB", 10, 100, "Existing.")

            created = strategy.generate(
                account,
                {
                    "AAA": market_security(99),
                    "BBB": market_security(98),
                    "CCC": market_security(97),
                    "DDD": market_security(96),
                },
            )

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["ticker"], "CCC")

    def test_entry_constraint_observation_compares_thresholds_without_proposals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(minimum_buy_score=88, maximum_new_proposals=2)
            observation = strategy.entry_constraint_observation(
                account,
                {
                    "AAA": market_security(91),
                    "BBB": market_security(88),
                    "CCC": market_security(87),
                    "DDD": market_security(86),
                    "SPY": {**market_security(99), "sector": "Benchmark ETF"},
                },
            )

        self.assertFalse(observation["policy_changed"])
        self.assertEqual(len(observation["scenarios"]), 3)
        self.assertEqual(observation["scenarios"][0]["eligible_ideas"], 2)
        self.assertGreaterEqual(observation["scenarios"][2]["eligible_ideas"], 2)
        self.assertEqual(account.proposals(), [])

    def test_entry_constraint_observation_records_confirmation_blocker_families(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(minimum_buy_score=88)
            observation = strategy.entry_constraint_observation(
                account,
                {
                    "AAA": market_security(91, change=-9.0),
                    "SPY": {**market_security(99), "sector": "Benchmark ETF"},
                },
            )

        self.assertEqual(observation["confirmation_blocked_candidates"], 1)
        self.assertEqual(observation["confirmation_blockers"]["daily_move"], 1)
        self.assertEqual(account.proposals(), [])

    def test_generates_exit_for_held_name_below_threshold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
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

    def test_sharp_downside_never_creates_buy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy()

            created = strategy.generate(
                account,
                {"AAA": market_security(99, change=-9.0)},
            )

        self.assertEqual(created, [])

    def test_limited_daily_change_never_creates_new_buy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy()
            security = market_security(99, change=4.0)
            security["daily_change_quality"] = "limited"
            benchmark = {
                **market_security(99, change=2.0),
                "sector": "Benchmark ETF",
                "daily_change_quality": "limited",
            }

            created = strategy.generate(
                account,
                {"AAA": security, "SPY": benchmark},
            )

        self.assertEqual(created, [])

    def test_limited_daily_change_does_not_hide_score_based_exit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "AAA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            security = market_security(55, price=90)
            security["daily_change_quality"] = "limited"

            created = PaperStrategy().generate(account, {"AAA": security})

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["side"], "sell")

    def test_prefers_sector_diversity_before_doubling_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy()
            market_data = {
                "AAA": market_security(95, change=3.0) | {"sector": "Software"},
                "BBB": market_security(94, change=2.8) | {"sector": "Software"},
                "CCC": market_security(92, change=2.7) | {"sector": "Healthcare"},
                "DDD": market_security(91, change=2.6) | {"sector": "Financials"},
                "SPY": {
                    **market_security(99, change=1.0),
                    "sector": "Benchmark ETF",
                },
                "QQQ": {
                    **market_security(99, change=1.5),
                    "sector": "Benchmark ETF",
                },
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA", "CCC", "DDD"])

    def test_prefers_benchmark_outperformer_when_scores_are_close(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security(90, change=3.5) | {"sector": "Software"},
                "BBB": market_security(91, change=1.6) | {"sector": "Healthcare"},
                "SPY": {
                    **market_security(99, change=1.0),
                    "sector": "Benchmark ETF",
                },
                "QQQ": {
                    **market_security(99, change=1.5),
                    "sector": "Benchmark ETF",
                },
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA"])

    def test_prefers_stronger_trend_quality_when_scores_are_close(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    91,
                    change=2.0,
                    trend_quality_score=82.0,
                    trend_state="uptrend",
                    trend_regime="leadership",
                    trend_regime_score=85.0,
                ) | {"sector": "Software"},
                "BBB": market_security_with_trend(
                    91,
                    change=2.0,
                    trend_quality_score=56.0,
                    trend_state="mixed",
                    trend_regime="fragile",
                    trend_regime_score=46.0,
                ) | {"sector": "Healthcare"},
                "SPY": {
                    **market_security(99, change=1.0),
                    "sector": "Benchmark ETF",
                },
                "QQQ": {
                    **market_security(99, change=1.2),
                    "sector": "Benchmark ETF",
                },
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA"])
        self.assertTrue(
            any(
                "Trend quality is 82.0" in line and "uptrend" in line
                for line in created[0]["rationale"]
            )
        )
        self.assertTrue(
            any("Sector rotation is" in line for line in created[0]["rationale"])
        )
        self.assertTrue(
            any("Follow-through score is" in line for line in created[0]["rationale"])
        )

    def test_prefers_sector_leader_when_scores_are_close(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    91,
                    change=1.9,
                    trend_quality_score=74.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=72.0,
                ) | {"sector": "Software"},
                "BBB": market_security_with_trend(
                    91,
                    change=1.9,
                    trend_quality_score=74.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=72.0,
                ) | {"sector": "Healthcare"},
                "CCC": market_security(88, change=2.8) | {"sector": "Software"},
                "DDD": market_security(84, change=0.1) | {"sector": "Healthcare"},
                "SPY": {
                    **market_security(99, change=1.0),
                    "sector": "Benchmark ETF",
                },
                "QQQ": {
                    **market_security(99, change=1.2),
                    "sector": "Benchmark ETF",
                },
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA"])
        self.assertTrue(
            any("Sector rotation is" in line for line in created[0]["rationale"])
        )

    def test_blocks_buy_when_follow_through_and_sector_confirmation_are_weak(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    94,
                    change=1.2,
                    trend_quality_score=64.0,
                    trend_state="improving",
                    trend_regime="repair",
                    trend_regime_score=60.0,
                ) | {"sector": "Software"},
                "BBB": market_security(80, change=-2.5) | {"sector": "Software"},
                "CCC": market_security(78, change=-1.8) | {"sector": "Software"},
                "SPY": {
                    **market_security(99, change=1.0),
                    "sector": "Benchmark ETF",
                },
                "QQQ": {
                    **market_security(99, change=1.1),
                    "sector": "Benchmark ETF",
                },
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(created, [])

    def test_prefers_better_persistence_when_other_inputs_are_close(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    90,
                    change=1.4,
                    trend_quality_score=74.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=74.0,
                    return_1m=5.0,
                    return_3m=12.0,
                    return_6m=20.0,
                    ema_20_slope_pct=2.0,
                    price_vs_sma_20_pct=4.0,
                    price_vs_sma_50_pct=7.0,
                    drawdown_63d_pct=-3.0,
                ) | {"sector": "Software"},
                "BBB": market_security_with_trend(
                    90,
                    change=1.4,
                    trend_quality_score=74.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=74.0,
                    return_1m=-1.0,
                    return_3m=2.0,
                    return_6m=4.0,
                    ema_20_slope_pct=-0.5,
                    price_vs_sma_20_pct=0.2,
                    price_vs_sma_50_pct=0.1,
                    drawdown_63d_pct=-12.0,
                ) | {"sector": "Healthcare"},
                "SPY": {**market_security(99, change=0.8), "sector": "Benchmark ETF"},
                "QQQ": {**market_security(99, change=0.9), "sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.7), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=0.6), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA"])
        self.assertTrue(
            any(
                "Multi-day persistence score is" in line
                for line in created[0]["rationale"]
            )
        )
        self.assertTrue(
            any("Sector breadth is" in line for line in created[0]["rationale"])
        )

    def test_prefers_ticker_with_supportive_paper_learning_when_scores_are_close(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 6, 9, 30, 0),
                    datetime(2026, 6, 6, 9, 31, 0),
                    datetime(2026, 6, 6, 9, 32, 0),
                    datetime(2026, 6, 6, 9, 33, 0),
                    datetime(2026, 6, 6, 9, 34, 0),
                    datetime(2026, 6, 6, 9, 35, 0),
                    datetime(2026, 6, 6, 9, 36, 0),
                    datetime(2026, 6, 6, 9, 37, 0),
                    datetime(2026, 6, 6, 16, 0, 0),
                    datetime(2026, 6, 7, 16, 0, 0),
                    datetime(2026, 6, 8, 16, 0, 0),
                    datetime(2026, 6, 9, 16, 0, 0),
                    datetime(2026, 6, 10, 16, 0, 0),
                    datetime(2026, 6, 11, 9, 30, 0),
                    datetime(2026, 6, 11, 9, 31, 0),
                    datetime(2026, 6, 11, 9, 32, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: next(times),
            )
            account.initialize(100000)
            prior_one = account.create_proposal("buy", "OLD1", 10, 100, "Prior paper entry one.")
            account.record_proposal_risk_review(prior_one["proposal_id"], "clear", [])
            account.decide_proposal(prior_one["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "OLD1",
                10,
                100,
                "Prior paper entry one.",
                proposal_id=prior_one["proposal_id"],
            )
            prior_two = account.create_proposal("buy", "OLD2", 10, 100, "Prior paper entry two.")
            account.record_proposal_risk_review(prior_two["proposal_id"], "clear", [])
            account.decide_proposal(prior_two["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "OLD2",
                10,
                100,
                "Prior paper entry two.",
                proposal_id=prior_two["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 108, "OLD2": 107},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 111, "OLD2": 110},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 112, "OLD2": 111},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    91,
                    change=1.8,
                    trend_quality_score=74.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=74.0,
                ) | {"sector": "Software"},
                "BBB": market_security_with_trend(
                    91,
                    change=1.8,
                    trend_quality_score=74.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=74.0,
                ) | {"sector": "Healthcare"},
                "OLD1": market_security_with_trend(
                    70,
                    change=1.1,
                    trend_quality_score=60.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=60.0,
                ) | {"sector": "Software"},
                "OLD2": market_security_with_trend(
                    70,
                    change=1.0,
                    trend_quality_score=60.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=60.0,
                ) | {"sector": "Software"},
                "SPY": {**market_security(99, change=1.0), "sector": "Benchmark ETF"},
                "QQQ": {**market_security(99, change=1.1), "sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.9), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=0.8), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA"])
        self.assertTrue(any("Paper learning sector boost +1.5" in line for line in created[0]["rationale"]))

    def test_sector_learning_summary_exposes_strategy_tilt(self):
        feedback_rows = [
            {
                "ticker": "OLD1",
                "side": "buy",
                "horizon_outcomes": [
                    {"snapshots": 3, "available": True, "verdict": "working"}
                ],
            },
            {
                "ticker": "OLD2",
                "side": "buy",
                "horizon_outcomes": [
                    {"snapshots": 3, "available": True, "verdict": "working"}
                ],
            },
            {
                "ticker": "OTHER",
                "side": "buy",
                "horizon_outcomes": [
                    {"snapshots": 3, "available": True, "verdict": "lagging"}
                ],
            },
        ]
        market_data = {
            "OLD1": {"sector": "Software"},
            "OLD2": {"sector": "Software"},
            "OTHER": {"sector": "Healthcare"},
        }

        summary = PaperStrategy.sector_learning_summary_from_feedback(
            feedback_rows,
            market_data,
        )

        self.assertTrue(summary["enabled"])
        self.assertTrue(summary["active"])
        self.assertEqual(summary["sectors"][0]["sector"], "Software")
        self.assertEqual(summary["sectors"][0]["posture"], "boost")
        self.assertEqual(summary["sectors"][0]["adjustment"], 1.5)
        self.assertIn("sector boost +1.5", summary["sectors"][0]["summary"])

    def test_supportive_paper_learning_can_unlock_borderline_buy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 6, 9, 30, 0),
                    datetime(2026, 6, 6, 9, 31, 0),
                    datetime(2026, 6, 6, 9, 32, 0),
                    datetime(2026, 6, 6, 9, 33, 0),
                    datetime(2026, 6, 6, 9, 34, 0),
                    datetime(2026, 6, 6, 9, 35, 0),
                    datetime(2026, 6, 6, 9, 36, 0),
                    datetime(2026, 6, 6, 9, 37, 0),
                    datetime(2026, 6, 6, 16, 0, 0),
                    datetime(2026, 6, 7, 16, 0, 0),
                    datetime(2026, 6, 8, 16, 0, 0),
                    datetime(2026, 6, 9, 16, 0, 0),
                    datetime(2026, 6, 10, 16, 0, 0),
                    datetime(2026, 6, 11, 9, 30, 0),
                    datetime(2026, 6, 11, 9, 31, 0),
                    datetime(2026, 6, 11, 9, 32, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: next(times),
            )
            account.initialize(100000)
            for ticker in ("OLD1", "OLD2"):
                prior = account.create_proposal("buy", ticker, 10, 100, f"Prior {ticker}.")
                account.record_proposal_risk_review(prior["proposal_id"], "clear", [])
                account.decide_proposal(prior["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"Prior {ticker}.",
                    proposal_id=prior["proposal_id"],
                )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 108, "OLD2": 107},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 111, "OLD2": 110},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 112, "OLD2": 111},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    90,
                    change=1.0,
                    trend_quality_score=58.5,
                    trend_state="improving",
                    trend_regime="repair",
                    trend_regime_score=62.0,
                    return_1m=2.0,
                    return_3m=5.0,
                    return_6m=8.0,
                    ema_20_slope_pct=0.8,
                    price_vs_sma_20_pct=1.8,
                    price_vs_sma_50_pct=2.8,
                    drawdown_63d_pct=-5.0,
                ) | {"sector": "Software"},
                "OLD1": market_security_with_trend(70, change=1.1, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "OLD2": market_security_with_trend(70, change=1.0, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "SPY": market_security_with_trend(
                    99,
                    change=0.2,
                    trend_quality_score=60.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=60.0,
                ) | {"sector": "Benchmark ETF"},
                "QQQ": market_security_with_trend(
                    99,
                    change=-0.4,
                    trend_quality_score=48.0,
                    trend_state="mixed",
                    trend_regime="fragile",
                    trend_regime_score=48.0,
                ) | {"sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.1), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=-0.2), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA"])

    def test_caution_paper_learning_blocks_borderline_buy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 6, 9, 30, 0),
                    datetime(2026, 6, 6, 9, 31, 0),
                    datetime(2026, 6, 6, 9, 32, 0),
                    datetime(2026, 6, 6, 9, 33, 0),
                    datetime(2026, 6, 6, 9, 34, 0),
                    datetime(2026, 6, 6, 9, 35, 0),
                    datetime(2026, 6, 6, 9, 36, 0),
                    datetime(2026, 6, 6, 9, 37, 0),
                    datetime(2026, 6, 6, 16, 0, 0),
                    datetime(2026, 6, 7, 16, 0, 0),
                    datetime(2026, 6, 8, 16, 0, 0),
                    datetime(2026, 6, 9, 16, 0, 0),
                    datetime(2026, 6, 10, 16, 0, 0),
                    datetime(2026, 6, 11, 9, 30, 0),
                    datetime(2026, 6, 11, 9, 31, 0),
                    datetime(2026, 6, 11, 9, 32, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: next(times),
            )
            account.initialize(100000)
            for ticker in ("OLD1", "OLD2"):
                prior = account.create_proposal("buy", ticker, 10, 100, f"Prior {ticker}.")
                account.record_proposal_risk_review(prior["proposal_id"], "clear", [])
                account.decide_proposal(prior["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"Prior {ticker}.",
                    proposal_id=prior["proposal_id"],
                )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 101, "OLD2": 101},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 99, "OLD2": 99},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    90,
                    change=0.4,
                    trend_quality_score=64.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=66.0,
                    return_1m=2.0,
                    return_3m=5.0,
                    return_6m=8.0,
                    ema_20_slope_pct=0.8,
                    price_vs_sma_20_pct=1.8,
                    price_vs_sma_50_pct=2.8,
                    drawdown_63d_pct=-5.0,
                ) | {"sector": "Software"},
                "OLD1": market_security_with_trend(70, change=0.2, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "OLD2": market_security_with_trend(70, change=0.1, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "SPY": {**market_security(99, change=0.1), "sector": "Benchmark ETF"},
                "QQQ": {**market_security(99, change=0.0), "sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.1), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=0.0), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(created, [])

    def test_sector_caution_requires_stronger_confirmation_for_new_buy(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 6, 9, 30, 0),
                    datetime(2026, 6, 6, 9, 31, 0),
                    datetime(2026, 6, 6, 9, 32, 0),
                    datetime(2026, 6, 6, 9, 33, 0),
                    datetime(2026, 6, 6, 9, 34, 0),
                    datetime(2026, 6, 6, 9, 35, 0),
                    datetime(2026, 6, 6, 9, 36, 0),
                    datetime(2026, 6, 6, 9, 37, 0),
                    datetime(2026, 6, 6, 16, 0, 0),
                    datetime(2026, 6, 7, 16, 0, 0),
                    datetime(2026, 6, 8, 16, 0, 0),
                    datetime(2026, 6, 9, 16, 0, 0),
                    datetime(2026, 6, 10, 16, 0, 0),
                    datetime(2026, 6, 11, 9, 30, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: next(times),
            )
            account.initialize(100000)
            for ticker in ("OLD1", "OLD2"):
                prior = account.create_proposal("buy", ticker, 10, 100, f"Prior {ticker}.")
                account.record_proposal_risk_review(prior["proposal_id"], "clear", [])
                account.decide_proposal(prior["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"Prior {ticker}.",
                    proposal_id=prior["proposal_id"],
                )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 101, "OLD2": 101},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 99, "OLD2": 99},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    91,
                    change=0.4,
                    trend_quality_score=66.0,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=68.0,
                    return_1m=2.0,
                    return_3m=5.0,
                    return_6m=8.0,
                    ema_20_slope_pct=0.8,
                    price_vs_sma_20_pct=1.8,
                    price_vs_sma_50_pct=2.8,
                    drawdown_63d_pct=-5.0,
                ) | {"sector": "Software"},
                "OLD1": market_security_with_trend(70, change=0.2, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "OLD2": market_security_with_trend(70, change=0.1, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "SPY": market_security_with_trend(99, change=0.1, trend_state="uptrend") | {"sector": "Benchmark ETF"},
                "QQQ": market_security_with_trend(99, change=0.0, trend_state="mixed") | {"sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.1), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=0.0), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(created, [])

    def test_sector_caution_gate_is_visible_when_strong_setup_clears(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            times = iter(
                [
                    datetime(2026, 6, 6, 9, 30, 0),
                    datetime(2026, 6, 6, 9, 31, 0),
                    datetime(2026, 6, 6, 9, 32, 0),
                    datetime(2026, 6, 6, 9, 33, 0),
                    datetime(2026, 6, 6, 9, 34, 0),
                    datetime(2026, 6, 6, 9, 35, 0),
                    datetime(2026, 6, 6, 9, 36, 0),
                    datetime(2026, 6, 6, 9, 37, 0),
                    datetime(2026, 6, 6, 16, 0, 0),
                    datetime(2026, 6, 7, 16, 0, 0),
                    datetime(2026, 6, 8, 16, 0, 0),
                    datetime(2026, 6, 9, 16, 0, 0),
                    datetime(2026, 6, 10, 16, 0, 0),
                    datetime(2026, 6, 11, 9, 30, 0),
                    datetime(2026, 6, 11, 9, 31, 0),
                    datetime(2026, 6, 11, 9, 32, 0),
                ]
            )
            account = PaperTradingAccount(
                account_file=Path(temp_dir) / "account.json",
                ledger_file=Path(temp_dir) / "ledger.jsonl",
                clock=lambda: next(times),
            )
            account.initialize(100000)
            for ticker in ("OLD1", "OLD2"):
                prior = account.create_proposal("buy", ticker, 10, 100, f"Prior {ticker}.")
                account.record_proposal_risk_review(prior["proposal_id"], "clear", [])
                account.decide_proposal(prior["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"Prior {ticker}.",
                    proposal_id=prior["proposal_id"],
                )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 101, "OLD2": 101},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 100, "OLD2": 100},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"OLD1": 99, "OLD2": 99},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )

            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    96,
                    change=1.8,
                    trend_quality_score=82.0,
                    trend_state="uptrend",
                    trend_regime="leadership",
                    trend_regime_score=84.0,
                    return_1m=9.0,
                    return_3m=15.0,
                    return_6m=20.0,
                    ema_20_slope_pct=4.0,
                    price_vs_sma_20_pct=8.0,
                    price_vs_sma_50_pct=12.0,
                    drawdown_63d_pct=-2.0,
                ) | {"sector": "Software"},
                "OLD1": market_security_with_trend(70, change=0.2, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "OLD2": market_security_with_trend(70, change=0.1, trend_quality_score=60.0, trend_state="uptrend", trend_regime="constructive", trend_regime_score=60.0) | {"sector": "Software"},
                "SPY": market_security_with_trend(99, change=0.1, trend_state="uptrend") | {"sector": "Benchmark ETF"},
                "QQQ": market_security_with_trend(99, change=0.0, trend_state="mixed") | {"sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.1), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=0.0), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual([item["ticker"] for item in created], ["AAA"])
        self.assertTrue(
            any(
                "Sector learning gate: Cleared stronger lagging-sector confirmation."
                in line
                for line in created[0]["rationale"]
            )
        )

    def test_blocks_buy_when_sector_breadth_is_too_thin_in_cautious_market(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    90,
                    change=1.1,
                    trend_quality_score=71.0,
                    trend_state="improving",
                    trend_regime="constructive",
                    trend_regime_score=72.0,
                ) | {"sector": "Software"},
                "BBB": market_security(70, change=-2.0) | {"sector": "Software"},
                "CCC": market_security(68, change=-1.7) | {"sector": "Software"},
                "SPY": {**market_security(99, change=0.2), "sector": "Benchmark ETF"},
                "QQQ": {**market_security(99, change=-0.4), "sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.1), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=-0.2), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(created, [])

    def test_blocks_buy_when_company_news_is_adverse(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    94,
                    change=2.2,
                    trend_quality_score=81.0,
                    trend_state="uptrend",
                    trend_regime="leadership",
                    trend_regime_score=84.0,
                )
                | {
                    "sector": "Software",
                    "news_signal": {
                        "signal_label": "adverse",
                        "negative_count": 2,
                        "positive_count": 0,
                        "signal_score": 14.0,
                    },
                },
                "SPY": {**market_security(99, change=1.0), "sector": "Benchmark ETF"},
                "QQQ": {**market_security(99, change=1.1), "sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.9), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=0.8), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(created, [])

    def test_blocks_buy_when_single_high_impact_negative_news_event_is_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    95,
                    change=2.4,
                    trend_quality_score=82.0,
                    trend_state="uptrend",
                    trend_regime="leadership",
                    trend_regime_score=85.0,
                )
                | {
                    "sector": "Software",
                    "news_signal": {
                        "signal_label": "adverse",
                        "negative_count": 1,
                        "positive_count": 0,
                        "negative_weight": 3.3,
                        "high_impact_negative_count": 1,
                        "dominant_event_type": "legal_risk",
                        "signal_score": 24.0,
                    },
                },
                "SPY": {**market_security(99, change=1.0), "sector": "Benchmark ETF"},
                "QQQ": {**market_security(99, change=1.1), "sector": "Benchmark ETF"},
                "IWM": {**market_security(99, change=0.9), "sector": "Benchmark ETF"},
                "RSP": {**market_security(99, change=0.8), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(created, [])

    def test_from_account_policy_reads_tunable_strategy_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.update_policy(
                {
                    "strategy_minimum_buy_score": 90.0,
                    "strategy_maximum_new_proposals": 1,
                    "strategy_target_position_pct": 7.0,
                    "strategy_benchmark_excess_weight": 4.0,
                    "strategy_trend_quality_weight": 0.5,
                    "strategy_sector_repeat_penalty": 0.0,
                },
                source="test",
            )
            strategy = PaperStrategy.from_account_policy(account)
            market_data = {
                "AAA": market_security_with_trend(
                    90,
                    change=2.0,
                    trend_quality_score=80.0,
                ) | {"sector": "Software"},
                "BBB": market_security_with_trend(
                    90,
                    change=1.0,
                    trend_quality_score=60.0,
                ) | {"sector": "Software"},
                "SPY": {**market_security(99, change=0.5), "sector": "Benchmark ETF"},
                "QQQ": {**market_security(99, change=0.7), "sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(strategy.maximum_new_proposals, 1)
        self.assertEqual(strategy.target_position_pct, 7.0)
        self.assertEqual(strategy.benchmark_excess_weight, 4.0)
        self.assertEqual(strategy.trend_quality_weight, 0.5)
        self.assertEqual(strategy.sector_repeat_penalty, 0.0)
        self.assertEqual(created[0]["shares"], 70)

    def test_from_account_policy_applies_adaptive_entry_overrides(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.entry_strategy_profile = lambda latest_prices=None: {
                "strategy_overrides": {
                    "strategy_minimum_buy_score": 90.0,
                    "strategy_target_position_pct": 4.5,
                    "strategy_maximum_new_proposals": 2,
                    "strategy_benchmark_excess_weight": 2.0,
                    "strategy_trend_quality_weight": 0.3,
                    "strategy_sector_repeat_penalty": 4.0,
                }
            }
            strategy = PaperStrategy.from_account_policy(account)

        self.assertEqual(strategy.minimum_buy_score, 90.0)
        self.assertEqual(strategy.target_position_pct, 4.5)
        self.assertEqual(strategy.maximum_new_proposals, 2)
        self.assertEqual(strategy.benchmark_excess_weight, 2.0)
        self.assertEqual(strategy.trend_quality_weight, 0.3)
        self.assertEqual(strategy.sector_repeat_penalty, 4.0)

    def test_from_account_policy_applies_adaptive_benchmark_preference(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            account.benchmark_preference_profile = lambda latest_prices=None: {
                "strategy_overrides": {"strategy_preferred_benchmark": "SPY"}
            }
            strategy = PaperStrategy.from_account_policy(account)

        self.assertEqual(strategy.preferred_benchmark, "SPY")

    def test_preferred_benchmark_can_admit_borderline_setup_that_auto_mode_rejects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            market_data = {
                "AAA": market_security_with_trend(
                    90,
                    change=1.0,
                    trend_quality_score=65.0,
                    trend_state="improving",
                    trend_regime="repair",
                    trend_regime_score=66.0,
                ) | {"sector": "Software"},
                "SPY": market_security_with_trend(
                    99,
                    change=1.0,
                    trend_state="uptrend",
                ) | {"sector": "Benchmark ETF"},
                "QQQ": market_security_with_trend(
                    99,
                    change=1.5,
                    trend_state="mixed",
                ) | {"sector": "Benchmark ETF"},
                "IWM": market_security_with_trend(
                    99,
                    change=0.2,
                    trend_state="mixed",
                ) | {"sector": "Benchmark ETF"},
                "RSP": market_security_with_trend(
                    99,
                    change=-0.1,
                    trend_state="mixed",
                ) | {"sector": "Benchmark ETF"},
            }

            auto_created = PaperStrategy(maximum_new_proposals=1).generate(account, market_data)
            spy_created = PaperStrategy(
                maximum_new_proposals=1,
                preferred_benchmark="SPY",
            ).generate(account, market_data)

        self.assertEqual(auto_created, [])
        self.assertEqual([item["ticker"] for item in spy_created], ["AAA"])

    def test_blocks_weaker_setup_in_risk_off_regime(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            strategy = PaperStrategy(maximum_new_proposals=1)
            market_data = {
                "AAA": market_security_with_trend(
                    94,
                    change=0.2,
                    trend_quality_score=62.0,
                    trend_state="improving",
                    trend_regime="repair",
                    trend_regime_score=61.0,
                ) | {"sector": "Software"},
                "SPY": market_security_with_trend(
                    99,
                    change=-1.5,
                    trend_state="downtrend",
                ) | {"sector": "Benchmark ETF"},
                "QQQ": market_security_with_trend(
                    99,
                    change=-2.0,
                    trend_state="downtrend",
                ) | {"sector": "Benchmark ETF"},
                "IWM": market_security_with_trend(
                    99,
                    change=-1.2,
                    trend_state="mixed",
                ) | {"sector": "Benchmark ETF"},
                "RSP": market_security_with_trend(
                    99,
                    change=-0.8,
                    trend_state="mixed",
                ) | {"sector": "Benchmark ETF"},
            }

            created = strategy.generate(account, market_data)

        self.assertEqual(created, [])

    def test_sector_gate_audit_counts_candidates_and_accepted_decisions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            recommendation = account.record_recommendation(
                side="buy",
                ticker="AAA",
                shares=10,
                reference_price=100,
                thesis="Accepted with sector gate.",
                rationale=[
                    "Sector learning gate: Cleared stronger lagging-sector confirmation. 6 of 6 stronger confirmation checks passed."
                ],
            )
            proposal = account.create_proposal(
                "buy",
                "AAA",
                10,
                100,
                "Accepted with sector gate.",
                recommendation_id=recommendation["recommendation_id"],
            )
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "AAA",
                10,
                100,
                "Accepted with sector gate.",
                proposal_id=proposal["proposal_id"],
                recommendation_id=recommendation["recommendation_id"],
            )
            for ticker in ("BBB", "CCC"):
                proposal = account.create_proposal(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"{ticker} prior sector buy.",
                )
                account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
                account.decide_proposal(proposal["proposal_id"], "approve")
                account.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"{ticker} prior sector buy.",
                    proposal_id=proposal["proposal_id"],
                )
            account.record_performance_snapshot(
                prices={"AAA": 100, "BBB": 100, "CCC": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"AAA": 101, "BBB": 96, "CCC": 95},
                benchmark_prices={"SPY": 501, "QQQ": 401},
            )
            account.record_performance_snapshot(
                prices={"AAA": 102, "BBB": 94, "CCC": 93},
                benchmark_prices={"SPY": 502, "QQQ": 402},
            )
            account.record_performance_snapshot(
                prices={"AAA": 103, "BBB": 92, "CCC": 91},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            market_data = {
                "AAA": market_security_with_trend(
                    96,
                    price=103,
                    change=2.0,
                    trend_quality_score=78,
                    trend_state="uptrend",
                    trend_regime="leadership",
                    trend_regime_score=76,
                )
                | {"sector": "Software"},
                "BBB": market_security_with_trend(
                    96,
                    price=92,
                    change=0.0,
                    trend_quality_score=50,
                    trend_state="mixed",
                    trend_regime="repair",
                    trend_regime_score=50,
                )
                | {"sector": "Software"},
                "CCC": market_security_with_trend(
                    96,
                    price=91,
                    change=0.0,
                    trend_quality_score=50,
                    trend_state="mixed",
                    trend_regime="repair",
                    trend_regime_score=50,
                )
                | {"sector": "Software"},
                "DDD": market_security_with_trend(
                    95,
                    price=100,
                    change=1.0,
                    trend_quality_score=70,
                    trend_state="uptrend",
                    trend_regime="constructive",
                    trend_regime_score=70,
                )
                | {"sector": "Software"},
                "SPY": market_security_with_trend(99, change=0.1)
                | {"sector": "Benchmark ETF"},
                "QQQ": market_security_with_trend(99, change=0.2)
                | {"sector": "Benchmark ETF"},
            }

            audit = PaperStrategy.sector_gate_audit(account, market_data)

        self.assertTrue(audit["enabled"])
        self.assertTrue(audit["active"])
        self.assertGreaterEqual(audit["candidate_counts"]["active"], 1)
        self.assertGreaterEqual(audit["candidate_counts"]["tightened"], 1)
        self.assertEqual(audit["accepted_decision_counts"]["with_gate"], 1)
        self.assertEqual(audit["accepted_decision_counts"]["cleared"], 1)
        self.assertTrue(audit["candidate_examples"])

    def test_generates_exit_for_regime_breakdown_even_above_exit_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
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
                {
                    "AAA": market_security_with_trend(
                        72,
                        price=92,
                        change=-2.6,
                        trend_quality_score=42.0,
                        trend_state="downtrend",
                        trend_regime="breakdown",
                        trend_regime_score=32.0,
                    ),
                    "SPY": market_security_with_trend(
                        99,
                        change=-1.0,
                        trend_state="downtrend",
                    ) | {"sector": "Benchmark ETF"},
                    "QQQ": market_security_with_trend(
                        99,
                        change=-1.8,
                        trend_state="downtrend",
                    ) | {"sector": "Benchmark ETF"},
                    "IWM": market_security_with_trend(
                        99,
                        change=-1.2,
                        trend_state="mixed",
                    ) | {"sector": "Benchmark ETF"},
                    "RSP": market_security_with_trend(
                        99,
                        change=-0.9,
                        trend_state="mixed",
                    ) | {"sector": "Benchmark ETF"},
                },
            )

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["side"], "sell")
        self.assertIn("risk off", created[0]["thesis"])
        self.assertIn("routine mention", created[0]["thesis"])

    def test_generates_exit_for_sector_and_follow_through_breakdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
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
                {
                    "AAA": market_security_with_trend(
                        68,
                        price=93,
                        change=-3.4,
                        trend_quality_score=35.0,
                        trend_state="mixed",
                        trend_regime="fragile",
                        trend_regime_score=32.0,
                    ) | {"sector": "Software"},
                    "BBB": market_security(79, change=-3.8) | {"sector": "Software"},
                    "CCC": market_security(76, change=-3.1) | {"sector": "Software"},
                    "SPY": {
                        **market_security(99, change=1.0),
                        "sector": "Benchmark ETF",
                    },
                    "QQQ": {
                        **market_security(99, change=1.2),
                        "sector": "Benchmark ETF",
                    },
                },
            )

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["side"], "sell")
        self.assertIn("follow-through score", created[0]["thesis"])
        self.assertIn("routine mention", created[0]["thesis"])

    def test_generates_exit_when_persistence_and_benchmark_breadth_break_down(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account = self.make_account(temp_dir)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            account.record_proposal_risk_review(
                proposal["proposal_id"], "clear", [], source="test"
            )
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
                {
                    "AAA": market_security_with_trend(
                        73,
                        price=91,
                        change=-2.4,
                        trend_quality_score=45.0,
                        trend_state="mixed",
                        trend_regime="repair",
                        trend_regime_score=55.0,
                        return_1m=-4.0,
                        return_3m=-8.0,
                        return_6m=-10.0,
                        ema_20_slope_pct=-1.2,
                        price_vs_sma_20_pct=-3.0,
                        price_vs_sma_50_pct=-4.5,
                        drawdown_63d_pct=-18.0,
                    ) | {"sector": "Software"},
                    "BBB": market_security(75, change=-2.6) | {"sector": "Software"},
                    "CCC": market_security(74, change=-2.9) | {"sector": "Software"},
                    "SPY": {**market_security(99, change=-1.4), "sector": "Benchmark ETF"},
                    "QQQ": {**market_security(99, change=-2.0), "sector": "Benchmark ETF"},
                    "IWM": {**market_security(99, change=-1.1), "sector": "Benchmark ETF"},
                    "RSP": {**market_security(99, change=-0.9), "sector": "Benchmark ETF"},
                },
            )

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["side"], "sell")


if __name__ == "__main__":
    unittest.main()
