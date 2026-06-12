import io
import json
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path

from app.tenant_accounts import TenantAccount
from app.tenant_store import TenantStore
from app.web_tenant import (
    TENANT_SESSION_COOKIE,
    TenantWebApplication,
    TenantWebSettings,
)


def call_wsgi(application, path="/", method="GET", headers=None):
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)
        captured["header_list"] = response_headers

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "wsgi.input": io.BytesIO(),
    }
    for name, value in (headers or {}).items():
        environ[f"HTTP_{name.upper().replace('-', '_')}"] = value
    body = b"".join(application(environ, start_response))
    captured["body"] = body
    if captured["headers"].get("Content-Type", "").startswith(
        "application/json"
    ):
        captured["json"] = json.loads(body.decode("utf-8"))
    return captured


def cookie_value(response, name):
    cookies = SimpleCookie()
    for header, value in response["header_list"]:
        if header.lower() == "set-cookie":
            cookies.load(value)
    return cookies[name].value


class TenantWebApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        root = Path(self.temp_dir.name)
        self.store = TenantStore(
            root / "tenant.sqlite3",
            clock=lambda: "2026-06-11T12:00:00+00:00",
        )
        self.store.migrate()
        self.alpha_owner = self._account(
            "alpha-workspace",
            "alpha-owner",
            "google-alpha",
            "alpha@example.com",
            "owner",
        )
        self.beta_owner = self._account(
            "beta-workspace",
            "beta-owner",
            "google-beta",
            "beta@example.com",
            "owner",
        )
        self.store.provision_account("Alpha Workspace", self.alpha_owner)
        self.store.provision_account("Beta Workspace", self.beta_owner)
        self.alpha_watchlist = self.store.create_watchlist(
            self.alpha_owner,
            "Alpha Core",
            watchlist_id="core",
        )
        self.store.add_watchlist_item(
            self.alpha_owner,
            self.alpha_watchlist,
            "NVDA",
            category="Core",
        )
        self.beta_watchlist = self.store.create_watchlist(
            self.beta_owner,
            "Beta Core",
            watchlist_id="beta-core",
        )
        self.store.add_watchlist_item(
            self.beta_owner,
            self.beta_watchlist,
            "MSFT",
        )
        self.alpha_portfolio = self.store.create_portfolio(
            self.alpha_owner,
            "Alpha Portfolio",
            portfolio_id="primary",
        )
        self.store.set_position(
            self.alpha_owner,
            self.alpha_portfolio,
            "NVDA",
            2,
            100,
        )
        self.beta_portfolio = self.store.create_portfolio(
            self.beta_owner,
            "Beta Portfolio",
            portfolio_id="beta-primary",
        )
        self.store.set_position(
            self.beta_owner,
            self.beta_portfolio,
            "MSFT",
            1,
            200,
        )
        self.store.create_report(
            self.alpha_owner,
            "Alpha Brief",
            "2026-06-11T12:00:00+00:00",
            report_id="alpha-brief",
        )
        self.store.create_research_task(
            self.alpha_owner,
            "CIO",
            "NVDA",
            "Review thesis.",
            task_id="alpha-task",
        )
        self.store.create_paper_account(
            self.alpha_owner,
            "Alpha Paper",
            100000,
            account_id="alpha-paper",
        )
        self.settings = TenantWebSettings(
            database_path=root / "tenant.sqlite3",
            session_secret="tenant-session-secret-that-is-long-enough",
            preview_provider=self.alpha_owner.provider,
            preview_subject=self.alpha_owner.subject,
            preview_email=self.alpha_owner.email,
            allow_preview_login=True,
            web_dir=root,
        )
        (root / "index.html").write_text("Atlas Tenant", encoding="utf-8")
        self.app = TenantWebApplication(
            self.settings,
            store=self.store,
            clock=lambda: 1000,
        )

    @staticmethod
    def _account(tenant, user, subject, email, role, status="active"):
        return TenantAccount(
            tenant_id=tenant,
            user_id=user,
            provider="google",
            subject=subject,
            email=email,
            role=role,
            status=status,
        )

    def _session(self, account=None, **overrides):
        account = account or self.alpha_owner
        payload = {
            "provider": account.provider,
            "subject": account.subject,
            "email": account.email,
            "tenant_id": account.tenant_id,
            "user_id": account.user_id,
            "exp": 1300,
        }
        payload.update(overrides)
        return self.app._sign(payload)

    def _headers(self, session=None):
        session = session or self._session()
        return {"Cookie": f"{TENANT_SESSION_COOKIE}={session}"}

    def test_api_requires_signed_session(self):
        response = call_wsgi(self.app, "/api/workspace")
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(response["json"], {"error": "authentication_required"})

        response = call_wsgi(
            self.app,
            "/api/workspace",
            headers=self._headers(self._session() + "tampered"),
        )
        self.assertEqual(response["status"], "401 Unauthorized")

    def test_preview_login_issues_strict_short_lived_cookie(self):
        response = call_wsgi(self.app, "/preview-login")
        self.assertEqual(response["status"], "302 Found")
        self.assertEqual(response["headers"]["Location"], "/")
        cookies = SimpleCookie()
        for header, value in response["header_list"]:
            if header.lower() == "set-cookie":
                cookies.load(value)
        cookie = cookies[TENANT_SESSION_COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["max-age"], "1800")

    def test_workspace_re_resolves_active_database_membership(self):
        response = call_wsgi(
            self.app,
            "/api/workspace",
            headers=self._headers(),
        )
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(
            response["json"]["tenant"]["tenant_id"],
            "alpha-workspace",
        )
        self.assertEqual(response["json"]["account"]["role"], "owner")
        self.assertEqual(response["json"]["counts"]["reports"], 1)

        forged = self._session(tenant_id="beta-workspace")
        denied = call_wsgi(
            self.app,
            "/api/workspace",
            headers=self._headers(forged),
        )
        self.assertEqual(denied["status"], "401 Unauthorized")

    def test_private_collection_routes_return_only_active_tenant_data(self):
        expected = {
            "/api/reports": "Alpha Brief",
            "/api/watchlists": "Alpha Core",
            "/api/portfolios": "Alpha Portfolio",
            "/api/research/tasks": "NVDA",
            "/api/paper/accounts": "Alpha Paper",
        }
        for path, marker in expected.items():
            with self.subTest(path=path):
                response = call_wsgi(
                    self.app,
                    path,
                    headers=self._headers(),
                )
                self.assertEqual(response["status"], "200 OK")
                self.assertIn(marker, json.dumps(response["json"]))
                self.assertNotIn("Beta", json.dumps(response["json"]))

    def test_object_routes_conceal_cross_tenant_ids(self):
        own_watchlist = call_wsgi(
            self.app,
            f"/api/watchlists/{self.alpha_watchlist}/items",
            headers=self._headers(),
        )
        other_watchlist = call_wsgi(
            self.app,
            f"/api/watchlists/{self.beta_watchlist}/items",
            headers=self._headers(),
        )
        own_portfolio = call_wsgi(
            self.app,
            f"/api/portfolios/{self.alpha_portfolio}/positions",
            headers=self._headers(),
        )
        other_portfolio = call_wsgi(
            self.app,
            f"/api/portfolios/{self.beta_portfolio}/positions",
            headers=self._headers(),
        )
        self.assertEqual(own_watchlist["json"]["items"][0]["ticker"], "NVDA")
        self.assertEqual(other_watchlist["json"]["items"], [])
        self.assertEqual(own_portfolio["json"]["items"][0]["ticker"], "NVDA")
        self.assertEqual(other_portfolio["json"]["items"], [])

    def test_admin_routes_enforce_role_permissions(self):
        viewer = self._account(
            "alpha-workspace",
            "alpha-viewer",
            "google-viewer",
            "viewer@example.com",
            "viewer",
        )
        self.store.add_membership(self.alpha_owner, viewer)
        viewer_headers = self._headers(self._session(viewer))
        for path in (
            "/api/admin/members",
            "/api/admin/invitations",
            "/api/admin/audit",
        ):
            with self.subTest(path=path):
                response = call_wsgi(
                    self.app,
                    path,
                    headers=viewer_headers,
                )
                self.assertEqual(response["status"], "403 Forbidden")
                self.assertEqual(
                    response["json"],
                    {"error": "insufficient_role"},
                )

        owner = call_wsgi(
            self.app,
            "/api/admin/members",
            headers=self._headers(),
        )
        self.assertEqual(owner["status"], "200 OK")

    def test_disabled_membership_invalidates_existing_session(self):
        viewer = self._account(
            "alpha-workspace",
            "alpha-viewer",
            "google-viewer",
            "viewer@example.com",
            "viewer",
        )
        self.store.add_membership(self.alpha_owner, viewer)
        session = self._session(viewer)
        before = call_wsgi(
            self.app,
            "/api/workspace",
            headers=self._headers(session),
        )
        self.assertEqual(before["status"], "200 OK")
        self.store.set_member_status(
            self.alpha_owner,
            viewer.user_id,
            "disabled",
        )
        after = call_wsgi(
            self.app,
            "/api/workspace",
            headers=self._headers(session),
        )
        self.assertEqual(after["status"], "401 Unauthorized")

    def test_dashboard_contains_workspace_identity(self):
        response = call_wsgi(
            self.app,
            "/api/dashboard",
            headers=self._headers(),
        )
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(
            response["json"]["workspace"]["tenant"]["name"],
            "Alpha Workspace",
        )
        self.assertEqual(
            response["json"]["access"]["tenant_isolation"],
            "Request enforced",
        )
        self.assertEqual(
            response["json"]["access"]["phase_completion"],
            70,
        )
        self.assertIn(
            "restore drill",
            response["json"]["access"]["recovery"],
        )

    def test_mutating_methods_are_rejected_and_static_files_are_protected(self):
        rejected = call_wsgi(
            self.app,
            "/api/workspace",
            method="POST",
            headers=self._headers(),
        )
        self.assertEqual(rejected["status"], "405 Method Not Allowed")

        unauthenticated = call_wsgi(self.app, "/")
        self.assertEqual(unauthenticated["status"], "302 Found")
        authenticated = call_wsgi(
            self.app,
            "/",
            headers=self._headers(),
        )
        self.assertEqual(authenticated["status"], "200 OK")
        self.assertEqual(authenticated["body"], b"Atlas Tenant")
        self.assertEqual(authenticated["headers"]["X-Frame-Options"], "DENY")


if __name__ == "__main__":
    unittest.main()
