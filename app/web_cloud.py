"""Fail-closed WSGI application for the Atlas owner cloud dashboard."""

from dataclasses import dataclass
import base64
from http.cookies import SimpleCookie
import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
import secrets
import time
from urllib.parse import parse_qs, unquote

from app.paper_trading import PaperTradingAccount
from app.research_tasks import ResearchTaskQueue
from app.web_dashboard import DashboardDataService, STATIC_FILES, WEB_DIR


IAP_ISSUER = "https://cloud.google.com/iap"
IAP_CERTS_URL = "https://www.gstatic.com/iap/verify/public_key"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
OAUTH_STATE_COOKIE = "__Host-atlas_oauth_state"
SESSION_COOKIE = "__Host-atlas_session"
OAUTH_STATE_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 3600
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CloudWebSettings:
    """Runtime settings for local preview or authenticated cloud service."""

    mode: str = "local"
    auth_mode: str = "local"
    owner_email: str = ""
    iap_audience: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_uri: str = ""
    session_secret: str = ""
    storage_bucket: str = ""
    web_dir: Path = WEB_DIR

    @classmethod
    def from_environment(cls):
        return cls(
            mode=os.getenv("ATLAS_WEB_MODE", "local").strip().lower(),
            auth_mode=os.getenv("ATLAS_AUTH_MODE", "local").strip().lower(),
            owner_email=os.getenv("ATLAS_OWNER_EMAIL", "").strip().lower(),
            iap_audience=os.getenv("ATLAS_IAP_AUDIENCE", "").strip(),
            google_client_id=os.getenv("ATLAS_GOOGLE_CLIENT_ID", "").strip(),
            google_client_secret=os.getenv(
                "ATLAS_GOOGLE_CLIENT_SECRET", ""
            ).strip(),
            oauth_redirect_uri=os.getenv(
                "ATLAS_OAUTH_REDIRECT_URI", ""
            ).strip(),
            session_secret=os.getenv("ATLAS_SESSION_SECRET", "").strip(),
            storage_bucket=os.getenv("ATLAS_GCS_BUCKET", "").strip(),
            web_dir=Path(os.getenv("ATLAS_WEB_DIR", str(WEB_DIR))),
        )

    def validate(self):
        if self.mode not in {"local", "cloud"}:
            raise ValueError("ATLAS_WEB_MODE must be local or cloud")
        if self.auth_mode not in {"local", "iap", "google_oauth"}:
            raise ValueError(
                "ATLAS_AUTH_MODE must be local, iap, or google_oauth"
            )
        if self.mode == "cloud":
            if self.auth_mode not in {"iap", "google_oauth"}:
                raise ValueError(
                    "Cloud mode requires IAP or Google OAuth authentication"
                )
            if not self.owner_email:
                raise ValueError("Cloud mode requires ATLAS_OWNER_EMAIL")
            if self.auth_mode == "iap" and not self.iap_audience:
                raise ValueError("Cloud mode requires ATLAS_IAP_AUDIENCE")
            if self.auth_mode == "google_oauth":
                required = {
                    "ATLAS_GOOGLE_CLIENT_ID": self.google_client_id,
                    "ATLAS_GOOGLE_CLIENT_SECRET": self.google_client_secret,
                    "ATLAS_OAUTH_REDIRECT_URI": self.oauth_redirect_uri,
                    "ATLAS_SESSION_SECRET": self.session_secret,
                }
                missing = [name for name, value in required.items() if not value]
                if missing:
                    raise ValueError(
                        "Google OAuth requires " + ", ".join(missing)
                    )
                if len(self.session_secret) < 32:
                    raise ValueError(
                        "ATLAS_SESSION_SECRET must be at least 32 characters"
                    )
                if not self.oauth_redirect_uri.startswith("https://"):
                    raise ValueError(
                        "ATLAS_OAUTH_REDIRECT_URI must use HTTPS"
                    )
            if not self.storage_bucket:
                raise ValueError("Cloud mode requires ATLAS_GCS_BUCKET")
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


class GoogleOIDCTokenVerifier:
    """Verify a Google OpenID Connect ID token."""

    def __call__(self, token, audience):
        try:
            from google.auth.transport import requests
            from google.oauth2 import id_token
        except ImportError as exc:
            raise RuntimeError(
                "Cloud authentication requires requirements-web.txt"
            ) from exc
        return id_token.verify_oauth2_token(
            token,
            requests.Request(),
            audience=audience,
        )


class GoogleOAuthClient:
    """Create Google authorization requests and exchange callback codes."""

    email_scope = "https://www.googleapis.com/auth/userinfo.email"
    scopes = [
        "openid",
        "email",
        email_scope,
    ]

    def __init__(self, settings):
        self.settings = settings

    def _flow(self, state=None, code_verifier=None):
        try:
            from google_auth_oauthlib.flow import Flow
        except ImportError as exc:
            raise RuntimeError(
                "Google OAuth requires requirements-web.txt"
            ) from exc
        client_config = {
            "web": {
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=self.scopes,
            state=state,
            code_verifier=code_verifier,
            autogenerate_code_verifier=code_verifier is None,
        )
        flow.redirect_uri = self.settings.oauth_redirect_uri
        return flow

    def authorization_url(self, state, nonce):
        flow = self._flow(state=state)
        url, _ = flow.authorization_url(
            access_type="online",
            include_granted_scopes="true",
            login_hint=self.settings.owner_email,
            nonce=nonce,
            prompt="select_account",
        )
        return url, flow.code_verifier

    def exchange_code(self, code, state, code_verifier):
        flow = self._flow(state=state, code_verifier=code_verifier)
        try:
            flow.fetch_token(code=code)
            token = flow.credentials.id_token
        except Warning as exc:
            granted_scopes = set(getattr(exc, "new_scope", ()))
            permitted_scopes = set(self.scopes)
            has_email = bool(
                granted_scopes.intersection({"email", self.email_scope})
            )
            token_response = getattr(exc, "token", {})
            if (
                not granted_scopes
                or not granted_scopes.issubset(permitted_scopes)
                or "openid" not in granted_scopes
                or not has_email
                or not hasattr(token_response, "get")
            ):
                raise
            token = token_response.get("id_token")
        if not token:
            raise ValueError("Google did not return an ID token")
        return token


class AtlasCloudApplication:
    """Small WSGI boundary around the existing read-only dashboard model."""

    def __init__(
        self,
        settings,
        data_service=None,
        token_verifier=None,
        oauth_client=None,
        oidc_verifier=None,
        clock=None,
        token_factory=None,
    ):
        settings.validate()
        self.settings = settings
        self.data_service = data_service or DashboardDataService()
        self.token_verifier = token_verifier or GoogleIAPTokenVerifier()
        self.oauth_client = oauth_client or (
            GoogleOAuthClient(settings)
            if settings.auth_mode == "google_oauth"
            else None
        )
        self.oidc_verifier = oidc_verifier or GoogleOIDCTokenVerifier()
        self.clock = clock or time.time
        self.token_factory = token_factory or secrets.token_urlsafe

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
        if self.settings.auth_mode == "google_oauth":
            if path == "/login":
                return self._start_google_login(start_response)
            if path == "/oauth/callback":
                return self._finish_google_login(environ, start_response)
            if path == "/logout":
                return self._redirect(
                    start_response,
                    "/login",
                    extra_headers=[
                        ("Set-Cookie", self._expired_cookie(SESSION_COOKIE))
                    ],
                )

        authorized, _reason = self._authorize(environ)
        if not authorized:
            if self.settings.auth_mode == "google_oauth" and not path.startswith(
                "/api/"
            ):
                return self._redirect(start_response, "/login")
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
        if self.settings.auth_mode == "google_oauth":
            session = self._read_signed_cookie(environ, SESSION_COOKIE)
            if not session:
                return False, "missing_session"
            if int(session.get("exp", 0)) < int(self.clock()):
                return False, "expired_session"
            if (
                str(session.get("email", "")).lower()
                != self.settings.owner_email
                or not session.get("sub")
            ):
                return False, "owner_access_required"
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

    def _start_google_login(self, start_response):
        state = self.token_factory(32)
        nonce = self.token_factory(32)
        try:
            location, code_verifier = self.oauth_client.authorization_url(
                state,
                nonce,
            )
        except Exception:
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                {"error": "authentication_unavailable"},
            )
        cookie_value = self._sign_payload(
            {
                "state": state,
                "nonce": nonce,
                "code_verifier": code_verifier,
                "exp": int(self.clock()) + OAUTH_STATE_TTL_SECONDS,
            }
        )
        return self._redirect(
            start_response,
            location,
            extra_headers=[
                (
                    "Set-Cookie",
                    self._cookie_header(
                        OAUTH_STATE_COOKIE,
                        cookie_value,
                        OAUTH_STATE_TTL_SECONDS,
                    ),
                )
            ],
        )

    def _finish_google_login(self, environ, start_response):
        query = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
        code = query.get("code", [""])[0]
        returned_state = query.get("state", [""])[0]
        pending = self._read_signed_cookie(environ, OAUTH_STATE_COOKIE)
        if (
            not code
            or not returned_state
            or not pending
            or int(pending.get("exp", 0)) < int(self.clock())
            or not hmac.compare_digest(
                returned_state,
                str(pending.get("state", "")),
            )
        ):
            return self._oauth_error(start_response, "invalid_oauth_state")
        try:
            raw_id_token = self.oauth_client.exchange_code(
                code,
                returned_state,
                str(pending.get("code_verifier", "")),
            )
        except Exception as exc:
            LOGGER.warning(
                "Google OAuth token exchange failed: %s",
                type(exc).__name__,
            )
            return self._oauth_error(start_response, "invalid_google_identity")
        try:
            claims = self.oidc_verifier(
                raw_id_token,
                self.settings.google_client_id,
            )
        except Exception as exc:
            LOGGER.warning(
                "Google OAuth ID token verification failed: %s",
                type(exc).__name__,
            )
            return self._oauth_error(start_response, "invalid_google_identity")
        issuer = str(claims.get("iss", ""))
        email = str(claims.get("email", "")).lower()
        subject = str(claims.get("sub", ""))
        nonce = str(claims.get("nonce", ""))
        if (
            issuer not in GOOGLE_ISSUERS
            or not subject
            or claims.get("email_verified") is not True
            or email != self.settings.owner_email
            or not hmac.compare_digest(nonce, str(pending.get("nonce", "")))
        ):
            return self._oauth_error(start_response, "owner_access_required")
        session = self._sign_payload(
            {
                "email": email,
                "sub": subject,
                "exp": int(self.clock()) + SESSION_TTL_SECONDS,
            }
        )
        return self._redirect(
            start_response,
            "/",
            extra_headers=[
                (
                    "Set-Cookie",
                    self._cookie_header(
                        SESSION_COOKIE,
                        session,
                        SESSION_TTL_SECONDS,
                    ),
                ),
                ("Set-Cookie", self._expired_cookie(OAUTH_STATE_COOKIE)),
            ],
        )

    def _oauth_error(self, start_response, reason):
        return self._json_response(
            start_response,
            "401 Unauthorized",
            {"error": reason},
            extra_headers=[
                ("Set-Cookie", self._expired_cookie(OAUTH_STATE_COOKIE))
            ],
        )

    def _sign_payload(self, payload):
        encoded = self._b64encode(
            json.dumps(
                payload,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        )
        signature = hmac.new(
            self.settings.session_secret.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return f"{encoded}.{self._b64encode(signature)}"

    def _read_signed_cookie(self, environ, name):
        raw_cookie = environ.get("HTTP_COOKIE", "")
        try:
            cookies = SimpleCookie()
            cookies.load(raw_cookie)
            value = cookies[name].value
            encoded, supplied_signature = value.split(".", 1)
            expected_signature = hmac.new(
                self.settings.session_secret.encode("utf-8"),
                encoded.encode("ascii"),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(
                supplied_signature,
                self._b64encode(expected_signature),
            ):
                return None
            return json.loads(self._b64decode(encoded).decode("utf-8"))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _b64encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64decode(value):
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)

    def _cookie_header(self, name, value, max_age):
        cookie = SimpleCookie()
        cookie[name] = value
        morsel = cookie[name]
        morsel["path"] = "/"
        morsel["max-age"] = str(max_age)
        morsel["httponly"] = True
        morsel["samesite"] = "Lax"
        if self.settings.mode == "cloud":
            morsel["secure"] = True
        return morsel.OutputString()

    def _expired_cookie(self, name):
        return self._cookie_header(name, "", 0)

    def _redirect(self, start_response, location, extra_headers=None):
        headers = self._security_headers("text/plain; charset=utf-8", 0)
        headers.append(("Location", location))
        headers.extend(extra_headers or [])
        start_response("302 Found", headers)
        return [b""]

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


def create_application(
    settings=None,
    data_service=None,
    token_verifier=None,
    oauth_client=None,
    oidc_verifier=None,
):
    """Waitress-compatible application factory."""

    return AtlasCloudApplication(
        settings or CloudWebSettings.from_environment(),
        data_service=data_service or data_service_from_environment(),
        token_verifier=token_verifier,
        oauth_client=oauth_client,
        oidc_verifier=oidc_verifier,
    )
