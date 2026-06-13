"""Fail-closed validation of Atlas governance and external release gates."""

import json
from pathlib import Path

from app.paths import project_path


DEFAULT_GOVERNANCE_PATH = project_path("config", "governance_review.json")

DOCUMENT_REQUIREMENTS = {
    "privacy_policy": {
        "status": "draft_complete",
        "headings": (
            "## Information Atlas May Collect",
            "## Privacy Choices",
            "## Security",
        ),
    },
    "terms_of_service": {
        "status": "draft_complete",
        "headings": (
            "## Research, Not Execution",
            "## Acceptable Use",
            "## Third-Party Services And Data",
        ),
    },
    "retention_schedule": {
        "status": "internal_baseline_complete",
        "headings": ("## Schedule", "## Deletion Workflow", "## Review"),
    },
    "incident_response": {
        "status": "internal_playbook_complete",
        "headings": (
            "## Severity",
            "## Contain",
            "## Notification",
            "## Post-Incident Review",
        ),
    },
    "external_review_packet": {
        "status": "packet_complete",
        "headings": (
            "## Investment-Adviser Counsel Questions",
            "## Market And News Data Review",
            "## Independent Security Review Scope",
        ),
    },
}

EXTERNAL_REVIEWS = {
    "investment_adviser_counsel",
    "market_data_licensing",
    "independent_security_test",
    "owner_invite_only_release",
}


class GovernanceReadiness:
    """Validate internal policy artifacts without self-approving external gates."""

    def __init__(self, review_path=DEFAULT_GOVERNANCE_PATH):
        self.review_path = Path(review_path)

    def evaluate(self):
        review = self._load()
        checks = []

        def check(name, passed, detail):
            checks.append(
                {"name": name, "passed": bool(passed), "detail": str(detail)}
            )

        documents = review.get("documents", {})
        for name, requirement in DOCUMENT_REQUIREMENTS.items():
            record = documents.get(name, {})
            path_value = record.get("path", "")
            path = project_path(path_value) if path_value else None
            exists = bool(path and path.is_file())
            content = path.read_text(encoding="utf-8") if exists else ""
            check(
                f"{name} document and sections",
                exists
                and record.get("status") == requirement["status"]
                and all(heading in content for heading in requirement["headings"]),
                path_value or "missing",
            )

        reviews = review.get("external_reviews", {})
        check(
            "External review gates are explicit",
            EXTERNAL_REVIEWS.issubset(reviews)
            and all(reviews.get(name) in {"pending", "approved"} for name in EXTERNAL_REVIEWS),
            f"{len(EXTERNAL_REVIEWS.intersection(reviews))}/{len(EXTERNAL_REVIEWS)}",
        )
        check(
            "External authorization matches review status",
            (
                review.get("external_users_authorized") is False
                and all(reviews.get(name) == "pending" for name in EXTERNAL_REVIEWS)
            )
            or (
                review.get("external_users_authorized") is True
                and all(reviews.get(name) == "approved" for name in EXTERNAL_REVIEWS)
            ),
            (
                "external users authorized"
                if review.get("external_users_authorized")
                else "external users blocked"
            ),
        )

        rules = review.get("release_rules", {})
        protected_rules = {
            "public_registration",
            "external_invitations",
            "real_trading",
            "brokerage_connection",
            "customer_data_redistribution",
        }
        check(
            "High-risk release capabilities remain disabled",
            protected_rules.issubset(rules)
            and all(rules.get(name) is False for name in protected_rules),
            f"{len(protected_rules.intersection(rules))}/{len(protected_rules)}",
        )

        engineering_ready = all(item["passed"] for item in checks)
        external_approved = (
            engineering_ready
            and review.get("external_users_authorized") is True
            and all(reviews.get(name) == "approved" for name in EXTERNAL_REVIEWS)
        )
        return {
            "review_version": review.get("review_version"),
            "engineering_ready": engineering_ready,
            "external_release_approved": external_approved,
            "checks": checks,
            "external_reviews": reviews,
            "blocking_gates": [
                name
                for name in sorted(EXTERNAL_REVIEWS)
                if reviews.get(name) != "approved"
            ],
        }

    def _load(self):
        try:
            review = json.loads(self.review_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError("Governance review is required") from exc
        except json.JSONDecodeError as exc:
            raise ValueError("Governance review is invalid JSON") from exc
        if review.get("review_version") != 1:
            raise ValueError("Unsupported governance review version")
        return review
