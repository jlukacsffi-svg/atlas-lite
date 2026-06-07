#!/usr/bin/env python3
"""Run the daily Atlas workflow and persist its private cloud artifacts."""

import sys

import main as atlas_daily
from app.cloud_storage import sync_from_environment


def main():
    sync_from_environment("pull")
    result = atlas_daily.main()
    if result == 0:
        sync_from_environment("push")
    return result


if __name__ == "__main__":
    sys.exit(main())
