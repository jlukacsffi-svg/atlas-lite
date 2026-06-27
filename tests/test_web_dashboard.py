import json
import tempfile
import threading
import unittest
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

        self.assertEqual(data["overview"]["tracked"], 2)
        self.assertEqual(data["overview"]["advancing"], 1)
        self.assertEqual(data["movers"][0]["ticker"], "AAA")
        self.assertEqual(data["score_leaders"][0]["score"], 90)
        self.assertEqual(data["watchlist"][0]["ticker"], "AAA")
        self.assertTrue(data["paper"]["configured"])
        self.assertEqual(data["paper"]["operating_mode"]["current"]["id"], "recommendation_only")
        self.assertEqual(data["paper"]["activity"], [])
        self.assertEqual(data["paper"]["feedback"], [])
        self.assertEqual(data["paper"]["proposals"]["approved"], 1)
        self.assertEqual(data["research"]["open"], 1)
        self.assertEqual(data["corporate_actions"], [])
        self.assertFalse(data["access"]["public_registration"])
        self.assertEqual(data["access"]["mode"], "owner_only")
        self.assertEqual(data["access"]["schema_version"], 3)
        self.assertEqual(data["access"]["phase_completion"], 78)
        self.assertIn("restore drill", data["access"]["recovery"])
        self.assertIn("tenant package", data["access"]["privacy_export"])
        self.assertIn(
            "Owner profile active",
            data["access"]["production_review"],
        )

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

    def test_browser_labels_local_and_cloud_environments(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        script = (root / "web" / "app.js").read_text(encoding="utf-8")
        styles = (root / "web" / "styles.css").read_text(encoding="utf-8")
        dashboard = (root / "app" / "web_dashboard.py").read_text(encoding="utf-8")
        paper_trading = (root / "app" / "paper_trading.py").read_text(encoding="utf-8")
        self.assertIn('id="workspace-status"', html)
        self.assertIn('id="sign-out"', html)
        self.assertIn('/styles.css?v=20260627-paper-calibration', html)
        self.assertIn('/app.js?v=20260627-paper-calibration', html)
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
        self.assertIn('id="recommendations"', html)
        self.assertIn('data-page="recommendations"', html)
        self.assertIn("Recommended for purchase", html)
        self.assertIn("Recommended for exit / trim", html)
        self.assertIn("recommended-exits", html)
        self.assertIn("overview-recommended-exits", html)
        self.assertIn("Currently in the Atlas list", html)
        self.assertIn("What Simulate fill does", html)
        self.assertIn("No brokerage order is sent", html)
        self.assertIn("Recommendation performance", html)
        self.assertIn("paper-feedback-summary", html)
        self.assertIn("paper-feedback", html)
        self.assertIn("later market behavior", html)
        self.assertIn("What Atlas bought and sold", html)
        self.assertIn("paper-activity", html)
        self.assertIn("How Atlas is managing the portfolio", html)
        self.assertIn("paper-operating-mode", html)
        self.assertIn("Portfolio thesis overview", html)
        self.assertIn("thesis-overview", html)
        self.assertIn("Access &amp; security foundation", html)
        self.assertIn('id="recovery-status"', html)
        self.assertIn('id="privacy-export-status"', html)
        self.assertIn('id="account-deletion-status"', html)
        self.assertIn('id="production-review-status"', html)
        self.assertIn("renderAccess", script)
        self.assertIn('id="workspace-identity"', html)
        self.assertIn("renderWorkspace", script)
        self.assertIn("setActivePage", script)
        self.assertIn("renderRecommendations", script)
        self.assertIn("renderRecommendationSummary", script)
        self.assertIn("renderRationale", script)
        self.assertIn("renderPaperFeedbackSummary", script)
        self.assertIn("renderPaperFeedback", script)
        self.assertIn("Atlas learning readout", script)
        self.assertIn("Buy calibration", script)
        self.assertIn("Sell calibration", script)
        self.assertIn('item.side === "sell"', script)
        self.assertIn('simulated ${escapeHtml(String(item.action_label || "sell"))}', script)
        self.assertIn("Post-sell move", script)
        self.assertIn("renderPaperActivity", script)
        self.assertIn("renderPaperOperatingMode", script)
        self.assertIn("renderThesisOverview", script)
        self.assertIn("thesis_status", script)
        self.assertIn("proposalActionLabel", script)
        self.assertIn("proposalImpact", script)
        self.assertIn("proposalControlTitle", script)
        self.assertIn("recommended for paper purchase", script)
        self.assertIn("Recommendation queue", html)
        self.assertIn("recommendation-summary", html)
        self.assertIn("Ready to simulate", script)
        self.assertIn("Buy candidate", script)
        self.assertIn("Trim candidate", script)
        self.assertIn("Exit candidate", script)
        self.assertIn("recommended for simulated ${escapeHtml(proposalActionLabel(item))}", script)
        self.assertIn("Record simulated ${action}", script)
        self.assertIn("exit-tag", styles)
        self.assertIn("exit-panel", styles)
        self.assertIn("Why now", script)
        self.assertIn("Why trim", script)
        self.assertIn("Why exit", script)
        self.assertIn("Why now rationale", script)
        self.assertIn("created before structured Why now rationale", script)
        self.assertIn("Simulate fill to record the hypothetical", script)
        self.assertIn("Would reduce the simulated holding", script)
        self.assertIn("Would close the full simulated holding", script)
        self.assertIn("current-watchlist", html)
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
        self.assertIn('id="owner-outcomes"', html)
        self.assertIn("daily_action_list", script)
        self.assertIn("owner_outcomes", script)
        self.assertIn("Outcome learning", script)
        self.assertIn("Outcome calibration:", script)
        self.assertIn("outcome_calibration", script)
        self.assertIn("renderPaperCalibration", script)
        self.assertIn("Paper learning:", script)
        self.assertIn("paper_calibration", script)
        self.assertIn("research_approval_rate_pct", script)
        self.assertIn("Suggested disposition:", script)
        self.assertIn("Evidence anchor:", script)
        self.assertIn("Portfolio context:", script)
        self.assertIn("Paper context:", script)
        self.assertIn("Thesis action:", script)

    def test_dashboard_explains_sections_and_terms(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        styles = (root / "web" / "styles.css").read_text(encoding="utf-8")

        self.assertIn("SPY is an ETF commonly used as a broad S&amp;P 500", html)
        self.assertIn("QQQ is an ETF commonly used as a Nasdaq-100", html)
        self.assertIn("growth, quality, moat, momentum, and risk", html)
        self.assertIn("largest daily percentage moves", html)
        self.assertIn("Open positions are securities currently held", html)
        self.assertIn("About market breadth", html)
        self.assertIn("About research agenda", html)
        self.assertIn("About decision controls", html)
        self.assertIn("About access and security", html)
        self.assertIn(".info-popover", styles)
        self.assertIn(".inline-help", styles)
        self.assertIn(".dashboard-page", styles)
        self.assertIn(".active-page", styles)
        self.assertIn(".recommendation-row", styles)
        self.assertIn(".recommendation-summary-grid", styles)
        self.assertIn(".recommendation-summary-card", styles)
        self.assertIn(".row-meta.paper-calibration.supportive", styles)
        self.assertIn(".row-meta.paper-calibration.caution", styles)
        self.assertIn(".ready-tag", styles)
        self.assertIn(".watchlist-item", styles)
        self.assertIn(".watchlist-item.core", styles)
        self.assertIn(".simulate-button", styles)
        self.assertIn(".feedback-row", styles)
        self.assertIn(".activity-row", styles)
        self.assertIn(".mode-grid", styles)
        self.assertIn(".mode-option", styles)
        self.assertIn(".why-now", styles)
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
