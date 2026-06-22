"""Local research task queue for Atlas Stage 4."""

from datetime import datetime, timedelta, timezone
from collections import Counter
import hashlib
import json
from pathlib import Path

from app.scoring import ScoringEngine
from app.paths import data_path


DEFAULT_TASK_DIR = data_path("research_tasks")
DEFAULT_TASK_FILE = DEFAULT_TASK_DIR / "tasks.json"
DEFAULT_ARCHIVE_INDEX = data_path("research_archive", "archive_index.json")
VALID_STATUSES = {"open", "in_progress", "awaiting_owner", "closed"}
VALID_ROLES = {"CEO", "CIO", "CRO", "Reporting", "Sector Analyst"}
VALID_CONFIDENCE = {"low", "medium", "high"}
VALID_RECOMMENDATIONS = {
    "no_action",
    "monitor",
    "research_further",
    "watchlist_review",
    "risk_review",
}
VALID_OWNER_DECISIONS = {"approve", "reject", "defer"}
GENERATED_TASK_TTLS = {
    "daily_market": 3,
    "daily_portfolio": 3,
    "weekly_research": 8,
}
ROLE_PURPOSES = {
    "CEO": "Prioritize the research agenda, escalate urgent risks, and summarize owner decisions needed.",
    "CIO": "Review investment opportunities, catalyst quality, and thesis conviction.",
    "CRO": "Challenge assumptions and investigate downside, concentration, and data-quality risks.",
    "Reporting": "Maintain concise, accurate, owner-focused research outputs.",
    "Sector Analyst": "Investigate sector trends, catalysts, and whether broad moves are durable or isolated.",
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
        generated_scope=None,
        signal_type=None,
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
        if generated_scope:
            task["generated_scope"] = generated_scope
        if signal_type:
            task["signal_type"] = signal_type
            task["signal_key"] = self._signal_key(
                generated_scope,
                role,
                task["subject"],
                signal_type,
            )
            task["last_seen_at"] = created_at
        payload["tasks"].append(task)
        self.save(payload)
        return task, True

    def refresh_generated_tasks(
        self,
        suggestions,
        source,
        generated_scope,
        limit=8,
        now=None,
    ):
        """Refresh generated signals, closing stale or duplicate open work."""
        if generated_scope not in GENERATED_TASK_TTLS:
            raise ValueError(f"invalid generated task scope: {generated_scope}")
        now = now or datetime.now()
        now_text = now.isoformat(timespec="seconds")
        payload = self.load()
        self._normalize_generated_tasks(payload["tasks"])
        self._close_stale_and_duplicate_tasks(payload["tasks"], now)

        refreshed = []
        active_keys = set()
        for suggestion in list(suggestions)[:limit]:
            suggestion = dict(suggestion)
            signal_type = suggestion.pop("signal_type", "general")
            role = self._normalize_role(suggestion["role"])
            subject = suggestion.get("subject") or "General"
            key = self._signal_key(generated_scope, role, subject, signal_type)
            active_keys.add(key)
            existing = next(
                (
                    task
                    for task in payload["tasks"]
                    if task.get("status") != "closed"
                    and task.get("signal_key") == key
                ),
                None,
            )
            if existing:
                existing["source"] = source
                existing["last_seen_at"] = now_text
                existing["updated_at"] = now_text
                if existing.get("status") == "open":
                    existing.update(
                        {
                            "role": role,
                            "subject": subject,
                            "priority": str(
                                suggestion.get("priority", "medium")
                            ).lower(),
                            "prompt": str(suggestion["prompt"]).strip(),
                            "generated_scope": generated_scope,
                            "signal_type": signal_type,
                            "signal_key": key,
                        }
                    )
                refreshed.append(existing)
                continue

            task = {
                "id": self._task_id(role, subject, key),
                "created_at": now_text,
                "last_seen_at": now_text,
                "role": role,
                "priority": str(suggestion.get("priority", "medium")).lower(),
                "status": "open",
                "subject": subject,
                "source": source,
                "prompt": str(suggestion["prompt"]).strip(),
                "notes": str(suggestion.get("notes") or ""),
                "generated_scope": generated_scope,
                "signal_type": signal_type,
                "signal_key": key,
            }
            payload["tasks"].append(task)
            refreshed.append(task)

        for task in payload["tasks"]:
            if (
                task.get("status") == "open"
                and task.get("generated_scope") == generated_scope
                and task.get("signal_key") not in active_keys
            ):
                self._close_generated_task(
                    task,
                    now_text,
                    "Signal was not present in the latest refresh.",
                )

        payload["queue_version"] = "1.1"
        self.save(payload)
        return refreshed

    def maintain_generated_tasks(self, now=None):
        """Close stale and duplicate generated work without deleting history."""
        now = now or datetime.now()
        payload = self.load()
        self._normalize_generated_tasks(payload["tasks"])
        closed = self._close_stale_and_duplicate_tasks(payload["tasks"], now)
        payload["queue_version"] = "1.1"
        self.save(payload)
        return closed

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
        default_name = f"{role.lower().replace(' ', '_')}_brief.md"
        output_path = Path(output_path) if output_path else self.task_file.parent / default_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.render_role_brief(role=role, status=status),
            encoding="utf-8",
        )
        return output_path

    def save_review_outputs(self, status="open"):
        """Refresh the shared agenda and every role-specific brief."""
        paths = {
            "agenda": self.save_agenda(status=status),
            "owner_review": self.save_owner_review(),
        }
        for role in sorted(VALID_ROLES):
            paths[role] = self.save_role_brief(role=role, status=status)
        return paths

    def complete_research(
        self,
        task_id,
        conclusion,
        recommendation,
        confidence="medium",
        evidence=None,
        catalyst_type=None,
        thesis_action=None,
        thesis_alignment=None,
    ):
        """Record a research finding and route it to owner review."""
        recommendation = str(recommendation).strip().lower()
        confidence = str(confidence).strip().lower()
        conclusion = str(conclusion).strip()
        if not conclusion:
            raise ValueError("research conclusion is required")
        if recommendation not in VALID_RECOMMENDATIONS:
            raise ValueError(f"invalid recommendation: {recommendation}")
        if confidence not in VALID_CONFIDENCE:
            raise ValueError(f"invalid confidence: {confidence}")

        if evidence is None:
            evidence = []
        elif isinstance(evidence, str):
            evidence = [evidence]
        evidence = [
            normalized
            for item in evidence
            if (normalized := self._normalize_evidence(item))
        ]

        payload = self.load()
        for task in payload["tasks"]:
            if task.get("id") != task_id:
                continue
            task["status"] = "awaiting_owner"
            task["updated_at"] = datetime.now().isoformat(timespec="seconds")
            task["result"] = {
                "conclusion": conclusion,
                "recommendation": recommendation,
                "confidence": confidence,
                "evidence": evidence,
            }
            if catalyst_type:
                task["result"]["catalyst_type"] = str(catalyst_type).strip()
            if thesis_action:
                task["result"]["thesis_action"] = str(thesis_action).strip()
            if thesis_alignment:
                task["result"]["thesis_alignment"] = str(thesis_alignment).strip()
            self.save(payload)
            return task

        raise ValueError(f"task not found: {task_id}")

    def record_owner_decision(self, task_id, decision, notes=None):
        """Record Joe's disposition of a research recommendation."""
        decision = str(decision).strip().lower()
        if decision not in VALID_OWNER_DECISIONS:
            raise ValueError(f"invalid owner decision: {decision}")

        payload = self.load()
        for task in payload["tasks"]:
            if task.get("id") != task_id:
                continue
            if task.get("status") != "awaiting_owner":
                raise ValueError("task is not awaiting owner review")

            task["owner_decision"] = {
                "decision": decision,
                "decided_at": datetime.now().isoformat(timespec="seconds"),
                "notes": str(notes or "").strip(),
            }
            task["status"] = "in_progress" if decision == "defer" else "closed"
            task["updated_at"] = task["owner_decision"]["decided_at"]
            self.save(payload)
            return task

        raise ValueError(f"task not found: {task_id}")

    def render_owner_review(self):
        """Render completed research recommendations awaiting Joe's review."""
        tasks = self.list_tasks(status="awaiting_owner")
        lines = [
            "# Atlas Owner Review Queue",
            "",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "## Pending Recommendations",
            "",
        ]
        if not tasks:
            lines.extend(["No research recommendations are awaiting owner review.", ""])
        else:
            lines.extend(
                [
                    "| Priority | Role | Subject | Recommendation | Confidence | Conclusion |",
                    "|----------|------|---------|----------------|------------|------------|",
                ]
            )
            for task in self._sorted_tasks(tasks):
                result = task.get("result", {})
                lines.append(
                    f"| {self._table_text(task.get('priority', 'medium')).title()} | "
                    f"{self._table_text(task.get('role', 'N/A'))} | "
                    f"{self._table_text(task.get('subject', 'General'))} | "
                    f"{self._table_text(result.get('recommendation', 'N/A')).replace('_', ' ').title()} | "
                    f"{self._table_text(result.get('confidence', 'N/A')).title()} | "
                    f"{self._table_text(result.get('conclusion', 'N/A'))} |"
                )
            lines.append("")

        lines.extend(
            [
                "## Authority Boundary",
                "",
                "Owner review accepts or rejects a research recommendation only. "
                "It does not authorize or execute a financial transaction.",
                "",
            ]
        )
        return "\n".join(lines)

    def save_owner_review(self, output_path=None):
        output_path = (
            Path(output_path)
            if output_path
            else self.task_file.parent / "owner_review.md"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render_owner_review(), encoding="utf-8")
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
        return self.refresh_generated_tasks(
            suggestions,
            source=str(latest.get("report_path") or "archive_index"),
            generated_scope="daily_market",
            limit=limit,
        )

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
        return self.refresh_generated_tasks(
            suggestions,
            source=source,
            generated_scope="daily_market",
            limit=limit,
        )

    def generate_from_portfolio_summary(self, portfolio_summary, source="daily_portfolio", limit=8):
        """Create research tasks from configured portfolio risk alerts."""
        if not portfolio_summary.get("configured"):
            return []

        suggestions = []
        for alert in portfolio_summary.get("risk_alerts", []):
            alert_type = alert.get("type", "portfolio_risk")
            message = alert.get("message")
            if not message:
                continue
            role = "Reporting" if alert_type == "missing_data" else "CRO"
            suggestions.append(
                {
                    "role": role,
                    "subject": alert_type.replace("_", " ").title(),
                    "priority": alert.get("severity", "medium"),
                    "source": source,
                    "prompt": f"Review portfolio alert: {message}",
                }
            )

        return self.refresh_generated_tasks(
            suggestions,
            source=source,
            generated_scope="daily_portfolio",
            limit=limit,
        )

    def _normalize_role(self, role):
        role = str(role).strip()
        if role not in VALID_ROLES:
            raise ValueError(f"invalid research role: {role}")
        return role

    def _task_id(self, role, subject, prompt):
        raw = f"{role}|{subject or 'General'}|{prompt}".lower()
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"task_{digest}"

    def _signal_key(self, scope, role, subject, signal_type):
        raw = (
            f"{scope or 'generated'}|{role}|{subject or 'General'}|"
            f"{signal_type or 'general'}"
        ).lower()
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def _normalize_generated_tasks(self, tasks):
        for task in tasks:
            if task.get("generated_scope") and task.get("signal_key"):
                continue
            scope, signal_type = self._infer_generated_identity(task)
            if not scope:
                continue
            task["generated_scope"] = scope
            task["signal_type"] = signal_type
            task["signal_key"] = self._signal_key(
                scope,
                task.get("role"),
                task.get("subject"),
                signal_type,
            )
            task["last_seen_at"] = task.get("updated_at") or task.get("created_at")

    def _close_stale_and_duplicate_tasks(self, tasks, now):
        now = self._comparable_datetime(now)
        now_text = now.isoformat(timespec="seconds")
        closed = []
        open_generated = [
            task
            for task in tasks
            if task.get("status") == "open" and task.get("generated_scope")
        ]
        grouped = {}
        for task in open_generated:
            grouped.setdefault(task.get("signal_key"), []).append(task)
        for duplicates in grouped.values():
            duplicates.sort(
                key=lambda task: task.get("last_seen_at")
                or task.get("updated_at")
                or task.get("created_at")
                or "",
                reverse=True,
            )
            for duplicate in duplicates[1:]:
                self._close_generated_task(
                    duplicate,
                    now_text,
                    "Superseded by a newer equivalent generated signal.",
                )
                closed.append(duplicate)

        for task in open_generated:
            if task.get("status") != "open":
                continue
            ttl_days = GENERATED_TASK_TTLS.get(task.get("generated_scope"))
            seen_at = self._parse_datetime(
                task.get("last_seen_at")
                or task.get("updated_at")
                or task.get("created_at")
            )
            if ttl_days and seen_at and now - seen_at > timedelta(days=ttl_days):
                self._close_generated_task(
                    task,
                    now_text,
                    f"Generated signal expired after {ttl_days} days without refresh.",
                )
                closed.append(task)
        return closed

    def _infer_generated_identity(self, task):
        source = str(task.get("source") or "").lower()
        prompt = str(task.get("prompt") or "").lower()
        if "weekly_summary" in source:
            scope = "weekly_research"
        elif "morning_brief" in source or "daily_run" in source:
            scope = "daily_market"
        elif "daily_portfolio" in source:
            scope = "daily_portfolio"
        else:
            return None, None

        patterns = (
            ("review downside risk", "downside_move"),
            ("review catalyst quality", "catalyst_move"),
            ("maintain or refresh", "score_leader"),
            ("review portfolio alert", "portfolio_alert"),
            ("score improved", "score_improvement"),
            ("score declined", "score_decline"),
            ("appeared as a top mover", "recurring_mover"),
            ("weakest sector trend", "sector_weakness"),
            ("recurring score leader", "recurring_score_leader"),
        )
        signal_type = next(
            (value for phrase, value in patterns if phrase in prompt),
            "general",
        )
        return scope, signal_type

    def _close_generated_task(self, task, closed_at, reason):
        task["status"] = "closed"
        task["updated_at"] = closed_at
        task["close_reason"] = reason
        task["notes"] = self._append_note(task.get("notes", ""), reason)

    @staticmethod
    def _parse_datetime(value):
        try:
            return ResearchTaskQueue._comparable_datetime(
                datetime.fromisoformat(str(value))
            )
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _comparable_datetime(value):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def _append_note(self, existing_notes, new_note):
        new_note = str(new_note).strip()
        if not new_note:
            return existing_notes or ""
        if not existing_notes:
            return new_note
        return f"{existing_notes}\n{new_note}"

    @staticmethod
    def _normalize_evidence(item):
        if isinstance(item, dict):
            normalized = {
                "title": str(item.get("title") or "").strip(),
                "source": str(item.get("source") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "detail": str(item.get("detail") or "").strip(),
            }
            return normalized if any(normalized.values()) else None
        text = str(item).strip()
        return text or None

    def _task_table(self, tasks):
        lines = [
            "| Priority | Role | Subject | Prompt | Source |",
            "|----------|------|---------|--------|--------|",
        ]
        for task in self._sorted_tasks(tasks):
            lines.append(
                f"| {self._table_text(task.get('priority', 'medium')).title()} | "
                f"{self._table_text(task.get('role', 'N/A'))} | "
                f"{self._table_text(task.get('subject', 'General'))} | "
                f"{self._table_text(task.get('prompt', 'N/A'))} | "
                f"{self._table_text(task.get('source', 'manual'))} |"
            )
        return lines

    def _sorted_tasks(self, tasks):
        return sorted(
            tasks,
            key=lambda item: (
                {"high": 0, "medium": 1, "low": 2}.get(item.get("priority", "medium"), 1),
                item.get("created_at", ""),
            ),
        )

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
                        "signal_type": "downside_move",
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
                        "signal_type": "catalyst_move",
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
                    "signal_type": "score_leader",
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
                        "signal_type": "data_quality",
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
