#!/usr/bin/env python3
"""Create, inspect, drill, or restore the Atlas tenant database backup."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from app.tenant_backup import TenantBackupManager


def _default_output():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path("backups") / f"atlas_tenant_{stamp}.zip"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("tenant_data/preview.sqlite3"),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("--output", type=Path, default=None)

    inspect = commands.add_parser("inspect")
    inspect.add_argument("backup", type=Path)

    drill = commands.add_parser("drill")
    drill.add_argument("backup", type=Path, nargs="?")
    drill.add_argument("--output", type=Path, default=None)

    restore = commands.add_parser("restore")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--target", type=Path, required=True)
    restore.add_argument("--approve-overwrite", action="store_true")

    args = parser.parse_args(argv)
    manager = TenantBackupManager(args.database)

    if args.command == "create":
        output = args.output or _default_output()
        manifest = manager.create(output)
        print(
            f"[tenant-backup] Created {output.resolve()} "
            f"(schema {manifest['database']['schema_version']})"
        )
        print(
            "[tenant-backup] Archive is not encrypted; keep it only in "
            "private encrypted-at-rest storage."
        )
        return 0
    if args.command == "inspect":
        print(json.dumps(manager.inspect(args.backup), indent=2))
        return 0
    if args.command == "drill":
        output = args.output
        if args.backup is None:
            output = output or _default_output()
        result = manager.drill(args.backup, output)
        print(
            f"[tenant-backup] Restore drill passed "
            f"(schema {result['schema_version']})"
        )
        return 0
    if args.command == "restore":
        restored = manager.restore(
            args.backup,
            args.target,
            replace_existing=args.approve_overwrite,
        )
        print(f"[tenant-backup] Restored validated database to {restored}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
