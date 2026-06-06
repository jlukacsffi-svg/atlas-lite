#!/usr/bin/env python3
"""Manage the local Atlas research task queue."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.research_tasks import ResearchTaskQueue

STATUS_CHOICES = ["open", "in_progress", "awaiting_owner", "closed"]
ROLE_CHOICES = ["CEO", "CIO", "CRO", "Reporting", "Sector Analyst"]


def build_parser():
    parser = argparse.ArgumentParser(description="Manage Atlas local research tasks.")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List research tasks.")
    list_parser.add_argument("--status", choices=STATUS_CHOICES)

    subparsers.add_parser("summary", help="Summarize research task queue status.")

    agenda_parser = subparsers.add_parser("agenda", help="Write a Markdown research agenda.")
    agenda_parser.add_argument("--status", choices=STATUS_CHOICES, default="open")
    agenda_parser.add_argument("--output", default=None)

    brief_parser = subparsers.add_parser("brief", help="Write a role-specific Markdown research brief.")
    brief_parser.add_argument("--role", required=True, choices=ROLE_CHOICES)
    brief_parser.add_argument("--status", choices=STATUS_CHOICES, default="open")
    brief_parser.add_argument("--output", default=None)

    add_parser = subparsers.add_parser("add", help="Add a research task.")
    add_parser.add_argument("--role", required=True, choices=ROLE_CHOICES)
    add_parser.add_argument("--subject", default="General")
    add_parser.add_argument("--priority", default="medium")
    add_parser.add_argument("--source", default="manual")
    add_parser.add_argument("--notes", default="")
    add_parser.add_argument("prompt")

    status_parser = subparsers.add_parser("status", help="Update a research task status.")
    status_parser.add_argument("task_id")
    status_parser.add_argument("status", choices=STATUS_CHOICES)
    status_parser.add_argument("--notes", default=None)

    complete_parser = subparsers.add_parser(
        "complete",
        help="Record research findings and route them to owner review.",
    )
    complete_parser.add_argument("task_id")
    complete_parser.add_argument("--conclusion", required=True)
    complete_parser.add_argument(
        "--recommendation",
        required=True,
        choices=["no_action", "monitor", "research_further", "watchlist_review", "risk_review"],
    )
    complete_parser.add_argument("--confidence", choices=["low", "medium", "high"], default="medium")
    complete_parser.add_argument("--evidence", action="append", default=[])

    decide_parser = subparsers.add_parser(
        "decide",
        help="Record the owner's disposition of a research recommendation.",
    )
    decide_parser.add_argument("task_id")
    decide_parser.add_argument("decision", choices=["approve", "reject", "defer"])
    decide_parser.add_argument("--notes", default=None)

    review_parser = subparsers.add_parser("review", help="Write the owner review queue.")
    review_parser.add_argument("--output", default=None)

    generate_parser = subparsers.add_parser("generate", help="Generate tasks from latest Atlas archive signals.")
    generate_parser.add_argument("--limit", type=int, default=8)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    queue = ResearchTaskQueue()

    if args.command == "add":
        task, created = queue.add_task(
            role=args.role,
            prompt=args.prompt,
            priority=args.priority,
            subject=args.subject,
            source=args.source,
            notes=args.notes,
        )
        status = "created" if created else "already open"
        print(f"[ok] Task {status}: {task['id']} ({task['role']}, {task['priority']})")
        return 0

    if args.command == "status":
        task = queue.update_status(args.task_id, args.status, notes=args.notes)
        print(f"[ok] Task {task['id']} updated to {task['status']}.")
        return 0

    if args.command == "complete":
        task = queue.complete_research(
            task_id=args.task_id,
            conclusion=args.conclusion,
            recommendation=args.recommendation,
            confidence=args.confidence,
            evidence=args.evidence,
        )
        queue.save_review_outputs()
        print(f"[ok] Task {task['id']} routed to owner review.")
        return 0

    if args.command == "decide":
        task = queue.record_owner_decision(
            task_id=args.task_id,
            decision=args.decision,
            notes=args.notes,
        )
        queue.save_review_outputs()
        print(
            f"[ok] Owner decision '{args.decision}' recorded for "
            f"{task['id']}; status is {task['status']}."
        )
        return 0

    if args.command == "review":
        output_path = queue.save_owner_review(output_path=args.output)
        print(f"[ok] Owner review queue saved to: {output_path}")
        return 0

    if args.command == "summary":
        summary = queue.summary()
        print(f"Total tasks: {summary['total']}")
        print("By status:")
        for status, count in sorted(summary["by_status"].items()):
            print(f"  {status}: {count}")
        print("By role:")
        for role, count in sorted(summary["by_role"].items()):
            print(f"  {role}: {count}")
        print("By priority:")
        for priority, count in sorted(summary["by_priority"].items()):
            print(f"  {priority}: {count}")
        if summary["open_high_priority"]:
            print("Open high-priority tasks:")
            for task in summary["open_high_priority"]:
                print(f"  {task['id']} | {task['role']} | {task['subject']} | {task['prompt']}")
        return 0

    if args.command == "agenda":
        output_path = queue.save_agenda(output_path=args.output, status=args.status)
        print(f"[ok] Research agenda saved to: {output_path}")
        return 0

    if args.command == "brief":
        output_path = queue.save_role_brief(
            role=args.role,
            output_path=args.output,
            status=args.status,
        )
        print(f"[ok] {args.role} research brief saved to: {output_path}")
        return 0

    if args.command == "generate":
        created = queue.generate_from_archive(limit=args.limit)
        if not created:
            print("[tasks] No new research tasks generated.")
            return 0
        for task in created:
            print(
                f"[ok] Generated {task['id']} | {task['priority']} | "
                f"{task['role']} | {task['subject']}"
            )
        return 0

    tasks = queue.list_tasks(status=args.status if args.command == "list" else "open")
    if not tasks:
        print("[tasks] No matching research tasks.")
        return 0

    for task in tasks:
        print(
            f"{task['id']} | {task['status']} | {task['priority']} | "
            f"{task['role']} | {task['subject']} | {task['prompt']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
