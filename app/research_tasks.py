"""Local research task queue for Atlas Stage 4."""

from datetime import datetime
import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASK_DIR = PROJECT_ROOT / "research_tasks"
DEFAULT_TASK_FILE = DEFAULT_TASK_DIR / "tasks.json"
DEFAULT_ARCHIVE_INDEX = PROJECT_ROOT / "research_archive" / "archive_index.json"
VALID_STATUSES = {"open", "in_progress", "closed"}
VALID_ROLES = {"CEO", "CIO", "CRO", "Reporting"}


class ResearchTaskQueue:
    """Manage local research tasks without autonomous execution."""

    def __init__(self, task_file=DEFAULT_TASK_FILE):
        self.task_file = Path(task_file)

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

    def update_status(self, task_id, status):
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid task status: {status}")

        payload = self.load()
        for task in payload["tasks"]:
            if task.get("id") == task_id:
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat(timespec="seconds")
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

    def _normalize_role(self, role):
        role = str(role).strip()
        if role not in VALID_ROLES:
            raise ValueError(f"invalid research role: {role}")
        return role

    def _task_id(self, role, subject, prompt):
        raw = f"{role}|{subject or 'General'}|{prompt}".lower()
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"task_{digest}"

    def _task_suggestions_from_entry(self, entry, snapshot=None):
        source = entry.get("report_path") or entry.get("snapshot_path") or "archive_index"
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
