#!/usr/bin/env python3
"""Operate local Atlas tenant privacy export and deletion workflows."""

import argparse
import json
from pathlib import Path
import tempfile
import sys

from app.tenant_store import TenantStore


def _write_private_json(destination, payload):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"Privacy export already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        mode="w",
        encoding="utf-8",
        delete=False,
    ) as temporary:
        json.dump(payload, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(destination)
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("tenant_data/preview.sqlite3"),
    )
    parser.add_argument("--provider", default="google")
    parser.add_argument("--subject", default="local-preview-owner")
    parser.add_argument("--email", default="preview-owner@atlas.local")
    commands = parser.add_subparsers(dest="command", required=True)

    export = commands.add_parser("export")
    export.add_argument("--output", type=Path, required=True)

    commands.add_parser("list")
    commands.add_parser("request-deletion")

    cancel = commands.add_parser("cancel-deletion")
    cancel.add_argument("request_id")

    complete = commands.add_parser("complete-deletion")
    complete.add_argument("request_id")
    complete.add_argument("--confirm", required=True)

    args = parser.parse_args(argv)
    store = TenantStore(args.database)
    store.migrate()
    actor = store.resolve(args.provider, args.subject, args.email)

    if args.command == "export":
        payload = store.export_tenant_data(actor)
        destination = _write_private_json(args.output, payload)
        print(f"[privacy] Tenant export written to {destination}")
        print(
            "[privacy] The export contains private account data; keep it "
            "only in private encrypted-at-rest storage."
        )
        return 0
    if args.command == "list":
        print(json.dumps(store.list_privacy_requests(actor), indent=2))
        return 0
    if args.command == "request-deletion":
        request_id = store.request_account_deletion(actor)
        print(f"[privacy] Account deletion requested: {request_id}")
        return 0
    if args.command == "cancel-deletion":
        store.cancel_account_deletion(actor, args.request_id)
        print(f"[privacy] Account deletion cancelled: {args.request_id}")
        return 0
    if args.command == "complete-deletion":
        result = store.complete_account_deletion(
            actor,
            args.request_id,
            args.confirm,
        )
        print(json.dumps(result, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
