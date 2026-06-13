import io
import json
import tempfile
import unittest
from http.cookies import SimpleCookie
from unittest.mock import patch
from pathlib import Path

from app.web_cloud import (
    AtlasCloudApplication,
    CloudWebSettings,
    GOOGLE_ISSUERS,
    GoogleOAuthClient,
    IAP_ISSUER,
    OAUTH_STATE_COOKIE,
    RefreshingDashboardDataService,
    SESSION_COOKIE,
    data_service_from_environment,
)


class StubDataService:
    def __init__(self, ready=True):
        self.ready = ready

    def _latest_snapshot(self):
        return {"generated_at": "2026-06-07T08:00:00"} if self.ready else {}

    def build(self):
        return {"generated_at": "2026-06-07T08:00:00", "overview": {}}


class RefreshingDashboardDataServiceTests(unittest.TestCase):
    def test_refreshes_only_after_interval(self):
        clock = [100.0]
        refreshes = []
        service = RefreshingDashboardDataService(
            StubDataService(),
            lambda: refreshes.append("refresh") or ["artifact"],
            interval_seconds=60,
            clock=lambda: clock[0],
        )

        service.build()
        clock[0] = 159.0
        service.build()
        clock[0] = 160.0
        service.build()

        self.assertEqual(refreshes, ["refresh"])

    def test_refresh_failure_serves_last_known_data(self):
        clock = [100.0]

        def fail_refresh():
            raise RuntimeError("network unavailable")

        service = RefreshingDashboardDataService(
            StubDataService(),
            fail_refresh,
            interval_seconds=60,
            clock=lambda: clock[0],
        )
        clock[0] = 160.0

        data = service.build()

        self.assertEqual(data["generated_at"], "2026-06-07T08:00:00")


def call_wsgi(
    application,
    path="/",
    method="GET",
    headers=None,
    query_string="",
    body=None,
):
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)
        captured["header_list"] = response_headers

    raw_body = (
        json.dumps(body).encode("utf-8")
        if isinstance(body, (dict, list))
        else body or b""
    )
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": io.BytesIO(raw_body),
        "CONTENT_LENGTH": str(len(raw_body)),
        "CONTENT_TYPE": "application/json",
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


def response_cookies(response):
    cookies = SimpleCookie()
    for name, value in response["header_list"]:
        if name.lower() == "set-cookie":
            cookies.load(value)
    return cookies


class StubOAuthClient:
    def __init__(self, id_token="google-id-token"):
        self.id_token = id_token
        self.authorization = None
        self.exchange = None

    def authorization_url(self, state, nonce):
        self.authorization = (state, nonce)
        return (
            f"https://accounts.google.com/o/oauth2/auth?state={state}",
            "pkce-verifier",
        )

    def exchange_code(self, code, state, code_verifier):
        self.exchange = (code, state, code_verifier)
        return self.id_token


class StubOwnerControl:
    def __init__(self):
        self.actions = []

    def model(self):
        return {
            "enabled": True,
            "boundary": "Owner only",
            "research_reviews": [],
            "paper_proposals": [],
        }

    def apply(self, action, payload):
        self.actions.append((action, payload))
        return {"action": action}


class StubTokenResponse(dict):
    pass


class StubOAuthFlow:
    def __init__(self, warning=None, id_token="google-id-token"):
        self.warning = warning
        self.credentials = type(
            "Credentials",
            (),
            {"id_token": id_token},
        )()

    def fetch_token(self, code):
        if self.warning:
            raise self.warning


class StubGoogleOAuthClient(GoogleOAuthClient):
    def __init__(self, flow):
        self.flow = flow

    def _flow(self, state=None, code_verifier=None):
        return self.flow


class GoogleOAuthClientTests(unittest.TestCase):
    def test_exchange_accepts_google_email_scope_alias_reduction(self):
        warning = Warning("Equivalent Google email scopes")
        warning.new_scope = {
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        }
        warning.token = StubTokenResponse(id_token="signed-id-token")
        client = StubGoogleOAuthClient(StubOAuthFlow(warning=warning))

        token = client.exchange_code("code", "state", "verifier")

        self.assertEqual(token, "signed-id-token")

    def test_exchange_rejects_unexpected_scope_changes(self):
        warning = Warning("Unexpected scope")
        warning.new_scope = {"openid", "https://www.googleapis.com/auth/drive"}
        warning.token = StubTokenResponse(id_token="signed-id-token")
        client = StubGoogleOAuthClient(StubOAuthFlow(warning=warning))

        with self.assertRaises(Warning):
            client.exchange_code("code", "state", "verifier")


class CloudWebSettingsTests(unittest.TestCase):
    def test_cloud_mode_fails_closed_without_iap_configuration(self):
        with self.assertRaisesRegex(ValueError, "IAP or Google OAuth"):
            CloudWebSettings(mode="cloud", auth_mode="local").validate()
        with self.assertRaisesRegex(ValueError, "ATLAS_OWNER_EMAIL"):
            CloudWebSettings(mode="cloud", auth_mode="iap").validate()
        with self.assertRaisesRegex(ValueError, "ATLAS_IAP_AUDIENCE"):
            CloudWebSettings(
                mode="cloud",
                auth_mode="iap",
                owner_email="owner@example.com",
            ).validate()
        with self.assertRaisesRegex(ValueError, "ATLAS_GCS_BUCKET"):
            CloudWebSettings(
                mode="cloud",
                auth_mode="iap",
                owner_email="owner@example.com",
                iap_audience="/projects/123/locations/us/services/atlas",
            ).validate()

    def test_local_mode_cannot_accept_cloud_identity_headers(self):
        with self.assertRaisesRegex(ValueError, "must use ATLAS_AUTH_MODE=local"):
            CloudWebSettings(mode="local", auth_mode="iap").validate()

    def test_owner_controls_require_authenticated_google_cloud_mode(self):
        with self.assertRaisesRegex(ValueError, "unauthenticated local"):
            CloudWebSettings(owner_controls_enabled=True).validate()
        with self.assertRaisesRegex(ValueError, "Google OAuth"):
            CloudWebSettings(
                mode="cloud",
                auth_mode="iap",
                owner_email="owner@example.com",
                iap_audience="audience",
                storage_bucket="atlas-private",
                owner_controls_enabled=True,
            ).validate()

    def test_google_oauth_mode_fails_closed_without_all_secrets(self):
        base = {
            "mode": "cloud",
            "auth_mode": "google_oauth",
            "owner_email": "owner@example.com",
            "storage_bucket": "atlas-private",
        }
        with self.assertRaisesRegex(ValueError, "ATLAS_GOOGLE_CLIENT_ID"):
            CloudWebSettings(**base).validate()
        with self.assertRaisesRegex(ValueError, "at least 32 characters"):
            CloudWebSettings(
                **base,
                google_client_id="client-id",
                google_client_secret="client-secret",
                oauth_redirect_uri="https://atlas.example/oauth/callback",
                session_secret="too-short",
            ).validate()
        with self.assertRaisesRegex(ValueError, "must use HTTPS"):
            CloudWebSettings(
                **base,
                google_client_id="client-id",
                google_client_secret="client-secret",
                oauth_redirect_uri="http://atlas.example/oauth/callback",
                session_secret="s" * 32,
            ).validate()

    def test_data_root_controls_all_private_artifact_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict(
                "os.environ",
                {"ATLAS_DATA_ROOT": temp_dir},
            ):
                service = data_service_from_environment()
        root = Path(temp_dir)
        self.assertEqual(service.archive_dir, root / "research_archive")
        self.assertEqual(
            service.paper_account.account_file,
            root / "paper_trading" / "account.json",
        )
        self.assertEqual(
            service.research_queue.task_file,
            root / "research_tasks" / "tasks.json",
        )


class CloudWebApplicationTests(unittest.TestCase):
    def _cloud_app(self, verifier):
        return AtlasCloudApplication(
            CloudWebSettings(
                mode="cloud",
                auth_mode="iap",
                owner_email="owner@example.com",
                iap_audience="/projects/123/locations/us/services/atlas",
                storage_bucket="atlas-private",
            ),
            data_service=StubDataService(),
            token_verifier=verifier,
        )

    def _oauth_app(
        self,
        oauth_client=None,
        verifier=None,
        now=1000,
        owner_controls=False,
        owner_control=None,
    ):
        return AtlasCloudApplication(
            CloudWebSettings(
                mode="cloud",
                auth_mode="google_oauth",
                owner_email="owner@example.com",
                google_client_id="client-id",
                google_client_secret="client-secret",
                oauth_redirect_uri="https://atlas.example/oauth/callback",
                session_secret="session-secret-value-that-is-long-enough",
                storage_bucket="atlas-private",
                owner_controls_enabled=owner_controls,
            ),
            data_service=StubDataService(),
            oauth_client=oauth_client or StubOAuthClient(),
            oidc_verifier=verifier or (lambda token, audience: {}),
            clock=lambda: now,
            token_factory=lambda length: "random-token",
            owner_control=owner_control,
        )

    def _begin_oauth(self, app):
        response = call_wsgi(app, path="/login")
        cookie = response_cookies(response)[OAUTH_STATE_COOKIE]
        return response, cookie

    def test_health_is_public_but_contains_no_dashboard_data(self):
        response = call_wsgi(
            self._cloud_app(lambda token, audience: {}),
            path="/healthz",
        )
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(response["json"], {"status": "ok"})

    def test_readiness_reflects_data_availability_without_exposing_data(self):
        app = AtlasCloudApplication(
            CloudWebSettings(),
            data_service=StubDataService(ready=False),
        )
        response = call_wsgi(app, path="/readyz")
        self.assertEqual(response["status"], "503 Service Unavailable")
        self.assertEqual(response["json"], {"status": "not_ready"})

    def test_cloud_dashboard_requires_signed_iap_token(self):
        response = call_wsgi(
            self._cloud_app(lambda token, audience: {}),
            path="/api/dashboard",
        )
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(response["json"], {"error": "authentication_required"})

    def test_cloud_dashboard_rejects_non_owner_identity(self):
        def verifier(token, audience):
            return {
                "iss": IAP_ISSUER,
                "sub": "user-123",
                "email": "someone@example.com",
            }

        response = call_wsgi(
            self._cloud_app(verifier),
            path="/api/dashboard",
            headers={"X-Goog-IAP-JWT-Assertion": "signed-token"},
        )
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(response["json"], {"error": "authentication_required"})

    def test_cloud_dashboard_accepts_verified_owner(self):
        observed = {}

        def verifier(token, audience):
            observed["token"] = token
            observed["audience"] = audience
            return {
                "iss": IAP_ISSUER,
                "sub": "owner-123",
                "email": "owner@example.com",
            }

        response = call_wsgi(
            self._cloud_app(verifier),
            path="/api/dashboard",
            headers={"X-Goog-IAP-JWT-Assertion": "signed-token"},
        )
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(observed["token"], "signed-token")
        self.assertEqual(
            observed["audience"],
            "/projects/123/locations/us/services/atlas",
        )
        self.assertEqual(response["headers"]["X-Frame-Options"], "DENY")
        self.assertIn(
            "max-age=31536000",
            response["headers"]["Strict-Transport-Security"],
        )
        self.assertIn(
            "form-action 'none'",
            response["headers"]["Content-Security-Policy"],
        )

    def test_oauth_private_page_redirects_to_login_without_session(self):
        response = call_wsgi(self._oauth_app(), path="/")
        self.assertEqual(response["status"], "302 Found")
        self.assertEqual(response["headers"]["Location"], "/login")

    def test_oauth_api_rejects_missing_session_as_json(self):
        response = call_wsgi(self._oauth_app(), path="/api/dashboard")
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(response["json"], {"error": "authentication_required"})

    def test_oauth_login_sets_secure_state_and_nonce_cookie(self):
        oauth_client = StubOAuthClient()
        app = self._oauth_app(oauth_client=oauth_client)
        response, cookie = self._begin_oauth(app)
        self.assertEqual(response["status"], "302 Found")
        self.assertTrue(
            response["headers"]["Location"].startswith(
                "https://accounts.google.com/"
            )
        )
        self.assertEqual(
            oauth_client.authorization,
            ("random-token", "random-token"),
        )
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["max-age"], "300")

    def test_oauth_callback_rejects_missing_or_mismatched_state(self):
        app = self._oauth_app()
        response = call_wsgi(
            app,
            path="/oauth/callback",
            query_string="code=abc&state=wrong",
        )
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(response["json"], {"error": "invalid_oauth_state"})

        _, cookie = self._begin_oauth(app)
        response = call_wsgi(
            app,
            path="/oauth/callback",
            query_string="code=abc&state=wrong",
            headers={"Cookie": f"{OAUTH_STATE_COOKIE}={cookie.value}"},
        )
        self.assertEqual(response["json"], {"error": "invalid_oauth_state"})

    def test_oauth_callback_rejects_non_owner_or_invalid_nonce(self):
        claims = {
            "iss": next(iter(GOOGLE_ISSUERS)),
            "sub": "user-123",
            "email": "someone@example.com",
            "email_verified": True,
            "nonce": "random-token",
        }
        app = self._oauth_app(verifier=lambda token, audience: claims)
        _, cookie = self._begin_oauth(app)
        response = call_wsgi(
            app,
            path="/oauth/callback",
            query_string="code=abc&state=random-token",
            headers={"Cookie": f"{OAUTH_STATE_COOKIE}={cookie.value}"},
        )
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(response["json"], {"error": "owner_access_required"})

        claims["email"] = "owner@example.com"
        claims["nonce"] = "wrong"
        response = call_wsgi(
            app,
            path="/oauth/callback",
            query_string="code=abc&state=random-token",
            headers={"Cookie": f"{OAUTH_STATE_COOKIE}={cookie.value}"},
        )
        self.assertEqual(response["json"], {"error": "owner_access_required"})

    def test_oauth_callback_rejects_expired_state(self):
        original_app = self._oauth_app(now=1000)
        _, cookie = self._begin_oauth(original_app)
        expired_app = self._oauth_app(now=1400)
        response = call_wsgi(
            expired_app,
            path="/oauth/callback",
            query_string="code=abc&state=random-token",
            headers={"Cookie": f"{OAUTH_STATE_COOKIE}={cookie.value}"},
        )
        self.assertEqual(response["status"], "401 Unauthorized")
        self.assertEqual(response["json"], {"error": "invalid_oauth_state"})

    def test_oauth_callback_rejects_unverified_or_invalid_issuer(self):
        claims = {
            "iss": "https://accounts.google.com",
            "sub": "owner-123",
            "email": "owner@example.com",
            "email_verified": False,
            "nonce": "random-token",
        }
        app = self._oauth_app(verifier=lambda token, audience: claims)
        _, cookie = self._begin_oauth(app)
        response = call_wsgi(
            app,
            path="/oauth/callback",
            query_string="code=abc&state=random-token",
            headers={"Cookie": f"{OAUTH_STATE_COOKIE}={cookie.value}"},
        )
        self.assertEqual(response["json"], {"error": "owner_access_required"})

        claims["email_verified"] = True
        claims["iss"] = "https://attacker.example"
        response = call_wsgi(
            app,
            path="/oauth/callback",
            query_string="code=abc&state=random-token",
            headers={"Cookie": f"{OAUTH_STATE_COOKIE}={cookie.value}"},
        )
        self.assertEqual(response["json"], {"error": "owner_access_required"})

    def test_oauth_owner_receives_session_and_can_access_dashboard(self):
        oauth_client = StubOAuthClient()
        observed = {}

        def verifier(token, audience):
            observed["token"] = token
            observed["audience"] = audience
            return {
                "iss": "https://accounts.google.com",
                "sub": "owner-123",
                "email": "owner@example.com",
                "email_verified": True,
                "nonce": "random-token",
            }

        app = self._oauth_app(
            oauth_client=oauth_client,
            verifier=verifier,
        )
        _, state_cookie = self._begin_oauth(app)
        response = call_wsgi(
            app,
            path="/oauth/callback",
            query_string="code=auth-code&state=random-token",
            headers={
                "Cookie": f"{OAUTH_STATE_COOKIE}={state_cookie.value}"
            },
        )
        self.assertEqual(response["status"], "302 Found")
        self.assertEqual(response["headers"]["Location"], "/")
        self.assertEqual(
            oauth_client.exchange,
            ("auth-code", "random-token", "pkce-verifier"),
        )
        self.assertEqual(observed["token"], "google-id-token")
        self.assertEqual(observed["audience"], "client-id")
        session_cookie = response_cookies(response)[SESSION_COOKIE]
        self.assertTrue(session_cookie["secure"])
        self.assertTrue(session_cookie["httponly"])

        dashboard = call_wsgi(
            app,
            path="/api/dashboard",
            headers={"Cookie": f"{SESSION_COOKIE}={session_cookie.value}"},
        )
        self.assertEqual(dashboard["status"], "200 OK")
        self.assertEqual(
            dashboard["json"]["generated_at"],
            "2026-06-07T08:00:00",
        )

    def test_oauth_tampered_or_expired_session_is_rejected(self):
        app = self._oauth_app()
        session = app._sign_payload(
            {
                "email": "owner@example.com",
                "sub": "owner-123",
                "exp": 999,
            }
        )
        expired = call_wsgi(
            app,
            path="/api/dashboard",
            headers={"Cookie": f"{SESSION_COOKIE}={session}"},
        )
        self.assertEqual(expired["status"], "401 Unauthorized")

        tampered = call_wsgi(
            app,
            path="/api/dashboard",
            headers={"Cookie": f"{SESSION_COOKIE}={session}x"},
        )
        self.assertEqual(tampered["status"], "401 Unauthorized")

    def test_oauth_logout_clears_session(self):
        response = call_wsgi(self._oauth_app(), path="/logout")
        self.assertEqual(response["status"], "302 Found")
        self.assertEqual(response["headers"]["Location"], "/login")
        self.assertEqual(response_cookies(response)[SESSION_COOKIE]["max-age"], "0")

    def test_all_mutating_methods_are_rejected(self):
        app = AtlasCloudApplication(
            CloudWebSettings(),
            data_service=StubDataService(),
        )
        response = call_wsgi(app, path="/api/dashboard", method="POST")
        self.assertEqual(response["status"], "405 Method Not Allowed")
        self.assertEqual(response["headers"]["Allow"], "GET")

    def test_enabled_owner_controls_require_service(self):
        with self.assertRaisesRegex(ValueError, "owner control service"):
            self._oauth_app(owner_controls=True)

    def test_owner_action_requires_session_and_csrf(self):
        owner = StubOwnerControl()
        app = self._oauth_app(
            owner_controls=True,
            owner_control=owner,
        )
        unauthenticated = call_wsgi(
            app,
            path="/api/owner/research-decision",
            method="POST",
            body={"task_id": "task-1", "decision": "approve"},
        )
        self.assertEqual(unauthenticated["status"], "401 Unauthorized")

        session = app._sign_payload(
            {
                "email": "owner@example.com",
                "sub": "owner-123",
                "csrf": "csrf-value",
                "exp": 2000,
            }
        )
        forbidden = call_wsgi(
            app,
            path="/api/owner/research-decision",
            method="POST",
            headers={"Cookie": f"{SESSION_COOKIE}={session}"},
            body={"task_id": "task-1", "decision": "approve"},
        )
        self.assertEqual(forbidden["status"], "403 Forbidden")

        response = call_wsgi(
            app,
            path="/api/owner/research-decision",
            method="POST",
            headers={
                "Cookie": f"{SESSION_COOKIE}={session}",
                "X-Atlas-CSRF": "csrf-value",
            },
            body={"task_id": "task-1", "decision": "approve"},
        )
        self.assertEqual(response["status"], "200 OK")
        self.assertEqual(
            owner.actions,
            [
                (
                    "research-decision",
                    {"task_id": "task-1", "decision": "approve"},
                )
            ],
        )

    def test_owner_dashboard_includes_session_csrf(self):
        owner = StubOwnerControl()
        app = self._oauth_app(
            owner_controls=True,
            owner_control=owner,
        )
        session = app._sign_payload(
            {
                "email": "owner@example.com",
                "sub": "owner-123",
                "csrf": "csrf-value",
                "exp": 2000,
            }
        )
        response = call_wsgi(
            app,
            path="/api/dashboard",
            headers={"Cookie": f"{SESSION_COOKIE}={session}"},
        )
        self.assertEqual(
            response["json"]["owner_controls"]["csrf_token"],
            "csrf-value",
        )

    def test_owner_action_rejects_invalid_or_oversized_json(self):
        owner = StubOwnerControl()
        app = self._oauth_app(
            owner_controls=True,
            owner_control=owner,
        )
        session = app._sign_payload(
            {
                "email": "owner@example.com",
                "sub": "owner-123",
                "csrf": "csrf-value",
                "exp": 2000,
            }
        )
        headers = {
            "Cookie": f"{SESSION_COOKIE}={session}",
            "X-Atlas-CSRF": "csrf-value",
        }
        invalid = call_wsgi(
            app,
            path="/api/owner/research-decision",
            method="POST",
            headers=headers,
            body=b"{",
        )
        self.assertEqual(invalid["status"], "400 Bad Request")
        oversized = call_wsgi(
            app,
            path="/api/owner/research-decision",
            method="POST",
            headers=headers,
            body=b"x" * (16 * 1024 + 1),
        )
        self.assertEqual(oversized["status"], "413 Payload Too Large")

    def test_local_static_file_is_served(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            web_dir = Path(temp_dir)
            (web_dir / "index.html").write_text("Atlas", encoding="utf-8")
            app = AtlasCloudApplication(
                CloudWebSettings(web_dir=web_dir),
                data_service=StubDataService(),
            )
            captured = {}

            def start_response(status, headers):
                captured["status"] = status

            body = b"".join(
                app(
                    {"REQUEST_METHOD": "GET", "PATH_INFO": "/"},
                    start_response,
                )
            )
        self.assertEqual(captured["status"], "200 OK")
        self.assertEqual(body, b"Atlas")


if __name__ == "__main__":
    unittest.main()
