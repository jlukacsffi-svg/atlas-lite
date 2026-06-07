#!/usr/bin/env python3
"""Create, inspect, restore, or test a private Atlas backup."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from app.backup_restore import AtlasBackupManager
from app.paths import DATA_ROOT, project_path


def _default_backup_path():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return project_path("backups", f"atlas_backup_{stamp}.zip")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--output", type=Path, default=None)
    create_parser.add_argument("--data-root", type=Path, default=DATA_ROOT)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("backup", type=Path)

    drill_parser = subparsers.add_parser("drill")
    drill_parser.add_argument("backup", type=Path)

    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("backup", type=Path)
    restore_parser.add_argument("--target", type=Path, required=True)
    restore_parser.add_argument("--apply", action="store_true")
    restore_parser.add_argument("--replace-existing", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "create":
        output = args.output or _default_backup_path()
        manifest = AtlasBackupManager(args.data_root).create(output)
        print(
            f"[backup] Created {output.resolve()} "
            f"with {len(manifest['files'])} files"
        )
        return 0

    manager = AtlasBackupManager()
    if args.command == "inspect":
        print(json.dumps(manager.inspect(args.backup), indent=2))
        return 0
    if args.command == "drill":
        result = manager.drill(args.backup)
        print(
            f"[backup] Restore drill passed: "
            f"{result['restored_file_count']} files, "
            f"{result['total_bytes']} bytes"
        )
        return 0
    if args.command == "restore":
        if not args.apply:
            print("[plan] Backup validated; no files were restored.")
            print(
                json.dumps(manager.inspect(args.backup), indent=2)
            )
            print("Re-run with --apply to write the restored files.")
            return 0
        restored = manager.restore(
            args.backup,
            args.target,
            replace_existing=args.replace_existing,
        )
        print(f"[backup] Restored {len(restored)} files to {args.target.resolve()}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
