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
        self.assertTrue(data["paper"]["configured"])
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

    def test_browser_labels_local_and_cloud_environments(self):
        root = Path(__file__).resolve().parent.parent
        html = (root / "web" / "index.html").read_text(encoding="utf-8")
        script = (root / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="workspace-status"', html)
        self.assertIn('id="sign-out"', html)
        self.assertIn("Secure owner cloud", script)
        self.assertIn("Local read-only workspace", script)
        self.assertIn("window.location.hostname", script)
        self.assertIn('id="access"', html)
        self.assertIn("Access &amp; security foundation", html)
        self.assertIn('id="recovery-status"', html)
        self.assertIn('id="privacy-export-status"', html)
        self.assertIn('id="account-deletion-status"', html)
        self.assertIn('id="production-review-status"', html)
        self.assertIn("renderAccess", script)
        self.assertIn('id="workspace-identity"', html)
        self.assertIn("renderWorkspace", script)
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
        self.assertIn("catalyst_type", script)
        self.assertIn("thesis_alignment", script)
        self.assertIn("Thesis alignment:", script)
        self.assertIn("Thesis action:", script)

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
