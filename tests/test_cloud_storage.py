import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.cloud_storage import CloudArtifactSync, CloudStorageSettings


class NotFound(Exception):
    code = 404


class FakeBlob:
    def __init__(self, name, objects):
        self.name = name
        self.objects = objects
        self.generation = None

    def reload(self):
        if self.name not in self.objects:
            raise NotFound()
        self.generation = self.objects[self.name]["generation"]

    def upload_from_filename(
        self,
        filename,
        content_type,
        if_generation_match,
        checksum,
    ):
        self._upload(
            Path(filename).read_bytes(),
            content_type,
            if_generation_match,
            checksum,
        )

    def upload_from_string(
        self,
        value,
        content_type,
        if_generation_match,
        checksum,
    ):
        self._upload(
            value.encode("utf-8"),
            content_type,
            if_generation_match,
            checksum,
        )

    def download_as_bytes(self, checksum):
        self._assert_checksum(checksum)
        if self.name not in self.objects:
            raise NotFound()
        return self.objects[self.name]["body"]

    def _upload(self, body, content_type, expected_generation, checksum):
        self._assert_checksum(checksum)
        current = self.objects.get(self.name)
        actual_generation = current["generation"] if current else 0
        if expected_generation != actual_generation:
            raise ValueError("generation mismatch")
        self.objects[self.name] = {
            "body": body,
            "content_type": content_type,
            "generation": actual_generation + 1,
        }
        self.generation = actual_generation + 1

    def _assert_checksum(self, checksum):
        if checksum != "auto":
            raise AssertionError("checksum verification must be enabled")


class FakeBucket:
    def __init__(self, objects):
        self.objects = objects

    def blob(self, name):
        return FakeBlob(name, self.objects)


class FakeStorageClient:
    def __init__(self):
        self.objects = {}

    def bucket(self, name):
        self.bucket_name = name
        return FakeBucket(self.objects)


class CloudArtifactSyncTests(unittest.TestCase):
    def test_push_then_pull_round_trip_with_manifest_and_checksums(self):
        client = FakeStorageClient()
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
            source = Path(source_dir)
            (source / "research_archive").mkdir()
            snapshot = source / "research_archive" / "snapshot_20260607_010000.json"
            snapshot.write_text('{"generated_at":"2026-06-07T01:00:00"}', encoding="utf-8")
            (source / "paper_trading").mkdir()
            ledger = source / "paper_trading" / "ledger.jsonl"
            ledger.write_text('{"event":"account_initialized"}\n', encoding="utf-8")

            pushed = CloudArtifactSync(
                CloudStorageSettings(
                    bucket="atlas-private",
                    prefix="owner-v1",
                    data_root=source,
                ),
                storage_client=client,
            ).push()

            pulled = CloudArtifactSync(
                CloudStorageSettings(
                    bucket="atlas-private",
                    prefix="owner-v1",
                    data_root=Path(target_dir),
                ),
                storage_client=client,
            ).pull()

            self.assertEqual(len(pushed["files"]), 2)
            self.assertEqual(len(pulled), 2)
            self.assertEqual(
                (Path(target_dir) / "research_archive" / snapshot.name).read_text(
                    encoding="utf-8"
                ),
                snapshot.read_text(encoding="utf-8"),
            )
            manifest = json.loads(
                client.objects["owner-v1/manifest.json"]["body"].decode("utf-8")
            )
            self.assertEqual(
                manifest["files"][0]["sha256"],
                hashlib.sha256(
                    source.joinpath(manifest["files"][0]["path"]).read_bytes()
                ).hexdigest(),
            )

    def test_pull_rejects_path_traversal_before_writing(self):
        client = FakeStorageClient()
        manifest = {
            "manifest_version": "1.0",
            "generated_at": "2026-06-07T01:00:00+00:00",
            "files": [
                {
                    "path": "../outside.json",
                    "size": 2,
                    "sha256": hashlib.sha256(b"{}").hexdigest(),
                    "object": "owner-v1/artifacts/../outside.json",
                }
            ],
        }
        client.objects["owner-v1/manifest.json"] = {
            "body": json.dumps(manifest).encode("utf-8"),
            "content_type": "application/json",
            "generation": 1,
        }
        with tempfile.TemporaryDirectory() as target_dir:
            sync = CloudArtifactSync(
                CloudStorageSettings(
                    bucket="atlas-private",
                    data_root=Path(target_dir),
                ),
                storage_client=client,
            )
            with self.assertRaisesRegex(ValueError, "Unsafe Atlas cloud path"):
                sync.pull()

    def test_pull_rejects_checksum_mismatch_without_replacing_local_file(self):
        client = FakeStorageClient()
        relative = "paper_trading/account.json"
        object_name = f"owner-v1/artifacts/{relative}"
        manifest = {
            "manifest_version": "1.0",
            "generated_at": "2026-06-07T01:00:00+00:00",
            "files": [
                {
                    "path": relative,
                    "size": 2,
                    "sha256": "0" * 64,
                    "object": object_name,
                }
            ],
        }
        client.objects["owner-v1/manifest.json"] = {
            "body": json.dumps(manifest).encode("utf-8"),
            "content_type": "application/json",
            "generation": 1,
        }
        client.objects[object_name] = {
            "body": b"{}",
            "content_type": "application/json",
            "generation": 1,
        }
        with tempfile.TemporaryDirectory() as target_dir:
            target = Path(target_dir) / relative
            target.parent.mkdir()
            target.write_text("preserve", encoding="utf-8")
            sync = CloudArtifactSync(
                CloudStorageSettings(
                    bucket="atlas-private",
                    data_root=Path(target_dir),
                ),
                storage_client=client,
            )
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                sync.pull()
            self.assertEqual(target.read_text(encoding="utf-8"), "preserve")

    def test_push_ignores_non_allowlisted_files(self):
        client = FakeStorageClient()
        with tempfile.TemporaryDirectory() as source_dir:
            source = Path(source_dir)
            (source / ".env").write_text("SECRET=value", encoding="utf-8")
            (source / "research_archive").mkdir()
            (source / "research_archive" / "archive_index.json").write_text(
                "{}",
                encoding="utf-8",
            )
            manifest = CloudArtifactSync(
                CloudStorageSettings(
                    bucket="atlas-private",
                    data_root=source,
                ),
                storage_client=client,
            ).push()
        self.assertEqual(
            [item["path"] for item in manifest["files"]],
            ["research_archive/archive_index.json"],
        )
        self.assertNotIn("owner-v1/artifacts/.env", client.objects)


if __name__ == "__main__":
    unittest.main()
