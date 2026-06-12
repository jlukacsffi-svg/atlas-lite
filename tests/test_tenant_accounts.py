import json
import tempfile
import unittest
from pathlib import Path

from app.tenant_accounts import (
    TenantAccessError,
    TenantRegistry,
    TenantWorkspacePaths,
)


class TenantAccountTests(unittest.TestCase):
    def _registry(self, accounts):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        path = Path(temp_dir.name) / "registry.json"
        path.write_text(
            json.dumps({"schema_version": 1, "accounts": accounts}),
            encoding="utf-8",
        )
        return TenantRegistry(path)

    @staticmethod
    def _account(
        tenant_id="alpha-workspace",
        user_id="alpha-owner",
        subject="google-alpha",
        email="alpha@example.com",
        role="owner",
        status="active",
    ):
        return {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "provider": "google",
            "subject": subject,
            "email": email,
            "role": role,
            "status": status,
        }

    def test_resolves_only_exact_verified_identity(self):
        registry = self._registry([self._account()])

        account = registry.resolve(
            "google",
            "google-alpha",
            "ALPHA@example.com",
        )

        self.assertEqual(account.tenant_id, "alpha-workspace")
        with self.assertRaisesRegex(TenantAccessError, "not invited"):
            registry.resolve("google", "google-unknown", "alpha@example.com")
        with self.assertRaisesRegex(TenantAccessError, "does not match"):
            registry.resolve("google", "google-alpha", "other@example.com")

    def test_disabled_account_fails_closed(self):
        registry = self._registry([self._account(status="disabled")])

        with self.assertRaisesRegex(TenantAccessError, "disabled"):
            registry.resolve("google", "google-alpha", "alpha@example.com")

    def test_cross_tenant_access_is_denied(self):
        registry = self._registry([self._account()])
        account = registry.resolve(
            "google",
            "google-alpha",
            "alpha@example.com",
        )

        registry.authorize(account, "alpha-workspace", "workspace:read")
        with self.assertRaisesRegex(TenantAccessError, "Cross-tenant"):
            registry.authorize(account, "beta-workspace", "workspace:read")

    def test_roles_enforce_least_privilege(self):
        viewer = self._account(
            user_id="alpha-viewer",
            subject="google-viewer",
            email="viewer@example.com",
            role="viewer",
        )
        registry = self._registry([viewer])
        account = registry.resolve(
            "google",
            "google-viewer",
            "viewer@example.com",
        )

        registry.authorize(account, "alpha-workspace", "workspace:read")
        with self.assertRaisesRegex(TenantAccessError, "Role"):
            registry.authorize(account, "alpha-workspace", "research:write")
        with self.assertRaisesRegex(TenantAccessError, "Role"):
            registry.authorize(account, "alpha-workspace", "members:manage")

    def test_duplicate_identity_or_membership_is_rejected(self):
        duplicate_identity = self._account(
            tenant_id="beta-workspace",
            user_id="beta-owner",
        )
        with self.assertRaisesRegex(ValueError, "Duplicate external identity"):
            self._registry([self._account(), duplicate_identity])

        duplicate_membership = self._account(
            subject="google-other",
            email="other@example.com",
        )
        with self.assertRaisesRegex(ValueError, "Duplicate tenant membership"):
            self._registry([self._account(), duplicate_membership])

    def test_workspace_paths_are_tenant_scoped(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            alpha = TenantWorkspacePaths(temp_dir, "alpha-workspace")
            beta = TenantWorkspacePaths(temp_dir, "beta-workspace")

            self.assertNotEqual(alpha.root, beta.root)
            self.assertEqual(
                alpha.research_archive,
                Path(temp_dir).resolve()
                / "tenants"
                / "alpha-workspace"
                / "research_archive",
            )
            self.assertNotIn(alpha.root, beta.root.parents)

    def test_workspace_rejects_unsafe_tenant_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            for tenant_id in ("../owner", "Owner Space", "/absolute", "a"):
                with self.subTest(tenant_id=tenant_id):
                    with self.assertRaisesRegex(ValueError, "Invalid tenant_id"):
                        TenantWorkspacePaths(temp_dir, tenant_id)

    def test_registry_rejects_invalid_role_and_schema(self):
        invalid_role = self._account(role="superuser")
        with self.assertRaisesRegex(ValueError, "Invalid tenant role"):
            self._registry([invalid_role])

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "registry.json"
            path.write_text(
                json.dumps({"schema_version": 2, "accounts": []}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                TenantRegistry(path)


if __name__ == "__main__":
    unittest.main()
