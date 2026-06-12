"""Fail-closed review of the Atlas tenant production architecture plan."""

import json
from pathlib import Path

from app.paths import project_path


DEFAULT_REVIEW_PATH = project_path(
    "config",
    "tenant_production_review.json",
)


class TenantProductionReadiness:
    """Validate that the documented plan preserves every release gate."""

    def __init__(self, review_path=DEFAULT_REVIEW_PATH):
        self.review_path = Path(review_path)

    def evaluate(self):
        review = self._load()
        checks = []

        def check(name, passed, detail):
            checks.append(
                {
                    "name": name,
                    "passed": bool(passed),
                    "detail": str(detail),
                }
            )

        database = review.get("database", {})
        identity = review.get("identity", {})
        deployment = review.get("deployment", {})
        cost = review.get("cost", {})
        gates = review.get("release_gates", {})

        check(
            "Conditional architecture decision",
            review.get("decision") == "conditional_go",
            review.get("decision", "missing"),
        )
        check(
            "Public registration remains disabled",
            review.get("public_registration") is False,
            review.get("public_registration"),
        )
        check(
            "Cloud changes remain unauthorized",
            review.get("cloud_changes_authorized") is False,
            review.get("cloud_changes_authorized"),
        )
        check(
            "Managed PostgreSQL selected",
            database.get("provider") == "cloud_sql_postgresql"
            and database.get("engine_major") >= 16,
            f"{database.get('provider')} {database.get('engine_major')}",
        )
        check(
            "Database uses IAM instead of static passwords",
            database.get("automatic_iam_authentication") is True
            and database.get("static_database_passwords") is False,
            "automatic IAM authentication",
        )
        check(
            "Database recovery controls required",
            database.get("automated_backups") is True
            and database.get("point_in_time_recovery") is True,
            "automated backups and point-in-time recovery",
        )
        check(
            "PostgreSQL adapter validated locally",
            database.get("driver") == "pg8000"
            and database.get("native_migrations") is True
            and database.get("adapter_validated_locally") is True,
            database.get("driver", "missing"),
        )
        check(
            "Identity Platform selected",
            identity.get("provider") == "identity_platform",
            identity.get("provider", "missing"),
        )
        check(
            "Invite-only registration retained",
            identity.get("registration") == "invite_only",
            identity.get("registration", "missing"),
        )
        check(
            "Privileged MFA uses TOTP",
            identity.get("mfa_factor") == "totp"
            and {"owner", "admin"}.issubset(
                set(identity.get("mfa_required_roles", []))
            ),
            ", ".join(identity.get("mfa_required_roles", [])),
        )
        check(
            "Owner service remains rollback path",
            deployment.get("separate_tenant_service") is True
            and deployment.get("preserve_owner_service_for_rollback") is True
            and deployment.get("separate_staging_data") is True,
            "separate service and data",
        )
        check(
            "Recurring schedules remain paused",
            deployment.get("schedules_remain_paused") is True,
            deployment.get("schedules_remain_paused"),
        )
        check(
            "Cost increase is visible",
            float(cost.get("estimated_staging_expected_usd", 0))
            > float(cost.get("current_target_monthly_usd", 0)),
            (
                f"${cost.get('estimated_staging_expected_usd')}/month expected "
                f"vs ${cost.get('current_target_monthly_usd')} target"
            ),
        )
        check(
            "Fresh cost approval remains required",
            cost.get("fresh_owner_approval_required") is True
            and database.get("activation_approved") is False
            and identity.get("activation_approved") is False,
            "no managed multi-user service activation approved",
        )
        required_gates = {
            "privacy_policy",
            "terms_of_service",
            "investment_adviser_review",
            "market_data_licensing",
            "incident_response",
            "retention_schedule",
            "external_security_test",
        }
        check(
            "Legal and operational gates documented",
            required_gates.issubset(gates)
            and all(gates.get(name) for name in required_gates),
            f"{len(required_gates.intersection(gates))}/{len(required_gates)}",
        )

        blocking = [
            "Cloud SQL activation approval",
            "Identity Platform activation approval",
            "Promotional credit expiration confirmation",
            "Privacy policy and terms",
            "Investment-adviser counsel review",
            "Market-data licensing review",
            "Incident-response and retention policies",
        ]
        all_passed = all(item["passed"] for item in checks)
        deployment_approved = (
            all_passed
            and review.get("cloud_changes_authorized") is True
            and database.get("activation_approved") is True
            and identity.get("activation_approved") is True
            and cost.get("credit_expiration_confirmed") is True
        )
        return {
            "review_version": review.get("review_version"),
            "decision": review.get("decision"),
            "architecture_checks_passed": all_passed,
            "deployment_approved": deployment_approved,
            "checks": checks,
            "blocking_gates": blocking,
            "cost": cost,
        }

    def _load(self):
        try:
            payload = json.loads(
                self.review_path.read_text(encoding="utf-8")
            )
        except FileNotFoundError as exc:
            raise ValueError("Tenant production review is required") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Tenant production review is invalid JSON") from exc
        if payload.get("review_version") != 1:
            raise ValueError("Unsupported tenant production review version")
        return payload
