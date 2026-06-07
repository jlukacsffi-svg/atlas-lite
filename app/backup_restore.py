"""Create and verify private Atlas backup archives."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

from app.cloud_storage import (
    ALLOWED_PATTERNS,
    MAX_BUNDLE_BYTES,
    MAX_FILE_BYTES,
)
from app.paths import DATA_ROOT


BACKUP_VERSION = "1.0"
MANIFEST_NAME = "atlas_backup_manifest.json"


class AtlasBackupManager:
    """Package allowlisted private runtime data and restore it safely."""

    def __init__(self, data_root=DATA_ROOT):
        self.data_root = Path(data_root).resolve()

    def create(self, destination):
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        files = self._local_files()
        entries = []
        total_bytes = 0

        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        try:
            with zipfile.ZipFile(
                temporary_path,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
            ) as archive:
                for path in files:
                    relative = path.relative_to(self.data_root).as_posix()
                    size = path.stat().st_size
                    self._validate_file_size(relative, size)
                    total_bytes += size
                    self._validate_bundle_size(total_bytes)
                    body = path.read_bytes()
                    entries.append(
                        {
                            "path": relative,
                            "size": size,
                            "sha256": hashlib.sha256(body).hexdigest(),
                        }
                    )
                    archive.writestr(f"artifacts/{relative}", body)

                manifest = {
                    "backup_version": BACKUP_VERSION,
                    "generated_at": datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                    "files": entries,
                }
                archive.writestr(
                    MANIFEST_NAME,
                    json.dumps(manifest, indent=2, sort_keys=True),
                )
            temporary_path.replace(destination)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        return manifest

    def inspect(self, backup_path):
        backup_path = Path(backup_path).resolve()
        with zipfile.ZipFile(backup_path, "r") as archive:
            manifest = self._read_manifest(archive)
            validated = self._validate_archive(archive, manifest)
        return {
            "backup_path": str(backup_path),
            "generated_at": manifest["generated_at"],
            "file_count": len(validated),
            "total_bytes": sum(item["size"] for item in validated),
            "files": [item["path"] for item in validated],
        }

    def restore(self, backup_path, target_root, replace_existing=False):
        backup_path = Path(backup_path).resolve()
        target_root = Path(target_root).resolve()
        with zipfile.ZipFile(backup_path, "r") as archive:
            manifest = self._read_manifest(archive)
            entries = self._validate_archive(archive, manifest)
            payloads = {
                entry["path"]: archive.read(f"artifacts/{entry['path']}")
                for entry in entries
            }

        destinations = {}
        for relative, body in payloads.items():
            destination = target_root.joinpath(*PurePosixPath(relative).parts)
            if destination.exists() and not replace_existing:
                raise FileExistsError(
                    f"Restore target already exists: {destination}"
                )
            destinations[destination] = body

        written = []
        for destination, body in destinations.items():
            self._atomic_write(destination, body)
            written.append(destination)
        return written

    def drill(self, backup_path):
        backup_path = Path(backup_path).resolve()
        expected = self.inspect(backup_path)
        with tempfile.TemporaryDirectory(prefix="atlas-restore-drill-") as target:
            restored = self.restore(backup_path, target)
            restored_manager = AtlasBackupManager(target)
            restored_files = {
                path.relative_to(Path(target)).as_posix()
                for path in restored_manager._local_files()
            }
            if restored_files != set(expected["files"]):
                raise ValueError("Restore drill file inventory mismatch")
            return {
                **expected,
                "restored_file_count": len(restored),
                "status": "passed",
            }

    def _local_files(self):
        files = set()
        for pattern in ALLOWED_PATTERNS:
            for path in self.data_root.glob(pattern):
                if path.is_file() and not path.is_symlink():
                    files.add(path.resolve())
        return sorted(files)

    def _read_manifest(self, archive):
        try:
            raw = archive.read(MANIFEST_NAME)
        except KeyError as exc:
            raise ValueError("Atlas backup manifest is missing") from exc
        try:
            manifest = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Atlas backup manifest is invalid") from exc
        if manifest.get("backup_version") != BACKUP_VERSION:
            raise ValueError("Unsupported Atlas backup version")
        if not isinstance(manifest.get("generated_at"), str):
            raise ValueError("Atlas backup timestamp is invalid")
        if not isinstance(manifest.get("files"), list):
            raise ValueError("Atlas backup file list is invalid")
        return manifest

    def _validate_archive(self, archive, manifest):
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Atlas backup contains duplicate archive entries")

        expected_names = {MANIFEST_NAME}
        validated = []
        seen_paths = set()
        total_bytes = 0

        for entry in manifest["files"]:
            if not isinstance(entry, dict):
                raise ValueError("Atlas backup contains an invalid file entry")
            if not {"path", "size", "sha256"}.issubset(entry):
                raise ValueError("Atlas backup contains an incomplete file entry")
            relative = self._validate_relative_path(entry["path"])
            normalized = relative.as_posix()
            if normalized in seen_paths:
                raise ValueError(f"Duplicate Atlas backup path: {normalized}")
            if not self._is_allowed(normalized):
                raise ValueError(f"Disallowed Atlas backup path: {normalized}")

            size = int(entry["size"])
            self._validate_file_size(normalized, size)
            total_bytes += size
            self._validate_bundle_size(total_bytes)
            checksum = str(entry["sha256"])
            if len(checksum) != 64:
                raise ValueError(f"Invalid checksum for {normalized}")

            archive_name = f"artifacts/{normalized}"
            try:
                info = archive.getinfo(archive_name)
            except KeyError as exc:
                raise ValueError(
                    f"Atlas backup payload is missing: {normalized}"
                ) from exc
            if self._is_symlink(info):
                raise ValueError(f"Atlas backup contains a symlink: {normalized}")
            if info.file_size != size:
                raise ValueError(f"Size mismatch for {normalized}")
            body = archive.read(archive_name)
            if len(body) != size:
                raise ValueError(f"Size mismatch for {normalized}")
            if hashlib.sha256(body).hexdigest() != checksum:
                raise ValueError(f"Checksum mismatch for {normalized}")

            expected_names.add(archive_name)
            seen_paths.add(normalized)
            validated.append(
                {"path": normalized, "size": size, "sha256": checksum}
            )

        unexpected = set(names) - expected_names
        if unexpected:
            raise ValueError(
                "Atlas backup contains unexpected entries: "
                + ", ".join(sorted(unexpected))
            )
        return validated

    def _validate_relative_path(self, value):
        relative = PurePosixPath(str(value))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError(f"Unsafe Atlas backup path: {value}")
        return relative

    def _is_allowed(self, relative):
        path = PurePosixPath(relative)
        return any(path.match(pattern) for pattern in ALLOWED_PATTERNS)

    def _validate_file_size(self, relative, size):
        if size < 0 or size > MAX_FILE_BYTES:
            raise ValueError(f"Atlas backup file size is invalid: {relative}")

    def _validate_bundle_size(self, size):
        if size > MAX_BUNDLE_BYTES:
            raise ValueError("Atlas backup exceeds maximum bundle size")

    def _is_symlink(self, info):
        mode = info.external_attr >> 16
        return (mode & 0o170000) == 0o120000

    def _atomic_write(self, destination, body):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as temporary:
            temporary.write(body)
            temporary_path = Path(temporary.name)
        temporary_path.replace(destination)
