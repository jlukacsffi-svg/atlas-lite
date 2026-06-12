import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.tenant_accounts import TenantAccount, TenantAccessError
from app.tenant_store import SCHEMA_VERSION, TenantStore


class TenantStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.database = Path(self.temp_dir.name) / "atlas-tenants.sqlite3"
        self.store = TenantStore(
            self.database,
            clock=lambda: "2026-06-11T12:00:00+00:00",
        )
        self.store.migrate()
        self.alpha_owner = self._account(
            "alpha-workspace",
            "alpha-owner",
            "google-alpha",
            "alpha@example.com",
            "owner",
        )
        self.beta_owner = self._account(
            "beta-workspace",
            "beta-owner",
            "google-beta",
            "beta@example.com",
            "owner",
        )
        self.store.provision_account("Alpha", self.alpha_owner)
        self.store.provision_account("Beta", self.beta_owner)

    @staticmethod
    def _account(tenant, user, subject, email, role, status="active"):
        return TenantAccount(
            tenant_id=tenant,
            user_id=user,
            provider="google",
            subject=subject,
            email=email,
            role=role,
            status=status,
        )

    def test_migration_is_versioned_and_idempotent(self):
        self.assertEqual(self.store.schema_version(), SCHEMA_VERSION)
        self.assertEqual(self.store.migrate(), SCHEMA_VERSION)
        self.assertEqual(self.store.schema_version(), SCHEMA_VERSION)

    def test_database_enables_foreign_keys(self):
        with self.store.connect() as connection:
            enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(enabled, 1)

    def test_identity_resolution_requires_subject_and_verified_email(self):
        resolved = self.store.resolve(
            "google",
            "google-alpha",
            "ALPHA@example.com",
        )
        self.assertEqual(resolved, self.alpha_owner)

        with self.assertRaisesRegex(PermissionError, "not invited"):
            self.store.resolve("google", "unknown", "alpha@example.com")
        with self.assertRaisesRegex(PermissionError, "does not match"):
            self.store.resolve(
                "google",
                "google-alpha",
                "attacker@example.com",
            )

    def test_viewer_can_read_but_cannot_write(self):
        viewer = self._account(
            "alpha-workspace",
            "alpha-viewer",
            "google-alpha-viewer",
            "viewer@example.com",
            "viewer",
        )
        self.store.add_membership(self.alpha_owner, viewer)
        self.assertEqual(self.store.list_reports(viewer), [])
        with self.assertRaisesRegex(TenantAccessError, "Role"):
            self.store.create_report(
                viewer,
                "Report",
                "2026-06-11T12:00:00+00:00",
            )

    def test_repository_rejects_forged_or_stale_account_claims(self):
        forged = self._account(
            "alpha-workspace",
            "invented-owner",
            "invented-subject",
            "forged@example.com",
            "owner",
        )
        with self.assertRaisesRegex(PermissionError, "not invited"):
            self.store.list_reports(forged)

        escalated = self._account(
            "alpha-workspace",
            "alpha-owner",
            "google-alpha",
            "alpha@example.com",
            "admin",
        )
        with self.assertRaisesRegex(PermissionError, "claims do not match"):
            self.store.list_reports(escalated)

    def test_disabled_membership_cannot_use_repository(self):
        with self.store.connect() as connection:
            connection.execute(
                """
                UPDATE memberships
                SET status = 'disabled'
                WHERE tenant_id = ? AND user_id = ?
                """,
                (
                    self.alpha_owner.tenant_id,
                    self.alpha_owner.user_id,
                ),
            )

        with self.assertRaisesRegex(PermissionError, "disabled"):
            self.store.list_reports(self.alpha_owner)

    def test_cross_tenant_resources_are_invisible(self):
        self.store.create_report(
            self.alpha_owner,
            "Alpha Brief",
            "2026-06-11T12:00:00+00:00",
            summary={"movers": ["NVDA"]},
            report_id="brief",
        )
        self.store.create_report(
            self.beta_owner,
            "Beta Brief",
            "2026-06-11T12:00:00+00:00",
            summary={"movers": ["MSFT"]},
            report_id="brief",
        )

        alpha = self.store.list_reports(self.alpha_owner)
        beta = self.store.list_reports(self.beta_owner)

        self.assertEqual([item["title"] for item in alpha], ["Alpha Brief"])
        self.assertEqual([item["title"] for item in beta], ["Beta Brief"])
        self.assertEqual(alpha[0]["summary"], {"movers": ["NVDA"]})

    def test_composite_foreign_keys_reject_cross_tenant_child_records(self):
        watchlist = self.store.create_watchlist(
            self.alpha_owner,
            "Alpha Core",
            watchlist_id="core",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.add_watchlist_item(
                self.beta_owner,
                watchlist,
                "NVDA",
            )

        portfolio = self.store.create_portfolio(
            self.alpha_owner,
            "Alpha Portfolio",
            portfolio_id="primary",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.set_position(
                self.beta_owner,
                portfolio,
                "NVDA",
                1,
                100,
            )

    def test_watchlists_are_tenant_scoped(self):
        alpha_list = self.store.create_watchlist(
            self.alpha_owner,
            "Core",
            watchlist_id="core",
        )
        beta_list = self.store.create_watchlist(
            self.beta_owner,
            "Core",
            watchlist_id="core",
        )
        self.store.add_watchlist_item(
            self.alpha_owner,
            alpha_list,
            "NVDA",
            category="Core",
        )
        self.store.add_watchlist_item(
            self.beta_owner,
            beta_list,
            "MSFT",
            category="Watchlist",
        )

        self.assertEqual(
            [item["ticker"] for item in self.store.list_watchlist_items(
                self.alpha_owner,
                alpha_list,
            )],
            ["NVDA"],
        )
        self.assertEqual(
            [item["ticker"] for item in self.store.list_watchlist_items(
                self.beta_owner,
                beta_list,
            )],
            ["MSFT"],
        )

    def test_portfolios_research_and_paper_accounts_are_isolated(self):
        portfolio = self.store.create_portfolio(
            self.alpha_owner,
            "Primary",
            portfolio_id="primary",
        )
        self.store.set_position(
            self.alpha_owner,
            portfolio,
            "NVDA",
            2,
            100,
        )
        self.store.create_research_task(
            self.alpha_owner,
            "CIO",
            "NVDA",
            "Review the thesis.",
            payload={"source": "daily"},
            task_id="task-alpha",
        )
        self.store.create_paper_account(
            self.alpha_owner,
            "Alpha Paper",
            100000,
            account_id="paper-alpha",
        )

        self.assertEqual(
            self.store.list_positions(self.alpha_owner, portfolio)[0]["ticker"],
            "NVDA",
        )
        self.assertEqual(self.store.list_positions(self.beta_owner, portfolio), [])
        self.assertEqual(len(self.store.list_research_tasks(self.alpha_owner)), 1)
        self.assertEqual(self.store.list_research_tasks(self.beta_owner), [])
        self.assertEqual(len(self.store.list_paper_accounts(self.alpha_owner)), 1)
        self.assertEqual(self.store.list_paper_accounts(self.beta_owner), [])

    def test_invalid_values_fail_at_database_boundary(self):
        portfolio = self.store.create_portfolio(
            self.alpha_owner,
            "Primary",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.set_position(
                self.alpha_owner,
                portfolio,
                "NVDA",
                0,
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.create_research_task(
                self.alpha_owner,
                "CIO",
                "NVDA",
                "Review.",
                priority="urgent",
            )
        with self.assertRaisesRegex(ValueError, "relative"):
            self.store.create_report(
                self.alpha_owner,
                "Brief",
                "2026-06-11T12:00:00+00:00",
                markdown_path="../secret.md",
            )

    def test_member_manager_cannot_invite_into_another_tenant(self):
        outsider = self._account(
            "beta-workspace",
            "beta-analyst",
            "google-beta-analyst",
            "analyst@example.com",
            "analyst",
        )
        with self.assertRaisesRegex(PermissionError, "Cross-tenant"):
            self.store.add_membership(self.alpha_owner, outsider)


if __name__ == "__main__":
    unittest.main()
