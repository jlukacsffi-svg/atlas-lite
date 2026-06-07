#!/usr/bin/env python3
"""Run the Atlas Web Phase 1 local owner dashboard."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.web_dashboard import run_server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the read-only Atlas owner dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        raise ValueError("Web Phase 1 may bind only to localhost")
    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
