"""Fail-closed WSGI application for the Atlas owner cloud dashboard."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
from urllib.parse import unquote

from app.paper_trading import PaperTradingAccount
from app.research_tasks import ResearchTaskQueue
from app.web_dashboard import DashboardDataService, STATIC_FILES, WEB_DIR


IAP_ISSUER = "https://cloud.google.com/iap"
IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key"


@dataclass(frozen=True)
class CloudWebSettings:
    """Runtime settings for local preview or authenticated cloud service."""

    mode: str = "local"
    auth_mode: str = "local"
    owner_email: str = ""
    iap_audience: str = ""
    web_dir: Path = WEB_DIR

    @classmethod
    def from_environment(cls):
        return cls(
            mode=os.getenv("ATLAS_WEB_MODE", "local").strip().lower(),
            auth_mode=os.getenv("ATLAS_AUTH_MODE", "local").strip().lower(),
            owner_email=os.getenv("ATLAS_OWNER_EMAIL", "").strip().lower(),
            iap_audience=os.getenv("ATLAS_IAP_AUDIENCE", "").strip(),
            web_dir=Path(os.getenv("ATLAS_WEB_DIR", str(WEB_DIR))),
        )

    def validate(self):
        if self.mode not in {"local", "cloud"}:
            raise ValueError("ATLAS_WEB_MODE must be local or cloud")
        if self.auth_mode not in {"local", "iap"}:
            raise ValueError("ATLAS_AUTH_MODE must be local or iap")
        if self.mode == "cloud":
            if self.auth_mode != "iap":
                raise ValueError("Cloud mode requires ATLAS_AUTH_MODE=iap")
            if not self.owner_email:
                raise ValueError("Cloud mode requires ATLAS_OWNER_EMAIL")
            if not self.iap_audience:
                raise ValueError("Cloud mode requires ATLAS_IAP_AUDIENCE")
        elif self.auth_mode != "local":
            raise ValueError("Local mode must use ATLAS_AUTH_MODE=local")


class GoogleIAPTokenVerifier:
    """Verify Google IAP's signed JWT and return its claims."""

    def __call__(self, token, audience):
        try:
            from google.auth.transport import requests
            from google.oauth2 import id_token
        except ImportError as exc:
            raise RuntimeError(
                "Cloud authentication requires requirements-web.txt"
            ) from exc
        return id_token.verify_token(
            token,
            requests.Request(),
            audience=audience,
            certs_url=IAP_CERTS_URL,
        )


class AtlasCloudApplication:
    """Small WSGI boundary around the existing read-only dashboard model."""

    def __init__(self, settings, data_service=None, token_verifier=None):
        settings.validate()
        self.settings = settings
        self.data_service = data_service or DashboardDataService()
        self.token_verifier = token_verifier or GoogleIAPTokenVerifier()

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = unquote(environ.get("PATH_INFO", "/"))

        if method != "GET":
            return self._json_response(
                start_response,
                "405 Method Not Allowed",
                {"error": "read_only"},
                extra_headers=[("Allow", "GET")],
            )
        if path == "/healthz":
            return self._json_response(start_response, "200 OK", {"status": "ok"})
        if path == "/readyz":
            ready = bool(self.data_service._latest_snapshot().get("generated_at"))
            status = "200 OK" if ready else "503 Service Unavailable"
            return self._json_response(
                start_response,
                status,
                {"status": "ready" if ready else "not_ready"},
            )

        authorized, _reason = self._authorize(environ)
        if not authorized:
            return self._json_response(
                start_response,
                "401 Unauthorized",
                {"error": "authentication_required"},
            )

        if path == "/api/dashboard":
            return self._json_response(
                start_response,
                "200 OK",
                self.data_service.build(),
            )
        static_file = STATIC_FILES.get(path)
        if static_file:
            filename, content_type = static_file
            return self._file_response(
                start_response,
                self.settings.web_dir / filename,
                content_type,
            )
        return self._json_response(
            start_response,
            "404 Not Found",
            {"error": "not_found"},
        )

    def _authorize(self, environ):
        if self.settings.auth_mode == "local":
            return True, ""
        token = environ.get("HTTP_X_GOOG_IAP_JWT_ASSERTION", "").strip()
        if not token:
            return False, "missing_iap_token"
        try:
            claims = self.token_verifier(token, self.settings.iap_audience)
        except Exception:
            return False, "invalid_iap_token"
        issuer = str(claims.get("iss", ""))
        email = str(claims.get("email", "")).lower()
        subject = str(claims.get("sub", ""))
        if issuer != IAP_ISSUER or not subject:
            return False, "invalid_iap_identity"
        if email != self.settings.owner_email:
            return False, "owner_access_required"
        return True, ""

    def _json_response(
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

    def _file_response(self, start_response, path, content_type):
        try:
            body = path.read_bytes()
        except FileNotFoundError:
            return self._json_response(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )
        start_response(
            "200 OK",
            self._security_headers(content_type, len(body)),
        )
        return [body]

    def _security_headers(self, content_type, content_length):
        headers = [
            ("Content-Type", content_type),
            ("Content-Length", str(content_length)),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
            ("X-Frame-Options", "DENY"),
            ("Referrer-Policy", "no-referrer"),
            ("Cross-Origin-Opener-Policy", "same-origin"),
            ("Cross-Origin-Resource-Policy", "same-origin"),
            (
                "Permissions-Policy",
                "camera=(), microphone=(), geolocation=(), payment=()",
            ),
            (
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                "base-uri 'none'; form-action 'none'",
            ),
        ]
        if self.settings.mode == "cloud":
            headers.append(
                (
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains",
                )
            )
        return headers


def data_service_from_environment():
    """Build the read model from an explicit persistent data root when supplied."""

    data_root = Path(
        os.getenv(
            "ATLAS_DATA_ROOT",
            str(Path(__file__).resolve().parent.parent),
        )
    )
    return DashboardDataService(
        archive_dir=data_root / "research_archive",
        paper_account=PaperTradingAccount(
            account_file=data_root / "paper_trading" / "account.json",
            ledger_file=data_root / "paper_trading" / "ledger.jsonl",
        ),
        research_queue=ResearchTaskQueue(
            data_root / "research_tasks" / "tasks.json"
        ),
    )


def create_application(settings=None, data_service=None, token_verifier=None):
    """Waitress-compatible application factory."""

    return AtlasCloudApplication(
        settings or CloudWebSettings.from_environment(),
        data_service=data_service or data_service_from_environment(),
        token_verifier=token_verifier,
    )
