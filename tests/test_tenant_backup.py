import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import zipfile

from app.tenant_accounts import TenantAccount
from app.tenant_backup import (
    DATABASE_NAME,
    MANIFEST_NAME,
    TenantBackupManager,
)
from app.tenant_store import SCHEMA_VERSION, TenantStore


class TenantBackupManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.database = self.root / "tenant.sqlite3"
        self.backup = self.root / "tenant.zip"
        self.store = TenantStore(
            self.database,
            clock=lambda: "2026-06-11T12:00:00+00:00",
        )
        self.store.migrate()
        self.owner = TenantAccount(
            tenant_id="alpha",
            user_id="owner",
            provider="google",
            subject="alpha-owner",
            email="owner@example.com",
            role="owner",
        )
        self.store.provision_account("Alpha", self.owner)
        watchlist = self.store.create_watchlist(
            self.owner,
            "Core",
            watchlist_id="core",
        )
        self.store.add_watchlist_item(self.owner, watchlist, "NVDA")
        self.manager = TenantBackupManager(self.database)

    def test_create_inspect_and_restore_drill(self):
        manifest = self.manager.create(self.backup)
        self.assertEqual(
            manifest["database"]["schema_version"],
            SCHEMA_VERSION,
        )
        inspected = self.manager.inspect(self.backup)
        self.assertEqual(inspected["status"], "valid")
        self.assertEqual(inspected["table_counts"]["tenants"], 1)
        self.assertEqual(inspected["table_counts"]["watchlist_items"], 1)

        drilled = self.manager.drill(self.backup)
        self.assertEqual(drilled["status"], "passed")

        target = self.root / "restored.sqlite3"
        self.manager.restore(self.backup, target)
        restored = TenantStore(target)
        resolved = restored.resolve(
            self.owner.provider,
            self.owner.subject,
            self.owner.email,
        )
        self.assertEqual(
            restored.list_watchlist_items(resolved, "core")[0]["ticker"],
            "NVDA",
        )

    def test_restore_refuses_existing_or_live_target(self):
        existing = self.root / "existing.sqlite3"
        existing.write_bytes(b"do not replace")
        self.manager.create(self.backup)
        with self.assertRaises(FileExistsError):
            self.manager.restore(self.backup, existing)
        self.assertEqual(existing.read_bytes(), b"do not replace")
        with self.assertRaisesRegex(ValueError, "maintenance window"):
            self.manager.restore(
                self.backup,
                self.database,
                replace_existing=True,
            )

    def test_checksum_tampering_is_rejected(self):
        self.manager.create(self.backup)
        self._rewrite_archive(
            database_body=b"not a sqlite database",
        )
        with self.assertRaisesRegex(ValueError, "size mismatch|checksum mismatch"):
            self.manager.inspect(self.backup)

    def test_manifest_schema_tampering_is_rejected(self):
        self.manager.create(self.backup)
        with zipfile.ZipFile(self.backup, "r") as archive:
            manifest = json.loads(archive.read(MANIFEST_NAME))
        manifest["database"]["schema_version"] = SCHEMA_VERSION + 1
        self._rewrite_archive(manifest=manifest)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            self.manager.inspect(self.backup)

    def test_unexpected_and_unsafe_entries_are_rejected(self):
        self.manager.create(self.backup)
        with zipfile.ZipFile(self.backup, "a") as archive:
            archive.writestr("extra.txt", "unexpected")
        with self.assertRaisesRegex(ValueError, "unexpected entries"):
            self.manager.inspect(self.backup)

        self.manager.create(self.backup)
        with zipfile.ZipFile(self.backup, "a") as archive:
            archive.writestr("../tenant.sqlite3", "unsafe")
        with self.assertRaisesRegex(ValueError, "unexpected entries|unsafe path"):
            self.manager.inspect(self.backup)

    def test_logical_inventory_tampering_is_rejected(self):
        self.manager.create(self.backup)
        with zipfile.ZipFile(self.backup, "r") as archive:
            manifest = json.loads(archive.read(MANIFEST_NAME))
        manifest["database"]["table_counts"]["tenants"] = 99
        self._rewrite_archive(manifest=manifest)
        with self.assertRaisesRegex(ValueError, "inventory mismatch"):
            self.manager.inspect(self.backup)

    def test_corrupt_sqlite_with_matching_checksum_is_rejected(self):
        self.manager.create(self.backup)
        corrupt = b"SQLite format 3\x00" + (b"\x00" * 4096)
        with zipfile.ZipFile(self.backup, "r") as archive:
            manifest = json.loads(archive.read(MANIFEST_NAME))
        import hashlib

        manifest["database"]["size"] = len(corrupt)
        manifest["database"]["sha256"] = hashlib.sha256(corrupt).hexdigest()
        self._rewrite_archive(
            manifest=manifest,
            database_body=corrupt,
        )
        with self.assertRaises((ValueError, sqlite3.DatabaseError)):
            self.manager.inspect(self.backup)

    def _rewrite_archive(self, manifest=None, database_body=None):
        with zipfile.ZipFile(self.backup, "r") as archive:
            current_manifest = json.loads(archive.read(MANIFEST_NAME))
            current_database = archive.read(DATABASE_NAME)
        with zipfile.ZipFile(
            self.backup,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.writestr(
                MANIFEST_NAME,
                json.dumps(manifest or current_manifest),
            )
            archive.writestr(
                DATABASE_NAME,
                database_body or current_database,
            )


if __name__ == "__main__":
    unittest.main()
