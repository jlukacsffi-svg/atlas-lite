#!/usr/bin/env python3
"""
Atlas Lite - Weekly Research Summary Generator

Reads the local research archive index and creates a weekly summary report.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.weekly_summary import WeeklySummaryGenerator


def main():
    print("=" * 60)
    print("Atlas Lite - Weekly Research Summary Generator")
    print("=" * 60)
    print()

    generator = WeeklySummaryGenerator()
    report_path = generator.save_summary(days=7)

    print(f"[ok] Weekly summary saved to: {report_path}")
    if generator.last_html_path:
        print(f"[ok] HTML weekly summary saved to: {generator.last_html_path}")
    print("[ok] Weekly summary generation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
