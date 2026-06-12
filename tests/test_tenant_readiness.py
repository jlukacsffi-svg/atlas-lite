import json
from pathlib import Path
import tempfile
import unittest

from app.tenant_readiness import (
    DEFAULT_REVIEW_PATH,
    TenantProductionReadiness,
)


class TenantProductionReadinessTests(unittest.TestCase):
    def test_default_review_passes_architecture_and_blocks_deployment(self):
        result = TenantProductionReadiness().evaluate()

        self.assertTrue(result["architecture_checks_passed"])
        self.assertFalse(result["deployment_approved"])
        self.assertEqual(len(result["checks"]), 15)
        self.assertGreater(
            result["cost"]["estimated_staging_expected_usd"],
            result["cost"]["current_target_monthly_usd"],
        )
        self.assertIn(
            "Cloud SQL activation approval",
            result["blocking_gates"],
        )

    def test_public_registration_fails_closed(self):
        review = json.loads(DEFAULT_REVIEW_PATH.read_text(encoding="utf-8"))
        review["public_registration"] = True

        result = self._evaluate(review)

        self.assertFalse(result["architecture_checks_passed"])
        failed = {
            item["name"] for item in result["checks"] if not item["passed"]
        }
        self.assertIn("Public registration remains disabled", failed)

    def test_static_database_passwords_fail_closed(self):
        review = json.loads(DEFAULT_REVIEW_PATH.read_text(encoding="utf-8"))
        review["database"]["static_database_passwords"] = True

        result = self._evaluate(review)

        self.assertFalse(result["architecture_checks_passed"])
        failed = {
            item["name"] for item in result["checks"] if not item["passed"]
        }
        self.assertIn(
            "Database uses IAM instead of static passwords",
            failed,
        )

    def test_missing_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.json"
            with self.assertRaisesRegex(
                ValueError,
                "Tenant production review is required",
            ):
                TenantProductionReadiness(missing).evaluate()

    def test_invalid_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError,
                "Tenant production review is invalid JSON",
            ):
                TenantProductionReadiness(path).evaluate()

    def _evaluate(self, review):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review.json"
            path.write_text(json.dumps(review), encoding="utf-8")
            return TenantProductionReadiness(path).evaluate()


if __name__ == "__main__":
    unittest.main()
