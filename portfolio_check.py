#!/usr/bin/env python3
"""Validate the optional local Atlas portfolio file."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.portfolio import Portfolio
from app.security_universe import SecurityUniverse


def main():
    print("=" * 60)
    print("Atlas Lite - Portfolio File Check")
    print("=" * 60)
    print()

    universe = SecurityUniverse()
    result = Portfolio().validate(allowed_tickers=universe.tickers(include_avoid=True))

    if not result.get("configured"):
        print("[portfolio] No local portfolio file found.")
        print("[hint] Copy data\\portfolio.example.json to data\\portfolio.json to enable portfolio intelligence.")
        return 0

    print(f"[portfolio] Loaded: {result.get('name', 'Local Portfolio')}")
    print(f"[portfolio] Positions: {len(result.get('positions', []))}")

    for warning in result.get("warnings", []):
        print(f"[warning] {warning}")

    for error in result.get("errors", []):
        print(f"[error] {error}")

    if result.get("errors"):
        return 1

    print("[ok] Portfolio file structure is valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
