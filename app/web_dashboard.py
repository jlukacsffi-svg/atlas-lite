"""Read-only local web dashboard for Atlas Web Phase 1."""

from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from app.paper_trading import PaperTradingAccount
from app.paths import data_path, project_path
from app.research_tasks import ResearchTaskQueue
from app.tenant_store import SCHEMA_VERSION


WEB_DIR = project_path("web")
DEFAULT_ARCHIVE_DIR = data_path("research_archive")

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class DashboardDataService:
    """Build a browser-safe read model from local Atlas artifacts."""

    def __init__(
        self,
        archive_dir=DEFAULT_ARCHIVE_DIR,
        paper_account=None,
        research_queue=None,
    ):
        self.archive_dir = Path(archive_dir)
        self.paper_account = paper_account or PaperTradingAccount()
        self.research_queue = research_queue or ResearchTaskQueue()

    def build(self):
        snapshot = self._latest_snapshot()
        securities = snapshot.get("securities", {})
        available = {
            ticker: data
            for ticker, data in securities.items()
            if data.get("status") == "available"
        }
        return {
            "generated_at": snapshot.get("generated_at"),
            "market": self._market(snapshot.get("market_summary", {})),
            "overview": self._overview(securities, available),
            "movers": self._movers(available),
            "score_leaders": self._score_leaders(available),
            "watchlist": self._watchlist(available),
            "sectors": self._sectors(available),
            "corporate_actions": self._corporate_actions(available),
            "paper": self._paper(available),
            "research": self._research(),
            "history": self._history(),
            "access": self._access(),
        }

    def _access(self):
        return {
            "mode": "owner_only",
            "public_registration": False,
            "roles": ["Owner"],
            "schema_version": SCHEMA_VERSION,
            "tenant_isolation": "Single-owner private workspace",
            "identity_binding": "Verified Google subject and email",
            "audit_log": "Research and paper decisions retained",
            "threat_model": "Documented control matrix",
            "recovery": "Integrity-checked restore drill",
            "privacy_export": "Secret-free tenant package",
            "account_deletion": "Future member accounts disabled",
            "production_review": (
                "Owner profile active; public release remains gated"
            ),
            "phase_completion": 78,
            "next_step": "Operate and validate the owner workspace",
        }

    def _latest_snapshot(self):
        files = sorted(self.archive_dir.glob("snapshot_*.json"), reverse=True)
        if not files:
            return {"securities": {}, "market_summary": {}}
        return self._read_json(files[0]) or {"securities": {}, "market_summary": {}}

    def _market(self, market_summary):
        return [
            {
                "ticker": ticker,
                "price": data.get("price"),
                "change": data.get("change"),
                "percent_change": data.get("percent_change"),
            }
            for ticker, data in sorted(market_summary.items())
        ]

    def _overview(self, securities, available):
        positive = sum(
            1
            for data in available.values()
            if (data.get("percent_change") or 0) > 0
        )
        negative = sum(
            1
            for data in available.values()
            if (data.get("percent_change") or 0) < 0
        )
        return {
            "tracked": len(securities),
            "available": len(available),
            "advancing": positive,
            "declining": negative,
        }

    def _movers(self, available):
        rows = [
            {
                "ticker": ticker,
                "company_name": data.get("company_name", ticker),
                "sector": data.get("sector", "Unclassified"),
                "price": data.get("price"),
                "percent_change": data.get("percent_change"),
            }
            for ticker, data in available.items()
            if data.get("percent_change") is not None
        ]
        return sorted(
            rows,
            key=lambda item: abs(item["percent_change"]),
            reverse=True,
        )[:8]

    def _score_leaders(self, available):
        rows = [
            {
                "ticker": ticker,
                "company_name": data.get("company_name", ticker),
                "sector": data.get("sector", "Unclassified"),
                "category": data.get("category", "Watchlist"),
                "score": data.get("total_score"),
                "percent_change": data.get("percent_change"),
            }
            for ticker, data in available.items()
            if data.get("total_score") is not None
            and data.get("sector") != "Benchmark ETF"
        ]
        return sorted(rows, key=lambda item: item["score"], reverse=True)[:8]

    def _watchlist(self, available):
        rows = [
            {
                "ticker": ticker,
                "company_name": data.get("company_name", ticker),
                "sector": data.get("sector", "Unclassified"),
                "category": data.get("category", "Watchlist"),
                "score": data.get("total_score"),
                "percent_change": data.get("percent_change"),
            }
            for ticker, data in available.items()
        ]
        return sorted(
            rows,
            key=lambda item: (
                str(item.get("category") or ""),
                str(item.get("sector") or ""),
                str(item.get("ticker") or ""),
            ),
        )

    def _sectors(self, available):
        grouped = defaultdict(list)
        for data in available.values():
            sector = data.get("sector")
            change = data.get("percent_change")
            if sector and sector != "Benchmark ETF" and change is not None:
                grouped[sector].append(float(change))
        rows = [
            {
                "sector": sector,
                "average_change": round(sum(changes) / len(changes), 2),
                "securities": len(changes),
            }
            for sector, changes in grouped.items()
        ]
        return sorted(rows, key=lambda item: item["average_change"], reverse=True)

    @staticmethod
    def _corporate_actions(available):
        rows = []
        for ticker, data in available.items():
            actions = data.get("corporate_actions") or {}
            for split in actions.get("splits") or []:
                rows.append(
                    {
                        "ticker": ticker,
                        "type": "Stock split",
                        "date": split.get("date"),
                        "ratio": split.get("split_ratio") or str(split.get("ratio")),
                        "source": split.get("source") or actions.get("source"),
                        "normalized": True,
                    }
                )
        return sorted(
            rows,
            key=lambda item: item.get("date") or "",
            reverse=True,
        )[:8]

    def _paper(self, available):
        if not self.paper_account.account_file.exists():
            return {"configured": False}
        prices = {
            ticker: data.get("price")
            for ticker, data in available.items()
            if data.get("price") is not None
        }
        status = self.paper_account.status(prices=prices)
        performance = self.paper_account.performance_summary()
        latest_reviews = self.paper_account.latest_position_reviews()
        proposals = self.paper_account.proposals()
        active_sell_proposals = {
            proposal["ticker"]: proposal
            for proposal in proposals
            if proposal["side"] == "sell"
            and proposal["status"] in {"pending", "approved"}
        }
        positions = [
            {
                "ticker": position["ticker"],
                "shares": position["shares"],
                "average_cost": position["average_cost"],
                "price": position["price"],
                "market_value": position["market_value"],
                "unrealized_gain_loss": position["unrealized_gain_loss"],
                "review": latest_reviews.get(position["ticker"]),
                "thesis_status": self._position_thesis_status(
                    position,
                    latest_reviews.get(position["ticker"]),
                    active_sell_proposals.get(position["ticker"]),
                ),
            }
            for position in status["positions"]
        ]
        return {
            "configured": True,
            "name": status["name"],
            "cash": round(status["cash"], 2),
            "equity": round(status["equity"], 2),
            "market_value": round(status["market_value"], 2),
            "total_return_pct": (
                performance.get("latest", {}).get("total_return_pct")
                if performance.get("available")
                else None
            ),
            "excess_return_pct": performance.get("excess_return_pct", {}),
            "positions": positions,
            "thesis_overview": self._thesis_overview(positions),
            "operating_mode": self._paper_operating_mode(),
            "activity": self.paper_account.trade_activity(),
            "feedback": self.paper_account.proposal_feedback(),
            "proposals": {
                "pending": sum(1 for item in proposals if item["status"] == "pending"),
                "approved": sum(1 for item in proposals if item["status"] == "approved"),
                "rejected": sum(1 for item in proposals if item["status"] == "rejected"),
            "executed": sum(1 for item in proposals if item["status"] == "executed"),
            },
        }

    @staticmethod
    def _paper_operating_mode():
        return {
            "current": {
                "id": "recommendation_only",
                "label": "Recommendation mode",
                "description": (
                    "Atlas currently researches, proposes, and explains paper trades, "
                    "but it does not auto-execute them."
                ),
            },
            "modes": [
                {
                    "id": "recommendation_only",
                    "label": "Recommendation mode",
                    "status": "active",
                    "description": (
                        "Atlas surfaces buys, trims, and exits for owner review before "
                        "anything is recorded."
                    ),
                },
                {
                    "id": "paper_auto_manage",
                    "label": "Auto-manage paper portfolio",
                    "status": "planned",
                    "description": (
                        "Future Atlas mode: automatically maintain a simulated portfolio "
                        "using approved paper rules and a full audit trail."
                    ),
                },
            ],
            "boundary": (
                "Real-money auto-trading remains disabled. Future automation, if added, "
                "must stay paper-only until explicitly expanded."
            ),
        }

    @staticmethod
    def _position_thesis_status(position, review, active_sell):
        shares = float(position.get("shares") or 0.0)
        if active_sell:
            sell_shares = float(active_sell.get("shares") or 0.0)
            if shares and sell_shares < shares:
                return {
                    "label": "trim",
                    "summary": (
                        f"Atlas has an active simulated trim proposal for "
                        f"{sell_shares:g} of {shares:g} shares."
                    ),
                }
            return {
                "label": "exit",
                "summary": "Atlas has an active simulated exit proposal for this holding.",
            }
        if not review:
            return {
                "label": "healthy",
                "summary": "Awaiting the next daily thesis review.",
            }

        verdict = str(review.get("verdict") or "maintain").lower()
        flags = review.get("flags") or []
        score = review.get("atlas_score")
        score_text = f" Atlas score {score:.1f}." if score is not None else ""
        if verdict == "exit":
            return {
                "label": "exit",
                "summary": (
                    (flags[0] if flags else "Atlas marked this holding for simulated exit.")
                    + score_text
                ).strip(),
            }
        if verdict == "review":
            return {
                "label": "watch",
                "summary": (
                    (flags[0] if flags else "Atlas wants a closer thesis review on this holding.")
                    + score_text
                ).strip(),
            }
        return {
            "label": "healthy",
            "summary": (
                (flags[0] if flags else "Latest thesis review remains constructive.")
                + score_text
            ).strip(),
        }

    @staticmethod
    def _thesis_overview(positions):
        counts = {label: 0 for label in ("healthy", "watch", "trim", "exit")}
        priority = {"exit": 0, "trim": 1, "watch": 2, "healthy": 3}
        attention = []
        for position in positions:
            thesis = position.get("thesis_status") or {}
            label = thesis.get("label", "healthy")
            counts[label] = counts.get(label, 0) + 1
            attention.append(
                {
                    "ticker": position.get("ticker"),
                    "label": label,
                    "summary": thesis.get("summary", ""),
                    "market_value": position.get("market_value") or 0.0,
                }
            )
        attention.sort(
            key=lambda item: (
                priority.get(item["label"], 99),
                -(float(item["market_value"]) if item["market_value"] is not None else 0.0),
                item.get("ticker") or "",
            )
        )
        return {
            "counts": counts,
            "attention": attention[:4],
        }

    def _research(self):
        summary = self.research_queue.summary()
        tasks = self.research_queue.list_tasks(status="open")
        awaiting_owner = self.research_queue.list_tasks(status="awaiting_owner")
        return {
            "open": summary["by_status"].get("open", 0),
            "high_priority": len(summary["open_high_priority"]),
            "awaiting_owner": len(awaiting_owner),
            "tasks": [
                {
                    "id": task.get("id"),
                    "role": task.get("role"),
                    "priority": task.get("priority"),
                    "subject": task.get("subject"),
                    "prompt": task.get("prompt"),
                }
                for task in self.research_queue._sorted_tasks(tasks)[:6]
            ],
        }

    def _history(self):
        if not self.paper_account.account_file.exists():
            return []
        return [
            {
                "timestamp": item.get("timestamp"),
                "equity": item.get("equity"),
                "atlas_return": item.get("total_return_pct"),
                "spy_return": item.get("benchmark_returns_pct", {}).get("SPY"),
                "qqq_return": item.get("benchmark_returns_pct", {}).get("QQQ"),
            }
            for item in self.paper_account.performance_history()[-30:]
        ]

    def _read_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None


def create_handler(data_service=None, web_dir=WEB_DIR):
    service = data_service or DashboardDataService()
    static_root = Path(web_dir)

    class DashboardHandler(BaseHTTPRequestHandler):
        server_version = "AtlasDashboard/1.0"

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/dashboard":
                self._send_json(service.build())
                return
            static_file = STATIC_FILES.get(path)
            if static_file:
                filename, content_type = static_file
                self._send_file(static_root / filename, content_type)
                return
            self.send_error(404)

        def do_POST(self):
            self.send_error(405, "Read-only dashboard")

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'",
            )
            super().end_headers()

        def log_message(self, format, *args):
            return

        def _send_json(self, payload):
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path, content_type):
            try:
                body = path.read_bytes()
            except FileNotFoundError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return DashboardHandler


def run_server(host="127.0.0.1", port=8765):
    server = ThreadingHTTPServer((host, int(port)), create_handler())
    print(f"[web] Atlas owner dashboard: http://{host}:{port}")
    print("[web] Read-only local server. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
