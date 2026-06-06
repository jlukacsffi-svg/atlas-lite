#!/usr/bin/env python3
"""Manage the local Atlas research task queue."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.research_tasks import ResearchTaskQueue


def build_parser():
    parser = argparse.ArgumentParser(description="Manage Atlas local research tasks.")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List research tasks.")
    list_parser.add_argument("--status", choices=["open", "in_progress", "closed"])

    add_parser = subparsers.add_parser("add", help="Add a research task.")
    add_parser.add_argument("--role", required=True, choices=["CEO", "CIO", "CRO", "Reporting"])
    add_parser.add_argument("--subject", default="General")
    add_parser.add_argument("--priority", default="medium")
    add_parser.add_argument("--source", default="manual")
    add_parser.add_argument("--notes", default="")
    add_parser.add_argument("prompt")

    status_parser = subparsers.add_parser("status", help="Update a research task status.")
    status_parser.add_argument("task_id")
    status_parser.add_argument("status", choices=["open", "in_progress", "closed"])

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
        task = queue.update_status(args.task_id, args.status)
        print(f"[ok] Task {task['id']} updated to {task['status']}.")
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
