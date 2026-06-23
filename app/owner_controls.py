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
        ranked_reviews = self._rank_research_reviews(awaiting)
        action_context = self._action_context()
        proposals = [
            proposal
            for proposal in self.paper_account.proposals()
            if proposal["status"] in {"pending", "approved"}
        ] if self.paper_account.account_file.exists() else []
        return {
            "enabled": True,
            "boundary": "Owner only; simulation and research decisions",
            "daily_action_list": self._daily_action_list(
                ranked_reviews,
                action_context,
            ),
            "research_reviews": ranked_reviews,
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

    def _rank_research_reviews(self, tasks):
        reviews = []
        for task in self.research_queue._sorted_tasks(tasks):
            attention = self._attention_score(task)
            reviews.append(
                {
                    "id": task["id"],
                    "role": task.get("role"),
                    "priority": task.get("priority"),
                    "subject": task.get("subject"),
                    "result": task.get("result", {}),
                    "source": task.get("source"),
                    "attention_score": attention["score"],
                    "attention_label": attention["label"],
                    "attention_reasons": attention["reasons"],
                }
            )
        return sorted(
            reviews,
            key=lambda item: (-item["attention_score"], item.get("subject") or ""),
        )

    def _daily_action_list(self, ranked_reviews, action_context=None, limit=3):
        action_context = action_context or {}
        actions = []
        for review in ranked_reviews[:limit]:
            result = review.get("result", {})
            subject = review.get("subject") or "Review"
            disposition = self._suggested_disposition(review)
            reasons = review.get("attention_reasons") or []
            reason_text = ", ".join(reasons[:3]) if reasons else "owner review"
            evidence_anchor = self._evidence_anchor(result)
            ticker_context = action_context.get("tickers", {}).get(subject, {})
            actions.append(
                {
                    "subject": subject,
                    "attention_score": review.get("attention_score", 0),
                    "attention_label": review.get("attention_label", "Low"),
                    "suggested_disposition": disposition,
                    "summary": (
                        f"{subject}: {disposition}. "
                        f"{reason_text}."
                    ),
                    "evidence_anchor": evidence_anchor,
                    "portfolio_context": ticker_context.get(
                        "portfolio_context",
                        action_context.get("default_portfolio_context", ""),
                    ),
                    "paper_context": ticker_context.get(
                        "paper_context",
                        action_context.get("default_paper_context", ""),
                    ),
                    "thesis_drift": result.get("thesis_drift"),
                    "thesis_alignment": result.get("thesis_alignment"),
                    "recommendation": result.get("recommendation"),
                }
            )
        return actions

    def _suggested_disposition(self, review):
        result = review.get("result", {})
        drift = result.get("thesis_drift")
        recommendation = result.get("recommendation")
        confidence = result.get("confidence")
        if drift == "recurring_risk":
            return "Review first; likely defer until risk is resolved"
        if drift == "new_risk":
            return "Review today and decide whether follow-up is needed"
        if recommendation == "research_further" or confidence == "low":
            return "Defer for more evidence"
        if result.get("thesis_alignment") == "supports_driver":
            return "Monitor for confirmation"
        if recommendation == "risk_review":
            return "Review risk before approving"
        return "Review when higher-priority items are handled"

    def _evidence_anchor(self, result):
        for item in result.get("evidence", []) or []:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    return text[:180]
                continue
            title = str(item.get("title") or "").strip()
            detail = str(item.get("detail") or "").strip()
            source = str(item.get("source") or "").strip()
            if title and detail:
                return f"{title}: {detail}"[:180]
            if title and source:
                return f"{title} ({source})"[:180]
            if title:
                return title[:180]
            if detail:
                return detail[:180]
        conclusion = str(result.get("conclusion") or "").strip()
        return conclusion[:180] if conclusion else ""

    def _action_context(self):
        if not self.paper_account.account_file.exists():
            return {
                "tickers": {},
                "default_portfolio_context": "No simulated paper account is initialized.",
                "default_paper_context": "Paper-performance context is not available yet.",
            }
        prices = self._latest_prices()
        try:
            status = self.paper_account.status(prices=prices)
        except ValueError:
            return {
                "tickers": {},
                "default_portfolio_context": "Paper account is unavailable.",
                "default_paper_context": "Paper-performance context is unavailable.",
            }
        performance = self.paper_account.performance_summary()
        reviews = self.paper_account.latest_position_reviews()
        equity = float(status.get("equity") or 0)
        ticker_context = {}
        for position in status.get("positions", []):
            ticker = position.get("ticker")
            if not ticker:
                continue
            portfolio_context = self._portfolio_context(position, equity)
            paper_context = self._paper_context(
                ticker,
                performance,
                reviews.get(ticker),
            )
            ticker_context[ticker] = {
                "portfolio_context": portfolio_context,
                "paper_context": paper_context,
            }
        return {
            "tickers": ticker_context,
            "default_portfolio_context": "No open simulated position is currently tracked.",
            "default_paper_context": self._paper_context(None, performance, None),
        }

    def _latest_prices(self):
        snapshot = self.dashboard_service._latest_snapshot()
        securities = snapshot.get("securities", {})
        return {
            ticker: data.get("price")
            for ticker, data in securities.items()
            if data.get("price") is not None
        }

    @staticmethod
    def _portfolio_context(position, equity):
        shares = float(position.get("shares") or 0)
        value = position.get("market_value")
        gain_loss = position.get("unrealized_gain_loss")
        allocation = (float(value) / equity * 100) if value is not None and equity else None
        pieces = [f"Simulated position: {shares:g} shares"]
        if value is not None:
            pieces.append(f"${float(value):,.2f} market value")
        if allocation is not None:
            pieces.append(f"{allocation:.1f}% of paper equity")
        if gain_loss is not None:
            pieces.append(f"{float(gain_loss):+,.2f} unrealized P/L")
        return "; ".join(pieces) + "."

    @staticmethod
    def _paper_context(ticker, performance, review):
        if not performance.get("available"):
            return "Paper-performance history is not available yet."
        latest = performance.get("latest", {})
        total_return = latest.get("total_return_pct")
        snapshots = performance.get("snapshots", 0)
        pieces = [
            (
                f"Paper account return {float(total_return):+.2f}%"
                if total_return is not None
                else "Paper account return unavailable"
            ),
            f"{snapshots} snapshot{'' if snapshots == 1 else 's'}",
        ]
        excess = performance.get("excess_return_pct", {})
        if excess:
            benchmark_bits = [
                f"{benchmark} excess {float(value):+.2f}%"
                for benchmark, value in sorted(excess.items())
            ]
            pieces.append(", ".join(benchmark_bits))
        if ticker and review:
            verdict = str(review.get("verdict") or "review").replace("_", " ")
            review_return = review.get("return_pct")
            review_text = f"latest {ticker} thesis review: {verdict}"
            if review_return is not None:
                review_text += f" at {float(review_return):+.2f}%"
            flags = review.get("flags") or []
            if flags:
                review_text += f" ({'; '.join(flags[:2])})"
            pieces.append(review_text)
        return "; ".join(pieces) + "."

    def _attention_score(self, task):
        result = task.get("result", {})
        score = 0
        reasons = []
        priority = task.get("priority")
        if priority == "high":
            score += 30
            reasons.append("high priority")
        elif priority == "medium":
            score += 15
            reasons.append("medium priority")
        recommendation = result.get("recommendation")
        if recommendation == "risk_review":
            score += 25
            reasons.append("risk review")
        elif recommendation == "watchlist_review":
            score += 18
            reasons.append("watchlist review")
        elif recommendation == "research_further":
            score += 12
            reasons.append("needs more research")
        elif recommendation == "monitor":
            score += 8
            reasons.append("monitor")
        drift = result.get("thesis_drift")
        if drift == "recurring_risk":
            score += 25
            reasons.append("recurring thesis risk")
        elif drift == "new_risk":
            score += 20
            reasons.append("new thesis risk")
        elif drift == "reinforcing_support":
            score += 12
            reasons.append("reinforcing support")
        elif drift == "new_support":
            score += 10
            reasons.append("new support signal")
        alignment = result.get("thesis_alignment")
        if alignment == "risk_to_thesis":
            score += 15
            reasons.append("risk to thesis")
        elif alignment == "supports_driver":
            score += 8
            reasons.append("supports key driver")
        catalyst = result.get("catalyst_type")
        if catalyst == "score_risk":
            score += 12
            reasons.append("score risk")
        elif catalyst in {"analyst_negative", "analyst_positive"}:
            score += 8
            reasons.append("analyst action")
        confidence = result.get("confidence")
        if confidence == "high":
            score += 5
        elif confidence == "low":
            score -= 5
        score = max(0, min(100, score))
        if score >= 80:
            label = "Urgent"
        elif score >= 55:
            label = "High"
        elif score >= 30:
            label = "Medium"
        else:
            label = "Low"
        return {
            "score": score,
            "label": label,
            "reasons": reasons[:4],
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
