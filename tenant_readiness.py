#!/usr/bin/env python3
"""Print the local Atlas tenant production-readiness decision."""

import argparse
import json
from pathlib import Path
import sys

from app.tenant_readiness import TenantProductionReadiness


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=None)
    args = parser.parse_args(argv)
    readiness = (
        TenantProductionReadiness(args.review)
        if args.review is not None
        else TenantProductionReadiness()
    ).evaluate()
    print(json.dumps(readiness, indent=2))
    if not readiness["architecture_checks_passed"]:
        return 1
    if not readiness["deployment_approved"]:
        print(
            "[blocked] Architecture review passed, but deployment remains "
            "unapproved."
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
