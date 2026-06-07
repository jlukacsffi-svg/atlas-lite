import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import zipfile

from app.backup_restore import (
    AtlasBackupManager,
    BACKUP_VERSION,
    MANIFEST_NAME,
)


class AtlasBackupManagerTests(unittest.TestCase):
    def _seed_private_data(self, root):
        root = Path(root)
        (root / "research_archive").mkdir(parents=True)
        (root / "research_archive" / "archive_index.json").write_text(
            '{"runs": 2}',
            encoding="utf-8",
        )
        (root / "paper_trading").mkdir()
        (root / "paper_trading" / "account.json").write_text(
            '{"cash": 100000}',
            encoding="utf-8",
        )
        (root / ".env").write_text("SECRET=never", encoding="utf-8")

    def test_create_inspect_and_restore_drill_round_trip(self):
        with tempfile.TemporaryDirectory() as source_dir:
            self._seed_private_data(source_dir)
            backup = Path(source_dir) / "backups" / "atlas.zip"
            manager = AtlasBackupManager(source_dir)

            manifest = manager.create(backup)
            inspection = manager.inspect(backup)
            drill = manager.drill(backup)

            self.assertEqual(len(manifest["files"]), 2)
            self.assertEqual(inspection["file_count"], 2)
            self.assertEqual(drill["status"], "passed")
            self.assertEqual(drill["restored_file_count"], 2)
            self.assertNotIn(".env", inspection["files"])

    def test_restore_refuses_to_overwrite_without_explicit_permission(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            self._seed_private_data(source_dir)
            backup = Path(source_dir) / "atlas.zip"
            manager = AtlasBackupManager(source_dir)
            manager.create(backup)
            target = Path(target_dir) / "paper_trading" / "account.json"
            target.parent.mkdir()
            target.write_text("preserve", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "already exists"):
                manager.restore(backup, target_dir)
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve")

    def test_tampered_payload_is_rejected_before_any_restore(self):
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            self._seed_private_data(source_dir)
            original = Path(source_dir) / "original.zip"
            tampered = Path(source_dir) / "tampered.zip"
            manager = AtlasBackupManager(source_dir)
            manager.create(original)

            with zipfile.ZipFile(original, "r") as source, zipfile.ZipFile(
                tampered, "w"
            ) as target:
                for name in source.namelist():
                    body = source.read(name)
                    if name == "artifacts/paper_trading/account.json":
                        body = b'{"cash": 0}'
                    target.writestr(name, body)

            with self.assertRaisesRegex(ValueError, "mismatch"):
                manager.restore(tampered, target_dir)
            self.assertFalse(any(Path(target_dir).rglob("*")))

    def test_path_traversal_and_unexpected_entries_are_rejected(self):
        with tempfile.TemporaryDirectory() as source_dir:
            backup = Path(source_dir) / "unsafe.zip"
            body = b"{}"
            manifest = {
                "backup_version": BACKUP_VERSION,
                "generated_at": "2026-06-07T12:00:00+00:00",
                "files": [
                    {
                        "path": "../outside.json",
                        "size": len(body),
                        "sha256": hashlib.sha256(body).hexdigest(),
                    }
                ],
            }
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr(MANIFEST_NAME, json.dumps(manifest))
                archive.writestr("artifacts/../outside.json", body)

            with self.assertRaisesRegex(ValueError, "Unsafe Atlas backup path"):
                AtlasBackupManager(source_dir).inspect(backup)

    def test_manifest_must_account_for_every_archive_entry(self):
        with tempfile.TemporaryDirectory() as source_dir:
            backup = Path(source_dir) / "unexpected.zip"
            manifest = {
                "backup_version": BACKUP_VERSION,
                "generated_at": "2026-06-07T12:00:00+00:00",
                "files": [],
            }
            with zipfile.ZipFile(backup, "w") as archive:
                archive.writestr(MANIFEST_NAME, json.dumps(manifest))
                archive.writestr("credentials.txt", "secret")

            with self.assertRaisesRegex(ValueError, "unexpected entries"):
                AtlasBackupManager(source_dir).inspect(backup)


if __name__ == "__main__":
    unittest.main()
