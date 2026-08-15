import json
import os
import tempfile
import threading
import unittest
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.paper_trading import PaperTradingAccount
from app.research_tasks import ResearchTaskQueue
from app.web_dashboard import (
    DashboardDataService,
    STATIC_FILES,
    ThreadingHTTPServer,
    create_handler,
)


class WebDashboardTests(unittest.TestCase):
    def test_overview_marks_all_zero_daily_movement_as_limited(self):
        available = {
            f"T{i}": {"status": "available", "percent_change": 0}
            for i in range(5)
        }

        overview = DashboardDataService._overview(None, available, available)

        self.assertEqual(overview["daily_change_quality"]["status"], "limited")
        self.assertTrue(
            overview["daily_change_quality"]["suspicious_all_zero"]
        )
        self.assertEqual(overview["daily_change_quality"]["limited"], 5)

    def test_overview_accepts_legacy_snapshot_with_real_daily_movement(self):
        available = {
            "AAA": {"status": "available", "percent_change": 1.2},
            "BBB": {"status": "available", "percent_change": -0.4},
        }

        overview = DashboardDataService._overview(None, available, available)

        self.assertEqual(overview["daily_change_quality"]["status"], "complete")
        self.assertFalse(
            overview["daily_change_quality"]["suspicious_all_zero"]
        )

    def test_movers_exclude_explicitly_limited_daily_changes(self):
        rows = DashboardDataService._movers(
            None,
            {
                "AAA": {
                    "status": "available",
                    "price": 100,
                    "percent_change": 8.0,
                    "daily_change_quality": "limited",
                },
                "BBB": {
                    "status": "available",
                    "price": 100,
                    "percent_change": 2.0,
                    "daily_change_quality": "complete",
                },
            },
        )

        self.assertEqual([row["ticker"] for row in rows], ["BBB"])

    def test_report_archive_lists_generated_reports_and_rejects_active_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            reports = root / "reports"
            reports.mkdir()
            safe = reports / "morning_brief_20260607_070000.html"
            safe.write_text("<!doctype html><title>Morning brief</title>", encoding="utf-8")
            (reports / "weekly_summary_20260606_180000.html").write_text(
                "<!doctype html><title>Weekly summary</title>",
                encoding="utf-8",
            )
            unsafe = reports / "morning_brief_20260608_070000.html"
            unsafe.write_text("<script>alert('no')</script>", encoding="utf-8")
            archive_dir = root / "archive"
            archive_dir.mkdir()
            (archive_dir / "archive_index.json").write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "html_report_path": (
                                    "../reports/morning_brief_20260607_070000.html"
                                ),
                                "available_securities": 140,
                                "score_leaders": [
                                    {"ticker": "AAA", "total_score": 91.2}
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            service = DashboardDataService(
                archive_dir=archive_dir,
                reports_dir=reports,
                paper_account=PaperTradingAccount(
                    account_file=root / "paper" / "account.json",
                    ledger_file=root / "paper" / "ledger.jsonl",
                ),
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )

            archive = service._reports()

            self.assertEqual(archive[0]["type"], "Morning brief")
            self.assertEqual(archive[0]["coverage"], 140)
            self.assertEqual(
                archive[0]["leader"],
                {"ticker": "AAA", "score": 91.2},
            )
            self.assertEqual(archive[1]["type"], "Weekly summary")
            self.assertEqual(
                service.report_document("morning_brief_20260607_070000"),
                safe.read_bytes(),
            )
            self.assertIsNone(
                service.report_document("morning_brief_20260608_070000")
            )
            self.assertIsNone(service.report_document("../.env"))

    def test_dashboard_builds_read_model_from_local_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {
                            "SPY": {"price": 500, "change": 5, "percent_change": 1},
                            "QQQ": {"price": 400, "change": -4, "percent_change": -1},
                        },
                        "securities": {
                            "AAA": {
                                "status": "available",
                                "company_name": "Alpha",
                                "sector": "Software",
                                "category": "Core",
                                "price": 100,
                                "percent_change": 5,
                                "total_score": 90,
                                "scores": {
                                    "growth": 92,
                                    "quality": 88,
                                    "moat": 85,
                                    "momentum": 81,
                                    "risk": 67,
                                },
                                "profile": {
                                    "thesis": "Durable recurring growth.",
                                    "key_driver": "Enterprise adoption.",
                                    "key_risk": "Premium valuation.",
                                },
                                "momentum_metrics": {
                                    "trend_quality_score": 78.5,
                                    "trend_regime": "leadership",
                                    "trend_regime_score": 84.0,
                                    "trend_state": "uptrend",
                                    "price_vs_sma_50_pct": 6.2,
                                    "price_vs_sma_200_pct": 14.4,
                                    "ema_20_slope_pct": 3.1,
                                    "rsi_14": 63.0,
                                    "distance_from_52w_high_pct": -2.8,
                                },
                                "news_signal": {
                                    "signal_label": "supportive",
                                    "signal_score": 82,
                                    "positive_count": 2,
                                    "negative_count": 0,
                                    "company_headline_count": 2,
                                    "positive_examples": ["Alpha raised guidance."],
                                },
                            },
                            "BBB": {
                                "status": "available",
                                "company_name": "Beta",
                                "sector": "Healthcare",
                                "category": "Watchlist",
                                "price": 50,
                                "percent_change": -3,
                                "total_score": 80,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            paper = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
                clock=iter(
                    [
                        datetime(2026, 6, 27, 9, 30, 0),
                        datetime(2026, 6, 27, 9, 31, 0),
                        datetime(2026, 6, 27, 9, 32, 0),
                        datetime(2026, 6, 27, 16, 0, 0),
                        datetime(2026, 6, 28, 16, 0, 0),
                        datetime(2026, 6, 29, 9, 30, 0),
                    ]
                ).__next__,
            )
            paper.initialize(100000)
            proposal = paper.create_proposal("buy", "AAA", 1, 100, "Paper entry.")
            paper.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            paper.decide_proposal(proposal["proposal_id"], "approve")
            paper.record_performance_snapshot(
                prices={},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            tasks = ResearchTaskQueue(root / "tasks" / "tasks.json")
            tasks.add_task(role="CIO", subject="AAA", prompt="Review thesis.")
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=paper,
                research_queue=tasks,
            )

            data = service.build()
            summary = service.build_summary()

        self.assertEqual(data["overview"]["tracked"], 2)
        self.assertEqual(data["overview"]["advancing"], 1)
        self.assertEqual(data["movers"][0]["ticker"], "AAA")
        self.assertEqual(data["score_leaders"][0]["score"], 90)
        self.assertEqual(data["score_leaders"][0]["scores"]["growth"], 92)
        self.assertEqual(data["score_leaders"][0]["thesis"], "Durable recurring growth.")
        self.assertEqual(data["score_leaders"][0]["key_driver"], "Enterprise adoption.")
        self.assertEqual(data["score_leaders"][0]["key_risk"], "Premium valuation.")
        self.assertEqual(
            data["score_leaders"][0]["score_horizon"],
            "Research priority; not a return forecast",
        )
        self.assertEqual(data["watchlist"][0]["ticker"], "AAA")
        self.assertEqual(data["watchlist"][0]["scores"]["quality"], 88)
        self.assertTrue(data["paper"]["configured"])
        self.assertIn("validation_summary", data["paper"])
        self.assertIn("validation_summary", summary["paper"])
        self.assertEqual(data["paper"]["operating_mode"]["current"]["id"], "recommendation_only")
        self.assertEqual(data["paper"]["activity"], [])
        self.assertEqual(data["paper"]["feedback"], [])
        self.assertEqual(data["paper"]["proposals"]["approved"], 1)
        self.assertEqual(data["research"]["open"], 1)
        self.assertIn("reports", data)
        self.assertIn("reports", summary)
        self.assertIsNotNone(data["research"]["tasks"][0]["created_at"])
        self.assertNotIn("activity", summary["paper"])
        self.assertNotIn("feedback", summary["paper"])
        self.assertIn("positions", summary["paper"])
        self.assertEqual(data["corporate_actions"], [])
        self.assertFalse(data["access"]["public_registration"])
        self.assertEqual(data["access"]["mode"], "owner_only")
        self.assertEqual(data["access"]["schema_version"], 3)
        self.assertEqual(data["access"]["phase_completion"], 78)
        self.assertEqual(len(data["access"]["owner_validation"]), 2)
        self.assertTrue(
            all(item["status"] == "pending" for item in data["access"]["owner_validation"])
        )
        self.assertIn("restore drill", data["access"]["recovery"])
        self.assertIn("tenant package", data["access"]["privacy_export"])
        self.assertIn(
            "Owner profile active",
            data["access"]["production_review"],
        )
        self.assertEqual(data["workspace"]["deployment"]["revision"], "local-preview")
        self.assertEqual(data["workspace"]["deployment"]["service"], "local-dashboard")

    def test_dashboard_shows_auto_manage_mode_when_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {},
                        "securities": {},
                    }
                ),
                encoding="utf-8",
            )
            paper = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
            )
            paper.initialize(100000)
            paper.update_policy({"auto_manage_enabled": True}, source="test")
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=paper,
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )

            data = service.build()

        self.assertEqual(data["paper"]["operating_mode"]["current"]["id"], "paper_auto_manage")
        self.assertEqual(data["paper"]["operating_mode"]["modes"][1]["status"], "active")
        self.assertTrue(data["paper"]["operating_mode"]["strategy_settings"])
        strategy_settings = {item["label"]: item for item in data["paper"]["operating_mode"]["strategy_settings"]}
        self.assertEqual(strategy_settings["Daily trade cap"]["value"], "5")
        self.assertEqual(strategy_settings["Benchmark trust"]["value"], "AUTO")

    def test_dashboard_reports_cloud_revision_from_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {},
                        "securities": {},
                    }
                ),
                encoding="utf-8",
            )
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=PaperTradingAccount(
                    account_file=root / "paper" / "account.json",
                    ledger_file=root / "paper" / "ledger.jsonl",
                ),
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )

            old_revision = os.environ.get("K_REVISION")
            old_service = os.environ.get("K_SERVICE")
            try:
                os.environ["K_REVISION"] = "atlas-dashboard-stg-00071-n4v"
                os.environ["K_SERVICE"] = "atlas-dashboard-stg"
                data = service.build()
            finally:
                if old_revision is None:
                    os.environ.pop("K_REVISION", None)
                else:
                    os.environ["K_REVISION"] = old_revision
                if old_service is None:
                    os.environ.pop("K_SERVICE", None)
                else:
                    os.environ["K_SERVICE"] = old_service

        self.assertEqual(
            data["workspace"]["deployment"]["revision"],
            "atlas-dashboard-stg-00071-n4v",
        )
        self.assertEqual(
            data["workspace"]["deployment"]["service"],
            "atlas-dashboard-stg",
        )

    def test_dashboard_exposes_news_summary_on_open_positions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {},
                        "securities": {
                            "SPY": {
                                "status": "available",
                                "company_name": "SPDR S&P 500 ETF Trust",
                                "sector": "Benchmark ETF",
                                "category": "Core",
                                "price": 500,
                                "percent_change": 1.2,
                            },
                            "QQQ": {
                                "status": "available",
                                "company_name": "Invesco QQQ Trust",
                                "sector": "Benchmark ETF",
                                "category": "Core",
                                "price": 400,
                                "percent_change": 0.4,
                            },
                            "IWM": {
                                "status": "available",
                                "company_name": "iShares Russell 2000 ETF",
                                "sector": "Benchmark ETF",
                                "category": "Watchlist",
                                "price": 210,
                                "percent_change": -0.3,
                            },
                            "RSP": {
                                "status": "available",
                                "company_name": "Invesco S&P 500 Equal Weight ETF",
                                "sector": "Benchmark ETF",
                                "category": "Core",
                                "price": 180,
                                "percent_change": 0.8,
                            },
                            "AAA": {
                                "status": "available",
                                "company_name": "Alpha",
                                "sector": "Software",
                                "category": "Core",
                                "price": 100,
                                "percent_change": 5,
                                "total_score": 90,
                                "momentum_metrics": {
                                    "trend_quality_score": 78.5,
                                    "trend_regime": "leadership",
                                    "trend_regime_score": 84.0,
                                    "trend_state": "uptrend",
                                    "price_vs_sma_50_pct": 6.2,
                                    "price_vs_sma_200_pct": 14.4,
                                    "ema_20_slope_pct": 3.1,
                                    "rsi_14": 63.0,
                                    "distance_from_52w_high_pct": -2.8,
                                },
                                "news_signal": {
                                    "signal_label": "supportive",
                                    "signal_score": 82,
                                    "positive_count": 2,
                                    "negative_count": 0,
                                    "company_headline_count": 2,
                                    "dominant_event_type": "guidance_raise",
                                    "high_impact_positive_count": 1,
                                    "positive_examples": ["Alpha raised guidance."],
                                },
                            },
                            "BBB": {
                                "status": "available",
                                "company_name": "Beta",
                                "sector": "Software",
                                "category": "Watchlist",
                                "price": 50,
                                "percent_change": 1.0,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            paper = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
                clock=iter(
                    [
                        datetime(2026, 6, 27, 9, 30, 0),
                        datetime(2026, 6, 27, 9, 31, 0),
                        datetime(2026, 6, 27, 9, 32, 0),
                        datetime(2026, 6, 27, 9, 33, 0),
                        datetime(2026, 6, 27, 9, 34, 0),
                    ]
                ).__next__,
            )
            paper.initialize(100000)
            proposal = paper.create_proposal("buy", "AAA", 1, 100, "Paper entry.")
            paper.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            paper.decide_proposal(proposal["proposal_id"], "approve")
            paper.execute_order(
                "buy",
                "AAA",
                1,
                100,
                "Paper entry.",
                proposal_id=proposal["proposal_id"],
            )
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=paper,
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )

            data = service.build()

        self.assertEqual(
            data["paper"]["positions"][0]["news_summary"]["label"],
            "supportive",
        )
        self.assertIn(
            "2 positive and 0 negative",
            data["paper"]["positions"][0]["news_summary"]["headline"],
        )
        self.assertIn(
            "Main event read: guidance raise.",
            data["paper"]["positions"][0]["news_summary"]["event_detail"],
        )
        self.assertIn(
            "high-impact supportive news",
            data["paper"]["positions"][0]["news_summary"]["event_detail"],
        )
        self.assertEqual(
            data["paper"]["positions"][0]["trend_summary"]["trend_regime"],
            "leadership",
        )
        self.assertIn(
            "continued outperformance",
            data["paper"]["positions"][0]["trend_summary"]["headline"],
        )
        self.assertEqual(
            data["paper"]["positions"][0]["trend_summary"]["stats"][0]["label"],
            "Trend quality",
        )
        self.assertIn(
            "leading the strongest benchmark tape",
            data["paper"]["positions"][0]["confirmation_summary"]["headline"],
        )
        self.assertEqual(
            data["paper"]["positions"][0]["confirmation_summary"]["strongest_benchmark"],
            "SPY",
        )
        self.assertEqual(
            data["paper"]["positions"][0]["confirmation_summary"]["stats"][1]["label"],
            "Sector average",
        )

    def test_dashboard_enriches_positions_and_activity_with_research_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {},
                        "securities": {
                            "NVDA": {
                                "status": "available",
                                "company_name": "NVIDIA Corporation",
                                "sector": "AI & Semiconductors",
                                "category": "Core",
                                "price": 110,
                                "percent_change": 2.5,
                                "total_score": 91,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            paper = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
                clock=iter(
                    [
                        datetime(2026, 6, 27, 9, 30, 0),
                        datetime(2026, 6, 27, 9, 31, 0),
                        datetime(2026, 6, 27, 9, 32, 0),
                        datetime(2026, 6, 27, 16, 0, 0),
                        datetime(2026, 6, 28, 16, 0, 0),
                        datetime(2026, 6, 29, 9, 30, 0),
                        datetime(2026, 6, 30, 9, 30, 0),
                        datetime(2026, 7, 1, 9, 30, 0),
                    ]
                ).__next__,
            )
            paper.initialize(100000)
            buy = paper.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "NVDA remains a high-conviction paper entry.",
                rationale=["Atlas score is above the buy threshold."],
            )
            paper.record_proposal_risk_review(
                buy["proposal_id"],
                "caution",
                ["valuation is stretched"],
            )
            paper.decide_proposal(buy["proposal_id"], "approve")
            paper.execute_order(
                "buy",
                "NVDA",
                10,
                100,
                "NVDA remains a high-conviction paper entry.",
                proposal_id=buy["proposal_id"],
            )
            paper.record_performance_snapshot(
                prices={"NVDA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            paper.record_performance_snapshot(
                prices={"NVDA": 110},
                benchmark_prices={"SPY": 505, "QQQ": 404},
            )
            paper.record_position_review(
                "NVDA",
                "review",
                current_price=110,
                return_pct=10.0,
                atlas_score=91.0,
                flags=[
                    "Projection caution triggered: Atlas wants more proof because benchmark leadership, sector participation, or news tone is no longer clearly supportive."
                ],
                thesis="Monitor the position more closely.",
            )
            tasks = ResearchTaskQueue(root / "tasks" / "tasks.json")
            task, _ = tasks.add_task(
                role="CRO",
                subject="NVDA",
                prompt="Review downside catalyst.",
                priority="high",
            )
            tasks.complete_research(
                task["id"],
                conclusion="Fresh risk review.",
                recommendation="risk_review",
                confidence="medium",
                catalyst_type="score_risk",
                thesis_alignment="risk_to_thesis",
                thesis_drift="new_risk",
                evidence=[
                    {
                        "title": "NVDA thesis history",
                        "source": "Atlas research task memory",
                        "detail": "Prior risk review",
                    }
                ],
            )
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=paper,
                research_queue=tasks,
            )

            data = service.build()

        position = data["paper"]["positions"][0]
        self.assertIn("stored review", position["research_memory"]["summary"])
        self.assertIn("risk to thesis", position["research_memory"]["detail"])
        journal = " ".join(position["decision_journal"])
        self.assertIn("Current basis is $100.00", journal)
        self.assertIn("Since the latest buy fill, NVDA is +10.00% versus SPY +1.00% and QQQ +1.00%.", journal)
        self.assertIn("Latest thesis review (", journal)
        self.assertIn("Projection caution triggered", journal)
        self.assertIn("move from hold toward trim or exit", journal)
        outcome = position["outcome_summary"]
        self.assertIn("genuine leader", outcome["headline"])
        self.assertIn("beating the stronger benchmark by +9.00%", outcome["detail"])
        projection = position["projection_summary"]
        self.assertIn("upside can continue", projection["headline"])
        self.assertIn("ahead of the market by +9.00% since entry", projection["detail"])
        self.assertTrue(projection["watchpoints"])
        self.assertIn("A shift toward adverse company-specific news", projection["watchpoints"][-1])
        self.assertIn(
            "Atlas is currently pacing the paper book around",
            position["adaptive_context"][0],
        )
        self.assertIn(
            "Atlas is still auto-picking the stronger benchmark tape",
            position["adaptive_context"][1],
        )
        self.assertEqual(position["decision_driver"]["label"], "Projection caution")
        activity = data["paper"]["activity"][0]
        combined = " ".join(activity["decision_context"])
        self.assertIn(
            "Latest stored Atlas review still marked NVDA as risk to thesis",
            combined,
        )
        self.assertIn(
            "Evidence on file at execution: NVDA thesis history.",
            combined,
        )
        self.assertIn("Execution risk review: valuation is stretched.", combined)

    def test_static_routes_are_explicit_and_read_only(self):
        self.assertEqual(set(STATIC_FILES), {"/", "/index.html", "/styles.css", "/app.js"})

    def test_dashboard_exposes_normalized_corporate_actions(self):
        rows = DashboardDataService._corporate_actions(
            {
                "KLAC": {
                    "corporate_actions": {
                        "splits": [
                            {
                                "date": "2026-06-12T13:30:00+00:00",
                                "ratio": 10.0,
                                "split_ratio": "10:1",
                                "source": "yahoo_chart_event",
                            }
                        ]
                    }
                }
            }
        )

        self.assertEqual(rows[0]["ticker"], "KLAC")
        self.assertEqual(rows[0]["ratio"], "10:1")
        self.assertTrue(rows[0]["normalized"])

    def test_dashboard_position_thesis_status_states(self):
        healthy = DashboardDataService._position_thesis_status(
            {"shares": 10},
            {"verdict": "maintain", "flags": [], "atlas_score": 88.0},
            None,
        )
        watch = DashboardDataService._position_thesis_status(
            {"shares": 10},
            {
                "verdict": "review",
                "flags": ["Benchmark review triggered: lagging."],
                "atlas_score": 68.0,
            },
            None,
        )
        trim = DashboardDataService._position_thesis_status(
            {"shares": 10},
            {"verdict": "maintain", "flags": [], "atlas_score": 88.0},
            {"side": "sell", "shares": 5, "status": "approved"},
        )
        exit_state = DashboardDataService._position_thesis_status(
            {"shares": 10},
            {"verdict": "exit", "flags": ["Exit rule triggered."], "atlas_score": 55.0},
            {"side": "sell", "shares": 10, "status": "pending"},
        )

        self.assertEqual(healthy["label"], "healthy")
        self.assertIn("Atlas score 88.0", healthy["summary"])
        self.assertEqual(watch["label"], "watch")
        self.assertIn("Benchmark review triggered", watch["summary"])
        self.assertEqual(trim["label"], "trim")
        self.assertIn("5 of 10 shares", trim["summary"])
        self.assertEqual(exit_state["label"], "exit")
        self.assertIn("active simulated exit proposal", exit_state["summary"])

    def test_dashboard_builds_thesis_overview_counts_and_priority(self):
        overview = DashboardDataService._thesis_overview(
            [
                {
                    "ticker": "AAA",
                    "market_value": 1000,
                    "thesis_status": {"label": "healthy", "summary": "Constructive."},
                },
                {
                    "ticker": "BBB",
                    "market_value": 800,
                    "thesis_status": {"label": "watch", "summary": "Needs review."},
                },
                {
                    "ticker": "CCC",
                    "market_value": 700,
                    "thesis_status": {"label": "trim", "summary": "Reduce."},
                },
                {
                    "ticker": "DDD",
                    "market_value": 600,
                    "thesis_status": {"label": "exit", "summary": "Close."},
                },
            ]
        )

        self.assertEqual(overview["counts"]["healthy"], 1)
        self.assertEqual(overview["counts"]["watch"], 1)
        self.assertEqual(overview["counts"]["trim"], 1)
        self.assertEqual(overview["counts"]["exit"], 1)
        self.assertEqual(
            [item["ticker"] for item in overview["attention"]],
            ["DDD", "CCC", "BBB", "AAA"],
        )

    def test_dashboard_builds_position_ladder_groups(self):
        ladder = DashboardDataService._position_ladder(
            [
                {
                    "ticker": "AAA",
                    "market_value": 1000,
                    "unrealized_gain_loss": 50,
                    "thesis_status": {"label": "healthy", "summary": "Constructive."},
                },
                {
                    "ticker": "BBB",
                    "market_value": 800,
                    "unrealized_gain_loss": -25,
                    "thesis_status": {"label": "watch", "summary": "Needs review."},
                },
                {
                    "ticker": "CCC",
                    "market_value": 700,
                    "unrealized_gain_loss": -50,
                    "thesis_status": {"label": "trim", "summary": "Reduce."},
                },
                {
                    "ticker": "DDD",
                    "market_value": 600,
                    "unrealized_gain_loss": -90,
                    "thesis_status": {"label": "exit", "summary": "Close."},
                },
            ]
        )

        self.assertEqual([item["label"] for item in ladder], [
            "Hold steady",
            "Watch closely",
            "Trim candidate",
            "Exit candidate",
        ])
        self.assertEqual(ladder[0]["count"], 1)
        self.assertEqual(ladder[0]["items"][0]["ticker"], "AAA")
        self.assertEqual(ladder[1]["items"][0]["ticker"], "BBB")
        self.assertEqual(ladder[2]["items"][0]["ticker"], "CCC")
        self.assertEqual(ladder[3]["items"][0]["ticker"], "DDD")

    def test_dashboard_builds_portfolio_focus_summary(self):
        focus = DashboardDataService._portfolio_focus(
            [
                {
                    "ticker": "AAA",
                    "market_value": 1000,
                    "unrealized_gain_loss": 50,
                    "thesis_status": {"label": "healthy", "summary": "Constructive."},
                    "decision_driver": {"label": "Projection leadership"},
                },
                {
                    "ticker": "BBB",
                    "market_value": 800,
                    "unrealized_gain_loss": -25,
                    "thesis_status": {"label": "watch", "summary": "Needs review."},
                    "decision_driver": {"label": "Projection caution"},
                },
                {
                    "ticker": "CCC",
                    "market_value": 700,
                    "unrealized_gain_loss": -50,
                    "thesis_status": {"label": "trim", "summary": "Reduce."},
                    "decision_driver": {"label": "Projection de-risk"},
                },
            ]
        )

        self.assertEqual(focus["headline"], "Atlas wants to reduce exposure in part of the paper book.")
        self.assertEqual(focus["counts"]["healthy"], 1)
        self.assertEqual(focus["counts"]["watch"], 1)
        self.assertEqual(focus["counts"]["trim"], 1)
        self.assertEqual(focus["highlights"][0]["ticker"], "CCC")
        self.assertEqual(focus["highlights"][0]["anchor_id"], "")
        self.assertEqual(focus["highlights"][0]["decision_driver"]["label"], "Projection de-risk")
        self.assertEqual(focus["highlights"][1]["ticker"], "BBB")

    def test_dashboard_groups_trade_history_by_ticker(self):
        history = DashboardDataService._group_trade_history(
            [
                {
                    "ticker": "NVDA",
                    "timestamp": "2026-07-03T09:31:00",
                    "side": "sell",
                    "action_label": "trim",
                    "shares": 5,
                    "fill_price": 150,
                    "realized_gain_loss": 20,
                    "summary": "Trimmed NVDA.",
                    "thesis": "Trim thesis.",
                    "decision_context": ["Exit rule."],
                },
                {
                    "ticker": "NVDA",
                    "timestamp": "2026-07-03T09:30:00",
                    "side": "buy",
                    "action_label": "purchase",
                    "shares": 10,
                    "fill_price": 120,
                    "realized_gain_loss": 0,
                    "summary": "Bought NVDA.",
                    "thesis": "Buy thesis.",
                    "decision_context": [],
                },
                {
                    "ticker": "AMD",
                    "timestamp": "2026-07-02T09:30:00",
                    "side": "buy",
                    "action_label": "purchase",
                    "shares": 8,
                    "fill_price": 100,
                    "realized_gain_loss": 0,
                    "summary": "Bought AMD.",
                    "thesis": "AMD thesis.",
                    "decision_context": [],
                },
            ]
        )

        self.assertEqual(history["total_trades"], 3)
        self.assertEqual(history["ticker_count"], 2)
        self.assertEqual(history["tickers"][0]["ticker"], "NVDA")
        self.assertEqual(history["tickers"][0]["trade_count"], 2)
        self.assertEqual(history["tickers"][0]["buy_count"], 1)
        self.assertEqual(history["tickers"][0]["sell_count"], 1)
        self.assertEqual(history["tickers"][0]["rows"][0]["action_label"], "trim")

    def test_dashboard_includes_accountability_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {},
                        "securities": {
                            "NVDA": {
                                "status": "available",
                                "company_name": "NVIDIA Corporation",
                                "sector": "AI & Semiconductors",
                                "category": "Core",
                                "price": 130,
                                "percent_change": 1.5,
                                "total_score": 90,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            paper = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
                clock=iter(
                    [
                        datetime(2026, 6, 27, 9, 30, 0),
                        datetime(2026, 6, 27, 9, 31, 0),
                        datetime(2026, 6, 27, 9, 32, 0),
                        datetime(2026, 6, 27, 9, 33, 0),
                        datetime(2026, 6, 27, 9, 34, 0),
                        datetime(2026, 6, 27, 9, 35, 0),
                        datetime(2026, 6, 27, 9, 36, 0),
                        datetime(2026, 6, 27, 9, 37, 0),
                        datetime(2026, 6, 27, 9, 38, 0),
                        datetime(2026, 6, 27, 9, 39, 0),
                    ]
                ).__next__,
            )
            paper.initialize(100000)
            buy = paper.create_proposal(
                "buy",
                "NVDA",
                10,
                100,
                "Buy.",
                rationale=[
                    "Atlas classifies the dominant event as product launch.",
                    "Projection watch remains supportive with 75% sector breadth and a leadership trend posture.",
                ],
            )
            paper.record_proposal_risk_review(buy["proposal_id"], "clear", [])
            paper.decide_proposal(buy["proposal_id"], "approve")
            paper.execute_order("buy", "NVDA", 10, 100, "Buy.", proposal_id=buy["proposal_id"])
            sell = paper.create_proposal("sell", "NVDA", 4, 130, "Trim.")
            paper.record_proposal_risk_review(sell["proposal_id"], "clear", [])
            paper.decide_proposal(sell["proposal_id"], "approve")
            paper.execute_order("sell", "NVDA", 4, 130, "Trim.", proposal_id=sell["proposal_id"])
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=paper,
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )

            data = service.build()

        report = data["paper"]["accountability_report"]
        self.assertEqual(report["summary"]["tickers"], 1)
        self.assertEqual(report["summary"]["transactions"], 2)
        self.assertEqual(report["tickers"][0]["ticker"], "NVDA")
        self.assertEqual(report["tickers"][0]["transactions"][0]["side"], "buy")
        self.assertEqual(
            report["tickers"][0]["transactions"][0]["news_event_summary"],
            "product launch",
        )
        self.assertEqual(
            report["tickers"][0]["transactions"][0]["decision_driver"]["label"],
            "Projection-supported add",
        )
        self.assertIn(
            "daily trade cap",
            report["tickers"][0]["transactions"][0]["adaptive_regime"],
        )
        self.assertEqual(report["tickers"][0]["transactions"][1]["side"], "sell")

    def test_dashboard_builds_capital_rotation_scoreboard_by_sector(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {},
                        "securities": {
                            "AAA": {
                                "status": "available",
                                "company_name": "Alpha",
                                "sector": "Software",
                                "category": "Core",
                                "price": 115,
                                "percent_change": 2.0,
                                "total_score": 92,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            paper = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
                clock=iter(
                    datetime(2026, 6, 27, 9, minute, 0)
                    for minute in range(30, 50)
                ).__next__,
            )
            paper.initialize(100000)
            buy = paper.create_proposal("buy", "AAA", 10, 100, "Software entry.")
            paper.record_proposal_risk_review(buy["proposal_id"], "clear", [])
            paper.decide_proposal(buy["proposal_id"], "approve")
            paper.execute_order(
                "buy",
                "AAA",
                10,
                100,
                "Software entry.",
                proposal_id=buy["proposal_id"],
            )
            paper.record_performance_snapshot(
                prices={"AAA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            paper.record_performance_snapshot(
                prices={"AAA": 115},
                benchmark_prices={"SPY": 505, "QQQ": 408},
            )
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=paper,
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )

            data = service.build()

        scoreboard = data["paper"]["capital_rotation_scoreboard"]
        self.assertTrue(scoreboard["available"])
        self.assertIn("simulated capital support", scoreboard["headline"])
        self.assertEqual(scoreboard["totals"]["open_market_value"], 1150)
        self.assertEqual(scoreboard["totals"]["buy_notional"], 1000)
        self.assertEqual(scoreboard["totals"]["buy_working_rate_pct"], 100.0)
        software = scoreboard["sectors"][0]
        self.assertEqual(software["sector"], "Software")
        self.assertEqual(software["open_positions"], 1)
        self.assertEqual(software["posture"], "press")
        self.assertEqual(software["avg_benchmark_edge_pct"], 13.0)

    def test_dashboard_exposes_sector_learning_bridge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "market_summary": {},
                        "securities": {
                            "AAA": {
                                "status": "available",
                                "sector": "Software",
                                "category": "Core",
                                "price": 116,
                                "percent_change": 2.0,
                                "total_score": 92,
                            },
                            "BBB": {
                                "status": "available",
                                "sector": "Software",
                                "category": "Core",
                                "price": 114,
                                "percent_change": 1.8,
                                "total_score": 91,
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            paper = PaperTradingAccount(
                account_file=root / "paper" / "account.json",
                ledger_file=root / "paper" / "ledger.jsonl",
                clock=iter(
                    datetime(2026, 6, 27, 9, minute, 0)
                    for minute in range(30, 60)
                ).__next__,
            )
            paper.initialize(100000)
            for ticker in ("AAA", "BBB"):
                proposal = paper.create_proposal(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"{ticker} Software entry.",
                )
                paper.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
                paper.decide_proposal(proposal["proposal_id"], "approve")
                paper.execute_order(
                    "buy",
                    ticker,
                    10,
                    100,
                    f"{ticker} Software entry.",
                    proposal_id=proposal["proposal_id"],
                )
            paper.record_performance_snapshot(
                prices={"AAA": 100, "BBB": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            paper.record_performance_snapshot(
                prices={"AAA": 108, "BBB": 107},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            paper.record_performance_snapshot(
                prices={"AAA": 112, "BBB": 111},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            paper.record_performance_snapshot(
                prices={"AAA": 116, "BBB": 114},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=paper,
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )

            data = service.build()

        bridge = data["paper"]["feedback_summary"]["sector_learning_bridge"]
        self.assertTrue(bridge["active"])
        self.assertEqual(bridge["sectors"][0]["sector"], "Software")
        self.assertEqual(bridge["sectors"][0]["adjustment"], 1.5)
        self.assertEqual(bridge["sectors"][0]["working"], 2)
        gate_audit = data["paper"]["feedback_summary"]["sector_gate_audit"]
        self.assertTrue(gate_audit["enabled"])
        self.assertIn("candidate_counts", gate_audit)
        self.assertIn("accepted_decision_counts", gate_audit)

    def test_verification_model_keeps_benchmark_learning_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive = root / "archive"
            archive.mkdir()
            (archive / "snapshot_20260606_120000.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-06T12:00:00",
                        "securities": {
                            "AAA": {
                                "status": "available",
                                "price": 116,
                                "sector": "Software",
                            },
                            "SPY": {
                                "status": "available",
                                "price": 506,
                                "sector": "Benchmark ETF",
                            },
                            "QQQ": {
                                "status": "available",
                                "price": 406,
                                "sector": "Benchmark ETF",
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            account = PaperTradingAccount(
                account_file=root / "account.json",
                ledger_file=root / "ledger.jsonl",
                clock=lambda: datetime(2026, 6, 6, 9, 30, 0),
            )
            account.initialize(100000)
            proposal = account.create_proposal("buy", "AAA", 10, 100, "Entry.")
            account.record_proposal_risk_review(proposal["proposal_id"], "clear", [])
            account.decide_proposal(proposal["proposal_id"], "approve")
            account.execute_order(
                "buy",
                "AAA",
                10,
                100,
                "Entry.",
                proposal_id=proposal["proposal_id"],
            )
            account.record_performance_snapshot(
                prices={"AAA": 100},
                benchmark_prices={"SPY": 500, "QQQ": 400},
            )
            account.record_performance_snapshot(
                prices={"AAA": 108},
                benchmark_prices={"SPY": 503, "QQQ": 403},
            )
            account.record_performance_snapshot(
                prices={"AAA": 112},
                benchmark_prices={"SPY": 505, "QQQ": 405},
            )
            account.record_performance_snapshot(
                prices={"AAA": 116},
                benchmark_prices={"SPY": 506, "QQQ": 406},
            )
            service = DashboardDataService(
                archive_dir=archive,
                paper_account=account,
                research_queue=ResearchTaskQueue(root / "tasks.json"),
            )

            data = service.build_verification()

        summary = data["paper"]["feedback_summary"]
        self.assertIn("benchmark_scorecard", summary)
        self.assertIn("benchmark_exit_stats", summary["projection_threshold_profile"])
        self.assertIn("benchmark_rotation_stats", summary["entry_strategy_profile"])
        self.assertIn("sector_gate_outcomes", summary)
        self.assertIn("scorecards", summary["sector_gate_outcomes"])

    def test_dashboard_builds_paper_position_anchor(self):
        self.assertEqual(
            DashboardDataService._paper_position_anchor_id("ANET"),
            "paper-position-anet",
        )
        self.assertEqual(
            DashboardDataService._paper_position_anchor_id("BRK.B"),
            "paper-position-brk-b",
        )

    def test_browser_labels_local_and_cloud_environments(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        script = (root / "web" / "app.js").read_text(encoding="utf-8")
        service_source = (root / "app" / "web_dashboard.py").read_text(
            encoding="utf-8"
        )
        styles = (root / "web" / "styles.css").read_text(encoding="utf-8")
        dashboard = (root / "app" / "web_dashboard.py").read_text(encoding="utf-8")
        paper_trading = (root / "app" / "paper_trading.py").read_text(encoding="utf-8")
        self.assertIn('id="workspace-status"', html)
        self.assertIn('id="data-freshness"', html)
        self.assertIn('id="sign-out"', html)
        self.assertIn('/styles.css?v=20260811-counted-ideas', html)
        self.assertIn('/app.js?v=20260814-entry-experiment-result', html)
        self.assertIn('id="ideas-action-count"', html)
        self.assertIn('id="ideas-universe-count"', html)
        self.assertIn("Current decision load", script)
        self.assertIn("active paper decision", script)
        self.assertIn(".recommendation-decision-status", styles)
        self.assertIn("section.hidden = sectionName !== recommendationView", script)
        self.assertIn('id="performance-summary"', html)
        self.assertIn("View performance history", html)
        self.assertIn("Current result", script)
        self.assertIn("In line with", script)
        self.assertIn("Compared with the stronger benchmark", script)
        self.assertIn(".performance-summary", styles)
        self.assertIn("Defensive trigger shadow test", script)
        self.assertIn("No policy change", script)
        self.assertIn(".paper-shadow-analysis", styles)
        self.assertIn("Prospective review tracker", script)
        self.assertIn("Needs attention", script)
        self.assertIn("Why this priority", script)
        self.assertIn("Priority ranks owner attention only", script)
        self.assertIn(".paper-review-priority", styles)
        self.assertIn("Priority escalation watch", script)
        self.assertIn("No new elevated-priority changes", script)
        self.assertIn("Routine score drift is omitted", script)
        self.assertIn(".paper-priority-escalation-strip", styles)
        self.assertIn("Elevated episode evidence", script)
        self.assertIn("No elevated warning episodes recorded yet", script)
        self.assertIn("Episode duration is observational evidence", script)
        self.assertIn(".paper-escalation-duration", styles)
        self.assertIn("Starts next snapshot", script)
        self.assertIn(".paper-prospective-tracker", styles)
        self.assertIn("Review signal effectiveness", script)
        self.assertIn("What happened after each warning", script)
        self.assertIn("Benchmark-adjusted separation", script)
        self.assertIn("Stronger benchmark", script)
        self.assertIn("does not claim the benchmark caused", script)
        self.assertIn("Confirmed outcome span", script)
        self.assertIn("Recovery first appeared", script)
        self.assertIn("First above trigger", script)
        self.assertIn("can be temporary", script)
        self.assertIn("Recovery durability gap", script)
        self.assertIn("Recovery quality", script)
        self.assertIn("sustained recovery and relapse frequency", script)
        self.assertIn(".paper-signal-timing", styles)
        self.assertIn("These are observed price paths after a review signal", script)
        self.assertIn("Passing these gates permits owner review only", script)
        self.assertIn(".paper-effectiveness-scorecard", styles)
        self.assertIn(".paper-signal-comparison", styles)
        self.assertIn(".paper-signal-outcome", styles)
        self.assertIn('id="owner-signal-digest"', html)
        self.assertIn("Priority escalation watch", script)
        self.assertIn("signalDigest.hidden = !hasEscalations && !entryMilestone", script)
        self.assertIn(".owner-signal-digest-list", styles)
        self.assertIn('href="#about"', html)
        self.assertIn('aria-label="Open Atlas today page"', html)
        self.assertNotIn('href="#market"', html)
        self.assertNotIn('data-page="market"', html)
        self.assertIn('id="about"', html)
        self.assertIn('class="atlas-logo"', html)
        self.assertIn("Research with a map, a summit, and a scoreboard", html)
        self.assertIn("Purpose, function, and goals", html)
        self.assertIn("maximize long-term returns", html)
        self.assertIn("Beat the major benchmarks over time", html)
        self.assertNotIn("Stage 5 validation scoreboard", html)
        self.assertNotIn("Original roadmap focus", html)
        self.assertIn("original Stage 5 checkpoint", html)
        self.assertIn("Real-capital discussion gate", script)
        self.assertIn("ready_for_owner_review", script)
        self.assertIn("overview-validation-summary", html)
        self.assertIn("What matters now", html)
        self.assertIn('href="#overview">Today</a>', html)
        self.assertIn('href="#recommendations">Ideas</a>', html)
        self.assertIn('href="#research">Reports</a>', html)
        self.assertIn('class="nav-more"', html)
        self.assertIn('id="owner-briefing-grid"', html)
        self.assertIn("Today&rsquo;s decision inbox", html)
        self.assertIn('id="today-decision-inbox"', html)
        self.assertIn('id="today-latest-paper-action"', html)
        self.assertIn('id="owner-report-status"', html)
        self.assertIn('id="owner-latest-report-link"', html)
        self.assertIn('id="page-title"', html)
        self.assertIn('id="page-description"', html)
        self.assertIn("paper-validation-summary", html)
        self.assertIn("capital-rotation-scoreboard", html)
        self.assertIn("Secure owner cloud", script)
        self.assertIn("Local read-only workspace", script)
        self.assertIn("window.location.hostname", script)
        self.assertIn("initializeHelpPopovers", script)
        self.assertIn('popover.querySelector("summary")', script)
        self.assertIn("mouseleave", script)
        self.assertIn("pointerdown", script)
        self.assertIn("scheduleClose", script)
        self.assertIn('event.key !== "Escape"', script)
        self.assertIn('id="access"', html)
        self.assertIn('href="#roadmap"', html)
        self.assertIn('id="roadmap"', html)
        self.assertIn('data-page="roadmap"', html)
        self.assertIn("Autonomy roadmap", html)
        self.assertIn("Web platform roadmap", html)
        self.assertIn("Estimated overall completion", html)
        self.assertIn("Current authority boundary", html)
        self.assertIn('id="roadmap-snapshots"', html)
        self.assertIn('id="roadmap-stage5-progress"', html)
        self.assertIn("renderRoadmap", script)
        self.assertIn('id="paper-entry-evidence"', html)
        self.assertIn('id="roadmap-entry-evidence"', html)
        self.assertIn("renderEntryEvidenceGate", script)
        self.assertIn("New simulated buys are automatically paused", script)
        self.assertIn("Atlas will wait before adding positions; sell protections still run", script)
        self.assertIn(".entry-evidence-gate", styles)
        self.assertIn(".roadmap-timeline", styles)
        self.assertIn(".roadmap-live-evidence", styles)
        self.assertIn('id="recommendations"', html)
        self.assertIn('data-page="recommendations"', html)
        self.assertIn("Buy recommendations", html)
        self.assertIn("Sell or trim recommendations", html)
        self.assertIn("recommended-exits", html)
        self.assertIn("overview-recommended-exits", html)
        self.assertIn("Currently in the Atlas list", html)
        self.assertIn("What Simulate fill does", html)
        self.assertIn("No brokerage order is sent", html)
        self.assertIn("Recommendation performance", html)
        self.assertIn("paper-feedback-summary", html)
        self.assertIn("paper-feedback", html)
        self.assertIn("later market behavior", html)
        self.assertIn("S&amp;P 500 ETF benchmark", html)
        self.assertIn("Nasdaq-100 ETF benchmark", html)
        self.assertIn("Recent simulated actions", html)
        self.assertIn("five most recent simulated buys and sells", html)
        self.assertIn("How Atlas is learning", html)
        self.assertIn("rows.slice(0, 5)", script)
        self.assertIn('target?.matches("details")', script)
        self.assertIn("paper-activity", html)
        self.assertIn("Paper portfolio at a glance", html)
        self.assertIn('id="paper-workspace-summary"', html)
        self.assertIn('id="paper-positions-panel"', html)
        self.assertIn('id="paper-activity-panel"', html)
        self.assertIn('id="paper-learning-panel"', html)
        self.assertIn("Open thesis status detail", html)
        self.assertIn("Open full action ladder", html)
        self.assertIn("renderPaperWorkspaceSummary", script)
        self.assertIn("Positions requiring attention", script)
        self.assertIn("Latest simulated action", script)
        self.assertIn("View position evidence", script)
        self.assertIn("Why Atlas acted", script)
        self.assertIn("data-paper-section", script)
        self.assertIn(".paper-summary-grid", styles)
        self.assertIn(".paper-priority-grid", styles)
        self.assertIn(".paper-evidence-roadmap", styles)
        self.assertIn("What Stage 5 needs next", script)
        self.assertIn(".paper-evidence-pipeline", styles)
        self.assertIn("Evidence pipeline", script)
        self.assertIn("Completed position diagnosis", script)
        self.assertIn("completed_position_diagnostics", paper_trading)
        self.assertIn(".paper-loss-diagnostic", styles)
        self.assertIn("Late risk response", script)
        self.assertIn("judgment_coverage_pct", script)
        self.assertIn("Completed positions", script)
        self.assertIn("partial_trims", script)
        self.assertIn("Trim escalation", service_source)
        self.assertIn("evidence maturity", script)
        self.assertIn("readiness.next_milestones", script)
        self.assertIn("It is not a time estimate and cannot enable real trading", script)
        self.assertIn(".paper-disclosure", styles)
        self.assertIn("View trade history", html)
        self.assertIn("Open basis report", html)
        self.assertIn("trade-history-dialog", html)
        self.assertIn("trade-history-content", html)
        self.assertIn("basis-report-dialog", html)
        self.assertIn("export-basis-report", html)
        self.assertIn("position-detail-dialog", html)
        self.assertIn("position-detail-open-basis", html)
        self.assertIn("How Atlas is managing the portfolio", html)
        self.assertIn("paper-operating-mode", html)
        self.assertIn("Portfolio thesis overview", html)
        self.assertIn("thesis-overview", html)
        self.assertIn("Today&rsquo;s decision inbox", html)
        self.assertIn("portfolio-focus", html)
        self.assertIn("What Atlas wants to do next", html)
        self.assertIn("position-ladder", html)
        self.assertIn("Access &amp; security", html)
        self.assertIn('id="access-workspace-summary"', html)
        self.assertIn('id="access-controls-panel"', html)
        self.assertIn('id="access-future-panel"', html)
        self.assertIn('id="recovery-status"', html)
        self.assertIn('id="privacy-export-status"', html)
        self.assertIn('id="account-deletion-status"', html)
        self.assertIn('id="production-review-status"', html)
        self.assertIn("renderAccess", script)
        self.assertIn('id="workspace-identity"', html)
        self.assertIn('id="workspace-revision"', html)
        self.assertIn("renderWorkspace", script)
        self.assertIn("workspace?.deployment?.revision", script)
        self.assertIn("Rev ${revision || \"unknown\"}", script)
        self.assertIn("setActivePage", script)
        self.assertIn('requested === "market" ? "overview" : requested', script)
        self.assertIn("jumpToPageTarget", script)
        self.assertIn("jumpToControlsTarget", script)
        self.assertIn("jumpToPaperTarget", script)
        self.assertIn("renderRecommendations", script)
        self.assertIn("renderRecommendationSummary", script)
        self.assertIn("Atlas auto-review queue", script)
        self.assertIn("Atlas auto-manages this queue", script)
        self.assertIn("Atlas auto-resolved current research recommendations.", script)
        self.assertIn("compareRecommendations", script)
        self.assertIn("recommendationCalibrationAdjustment", script)
        self.assertIn("recommendationJudgedCount", script)
        self.assertIn("renderRationale", script)
        self.assertIn("renderPaperFeedbackSummary", script)
        self.assertIn("renderPaperFeedback", script)
        self.assertIn("renderValidationSummary", script)
        self.assertIn("Stage 5 status", script)
        self.assertIn("benchmarkLabel", script)
        self.assertIn("SPY (S&P 500 ETF benchmark)", script)
        self.assertIn("QQQ (Nasdaq-100 ETF benchmark)", script)
        self.assertIn("Atlas learning readout", script)
        self.assertIn("Buy calibration", script)
        self.assertIn("Sell calibration", script)
        self.assertIn("Adaptive entry pacing", script)
        self.assertIn("entry_strategy_profile", script)
        self.assertIn("Benchmark rotation read", script)
        self.assertIn("Sector learning bridge", script)
        self.assertIn("Sector learning gate", script)
        self.assertIn("sector_learning_bridge", script)
        self.assertIn("Sector gate audit", script)
        self.assertIn("sector_gate_audit", script)
        self.assertIn("Sector gate outcomes", script)
        self.assertIn("sector_gate_outcomes", script)
        self.assertIn("Strategy tilt", script)
        self.assertIn("Adaptive projection tuning", script)
        self.assertIn("Adaptive trade pressure", script)
        self.assertIn("trade_pressure_profile", script)
        self.assertIn("Current daily cap", script)
        self.assertIn("Adaptive benchmark trust", script)
        self.assertIn("benchmark_preference_profile", script)
        self.assertIn("Current benchmark bar", script)
        self.assertIn("Benchmark scorecard", script)
        self.assertIn("benchmark_scorecard", script)
        self.assertIn("Avg decision edge", script)
        self.assertIn("renderCapitalRotationScoreboard", script)
        self.assertIn("Capital rotation scoreboard", script)
        self.assertIn("capital_rotation_scoreboard", script)
        self.assertIn("Benchmark trust", script)
        self.assertIn("adaptive_profiles", script)
        self.assertIn("Adaptive benchmark trust:", script)
        self.assertIn("Adaptive trade pressure:", script)
        self.assertIn("projection_threshold_profile", script)
        self.assertIn("decision_driver_learning", script)
        self.assertIn("sell_trigger_learning", script)
        self.assertIn("horizon_learning", script)
        self.assertIn("feedback-driver-learning", script)
        self.assertIn("Sell trigger", script)
        self.assertIn("judged trims/exits using this trigger are currently helping", script)
        self.assertIn('item.side === "sell"', script)
        self.assertIn('simulated ${escapeHtml(String(item.action_label || "sell"))}', script)
        self.assertIn("Post-sell move", script)
        self.assertIn("Persistence:", script)
        self.assertIn("Snapshot persistence", script)
        self.assertIn("judged trades are still working at this checkpoint", script)
        self.assertIn("renderPaperActivity", script)
        self.assertIn("renderTradeHistory", script)
        self.assertIn("renderAccountabilityReport", script)
        self.assertIn("renderNewsSummary", script)
        self.assertIn("News event", script)
        self.assertIn("Adaptive Regime", script)
        self.assertIn("adaptive_regime", script)
        self.assertIn("<th>Driver</th>", script)
        self.assertIn("Driver Detail", script)
        self.assertIn("renderDecisionDriver(item.decision_driver)", script)
        self.assertIn("news-tone", styles)
        self.assertIn(".capital-rotation-scoreboard", styles)
        self.assertIn(".capital-rotation-card", styles)
        self.assertIn("exportBasisReportCsv", script)
        self.assertIn("openPositionDetailDialog", script)
        self.assertIn("closePositionDetailDialog", script)
        self.assertIn("data-position-detail", script)
        self.assertIn("Open holding", script)
        self.assertIn("lifecycle detail", script)
        self.assertIn("Total lifecycle result", script)
        self.assertIn("openTradeHistoryDialog", script)
        self.assertIn("closeTradeHistoryDialog", script)
        self.assertIn("openBasisReportDialog", script)
        self.assertIn("closeBasisReportDialog", script)
        self.assertIn("Research memory:", script)
        self.assertIn("What changed since entry", script)
        self.assertIn("Atlas context", script)
        self.assertIn("renderPaperOperatingMode", script)
        self.assertIn("renderDashboardSummary", script)
        self.assertIn("DASHBOARD_SUMMARY_CACHE_KEY", script)
        self.assertIn("DASHBOARD_FULL_CACHE_KEY", script)
        self.assertIn("setDataFreshness", script)
        self.assertIn("readCachedDashboardSummary", script)
        self.assertIn("readCachedDashboardFull", script)
        self.assertIn("writeCachedDashboardSummary", script)
        self.assertIn("writeCachedDashboardFull", script)
        self.assertIn("sanitizeDashboardForCache", script)
        self.assertIn("hydrateDashboardFromCache", script)
        self.assertIn("window.localStorage.getItem", script)
        self.assertIn("window.localStorage.setItem", script)
        self.assertIn("delete clone.owner_controls", script)
        self.assertIn("Cached snapshot", script)
        self.assertIn("Refreshing", script)
        self.assertIn("Live", script)
        self.assertIn('/api/dashboard/summary', script)
        self.assertIn("strategy_settings", script)
        self.assertIn("renderStrategyControls", script)
        self.assertIn("policy.adaptive_profiles", script)
        self.assertIn("applyStrategyPreset", script)
        self.assertIn("submitStrategyPolicy", script)
        self.assertIn("paper-policy", script)
        self.assertIn("Benchmark weight", service_source)
        self.assertIn("Sector diversity", service_source)
        self.assertIn("renderThesisOverview", script)
        self.assertIn("renderPortfolioFocus", script)
        self.assertIn("renderOwnerBriefing", script)
        self.assertIn("renderOwnerReportStatus", script)
        self.assertIn("Latest briefing is current", script)
        self.assertIn("Daily briefing needs a freshness check", script)
        self.assertIn("PAGE_METADATA", script)
        self.assertIn("Monitor paper results", script)
        self.assertIn("real-money trading remains disabled", script)
        self.assertIn(".owner-briefing-grid", styles)
        self.assertIn(".owner-report-status", styles)
        self.assertIn(".briefing-link.primary", styles)
        self.assertIn("renderPositionLadder", script)
        self.assertIn("Portfolio action readout", script)
        self.assertIn("Open holding", script)
        self.assertIn("data-paper-target", script)
        self.assertIn("View trade history", script)
        self.assertIn('document.getElementById("overview").addEventListener("click", event => {', script)
        self.assertIn('document.getElementById("open-trade-history").addEventListener("click", openTradeHistoryDialog);', script)
        self.assertIn("Hold steady", script)
        self.assertIn("thesis_status", script)
        self.assertIn("proposalActionLabel", script)
        self.assertIn("proposalImpact", script)
        self.assertIn("proposalControlTitle", script)
        self.assertIn("recommended for paper purchase", script)
        self.assertIn("What needs attention", html)
        self.assertIn("recommendation-summary", html)
        self.assertIn('id="paper-strategy-controls"', html)
        self.assertIn("Use aggressive preset", script)
        self.assertIn("Save Atlas strategy", script)
        self.assertIn("Ready to simulate", script)
        self.assertIn("Buy candidate", script)
        self.assertIn("Trim candidate", script)
        self.assertIn("Exit candidate", script)
        self.assertIn("recommended for simulated ${escapeHtml(proposalActionLabel(item))}", script)
        self.assertIn("Record simulated ${action}", script)
        self.assertIn("exit-tag", styles)
        self.assertIn("exit-panel", styles)
        self.assertIn(".why-now.compact.memory", styles)
        self.assertIn(".portfolio-focus", styles)
        self.assertIn(".position-journal", styles)
        self.assertIn(".position-ladder", styles)
        self.assertIn(".ladder-card", styles)
        self.assertIn(".position-actions", styles)
        self.assertIn(".link-button", styles)
        self.assertIn(".position-detail-dialog", styles)
        self.assertIn(".position-detail-section", styles)
        self.assertIn("Why now", script)
        self.assertIn("Why not", script)
        self.assertIn("What could go wrong", script)
        self.assertIn("renderSellTrigger", script)
        self.assertIn("Trim trigger", script)
        self.assertIn("Exit trigger", script)
        self.assertIn("Why trim", script)
        self.assertIn("Why exit", script)
        self.assertIn("renderObjections", script)
        self.assertIn("Why now rationale", script)
        self.assertIn("created before structured Why now rationale", script)
        self.assertIn("Simulate fill to record the hypothetical", script)
        self.assertIn("Would reduce the simulated holding", script)
        self.assertIn("Would close the full simulated holding", script)
        self.assertIn("current-watchlist", html)
        self.assertIn('id="universe-search"', html)
        self.assertIn('id="universe-category"', html)
        self.assertIn('id="universe-toggle"', html)
        self.assertIn("Atlas scores indicate research priority, not a purchase recommendation.", html)
        self.assertIn("renderUniverseList", script)
        self.assertIn("position warning", script)
        self.assertIn("View evidence", script)
        self.assertIn("Positions Atlas recommends reducing", script)
        self.assertIn(".universe-toolbar", styles)
        self.assertIn(".evidence-disclosure", styles)
        self.assertIn("40% complete", html)
        self.assertIn("access.phase_completion", script)
        self.assertIn('id="corporate-actions"', html)
        self.assertIn("renderCorporateActions", script)
        self.assertIn('id="paper-fill-dialog"', html)
        self.assertIn("openPaperFillDialog", script)
        self.assertIn("SIMULATE ${proposalId}", script)
        self.assertNotIn("window.prompt", script)
        self.assertIn("Review evidence", script)
        self.assertIn("safeExternalUrl", script)
        self.assertIn("Recommendation mode", script)
        self.assertIn("Auto-manage paper portfolio", dashboard)
        self.assertIn("Atlas purchased", paper_trading)
        self.assertIn("Atlas sold", paper_trading)
        self.assertIn("catalyst_type", script)
        self.assertIn("thesis_alignment", script)
        self.assertIn("Thesis alignment:", script)
        self.assertIn("thesis_drift", script)
        self.assertIn("Thesis drift:", script)
        self.assertIn("attention_label", script)
        self.assertIn("Attention drivers:", script)
        self.assertIn('id="daily-action-list"', html)
        self.assertIn('id="control-workspace-summary"', html)
        self.assertIn('id="control-decisions-panel"', html)
        self.assertIn('id="control-strategy-panel"', html)
        self.assertIn('id="control-portfolio-panel"', html)
        self.assertIn('id="controls-summary"', html)
        self.assertIn('id="controls-summary-label"', html)
        self.assertIn('id="portfolio-action-list"', html)
        self.assertIn('id="portfolio-action-count"', html)
        self.assertIn('id="healthy-holdings-list"', html)
        self.assertIn('id="healthy-holdings-count"', html)
        self.assertIn('id="owner-outcomes"', html)
        self.assertIn("controls_summary", script)
        self.assertIn("renderControlWorkspace", script)
        self.assertIn("What Atlas can do now", script)
        self.assertIn("Current paper guardrails", script)
        self.assertIn("Trim escalation", script)
        self.assertIn("maximum_partial_trims_per_position", script)
        self.assertIn("Real trading blocked", script)
        self.assertIn("daily_action_list", script)
        self.assertIn("portfolio_action_queue", script)
        self.assertIn("healthy_holdings_summary", script)
        self.assertIn("owner_outcomes", script)
        self.assertIn("Outcome learning", script)
        self.assertIn("Paper book posture", html)
        self.assertIn("Controls summary", script)
        self.assertIn("Portfolio watch queue", html)
        self.assertIn("Hold-steady holdings", html)
        self.assertIn("Healthy holdings stay out of the ranked queue on purpose", html)
        self.assertIn("Atlas ranks simulated proposals beside open paper holdings", html)
        self.assertIn("Outcome calibration:", script)
        self.assertIn("outcome_calibration", script)
        self.assertIn("renderPaperCalibration", script)
        self.assertIn("Paper learning:", script)
        self.assertIn("paper_calibration", script)
        self.assertIn("Paper learning ${recommendationCalibrationAdjustment(entry.item) >= 0 ? \"+\" : \"\"}", script)
        self.assertIn("function renderTodayDecisionInbox(data)", script)
        self.assertIn("Entry study started", script)
        self.assertIn("Entry study halfway", script)
        self.assertIn("Entry study ready for owner review", script)
        self.assertIn("Review the entry-policy experiment proposal", script)
        self.assertIn('id="entry-experiment-dialog"', html)
        self.assertIn("APPROVE PAPER EXPERIMENT", html)
        self.assertIn("function renderEntryExperimentReview(study)", script)
        self.assertIn('"entry-experiment-decision"', script)
        self.assertIn("Entry experiment started", script)
        self.assertIn("Entry experiment halfway", script)
        self.assertIn("Entry experiment ready for owner review", script)
        self.assertIn("Review the completed entry experiment", script)
        self.assertIn('id="entry-experiment-result-dialog"', html)
        self.assertIn("RETAIN PAPER EXPERIMENT", script)
        self.assertIn("ROLL BACK PAPER EXPERIMENT", script)
        self.assertIn("Retain setting", script)
        self.assertIn("Roll back setting", script)
        self.assertIn('"entry-experiment-result"', script)
        self.assertIn("function renderTodayLatestPaperAction(paper)", script)
        self.assertIn("Latest paper action", script)
        self.assertIn("data-paper-section=\"paper-activity-panel\"", script)
        self.assertIn('document.getElementById("overview").addEventListener("click"', script)
        self.assertIn("<b>Why:</b>", script)
        self.assertIn("<b>Next:</b>", script)
        self.assertIn("research_approval_rate_pct", script)
        self.assertIn("Suggested disposition:", script)
        self.assertIn("Next step:", script)
        self.assertIn("Current paper result:", script)
        self.assertIn("What changed since entry", script)
        self.assertIn("Ranked queue:", script)
        self.assertIn("Freshest shift:", script)
        self.assertIn("item.is_freshest_shift", script)
        self.assertIn("item.freshness_label", script)
        self.assertIn("data-controls-target", script)
        self.assertIn("Open item", script)
        self.assertIn("item.anchor_id", script)
        self.assertIn('id="${escapeHtml(item.anchor_id || "")}"', script)
        self.assertIn('document.getElementById("controls-summary").innerHTML = `\n    <article class="decision-row">', script)
        self.assertIn('document.getElementById("portfolio-action-list").innerHTML = portfolioQueue.map(item => `\n    <article class="decision-row" id="${escapeHtml(item.anchor_id || "")}">', script)
        self.assertIn("Evidence anchor:", script)
        self.assertIn("renderDecisionDriver", script)
        self.assertIn("decision_driver", script)
        self.assertIn("Driver:", script)
        self.assertIn("projection-driver-tag", script)
        self.assertIn("Portfolio context:", script)
        self.assertIn("Paper context:", script)
        self.assertIn("Thesis action:", script)

    def test_dashboard_explains_sections_and_terms(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        script = (root / "web" / "app.js").read_text(encoding="utf-8")
        styles = (root / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("SPY is an ETF commonly used as a broad S&amp;P 500", html)
        self.assertIn("QQQ is an ETF commonly used as a Nasdaq-100", html)
        self.assertIn("SPY tracks the S&amp;P 500 as a broad U.S. large-cap benchmark.", html)
        self.assertIn("QQQ tracks the Nasdaq-100 and is commonly used as a growth and technology benchmark.", html)
        self.assertIn(".projection-driver-tag", styles)
        self.assertIn("Atlas Capital Research is an AI-driven investment research and paper-portfolio operating system", html)
        self.assertIn("Atlas exists to maximize long-term returns", html)
        self.assertIn("Atlas gathers market data, scores securities, compares ideas against benchmarks like SPY and QQQ", html)
        self.assertIn("growth, quality, moat, momentum, and risk", html)
        self.assertIn("largest daily percentage moves", html)
        self.assertIn("Open positions are securities currently held", html)
        self.assertNotIn("About market breadth", html)
        self.assertIn("About research agenda", html)
        self.assertIn("Research priorities at a glance", html)
        self.assertIn('id="research-workspace-summary"', html)
        self.assertIn('id="research-scores-panel"', html)
        self.assertIn('id="research-movers-panel"', html)
        self.assertIn('id="research-sectors-panel"', html)
        self.assertIn('id="research-actions-panel"', html)
        self.assertIn('id="research-agenda-panel"', html)
        self.assertIn("Open score ranking", html)
        self.assertIn("Open watchlist moves", html)
        self.assertIn("Open sector movement detail", html)
        self.assertIn("Open corporate-action detail", html)
        self.assertIn("Open full assignment queue", html)
        self.assertIn("renderResearchWorkspace", script)
        self.assertIn("renderReportArchive", script)
        self.assertIn('data-report-view="latest"', html)
        self.assertIn('data-report-view="history"', html)
        self.assertIn('data-report-view="insights"', html)
        self.assertIn('id="latest-report"', html)
        self.assertIn("renderLatestReport", script)
        self.assertIn("setReportView", script)
        self.assertIn("Open latest report", script)
        self.assertIn("View report history", script)
        self.assertIn('id="report-archive"', html)
        self.assertIn('data-report-filter="daily"', html)
        self.assertIn('id="report-result-count"', html)
        self.assertIn('id="report-archive-toggle"', html)
        self.assertIn("reportArchiveExpanded", script)
        self.assertIn('id="research-priorities-panel"', html)
        self.assertIn("reportArchiveFilter", script)
        self.assertIn("Compare current priorities", script)
        self.assertIn(".report-archive-list", styles)
        self.assertIn(".report-filter-group", styles)
        self.assertIn(".latest-report", styles)
        self.assertIn("What Atlas currently concludes", script)
        self.assertIn("Evidence changing now", script)
        self.assertIn("Assigned follow-up", script)
        self.assertIn("researchTaskAgeLabel", script)
        self.assertIn("Persistent assignment opened", script)
        self.assertIn("Revalidate against current evidence before acting.", script)
        self.assertIn("jumpToResearchTarget", script)
        self.assertIn("data-research-target", script)
        self.assertIn(".research-summary-grid", styles)
        self.assertIn(".research-conclusion-grid", styles)
        self.assertIn(".research-disclosure", styles)
        self.assertIn(".research-more", styles)
        self.assertIn(".control-workspace-panel", styles)
        self.assertIn(".control-summary-grid", styles)
        self.assertIn(".control-disclosure", styles)
        self.assertIn("Paper settings", html)
        self.assertIn("Paper strategy &amp; limits", html)
        self.assertIn('data-control-view="settings"', html)
        self.assertIn('data-control-view="decisions"', html)
        self.assertIn('data-control-view="monitoring"', html)
        self.assertIn("Current policy performance", script)
        self.assertIn("evaluation-period-metrics", script)
        self.assertIn("What is driving the result", script)
        self.assertIn("Idle-cash exposure study", script)
        self.assertIn("Forward entry-constraint study", script)
        self.assertIn("Entry experiment evidence gate", script)
        self.assertIn("duplicate research cycles are ignored", script)
        self.assertIn("exposure-scenario-grid", styles)
        self.assertIn("evaluation-attribution", styles)
        self.assertIn('data-control-section="settings"', html)
        self.assertIn("setControlView", script)
        self.assertIn("control-decisions-count", script)
        self.assertIn("control-monitoring-count", script)
        self.assertIn("--teal:", styles)
        self.assertIn("--teal-dark:", styles)
        self.assertIn("jumpToAccessTarget", script)
        self.assertIn("Owner checks remaining", script)
        self.assertIn("Before inviting anyone else", script)
        self.assertIn("This percentage is not overall Atlas program completion", html)
        self.assertIn(".access-workspace-panel", styles)
        self.assertIn(".access-posture-grid", styles)
        self.assertIn(".access-disclosure", styles)
        self.assertIn("About decision controls", html)
        self.assertIn("About access and security", html)
        self.assertIn(".info-popover", styles)
        self.assertIn(".inline-help", styles)
        self.assertIn(".dashboard-page", styles)
        self.assertIn(".data-freshness.live", styles)
        self.assertIn(".data-freshness.cached", styles)
        self.assertIn(".data-freshness.loading", styles)
        self.assertIn(".active-page", styles)
        self.assertIn(".about-hero-panel", styles)
        self.assertIn(".about-panel", styles)
        self.assertIn(".about-hero", styles)
        self.assertIn(".about-hero-brand", styles)
        self.assertIn(".about-logo", styles)
        self.assertIn(".atlas-logo", styles)
        self.assertIn(".about-grid", styles)
        self.assertIn(".recommendation-row", styles)
        self.assertIn(".recommendation-summary-grid", styles)
        self.assertIn(".recommendation-summary-card", styles)
        self.assertIn("What matters now", html)
        self.assertIn("The current action, portfolio result, and most important item to watch.", html)
        self.assertIn('data-recommendation-view="actions"', html)
        self.assertIn('data-recommendation-view="universe"', html)
        self.assertIn("renderScoreDrivers", script)
        self.assertIn("setRecommendationView", script)
        self.assertIn(".owner-mode-line", styles)
        self.assertIn(".portfolio-more", styles)
        self.assertIn('id="paper-evidence-detail"', html)
        self.assertIn(".recommendation-view-switcher", styles)
        self.assertIn(".score-driver-grid", styles)
        self.assertIn(".atlas-score-badge", styles)
        self.assertIn(".score-universe-row", styles)
        self.assertIn(".row-meta.paper-calibration.supportive", styles)
        self.assertIn(".row-meta.paper-calibration.caution", styles)
        self.assertIn(".ready-tag", styles)
        self.assertIn(".healthy-tag", styles)
        self.assertIn(".freshest-tag", styles)
        self.assertIn(".inline-jump", styles)
        self.assertIn(".watchlist-item", styles)
        self.assertIn(".watchlist-item.core", styles)
        self.assertIn(".simulate-button", styles)
        self.assertIn(".feedback-row", styles)
        self.assertIn(".validation-grid", styles)
        self.assertIn(".validation-spotlight.encouraging", styles)
        self.assertIn(".feedback-driver-card", styles)
        self.assertIn(".activity-row", styles)
        self.assertIn(".basis-table", styles)
        self.assertIn(".basis-summary-grid", styles)
        self.assertIn(".history-button", styles)
        self.assertIn(".history-dialog", styles)
        self.assertIn(".history-ticker", styles)
        self.assertIn(".mode-grid", styles)
        self.assertIn(".mode-option", styles)
        self.assertIn(".why-now", styles)
        self.assertIn(".why-not", styles)
        self.assertIn(".thesis-badge", styles)
        self.assertIn(".thesis-summary", styles)
        self.assertIn(".thesis-overview", styles)
        self.assertIn(".thesis-counts", styles)

    def test_http_server_is_read_only_and_sets_security_headers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = DashboardDataService(
                archive_dir=root / "archive",
                paper_account=PaperTradingAccount(
                    account_file=root / "paper" / "account.json",
                    ledger_file=root / "paper" / "ledger.jsonl",
                ),
                research_queue=ResearchTaskQueue(root / "tasks" / "tasks.json"),
            )
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                create_handler(data_service=service, web_dir=root),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            try:
                with urlopen(f"{base_url}/api/dashboard", timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
                    self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
                    self.assertIn(
                        "frame-ancestors 'none'",
                        response.headers["Content-Security-Policy"],
                    )

                with self.assertRaises(HTTPError) as raised:
                    urlopen(Request(base_url, data=b"{}", method="POST"), timeout=5)
                self.assertEqual(raised.exception.code, 405)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
