"""Local research task queue for Atlas Stage 4."""

from datetime import datetime
import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TASK_DIR = PROJECT_ROOT / "research_tasks"
DEFAULT_TASK_FILE = DEFAULT_TASK_DIR / "tasks.json"
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

    def _normalize_role(self, role):
        role = str(role).strip()
        if role not in VALID_ROLES:
            raise ValueError(f"invalid research role: {role}")
        return role

    def _task_id(self, role, subject, prompt):
        raw = f"{role}|{subject or 'General'}|{prompt}".lower()
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"task_{digest}"
