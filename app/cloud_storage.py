"""Checksum-verified synchronization for Atlas private cloud artifacts."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
import os
from pathlib import Path, PurePosixPath
import tempfile

from app.paths import DATA_ROOT


MANIFEST_VERSION = "1.0"
DEFAULT_PREFIX = "owner-v1"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_BUNDLE_BYTES = 100 * 1024 * 1024

ALLOWED_PATTERNS = (
    "research_archive/snapshot_*.json",
    "research_archive/archive_index.json",
    "research_archive/archive_index.md",
    "paper_trading/account.json",
    "paper_trading/ledger.jsonl",
    "paper_trading/performance.md",
    "research_tasks/*.json",
    "research_tasks/*.md",
    "reports/*.md",
    "reports/*.html",
    "portfolio_history/*.json",
    "data/portfolio.json",
)


@dataclass(frozen=True)
class CloudStorageSettings:
    bucket: str
    prefix: str = DEFAULT_PREFIX
    data_root: Path = Path(".")

    @classmethod
    def from_environment(cls):
        return cls(
            bucket=os.getenv("ATLAS_GCS_BUCKET", "").strip(),
            prefix=os.getenv("ATLAS_GCS_PREFIX", DEFAULT_PREFIX).strip().strip("/"),
            data_root=Path(os.getenv("ATLAS_DATA_ROOT", str(DATA_ROOT))).resolve(),
        )

    def validate(self):
        if not self.bucket:
            raise ValueError("ATLAS_GCS_BUCKET is required")
        if not self.prefix:
            raise ValueError("ATLAS_GCS_PREFIX cannot be empty")
        prefix = PurePosixPath(self.prefix)
        if prefix.is_absolute() or ".." in prefix.parts:
            raise ValueError("ATLAS_GCS_PREFIX must be a safe relative prefix")


class CloudArtifactSync:
    """Push and pull an allowlisted Atlas artifact bundle."""

    def __init__(self, settings, storage_client=None):
        settings.validate()
        self.settings = settings
        self.storage_client = storage_client or self._default_client()
        self.bucket = self.storage_client.bucket(settings.bucket)

    def push(self):
        files = self._local_files()
        entries = []
        total_bytes = 0
        for path in files:
            relative = path.relative_to(self.settings.data_root).as_posix()
            size = path.stat().st_size
            self._validate_size(relative, size)
            total_bytes += size
            if total_bytes > MAX_BUNDLE_BYTES:
                raise ValueError("Atlas artifact bundle exceeds maximum size")
            body = path.read_bytes()
            digest = hashlib.sha256(body).hexdigest()
            object_name = self._object_name(relative)
            blob = self.bucket.blob(object_name)
            generation = self._generation(blob)
            blob.upload_from_filename(
                str(path),
                content_type=self._content_type(path),
                if_generation_match=generation,
                checksum="auto",
            )
            entries.append(
                {
                    "path": relative,
                    "size": size,
                    "sha256": digest,
                    "object": object_name,
                }
            )

        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": entries,
        }
        manifest_blob = self.bucket.blob(self._manifest_object())
        generation = self._generation(manifest_blob)
        manifest_blob.upload_from_string(
            json.dumps(manifest, indent=2, sort_keys=True),
            content_type="application/json",
            if_generation_match=generation,
            checksum="auto",
        )
        return manifest

    def pull(self):
        manifest_blob = self.bucket.blob(self._manifest_object())
        manifest = json.loads(manifest_blob.download_as_bytes(checksum="auto"))
        self._validate_manifest(manifest)

        downloaded = []
        total_bytes = 0
        for entry in manifest["files"]:
            relative = self._validate_relative_path(entry["path"])
            size = int(entry["size"])
            self._validate_size(relative.as_posix(), size)
            total_bytes += size
            if total_bytes > MAX_BUNDLE_BYTES:
                raise ValueError("Atlas artifact bundle exceeds maximum size")
            expected_object = self._object_name(relative.as_posix())
            if entry.get("object") != expected_object:
                raise ValueError(f"Unexpected object mapping for {relative}")
            body = self.bucket.blob(expected_object).download_as_bytes(checksum="auto")
            if len(body) != size:
                raise ValueError(f"Size mismatch for {relative}")
            digest = hashlib.sha256(body).hexdigest()
            if digest != entry["sha256"]:
                raise ValueError(f"Checksum mismatch for {relative}")
            destination = self.settings.data_root.joinpath(*relative.parts)
            self._atomic_write(destination, body)
            downloaded.append(destination)
        return downloaded

    def _local_files(self):
        files = set()
        root = self.settings.data_root
        for pattern in ALLOWED_PATTERNS:
            for path in root.glob(pattern):
                if path.is_file() and not path.is_symlink():
                    files.add(path.resolve())
        return sorted(files)

    def _validate_manifest(self, manifest):
        if manifest.get("manifest_version") != MANIFEST_VERSION:
            raise ValueError("Unsupported Atlas cloud manifest version")
        if not isinstance(manifest.get("files"), list):
            raise ValueError("Atlas cloud manifest files must be a list")
        seen = set()
        for entry in manifest["files"]:
            if not isinstance(entry, dict):
                raise ValueError("Invalid Atlas cloud manifest entry")
            required = {"path", "size", "sha256", "object"}
            if not required.issubset(entry):
                raise ValueError("Incomplete Atlas cloud manifest entry")
            relative = self._validate_relative_path(entry["path"])
            normalized = relative.as_posix()
            if normalized in seen:
                raise ValueError(f"Duplicate Atlas cloud path: {normalized}")
            if not self._is_allowed(normalized):
                raise ValueError(f"Disallowed Atlas cloud path: {normalized}")
            if len(str(entry["sha256"])) != 64:
                raise ValueError(f"Invalid checksum for {normalized}")
            seen.add(normalized)

    def _validate_relative_path(self, value):
        relative = PurePosixPath(str(value))
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            raise ValueError(f"Unsafe Atlas cloud path: {value}")
        return relative

    def _is_allowed(self, relative):
        path = PurePosixPath(relative)
        return any(path.match(pattern) for pattern in ALLOWED_PATTERNS)

    def _validate_size(self, relative, size):
        if size < 0 or size > MAX_FILE_BYTES:
            raise ValueError(f"Atlas cloud file size is invalid: {relative}")

    def _object_name(self, relative):
        return f"{self.settings.prefix}/artifacts/{relative}"

    def _manifest_object(self):
        return f"{self.settings.prefix}/manifest.json"

    def _generation(self, blob):
        try:
            blob.reload()
        except Exception as exc:
            if self._is_not_found(exc):
                return 0
            raise
        return int(blob.generation)

    def _is_not_found(self, exc):
        return exc.__class__.__name__ == "NotFound" or getattr(exc, "code", None) == 404

    def _content_type(self, path):
        return mimetypes.guess_type(path.name)[0] or "application/octet-stream"

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

    def _default_client(self):
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError(
                "Cloud storage requires requirements-web.txt"
            ) from exc
        return storage.Client()


def sync_from_environment(direction):
    sync = CloudArtifactSync(CloudStorageSettings.from_environment())
    if direction == "pull":
        return sync.pull()
    if direction == "push":
        return sync.push()
    raise ValueError("direction must be pull or push")
