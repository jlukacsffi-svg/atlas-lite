"""Local research task queue for Atlas Stage 4."""

from datetime import datetime
from collections import Counter
import hashlib
import json
from pathlib import Path

from app.scoring import ScoringEngine


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASK_DIR = PROJECT_ROOT / "research_tasks"
DEFAULT_TASK_FILE = DEFAULT_TASK_DIR / "tasks.json"
DEFAULT_ARCHIVE_INDEX = PROJECT_ROOT / "research_archive" / "archive_index.json"
VALID_STATUSES = {"open", "in_progress", "closed"}
VALID_ROLES = {"CEO", "CIO", "CRO", "Reporting"}
ROLE_PURPOSES = {
    "CEO": "Prioritize the research agenda, escalate urgent risks, and summarize owner decisions needed.",
    "CIO": "Review investment opportunities, catalyst quality, and thesis conviction.",
    "CRO": "Challenge assumptions and investigate downside, concentration, and data-quality risks.",
    "Reporting": "Maintain concise, accurate, owner-focused research outputs.",
}


class ResearchTaskQueue:
    """Manage local research tasks without autonomous execution."""

    def __init__(self, task_file=DEFAULT_TASK_FILE):
        self.task_file = Path(task_file)
        self.scoring_engine = ScoringEngine()

    def load(self):
        if not self.task_file.exists():
            return {"queue_version": "1.0", "tasks": []}

        with open(self.task_file, "r", encoding="utf-8") as f:
            payload = json.load(f)

        return {
            "queue_version": payload.get("queue_version", "1.0"),
            "tasks": payload.get("tasks", []),
        }

    def save(self, payload):
        self.task_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.task_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        return self.task_file

    def add_task(
        self,
        role,
        prompt,
        priority="medium",
        subject=None,
        source=None,
        notes=None,
        created_at=None,
    ):
        role = self._normalize_role(role)
        prompt = str(prompt).strip()
        if not prompt:
            raise ValueError("task prompt is required")

        created_at = created_at or datetime.now().isoformat(timespec="seconds")
        payload = self.load()
        task_id = self._task_id(role=role, subject=subject, prompt=prompt)

        for task in payload["tasks"]:
            if task.get("id") == task_id and task.get("status") != "closed":
                return task, False

        task = {
            "id": task_id,
            "created_at": created_at,
            "role": role,
            "priority": str(priority).lower(),
            "status": "open",
            "subject": subject or "General",
            "source": source or "manual",
            "prompt": prompt,
            "notes": notes or "",
        }
        payload["tasks"].append(task)
        self.save(payload)
        return task, True

    def list_tasks(self, status=None):
        tasks = self.load()["tasks"]
        if status:
            return [task for task in tasks if task.get("status") == status]
        return tasks

    def summary(self):
        tasks = self.load()["tasks"]
        return {
            "total": len(tasks),
            "by_status": dict(Counter(task.get("status", "open") for task in tasks)),
            "by_role": dict(Counter(task.get("role", "Unknown") for task in tasks)),
            "by_priority": dict(Counter(task.get("priority", "medium") for task in tasks)),
            "open_high_priority": [
                task for task in tasks
                if task.get("status") == "open" and task.get("priority") == "high"
            ],
        }

    def render_agenda(self, status="open"):
        """Render a Markdown agenda for the selected task status."""
        tasks = self.list_tasks(status=status)
        summary = self.summary()
        generated_at = datetime.now().isoformat(timespec="seconds")
        lines = [
            "# Atlas Research Task Agenda",
            "",
            f"Generated: {generated_at}",
            f"Status filter: {status or 'all'}",
            "",
            "## Queue Summary",
            "",
            f"- **Total Tasks**: {summary['total']}",
            f"- **Open Tasks**: {summary['by_status'].get('open', 0)}",
            f"- **High Priority Open Tasks**: {len(summary['open_high_priority'])}",
            "",
        ]

        if not tasks:
            lines.append("No matching research tasks.")
            lines.append("")
            return "\n".join(lines)

        high_priority = [
            task for task in tasks
            if task.get("priority") == "high"
        ]
        if high_priority:
            lines.extend(["## High Priority", ""])
            lines.extend(self._task_table(high_priority))
            lines.append("")

        lines.extend(["## By Role", ""])
        for role in sorted(VALID_ROLES):
            role_tasks = [
                task for task in tasks
                if task.get("role") == role
            ]
            if not role_tasks:
                continue
            lines.extend([f"### {role}", ""])
            lines.extend(self._task_table(role_tasks))
            lines.append("")

        return "\n".join(lines)

    def save_agenda(self, output_path=None, status="open"):
        output_path = Path(output_path) if output_path else self.task_file.parent / "agenda.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render_agenda(status=status), encoding="utf-8")
        return output_path

    def render_role_brief(self, role, status="open"):
        """Render a focused Markdown work brief for one Atlas role."""
        role = self._normalize_role(role)
        tasks = self.list_tasks(status=status)
        if role != "CEO":
            tasks = [task for task in tasks if task.get("role") == role]

        generated_at = datetime.now().isoformat(timespec="seconds")
        high_priority = [task for task in tasks if task.get("priority") == "high"]
        lines = [
            f"# Atlas {role} Research Brief",
            "",
            f"Generated: {generated_at}",
            f"Status filter: {status or 'all'}",
            "",
            "## Role Mandate",
            "",
            ROLE_PURPOSES[role],
            "",
            "## Workload",
            "",
            f"- **Matching Tasks**: {len(tasks)}",
            f"- **High Priority**: {len(high_priority)}",
            "",
        ]

        if not tasks:
            lines.extend(
                [
                    "## Assigned Work",
                    "",
                    "No matching research tasks.",
                    "",
                ]
            )
            return "\n".join(lines)

        if high_priority:
            lines.extend(["## Immediate Attention", ""])
            lines.extend(self._task_table(high_priority))
            lines.append("")

        remaining = [task for task in tasks if task.get("priority") != "high"]
        if remaining:
            lines.extend(["## Research Queue", ""])
            lines.extend(self._task_table(remaining))
            lines.append("")

        lines.extend(
            [
                "## Owner Boundary",
                "",
                "This brief organizes research only. It does not authorize trades, "
                "capital commitments, or external actions.",
                "",
            ]
        )
        return "\n".join(lines)

    def save_role_brief(self, role, output_path=None, status="open"):
        role = self._normalize_role(role)
        default_name = f"{role.lower()}_brief.md"
        output_path = Path(output_path) if output_path else self.task_file.parent / default_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.render_role_brief(role=role, status=status),
            encoding="utf-8",
        )
        return output_path

    def update_status(self, task_id, status, notes=None):
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid task status: {status}")

        payload = self.load()
        for task in payload["tasks"]:
            if task.get("id") == task_id:
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat(timespec="seconds")
                if notes is not None:
                    existing_notes = task.get("notes", "")
                    task["notes"] = self._append_note(existing_notes, notes)
                self.save(payload)
                return task

        raise ValueError(f"task not found: {task_id}")

    def generate_from_archive(self, archive_index_path=DEFAULT_ARCHIVE_INDEX, limit=8):
        """Create research tasks from the latest structured archive entry."""
        archive_index_path = Path(archive_index_path)
        if not archive_index_path.exists():
            return []

        with open(archive_index_path, "r", encoding="utf-8") as f:
            archive = json.load(f)

        entries = archive.get("entries", [])
        if not entries:
            return []

        latest = sorted(entries, key=lambda item: item.get("generated_at", ""), reverse=True)[0]
        snapshot = self._load_snapshot_for_entry(latest, archive_index_path.parent)
        suggestions = self._task_suggestions_from_entry(latest, snapshot=snapshot)
        created = []

        for suggestion in suggestions[:limit]:
            task, was_created = self.add_task(**suggestion)
            if was_created:
                created.append(task)

        return created

    def generate_from_market_data(self, market_data, source="daily_run", limit=8):
        """Create research tasks directly from the current market-data run."""
        available = [
            (ticker, data)
            for ticker, data in market_data.items()
            if data.get("status") == "available"
        ]
        top_movers = [
            {
                "ticker": ticker,
                "percent_change": float(data["percent_change"]),
            }
            for ticker, data in sorted(
                available,
                key=lambda item: abs(float(item[1].get("percent_change") or 0)),
                reverse=True,
            )[:5]
            if data.get("percent_change") is not None
        ]

        score_leaders = []
        for ticker, data in available:
            scores = data.get("scores")
            if not scores or data.get("sector") == "Benchmark ETF":
                continue
            try:
                total_score = self.scoring_engine.score(scores)
            except (TypeError, ValueError):
                continue
            score_leaders.append(
                {
                    "ticker": ticker,
                    "total_score": total_score,
                }
            )
        score_leaders.sort(key=lambda item: item["total_score"], reverse=True)

        entry = {
            "source": source,
            "top_movers": top_movers,
            "score_leaders": score_leaders[:3],
        }
        snapshot = {"securities": market_data}
        suggestions = self._task_suggestions_from_entry(entry, snapshot=snapshot)
        created = []

        for suggestion in suggestions[:limit]:
            task, was_created = self.add_task(**suggestion)
            if was_created:
                created.append(task)

        return created

    def _normalize_role(self, role):
        role = str(role).strip()
        if role not in VALID_ROLES:
            raise ValueError(f"invalid research role: {role}")
        return role

    def _task_id(self, role, subject, prompt):
        raw = f"{role}|{subject or 'General'}|{prompt}".lower()
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"task_{digest}"

    def _append_note(self, existing_notes, new_note):
        new_note = str(new_note).strip()
        if not new_note:
            return existing_notes or ""
        if not existing_notes:
            return new_note
        return f"{existing_notes}\n{new_note}"

    def _task_table(self, tasks):
        lines = [
            "| Priority | Role | Subject | Prompt | Source |",
            "|----------|------|---------|--------|--------|",
        ]
        for task in sorted(
            tasks,
            key=lambda item: (
                {"high": 0, "medium": 1, "low": 2}.get(item.get("priority", "medium"), 1),
                item.get("created_at", ""),
            ),
        ):
            lines.append(
                f"| {self._table_text(task.get('priority', 'medium')).title()} | "
                f"{self._table_text(task.get('role', 'N/A'))} | "
                f"{self._table_text(task.get('subject', 'General'))} | "
                f"{self._table_text(task.get('prompt', 'N/A'))} | "
                f"{self._table_text(task.get('source', 'manual'))} |"
            )
        return lines

    def _table_text(self, value):
        return str(value).replace("|", "/").replace("\n", " ").strip()

    def _task_suggestions_from_entry(self, entry, snapshot=None):
        source = (
            entry.get("source")
            or entry.get("report_path")
            or entry.get("snapshot_path")
            or "archive_index"
        )
        suggestions = []

        for mover in entry.get("top_movers", [])[:5]:
            ticker = mover.get("ticker")
            pct = mover.get("percent_change")
            if not ticker or pct is None:
                continue

            if pct <= -4:
                suggestions.append(
                    {
                        "role": "CRO",
                        "subject": ticker,
                        "priority": "high",
                        "source": source,
                        "prompt": (
                            f"Review downside risk for {ticker} after a {pct:+.2f}% move. "
                            "Identify whether this looks like temporary volatility or thesis damage."
                        ),
                    }
                )
            elif abs(pct) >= 4:
                suggestions.append(
                    {
                        "role": "CIO",
                        "subject": ticker,
                        "priority": "medium",
                        "source": source,
                        "prompt": (
                            f"Review catalyst quality for {ticker} after a {pct:+.2f}% move. "
                            "Determine whether the move changes conviction or watchlist priority."
                        ),
                    }
                )

        for leader in entry.get("score_leaders", [])[:3]:
            ticker = leader.get("ticker")
            score = leader.get("total_score")
            if not ticker or score is None:
                continue
            suggestions.append(
                {
                    "role": "CIO",
                    "subject": ticker,
                    "priority": "medium",
                    "source": source,
                    "prompt": (
                        f"Maintain or refresh the investment thesis for {ticker}, "
                        f"a recurring high-score name at {score:.1f}."
                    ),
                }
            )

        if snapshot:
            unavailable = [
                ticker for ticker, data in snapshot.get("securities", {}).items()
                if data.get("status") != "available"
            ]
            if unavailable:
                suggestions.append(
                    {
                        "role": "Reporting",
                        "subject": "Data Quality",
                        "priority": "high",
                        "source": source,
                        "prompt": (
                            "Investigate missing market data for "
                            f"{', '.join(sorted(unavailable)[:10])}."
                        ),
                    }
                )

        return suggestions

    def _load_snapshot_for_entry(self, entry, archive_dir):
        snapshot_path = entry.get("snapshot_path")
        if not snapshot_path:
            return None

        path = Path(snapshot_path)
        if not path.is_absolute():
            path = Path(archive_dir) / path

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
