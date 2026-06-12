#!/usr/bin/env python3
"""Run the local-only Atlas tenant boundary preview."""

import argparse
from pathlib import Path
import secrets
import sys

from app.tenant_accounts import TenantAccount
from app.tenant_store import TenantStore
from app.web_tenant import TenantWebApplication, TenantWebSettings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run the local tenant-aware Atlas preview."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--database",
        default="tenant_data/preview.sqlite3",
    )
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Tenant preview may bind only to localhost")
    try:
        from waitress import serve
    except ImportError:
        print(
            "Install web dependencies first: "
            "py -3.12 -m pip install -r requirements-web.txt",
            file=sys.stderr,
        )
        return 2

    database = Path(args.database).resolve()
    store = TenantStore(database)
    store.migrate()
    owner = TenantAccount(
        tenant_id="atlas-preview",
        user_id="preview-owner",
        provider="google",
        subject="local-preview-owner",
        email="preview-owner@atlas.local",
        role="owner",
    )
    try:
        store.resolve(owner.provider, owner.subject, owner.email)
    except PermissionError:
        store.provision_account("Atlas Preview Workspace", owner)

    settings = TenantWebSettings(
        database_path=database,
        session_secret=secrets.token_urlsafe(48),
        preview_provider=owner.provider,
        preview_subject=owner.subject,
        preview_email=owner.email,
        allow_preview_login=True,
    )
    print(
        f"[web] Atlas tenant preview: http://{args.host}:{args.port}"
    )
    print("[web] Local-only signed preview session. Press Ctrl+C to stop.")
    serve(
        TenantWebApplication(settings, store=store),
        host=args.host,
        port=args.port,
        threads=4,
        clear_untrusted_proxy_headers=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
