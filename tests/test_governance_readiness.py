import json
from pathlib import Path
import tempfile
import unittest

from app.governance_readiness import (
    DEFAULT_GOVERNANCE_PATH,
    GovernanceReadiness,
)


class GovernanceReadinessTests(unittest.TestCase):
    def test_default_review_passes_engineering_and_blocks_external_release(self):
        result = GovernanceReadiness().evaluate()

        self.assertTrue(result["engineering_ready"])
        self.assertFalse(result["external_release_approved"])
        self.assertEqual(len(result["checks"]), 8)
        self.assertEqual(len(result["blocking_gates"]), 4)

    def test_missing_document_fails_closed(self):
        review = json.loads(DEFAULT_GOVERNANCE_PATH.read_text(encoding="utf-8"))
        review["documents"]["privacy_policy"]["path"] = "missing-policy.md"

        result = self._evaluate(review)

        self.assertFalse(result["engineering_ready"])

    def test_external_review_cannot_enable_release_without_all_approvals(self):
        review = json.loads(DEFAULT_GOVERNANCE_PATH.read_text(encoding="utf-8"))
        review["external_users_authorized"] = True
        review["external_reviews"]["investment_adviser_counsel"] = "approved"

        result = self._evaluate(review)

        self.assertFalse(result["engineering_ready"])
        self.assertFalse(result["external_release_approved"])

    def test_invalid_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "governance.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid JSON"):
                GovernanceReadiness(path).evaluate()

    def test_release_requires_every_external_approval(self):
        review = json.loads(DEFAULT_GOVERNANCE_PATH.read_text(encoding="utf-8"))
        review["external_users_authorized"] = True
        for name in review["external_reviews"]:
            review["external_reviews"][name] = "approved"

        result = self._evaluate(review)

        self.assertTrue(result["engineering_ready"])
        self.assertTrue(result["external_release_approved"])
        self.assertEqual(result["blocking_gates"], [])

    def _evaluate(self, review):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "governance.json"
            path.write_text(json.dumps(review), encoding="utf-8")
            return GovernanceReadiness(path).evaluate()


if __name__ == "__main__":
    unittest.main()
