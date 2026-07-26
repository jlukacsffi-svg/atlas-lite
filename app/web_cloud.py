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
import threading
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
MAX_OWNER_REQUEST_BYTES = 16 * 1024


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
    owner_controls_enabled: bool = False
    verification_token: str = ""
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
            owner_controls_enabled=os.getenv(
                "ATLAS_OWNER_CONTROLS_ENABLED",
                "false",
            ).strip().lower() == "true",
            verification_token=os.getenv(
                "ATLAS_VERIFICATION_TOKEN",
                "",
            ).strip(),
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
            if self.owner_controls_enabled and self.auth_mode != "google_oauth":
                raise ValueError(
                    "Owner controls require Google OAuth cloud mode"
                )
        elif self.auth_mode != "local":
            raise ValueError("Local mode must use ATLAS_AUTH_MODE=local")
        elif self.owner_controls_enabled:
            raise ValueError(
                "Owner controls cannot run in unauthenticated local mode"
            )


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
        owner_control=None,
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
        self.owner_control = owner_control
        if settings.owner_controls_enabled and owner_control is None:
            raise ValueError(
                "Enabled owner controls require an owner control service"
            )

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD", "GET").upper()
        path = unquote(environ.get("PATH_INFO", "/"))

        if method not in {"GET", "POST"}:
            return self._json_response(
                start_response,
                "405 Method Not Allowed",
                {"error": "read_only"},
                extra_headers=[("Allow", "GET, POST")],
            )
        if method == "POST" and not path.startswith("/api/owner/"):
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
        if path == "/api/dashboard/verification":
            if not self.settings.verification_token:
                return self._json_response(
                    start_response,
                    "404 Not Found",
                    {"error": "not_found"},
                )
            if not self._verification_authorized(environ):
                return self._json_response(
                    start_response,
                    "401 Unauthorized",
                    {"error": "authentication_required"},
                )
            return self._json_response(
                start_response,
                "200 OK",
                self._verification_payload(),
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

        if method == "POST":
            return self._owner_action(environ, start_response, path)
        if path == "/api/dashboard/summary":
            return self._json_response(
                start_response,
                "200 OK",
                self.data_service.build_summary(),
            )
        if path == "/api/dashboard":
            data = self.data_service.build()
            if self.settings.owner_controls_enabled:
                session = self._read_signed_cookie(environ, SESSION_COOKIE)
                data["owner_controls"] = {
                    **self.owner_control.model(),
                    "csrf_token": session.get("csrf", "") if session else "",
                }
            return self._json_response(
                start_response,
                "200 OK",
                data,
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

    def _verification_authorized(self, environ):
        provided = environ.get("HTTP_X_ATLAS_VERIFICATION", "").strip()
        expected = self.settings.verification_token.strip()
        if not provided or not expected:
            return False
        return hmac.compare_digest(provided, expected)

    def _verification_payload(self):
        # Verification must stay read-only and fast. Avoid the refreshing wrapper
        # here so smoke checks do not attempt a cloud artifact sync under the
        # Cloud Run request timeout.
        data_service = getattr(self.data_service, "data_service", self.data_service)
        if hasattr(data_service, "build_verification"):
            data = data_service.build_verification()
        else:
            data = data_service.build()
        paper = data.get("paper") or {}
        validation = paper.get("validation_summary") or {}
        feedback_summary = paper.get("feedback_summary") or {}
        accountability = paper.get("accountability_report") or {}
        capital_rotation = paper.get("capital_rotation_scoreboard") or {}
        proposal_counts = paper.get("proposals") or {}
        auto_manage_enabled = (
            str(
                ((paper.get("operating_mode") or {}).get("current") or {}).get("id")
                or ""
            )
            == "paper_auto_manage"
        )
        pending_manual_count = int(proposal_counts.get("pending") or 0)
        evidence_pipeline = validation.get("evidence_pipeline") or {}
        completed_diagnostics = (
            validation.get("completed_position_diagnostics") or {}
        )
        shadow_trigger_analysis = validation.get("shadow_trigger_analysis") or {}
        evidence_maturity_pct = (
            (validation.get("capital_readiness") or {}).get("progress_pct")
        )
        return {
            "generated_at": data.get("generated_at"),
            "workspace": data.get("workspace") or {},
            "checks": {
                "stage5_scoreboard": {
                    "ok": bool(validation),
                    "detail": (
                        "Stage 5 validation summary is available with "
                        f"{int(evidence_pipeline.get('snapshot_count') or 0)} snapshots, "
                        f"{int(evidence_pipeline.get('judged_decisions') or 0)} judged decisions, "
                        f"and {int(evidence_pipeline.get('completed_positions') or 0)} completed positions."
                    ),
                    "evidence_maturity_pct": evidence_maturity_pct,
                    "snapshot_count": int(
                        evidence_pipeline.get("snapshot_count") or 0
                    ),
                    "judged_decisions": int(
                        evidence_pipeline.get("judged_decisions") or 0
                    ),
                    "realized_exits": int(
                        evidence_pipeline.get("realized_exits") or 0
                    ),
                    "partial_trims": int(
                        evidence_pipeline.get("partial_trims") or 0
                    ),
                },
                "completed_position_diagnostics": {
                    "ok": bool(completed_diagnostics.get("available"))
                    and bool(completed_diagnostics.get("cycles"))
                    and self._ui_contains("Completed position diagnosis"),
                    "detail": (
                        "Dashboard diagnoses entry timing, first defensive "
                        "response, and exit execution across "
                        f"{int(completed_diagnostics.get('sample_size') or 0)} "
                        "completed paper positions."
                    ),
                    "sample_size": int(
                        completed_diagnostics.get("sample_size") or 0
                    ),
                    "late_risk_responses": int(
                        completed_diagnostics.get("late_risk_responses") or 0
                    ),
                    "fragmented_exits": int(
                        completed_diagnostics.get("fragmented_exits") or 0
                    ),
                },
                "shadow_trigger_analysis": {
                    "ok": bool(shadow_trigger_analysis.get("available"))
                    and shadow_trigger_analysis.get("policy_changed") is False
                    and bool(shadow_trigger_analysis.get("candidates"))
                    and self._ui_contains("Defensive trigger shadow test"),
                    "detail": (
                        "Dashboard exposes no-action defensive-trigger replay "
                        "results while preserving the current paper policy."
                    ),
                    "policy_changed": bool(
                        shadow_trigger_analysis.get("policy_changed")
                    ),
                    "automatic_exit_improvement": float(
                        shadow_trigger_analysis.get(
                            "automatic_exit_improvement"
                        )
                        or 0
                    ),
                    "automatic_exit_recovery_rate_pct": float(
                        shadow_trigger_analysis.get(
                            "automatic_exit_recovery_rate_pct"
                        )
                        or 0
                    ),
                },
                "persistence_learning": {
                    "ok": bool(
                        (feedback_summary.get("horizon_learning") or [])
                        or (paper.get("feedback") or [])
                    ),
                    "detail": "Paper feedback includes persistence checkpoints and learning context.",
                },
                "benchmark_labels": {
                    "ok": self._ui_contains("Stage 5 validation scoreboard")
                    and self._ui_contains("SPY (S&P 500 ETF benchmark)")
                    and self._ui_contains("QQQ (Nasdaq-100 ETF benchmark)"),
                    "detail": "UI assets label SPY and QQQ explicitly and keep the Stage 5 scoreboard contract.",
                },
                "benchmark_scorecard": {
                    "ok": bool(feedback_summary.get("benchmark_scorecard"))
                    and self._ui_contains("Benchmark scorecard")
                    and self._ui_contains("Avg decision edge"),
                    "detail": "Paper feedback includes benchmark-specific decision scorecards for SPY and QQQ.",
                },
                "benchmark_exit_tuning": {
                    "ok": "benchmark_exit_stats"
                    in (
                        (feedback_summary.get("projection_threshold_profile") or {})
                    ),
                    "detail": "Adaptive projection tuning carries benchmark-specific exit scorecard evidence.",
                },
                "benchmark_entry_pacing": {
                    "ok": "benchmark_rotation_stats"
                    in ((feedback_summary.get("entry_strategy_profile") or {}))
                    and self._ui_contains("Adaptive entry pacing"),
                    "detail": "Adaptive entry pacing carries benchmark-specific buy scorecard evidence.",
                },
                "capital_rotation_scoreboard": {
                    "ok": "sectors" in capital_rotation
                    and "totals" in capital_rotation
                    and self._ui_contains("Capital rotation scoreboard"),
                    "detail": "Dashboard exposes sector-level simulated capital rotation, exposure, and outcome accountability.",
                    "sector_count": len(capital_rotation.get("sectors") or []),
                },
                "sector_learning_bridge": {
                    "ok": "sector_learning_bridge" in feedback_summary
                    and self._ui_contains("Sector learning bridge")
                    and self._ui_contains("Sector learning gate")
                    and self._ui_contains("Strategy tilt"),
                    "detail": "Dashboard exposes the sector-level paper-learning bridge behind small strategy boosts or cautions.",
                    "sector_count": len(
                        (feedback_summary.get("sector_learning_bridge") or {}).get(
                            "sectors"
                        )
                        or []
                    ),
                },
                "sector_gate_audit": {
                    "ok": "sector_gate_audit" in feedback_summary
                    and "candidate_counts"
                    in (feedback_summary.get("sector_gate_audit") or {})
                    and "accepted_decision_counts"
                    in (feedback_summary.get("sector_gate_audit") or {})
                    and self._ui_contains("Sector gate audit"),
                    "detail": "Dashboard exposes sector-gate pass, tighten, boost, and accepted-decision accountability.",
                },
                "sector_gate_outcomes": {
                    "ok": "sector_gate_outcomes" in feedback_summary
                    and "scorecards"
                    in (feedback_summary.get("sector_gate_outcomes") or {})
                    and self._ui_contains("Sector gate outcomes"),
                    "detail": "Dashboard measures whether accepted sector-gate buys are working versus the stronger SPY/QQQ benchmark bar.",
                },
                "autonomous_queue": {
                    "ok": auto_manage_enabled and pending_manual_count == 0,
                    "detail": (
                        "Atlas paper auto-manage mode is active and no pending paper proposals "
                        "still require manual approval."
                    ),
                    "pending_manual_proposals": pending_manual_count,
                },
                "accountability_report": {
                    "ok": "tickers" in accountability and "summary" in accountability,
                    "detail": "Paper accountability report exposes ticker-grouped lot history and summary fields for tax review.",
                    "ticker_count": len(accountability.get("tickers") or []),
                },
            },
            "paper": {
                "validation_summary": validation,
                "feedback_summary": feedback_summary,
                "accountability_report": accountability,
                "capital_rotation_scoreboard": capital_rotation,
                "operating_mode": paper.get("operating_mode") or {},
                "proposal_counts": proposal_counts,
            },
            "owner_controls": {
                "enabled": bool(self.settings.owner_controls_enabled),
                "paper_proposals": [],
            },
        }

    def _ui_contains(self, needle):
        for filename in ("index.html", "app.js"):
            path = self.settings.web_dir / filename
            try:
                if needle in path.read_text(encoding="utf-8"):
                    return True
            except OSError:
                continue
        return False

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
                "csrf": self.token_factory(32),
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

    def _owner_action(self, environ, start_response, path):
        if not self.settings.owner_controls_enabled or self.owner_control is None:
            return self._json_response(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )
        session = self._read_signed_cookie(environ, SESSION_COOKIE)
        supplied = environ.get("HTTP_X_ATLAS_CSRF", "")
        expected = str((session or {}).get("csrf", ""))
        if not expected or not hmac.compare_digest(supplied, expected):
            return self._json_response(
                start_response,
                "403 Forbidden",
                {"error": "invalid_csrf"},
            )
        try:
            length = int(environ.get("CONTENT_LENGTH", "0") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_OWNER_REQUEST_BYTES:
            return self._json_response(
                start_response,
                "413 Payload Too Large",
                {"error": "invalid_request_size"},
            )
        try:
            body = environ.get("wsgi.input").read(length)
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
            return self._json_response(
                start_response,
                "400 Bad Request",
                {"error": "invalid_json"},
            )
        action = path.removeprefix("/api/owner/")
        try:
            result = self.owner_control.apply(action, payload)
        except ValueError as exc:
            return self._json_response(
                start_response,
                "400 Bad Request",
                {"error": "invalid_owner_action", "detail": str(exc)},
            )
        except Exception as exc:
            LOGGER.error(
                "Owner action failed: %s",
                type(exc).__name__,
            )
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                {"error": "owner_action_not_persisted"},
            )
        return self._json_response(
            start_response,
            "200 OK",
            {"status": "ok", "result": result},
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


class RefreshingDashboardDataService:
    """Refresh cloud artifacts periodically while retaining last-known data."""

    def __init__(
        self,
        data_service,
        refresh,
        interval_seconds=60,
        clock=None,
    ):
        self.data_service = data_service
        self.refresh = refresh
        self.interval_seconds = interval_seconds
        self.clock = clock or time.monotonic
        self.last_attempt = self.clock()
        self.lock = threading.Lock()

    def build(self):
        self._refresh_if_due()
        return self.data_service.build()

    def build_summary(self):
        self._refresh_if_due()
        return self.data_service.build_summary()

    def _latest_snapshot(self):
        self._refresh_if_due()
        return self.data_service._latest_snapshot()

    def _refresh_if_due(self):
        now = self.clock()
        if now - self.last_attempt < self.interval_seconds:
            return
        with self.lock:
            now = self.clock()
            if now - self.last_attempt < self.interval_seconds:
                return
            self.last_attempt = now
            try:
                downloaded = self.refresh()
                LOGGER.info(
                    "Refreshed %d private cloud artifacts",
                    len(downloaded),
                )
            except Exception as exc:
                LOGGER.warning(
                    "Cloud artifact refresh failed; serving last-known data: %s",
                    type(exc).__name__,
                )


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
    owner_control=None,
):
    """Waitress-compatible application factory."""

    return AtlasCloudApplication(
        settings or CloudWebSettings.from_environment(),
        data_service=data_service or data_service_from_environment(),
        token_verifier=token_verifier,
        oauth_client=oauth_client,
        oidc_verifier=oidc_verifier,
        owner_control=owner_control,
    )
