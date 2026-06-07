#!/usr/bin/env python3
"""Run the Atlas dashboard with its cloud-ready WSGI boundary."""

import os
import sys

from app.web_cloud import CloudWebSettings, create_application


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
    print(f"[web] Atlas {settings.mode} dashboard listening on {host}:{port}")
    serve(
        create_application(settings=settings),
        host=host,
        port=port,
        threads=4,
        clear_untrusted_proxy_headers=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
