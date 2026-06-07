#!/usr/bin/env python3
"""Synchronize Atlas private artifacts with managed Cloud Storage."""

import argparse
import sys

from app.cloud_storage import sync_from_environment


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direction", choices=("pull", "push"))
    args = parser.parse_args(argv)
    result = sync_from_environment(args.direction)
    count = len(result) if isinstance(result, list) else len(result["files"])
    print(f"[cloud-storage] {args.direction} complete: {count} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
