#!/usr/bin/env python3
"""Audit the local Atlas PostgreSQL adapter without connecting to a database."""

import json
import sys

from app.tenant_postgres import validate_postgres_contract


def main():
    result = validate_postgres_contract()
    print(json.dumps(result, indent=2))
    if result["passed"]:
        print("[ok] PostgreSQL adapter contract passed offline validation.")
        print("[blocked] No database connection or cloud resource was created.")
        return 0
    print("[failed] PostgreSQL adapter contract is incomplete.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
