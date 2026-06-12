"""Local-only tenant-aware WSGI boundary for Web Phase 3 validation."""

from dataclasses import dataclass
import base64
from http.cookies import SimpleCookie
import hashlib
import hmac
import json
from pathlib import Path
import time
from urllib.parse import unquote

from app.tenant_accounts import TenantAccessError
from app.tenant_store import TenantStore
from app.web_dashboard import STATIC_FILES, WEB_DIR


TENANT_SESSION_COOKIE = "atlas_tenant_preview"
TENANT_SESSION_TTL_SECONDS = 1800


@dataclass(frozen=True)
class TenantWebSettings:
    database_path: Path
    session_secret: str
    preview_provider: str = ""
    preview_subject: str = ""
    preview_email: str = ""
    allow_preview_login: bool = False
    web_dir: Path = WEB_DIR

    def validate(self):
        if len(self.session_secret) < 32:
            raise ValueError("Tenant preview session secret must be at least 32 characters")
        if self.allow_preview_login:
            required = (
                self.preview_provider,
                self.preview_subject,
                self.preview_email,
            )
            if not all(required):
                raise ValueError("Preview login requires a complete identity")


class TenantWebApplication:
    """Resolve a signed local session into one tenant on every request."""

    def __init__(self, settings, store=None, clock=None):
        settings.validate()
        self.settings = settings
        self.store = store or TenantStore(settings.database_path)
        self.store.migrate()
        self.clock = clock or time.time

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = unquote(environ.get("PATH_INFO", "/"))
        if method != "GET":
            return self._json(
                start_response,
                "405 Method Not Allowed",
                {"error": "read_only"},
                [("Allow", "GET")],
            )
        if path == "/healthz":
            return self._json(start_response, "200 OK", {"status": "ok"})
        if path == "/preview-login":
            return self._preview_login(start_response)
        if path == "/logout":
            return self._redirect(
                start_response,
                "/",
                [("Set-Cookie", self._expired_cookie())],
            )

        account = self._account(environ)
        if account is None:
            if path.startswith("/api/"):
                return self._json(
                    start_response,
                    "401 Unauthorized",
                    {"error": "authentication_required"},
                )
            if self.settings.allow_preview_login:
                return self._redirect(start_response, "/preview-login")
            return self._json(
                start_response,
                "401 Unauthorized",
                {"error": "authentication_required"},
            )

        if path == "/api/workspace":
            return self._json(
                start_response,
                "200 OK",
                self.store.workspace_summary(account),
            )
        if path == "/api/reports":
            return self._json(
                start_response,
                "200 OK",
                {"items": self.store.list_reports(account)},
            )
        if path == "/api/watchlists":
            return self._json(
                start_response,
                "200 OK",
                {"items": self.store.list_watchlists(account)},
            )
        if path.startswith("/api/watchlists/") and path.endswith("/items"):
            watchlist_id = path.removeprefix("/api/watchlists/").removesuffix(
                "/items"
            ).strip("/")
            return self._json(
                start_response,
                "200 OK",
                {
                    "items": self.store.list_watchlist_items(
                        account,
                        watchlist_id,
                    )
                },
            )
        if path == "/api/portfolios":
            return self._json(
                start_response,
                "200 OK",
                {"items": self.store.list_portfolios(account)},
            )
        if path.startswith("/api/portfolios/") and path.endswith("/positions"):
            portfolio_id = path.removeprefix("/api/portfolios/").removesuffix(
                "/positions"
            ).strip("/")
            return self._json(
                start_response,
                "200 OK",
                {
                    "items": self.store.list_positions(
                        account,
                        portfolio_id,
                    )
                },
            )
        if path == "/api/research/tasks":
            return self._json(
                start_response,
                "200 OK",
                {"items": self.store.list_research_tasks(account)},
            )
        if path == "/api/paper/accounts":
            return self._json(
                start_response,
                "200 OK",
                {"items": self.store.list_paper_accounts(account)},
            )
        if path == "/api/admin/members":
            return self._guarded(
                start_response,
                lambda: {"items": self.store.list_members(account)},
            )
        if path == "/api/admin/invitations":
            return self._guarded(
                start_response,
                lambda: {"items": self.store.list_invitations(account)},
            )
        if path == "/api/admin/audit":
            return self._guarded(
                start_response,
                lambda: {"items": self.store.list_audit_events(account)},
            )
        if path == "/api/dashboard":
            summary = self.store.workspace_summary(account)
            return self._json(
                start_response,
                "200 OK",
                {
                    "generated_at": None,
                    "market": [],
                    "overview": {
                        "tracked": 0,
                        "available": 0,
                        "advancing": 0,
                        "declining": 0,
                    },
                    "movers": [],
                    "score_leaders": [],
                    "sectors": [],
                    "paper": {"configured": False, "positions": []},
                    "research": {
                        "open": summary["counts"]["research_tasks"],
                        "high_priority": 0,
                        "tasks": [],
                    },
                    "history": [],
                    "workspace": summary,
                    "access": {
                        "mode": "invite_only",
                        "public_registration": False,
                        "roles": [
                            "Owner",
                            "Administrator",
                            "Analyst",
                            "Viewer",
                        ],
                        "tenant_isolation": "Request enforced",
                        "identity_binding": "Active database membership",
                        "audit_log": "Append-only administration events",
                    },
                },
            )

        static_file = STATIC_FILES.get(path)
        if static_file:
            filename, content_type = static_file
            return self._file(
                start_response,
                self.settings.web_dir / filename,
                content_type,
            )
        return self._json(
            start_response,
            "404 Not Found",
            {"error": "not_found"},
        )

    def _account(self, environ):
        session = self._read_session(environ)
        if not session or int(session.get("exp", 0)) < int(self.clock()):
            return None
        try:
            account = self.store.resolve(
                session.get("provider", ""),
                session.get("subject", ""),
                session.get("email", ""),
            )
        except (PermissionError, ValueError):
            return None
        if (
            account.tenant_id != session.get("tenant_id")
            or account.user_id != session.get("user_id")
        ):
            return None
        return account

    def _preview_login(self, start_response):
        if not self.settings.allow_preview_login:
            return self._json(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )
        try:
            account = self.store.resolve(
                self.settings.preview_provider,
                self.settings.preview_subject,
                self.settings.preview_email,
            )
        except (PermissionError, ValueError):
            return self._json(
                start_response,
                "401 Unauthorized",
                {"error": "preview_identity_unavailable"},
            )
        session = self._sign(
            {
                "provider": account.provider,
                "subject": account.subject,
                "email": account.email,
                "tenant_id": account.tenant_id,
                "user_id": account.user_id,
                "exp": int(self.clock()) + TENANT_SESSION_TTL_SECONDS,
            }
        )
        return self._redirect(
            start_response,
            "/",
            [
                (
                    "Set-Cookie",
                    self._cookie_header(
                        session,
                        TENANT_SESSION_TTL_SECONDS,
                    ),
                )
            ],
        )

    def _guarded(self, start_response, callback):
        try:
            payload = callback()
        except TenantAccessError:
            return self._json(
                start_response,
                "403 Forbidden",
                {"error": "insufficient_role"},
            )
        return self._json(start_response, "200 OK", payload)

    def _sign(self, payload):
        encoded = self._b64encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
                "utf-8"
            )
        )
        signature = hmac.new(
            self.settings.session_secret.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{encoded}.{self._b64encode(signature)}"

    def _read_session(self, environ):
        try:
            cookies = SimpleCookie()
            cookies.load(environ.get("HTTP_COOKIE", ""))
            value = cookies[TENANT_SESSION_COOKIE].value
            encoded, supplied = value.split(".", 1)
            expected = hmac.new(
                self.settings.session_secret.encode("utf-8"),
                encoded.encode("ascii"),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(supplied, self._b64encode(expected)):
                return None
            return json.loads(self._b64decode(encoded).decode("utf-8"))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _cookie_header(self, value, max_age):
        cookie = SimpleCookie()
        cookie[TENANT_SESSION_COOKIE] = value
        morsel = cookie[TENANT_SESSION_COOKIE]
        morsel["path"] = "/"
        morsel["max-age"] = str(max_age)
        morsel["httponly"] = True
        morsel["samesite"] = "Strict"
        return morsel.OutputString()

    def _expired_cookie(self):
        return self._cookie_header("", 0)

    def _redirect(self, start_response, location, extra_headers=None):
        headers = self._security_headers("text/plain; charset=utf-8", 0)
        headers.append(("Location", location))
        headers.extend(extra_headers or [])
        start_response("302 Found", headers)
        return [b""]

    def _json(
        self,
        start_response,
        status,
        payload,
        extra_headers=None,
    ):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = self._security_headers(
            "application/json; charset=utf-8",
            len(body),
        )
        headers.extend(extra_headers or [])
        start_response(status, headers)
        return [body]

    def _file(self, start_response, path, content_type):
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            return self._json(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )
        start_response(
            "200 OK",
            self._security_headers(content_type, len(body)),
        )
        return [body]

    @staticmethod
    def _security_headers(content_type, content_length):
        return [
            ("Content-Type", content_type),
            ("Content-Length", str(content_length)),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
            (
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; "
                "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
            ),
        ]

    @staticmethod
    def _b64encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64decode(value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

