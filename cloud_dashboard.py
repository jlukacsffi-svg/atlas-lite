#!/usr/bin/env python3
"""Run the Atlas dashboard with its cloud-ready WSGI boundary."""

import os
import sys

from app.cloud_storage import sync_from_environment
from app.owner_controls import OwnerControlService
from app.web_cloud import (
    CloudWebSettings,
    RefreshingDashboardDataService,
    create_application,
    data_service_from_environment,
)


def main():
    try:
        from waitress import serve
    except ImportError:
        print(
            "Install web dependencies first: "
            "py -3.12 -m pip install -r requirements-web.txt",
            file=sys.stderr,
        )
        return 2

    settings = CloudWebSettings.from_environment()
    settings.validate()
    host = "127.0.0.1" if settings.mode == "local" else "0.0.0.0"
    port = int(os.getenv("PORT", "8765"))
    if settings.mode == "cloud":
        downloaded = sync_from_environment("pull")
        print(f"[cloud-storage] Loaded {len(downloaded)} private artifacts")
    data_service = data_service_from_environment()
    owner_control = None
    if settings.owner_controls_enabled:
        owner_control = OwnerControlService(
            data_service,
            persist=lambda paths: sync_from_environment(
                "push",
                paths=paths,
            ),
            refresh=lambda: sync_from_environment("pull"),
        )
    if settings.mode == "cloud":
        data_service = RefreshingDashboardDataService(
            data_service,
            lambda: sync_from_environment("pull"),
        )
    print(f"[web] Atlas {settings.mode} dashboard listening on {host}:{port}")
    serve(
        create_application(
            settings=settings,
            data_service=data_service,
            owner_control=owner_control,
        ),
        host=host,
        port=port,
        threads=4,
        clear_untrusted_proxy_headers=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
