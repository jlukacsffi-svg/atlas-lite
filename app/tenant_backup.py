"""Integrity-checked backup and recovery for the Atlas tenant database."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from app.tenant_store import SCHEMA_VERSION


BACKUP_VERSION = "1.0"
DATABASE_NAME = "tenant.sqlite3"
MANIFEST_NAME = "tenant_backup_manifest.json"
MAX_DATABASE_BYTES = 64 * 1024 * 1024


class TenantBackupManager:
    """Create a consistent SQLite backup and validate it before restoration."""

    def __init__(self, database_path):
        self.database_path = Path(database_path).resolve()

    def create(self, destination):
        if not self.database_path.is_file():
            raise FileNotFoundError(
                f"Tenant database does not exist: {self.database_path}"
            )
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix="atlas-tenant-backup-"
        ) as temporary:
            snapshot = Path(temporary) / DATABASE_NAME
            self._sqlite_backup(self.database_path, snapshot)
            database_body = snapshot.read_bytes()
            self._validate_size(len(database_body))
            details = self._database_details(snapshot)
            manifest = {
                "backup_version": BACKUP_VERSION,
                "created_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "database": {
                    "name": DATABASE_NAME,
                    "size": len(database_body),
                    "sha256": hashlib.sha256(database_body).hexdigest(),
                    "schema_version": details["schema_version"],
                    "table_counts": details["table_counts"],
                },
            }
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_archive:
                temporary_archive_path = Path(temporary_archive.name)
            try:
                with zipfile.ZipFile(
                    temporary_archive_path,
                    "w",
                    compression=zipfile.ZIP_DEFLATED,
                    compresslevel=6,
                ) as archive:
                    archive.writestr(DATABASE_NAME, database_body)
                    archive.writestr(
                        MANIFEST_NAME,
                        json.dumps(manifest, indent=2, sort_keys=True),
                    )
                temporary_archive_path.replace(destination)
            except Exception:
                temporary_archive_path.unlink(missing_ok=True)
                raise
        return manifest

    def inspect(self, backup_path):
        with self._validated_database(backup_path) as validated:
            return {
                "backup_path": str(Path(backup_path).resolve()),
                "created_at": validated["manifest"]["created_at"],
                **validated["details"],
                "status": "valid",
            }

    def restore(self, backup_path, target_path, replace_existing=False):
        target = Path(target_path).resolve()
        if target.exists() and not replace_existing:
            raise FileExistsError(f"Restore target already exists: {target}")
        if target == self.database_path:
            raise ValueError(
                "Restore to a separate path first; replace the live database "
                "only during a controlled maintenance window"
            )

        with self._validated_database(backup_path) as validated:
            body = validated["database_path"].read_bytes()
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(body)
                temporary_path = Path(temporary.name)
            try:
                self._database_details(temporary_path)
                temporary_path.replace(target)
            except Exception:
                temporary_path.unlink(missing_ok=True)
                raise
        return target

    def drill(self, backup_path=None, output_path=None):
        created = False
        if backup_path is None:
            if output_path is None:
                raise ValueError("A drill requires a backup or output path")
            backup_path = Path(output_path)
            self.create(backup_path)
            created = True

        expected = self.inspect(backup_path)
        with tempfile.TemporaryDirectory(
            prefix="atlas-tenant-restore-drill-"
        ) as temporary:
            restored = Path(temporary) / "restored.sqlite3"
            self.restore(backup_path, restored)
            actual = self._database_details(restored)
            if actual["schema_version"] != expected["schema_version"]:
                raise ValueError("Restore drill schema version mismatch")
            if actual["table_counts"] != expected["table_counts"]:
                raise ValueError("Restore drill table inventory mismatch")
        return {
            **expected,
            "created_for_drill": created,
            "status": "passed",
        }

    def _validated_database(self, backup_path):
        return _ValidatedTenantBackup(self, backup_path)

    @staticmethod
    def _sqlite_backup(source_path, destination_path):
        source_uri = f"{Path(source_path).resolve().as_uri()}?mode=ro"
        source = sqlite3.connect(source_uri, uri=True)
        destination = sqlite3.connect(destination_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

    def _read_archive(self, backup_path, target):
        backup_path = Path(backup_path).resolve()
        with zipfile.ZipFile(backup_path, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("Tenant backup contains duplicate entries")
            expected = {MANIFEST_NAME, DATABASE_NAME}
            if set(names) != expected:
                raise ValueError("Tenant backup contains unexpected entries")
            for info in archive.infolist():
                if info.filename.startswith(("/", "\\")) or ".." in Path(
                    info.filename
                ).parts:
                    raise ValueError("Tenant backup contains an unsafe path")
                if self._is_symlink(info):
                    raise ValueError("Tenant backup contains a symlink")
            try:
                manifest = json.loads(archive.read(MANIFEST_NAME))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("Tenant backup manifest is invalid") from exc
            self._validate_manifest(manifest)
            info = archive.getinfo(DATABASE_NAME)
            self._validate_size(info.file_size)
            body = archive.read(DATABASE_NAME)
            database = manifest["database"]
            if len(body) != database["size"]:
                raise ValueError("Tenant backup database size mismatch")
            if hashlib.sha256(body).hexdigest() != database["sha256"]:
                raise ValueError("Tenant backup database checksum mismatch")
            target.write_bytes(body)
        details = self._database_details(target)
        if details["schema_version"] != manifest["database"]["schema_version"]:
            raise ValueError("Tenant backup schema version mismatch")
        if details["table_counts"] != manifest["database"]["table_counts"]:
            raise ValueError("Tenant backup table inventory mismatch")
        return manifest, details

    @staticmethod
    def _validate_manifest(manifest):
        if not isinstance(manifest, dict):
            raise ValueError("Tenant backup manifest is invalid")
        if manifest.get("backup_version") != BACKUP_VERSION:
            raise ValueError("Unsupported tenant backup version")
        if not isinstance(manifest.get("created_at"), str):
            raise ValueError("Tenant backup timestamp is invalid")
        database = manifest.get("database")
        if not isinstance(database, dict):
            raise ValueError("Tenant backup database metadata is invalid")
        if database.get("name") != DATABASE_NAME:
            raise ValueError("Tenant backup database name is invalid")
        if not isinstance(database.get("size"), int):
            raise ValueError("Tenant backup database size is invalid")
        checksum = database.get("sha256")
        if not isinstance(checksum, str) or len(checksum) != 64:
            raise ValueError("Tenant backup checksum is invalid")
        if database.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Tenant backup schema version is unsupported")
        if not isinstance(database.get("table_counts"), dict):
            raise ValueError("Tenant backup table inventory is invalid")

    @staticmethod
    def _database_details(database_path):
        uri = f"{Path(database_path).resolve().as_uri()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise ValueError("Tenant database integrity check failed")
            if connection.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Tenant database foreign key check failed")
            try:
                schema = connection.execute(
                    "SELECT MAX(version) FROM schema_migrations"
                ).fetchone()
            except sqlite3.DatabaseError as exc:
                raise ValueError("Tenant database schema is unavailable") from exc
            schema_version = int((schema or [0])[0] or 0)
            if schema_version != SCHEMA_VERSION:
                raise ValueError("Tenant database schema version is unsupported")
            table_names = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                )
            ]
            table_counts = {
                name: int(
                    connection.execute(
                        'SELECT COUNT(*) FROM "'
                        + name.replace('"', '""')
                        + '"'
                    ).fetchone()[0]
                )
                for name in table_names
            }
        finally:
            connection.close()
        return {
            "schema_version": schema_version,
            "table_counts": table_counts,
        }

    @staticmethod
    def _validate_size(size):
        if size <= 0 or size > MAX_DATABASE_BYTES:
            raise ValueError("Tenant backup database size is invalid")

    @staticmethod
    def _is_symlink(info):
        mode = info.external_attr >> 16
        return (mode & 0o170000) == 0o120000


class _ValidatedTenantBackup:
    def __init__(self, manager, backup_path):
        self.manager = manager
        self.backup_path = backup_path
        self.temporary = None
        self.value = None

    def __enter__(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="atlas-tenant-validate-"
        )
        database_path = Path(self.temporary.name) / DATABASE_NAME
        try:
            manifest, details = self.manager._read_archive(
                self.backup_path,
                database_path,
            )
        except Exception:
            self.temporary.cleanup()
            raise
        self.value = {
            "manifest": manifest,
            "details": details,
            "database_path": database_path,
        }
        return self.value

    def __exit__(self, exc_type, exc_value, traceback):
        self.temporary.cleanup()
