import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from app.web_cloud import (
    AtlasCloudApplication,
    CloudWebSettings,
    IAP_ISSUER,
    data_service_from_environment,
)


class StubDataService:
    def __init__(self, ready=True):
        self.ready = ready

    def _latest_snapshot(self):
        return {"generated_at": "2026-06-07T08:00:00"} if self.ready else {}

    def build(self):
        return {"generated_at": "2026-06-07T08:00:00", "overview": {}}


def call_wsgi(application, path="/", method="GET", headers=None):
    captured = {}

    def start_response(status, response_headers):
        captured["status"] = status
        captured["headers"] = dict(response_headers)

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "wsgi.input": io.BytesIO(),
    }
    for name, value in (headers or {}).items():
        environ[f"HTTP_{name.upper().replace('-', '_')}"] = value
    body = b"".join(application(environ, start_response))
    captured["json"] = json.loads(body.decode("utf-8"))
    return captured


class CloudWebSettingsTests(unittest.TestCase):
    def test_cloud_mode_fails_closed_without_iap_configuration(self):
        with self.assertRaisesRegex(ValueError, "ATLAS_AUTH_MODE=iap"):
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

    def test_all_mutating_methods_are_rejected(self):
        app = AtlasCloudApplication(
            CloudWebSettings(),
            data_service=StubDataService(),
        )
        response = call_wsgi(app, path="/api/dashboard", method="POST")
        self.assertEqual(response["status"], "405 Method Not Allowed")
        self.assertEqual(response["headers"]["Allow"], "GET")

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
