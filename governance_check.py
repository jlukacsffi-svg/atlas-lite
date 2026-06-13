#!/usr/bin/env python3
"""Print the Atlas governance readiness decision."""

import json
import sys

from app.governance_readiness import GovernanceReadiness


def main():
    result = GovernanceReadiness().evaluate()
    print(json.dumps(result, indent=2))
    if not result["engineering_ready"]:
        return 1
    if not result["external_release_approved"]:
        print(
            "[blocked] Internal governance artifacts pass, but external "
            "release reviews remain pending."
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

