#!/usr/bin/env python3
"""
Atlas Lite - Weekly Research Summary Generator

Reads the local research archive index and creates a weekly summary report.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.email_delivery import EmailDelivery
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

    print()
    print("[email] Checking email delivery settings...")
    email_delivery = EmailDelivery()
    if email_delivery.config.enabled:
        try:
            email_delivery.send_report(
                report_path,
                generator.last_html_path,
                subject=f"Atlas Weekly Research Summary - {generator.timestamp.strftime('%B %d, %Y')}",
                body=(
                    "Atlas Lite generated the weekly research summary.\n\n"
                    "The Markdown and HTML summary files are attached.\n"
                ),
            )
            print("[ok] Weekly summary email sent.")
        except Exception as email_error:
            print(f"[warning] Weekly summary email delivery failed: {email_error}")
    else:
        print("[email] Email delivery disabled.")

    print("[ok] Weekly summary generation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
