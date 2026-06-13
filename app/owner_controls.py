"""Authenticated owner operations over existing Atlas private artifacts."""

from pathlib import Path
import threading


VALID_RESEARCH_DECISIONS = {"approve", "reject", "defer"}
VALID_PAPER_DECISIONS = {"approve", "reject"}


class OwnerControlService:
    """Apply narrow owner decisions and persist them as one guarded operation."""

    def __init__(self, dashboard_service, persist=None, refresh=None):
        self.dashboard_service = dashboard_service
        self.research_queue = dashboard_service.research_queue
        self.paper_account = dashboard_service.paper_account
        self.persist = persist or (lambda paths: None)
        self.refresh = refresh or (lambda: None)
        self.lock = threading.Lock()

    def model(self):
        awaiting = self.research_queue.list_tasks(status="awaiting_owner")
        proposals = [
            proposal
            for proposal in self.paper_account.proposals()
            if proposal["status"] in {"pending", "approved"}
        ] if self.paper_account.account_file.exists() else []
        return {
            "enabled": True,
            "boundary": "Owner only; simulation and research decisions",
            "research_reviews": [
                {
                    "id": task["id"],
                    "role": task.get("role"),
                    "priority": task.get("priority"),
                    "subject": task.get("subject"),
                    "result": task.get("result", {}),
                }
                for task in self.research_queue._sorted_tasks(awaiting)
            ],
            "paper_proposals": [
                {
                    "proposal_id": item["proposal_id"],
                    "status": item["status"],
                    "side": item["side"],
                    "ticker": item["ticker"],
                    "shares": item["shares"],
                    "reference_price": item["price"],
                    "thesis": item["thesis"],
                    "risk_review": item.get("risk_review"),
                }
                for item in proposals
            ],
            "capabilities": {
                "research_decisions": True,
                "paper_proposal_decisions": True,
                "simulated_fills": True,
                "real_trading": False,
                "brokerage_connection": False,
            },
        }

    def apply(self, action, payload):
        action = str(action).strip()
        if not isinstance(payload, dict):
            raise ValueError("JSON object is required")
        with self.lock:
            self.refresh()
            paths = self._affected_paths(action)
            before = self._snapshot(paths)
            try:
                if action == "research-decision":
                    result = self._research_decision(payload)
                elif action == "paper-decision":
                    result = self._paper_decision(payload)
                elif action == "paper-fill":
                    result = self._paper_fill(payload)
                else:
                    raise ValueError("Unknown owner action")
                self.persist(paths)
                return result
            except Exception:
                self._restore(before)
                raise

    def _research_decision(self, payload):
        task_id = self._required(payload.get("task_id"), "task_id")
        decision = self._required(payload.get("decision"), "decision").lower()
        if decision not in VALID_RESEARCH_DECISIONS:
            raise ValueError("Invalid research decision")
        task = self.research_queue.record_owner_decision(
            task_id,
            decision,
            notes=payload.get("notes"),
        )
        self.research_queue.save_review_outputs()
        return {
            "action": "research-decision",
            "task_id": task_id,
            "decision": decision,
            "status": task["status"],
        }

    def _paper_decision(self, payload):
        proposal_id = self._required(
            payload.get("proposal_id"),
            "proposal_id",
        )
        decision = self._required(payload.get("decision"), "decision").lower()
        if decision not in VALID_PAPER_DECISIONS:
            raise ValueError("Invalid paper decision")
        event = self.paper_account.decide_proposal(
            proposal_id,
            decision,
            notes=payload.get("notes"),
        )
        self.paper_account.save_performance_report()
        return {
            "action": "paper-decision",
            "proposal_id": proposal_id,
            "decision": event["decision"],
            "status": self.paper_account.proposal_status(proposal_id),
        }

    def _paper_fill(self, payload):
        proposal_id = self._required(
            payload.get("proposal_id"),
            "proposal_id",
        )
        confirmation = self._required(
            payload.get("confirmation"),
            "confirmation",
        )
        if confirmation != f"SIMULATE {proposal_id}":
            raise ValueError(
                f"Confirmation must be SIMULATE {proposal_id}"
            )
        proposal = next(
            (
                item
                for item in self.paper_account.proposals()
                if item["proposal_id"] == proposal_id
            ),
            None,
        )
        if proposal is None:
            raise ValueError("Paper proposal not found")
        snapshot = self.dashboard_service._latest_snapshot()
        security = snapshot.get("securities", {}).get(proposal["ticker"], {})
        current_price = security.get("price")
        if current_price is None:
            raise ValueError("Current market price is unavailable")
        event = self.paper_account.execute_order(
            proposal["side"],
            proposal["ticker"],
            proposal["shares"],
            current_price,
            proposal["thesis"],
            source="owner_cloud",
            recommendation_id=proposal.get("recommendation_id"),
            proposal_id=proposal_id,
        )
        self.paper_account.save_performance_report()
        return {
            "action": "paper-fill",
            "proposal_id": proposal_id,
            "trade_id": event["trade_id"],
            "ticker": event["ticker"],
            "side": event["side"],
            "shares": event["shares"],
            "price": event["price"],
            "simulation_only": True,
        }

    def _affected_paths(self, action):
        if action == "research-decision":
            return [self.research_queue.task_file, *self._research_outputs()]
        if action in {"paper-decision", "paper-fill"}:
            return [
                self.paper_account.account_file,
                self.paper_account.ledger_file,
                self.paper_account.account_file.parent / "performance.md",
            ]
        return []

    def _research_outputs(self):
        root = self.research_queue.task_file.parent
        return [
            root / "agenda.md",
            root / "owner_review.md",
            *[
                root / name
                for name in (
                    "ceo_brief.md",
                    "cio_brief.md",
                    "cro_brief.md",
                    "reporting_brief.md",
                    "sector_analyst_brief.md",
                )
            ],
        ]

    @staticmethod
    def _snapshot(paths):
        return {
            Path(path): Path(path).read_bytes() if Path(path).exists() else None
            for path in paths
        }

    @staticmethod
    def _restore(snapshot):
        for path, body in snapshot.items():
            if body is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)

    @staticmethod
    def _required(value, label):
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError(f"{label} is required")
        return normalized
