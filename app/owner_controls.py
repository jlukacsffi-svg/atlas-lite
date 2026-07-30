"""Authenticated owner operations over existing Atlas private artifacts."""

from pathlib import Path
import threading

from app.decision_driver import infer_decision_driver


VALID_RESEARCH_DECISIONS = {"approve", "reject", "defer"}
VALID_PAPER_DECISIONS = {"approve", "reject"}
PAPER_POLICY_FIELDS = (
    "auto_manage_enabled",
    "strategy_minimum_buy_score",
    "strategy_maximum_exit_score",
    "strategy_target_position_pct",
    "strategy_maximum_new_proposals",
    "strategy_minimum_daily_move_pct",
    "strategy_benchmark_excess_weight",
    "strategy_trend_quality_weight",
    "strategy_sector_repeat_penalty",
)


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
        auto_manage_enabled = self._auto_manage_enabled()
        autonomous_research_cycle = self._run_research_autonomy_if_enabled(
            auto_manage_enabled
        )
        awaiting = self.research_queue.list_tasks(status="awaiting_owner")
        ranked_reviews = self._rank_research_reviews(awaiting)
        action_context = self._action_context()
        snapshot = self.dashboard_service._latest_snapshot()
        securities = snapshot.get("securities", {})
        latest_prices = self._latest_prices()
        autonomous_cycle = self._run_autonomous_cycle_if_enabled(
            latest_prices,
            auto_manage_enabled,
            securities,
        )
        self._persist_autonomous_updates(
            autonomous_research_cycle,
            autonomous_cycle,
        )
        position_shares = self._position_shares_with_prices(latest_prices)
        paper_feedback = (
            self.paper_account.proposal_feedback(latest_prices=latest_prices)
            if self.paper_account.account_file.exists()
            else []
        )
        proposals = [
            proposal
            for proposal in self.paper_account.proposals()
            if proposal["status"] in {"pending", "approved"}
        ] if self.paper_account.account_file.exists() else []
        proposal_models = [
            self._proposal_model(
                item,
                securities.get(item["ticker"], {}),
                position_shares,
                paper_feedback,
                auto_manage_enabled,
            )
            for item in proposals
        ]
        position_models = self._position_models(latest_prices, proposals)
        portfolio_action_queue = self._portfolio_action_queue(
            proposal_models,
            position_models,
            action_context,
        )
        healthy_holdings_summary = self._healthy_holdings_summary(
            position_models,
            action_context,
        )
        controls_summary = self._controls_summary(
            ranked_reviews,
            proposal_models,
            position_models,
        )
        portfolio_action_queue, healthy_holdings_summary = (
            self._apply_controls_freshness(
                portfolio_action_queue,
                healthy_holdings_summary,
                controls_summary,
            )
        )
        return {
            "enabled": True,
            "boundary": "Owner only; simulation and research decisions",
            "paper_strategy_policy": self._paper_strategy_policy(),
            "daily_action_list": self._daily_action_list(
                ranked_reviews,
                action_context,
            ),
            "portfolio_action_queue": portfolio_action_queue,
            "healthy_holdings_summary": healthy_holdings_summary,
            "controls_summary": controls_summary,
            "owner_outcomes": self._owner_outcomes(),
            "research_reviews": ranked_reviews,
            "paper_proposals": proposal_models,
            "paper_auto_manage_enabled": auto_manage_enabled,
            "research_auto_manage_enabled": auto_manage_enabled,
            "autonomous_cycle": autonomous_cycle,
            "autonomous_research_cycle": autonomous_research_cycle,
            "capabilities": {
                "research_decisions": not auto_manage_enabled,
                "paper_proposal_decisions": not auto_manage_enabled,
                "simulated_fills": not auto_manage_enabled,
                "real_trading": False,
                "brokerage_connection": False,
            },
        }

    def _paper_strategy_policy(self):
        if not self.paper_account.account_file.exists():
            return {
                "available": False,
                "headline": "Initialize the Atlas paper account before changing strategy policy.",
                "values": {},
                "adaptive_profiles": [],
            }
        account = self.paper_account.load()
        policy = dict(self.paper_account.policy)
        policy.update(account.get("policy", {}))
        latest_prices = self._latest_prices()
        entry_strategy = self.paper_account.entry_strategy_profile(
            latest_prices=latest_prices
        )
        trade_pressure = self.paper_account.trade_pressure_profile(
            latest_prices=latest_prices
        )
        benchmark_preference = self.paper_account.benchmark_preference_profile(
            latest_prices=latest_prices
        )
        values = {
            "auto_manage_enabled": bool(policy.get("auto_manage_enabled")),
            "strategy_minimum_buy_score": float(
                policy.get("strategy_minimum_buy_score", 88.0)
            ),
            "strategy_maximum_exit_score": float(
                policy.get("strategy_maximum_exit_score", 60.0)
            ),
            "strategy_target_position_pct": float(
                policy.get("strategy_target_position_pct", 5.0)
            ),
            "strategy_maximum_new_proposals": int(
                policy.get("strategy_maximum_new_proposals", 3)
            ),
            "strategy_minimum_daily_move_pct": float(
                policy.get("strategy_minimum_daily_move_pct", -8.0)
            ),
            "strategy_benchmark_excess_weight": float(
                policy.get("strategy_benchmark_excess_weight", 1.5)
            ),
            "strategy_trend_quality_weight": float(
                policy.get("strategy_trend_quality_weight", 0.2)
            ),
            "strategy_sector_repeat_penalty": float(
                policy.get("strategy_sector_repeat_penalty", 3.0)
            ),
        }
        return {
            "available": True,
            "headline": (
                "These settings change how aggressively Atlas opens, sizes, and "
                "diversifies autonomous paper trades."
            ),
            "values": values,
            "adaptive_profiles": self._strategy_adaptive_profiles(
                entry_strategy,
                trade_pressure,
                benchmark_preference,
            ),
        }

    @staticmethod
    def _strategy_adaptive_profiles(entry_strategy, trade_pressure, benchmark_preference):
        return [
            {
                "id": "trade_pressure",
                "label": "Adaptive trade pressure",
                "status": "active" if trade_pressure.get("active") else "watching",
                "value": str(
                    trade_pressure.get("policy_overrides", {}).get(
                        "maximum_daily_trades",
                        trade_pressure.get("baseline", {}).get(
                            "maximum_daily_trades", "--"
                        ),
                    )
                ),
                "detail": trade_pressure.get("headline")
                or "Atlas is monitoring how quickly it should turn the paper book.",
            },
            {
                "id": "benchmark_trust",
                "label": "Adaptive benchmark trust",
                "status": (
                    "active" if benchmark_preference.get("active") else "watching"
                ),
                "value": str(
                    benchmark_preference.get("strategy_overrides", {}).get(
                        "strategy_preferred_benchmark",
                        benchmark_preference.get("baseline", {}).get(
                            "strategy_preferred_benchmark", "auto"
                        ),
                    )
                ).upper(),
                "detail": benchmark_preference.get("headline")
                or "Atlas is monitoring which benchmark bar explains outcomes best.",
            },
            {
                "id": "entry_pacing",
                "label": "Adaptive entry pacing",
                "status": "active" if entry_strategy.get("active") else "watching",
                "value": str(
                    entry_strategy.get("strategy_overrides", {}).get(
                        "strategy_target_position_pct",
                        entry_strategy.get("baseline", {}).get(
                            "strategy_target_position_pct", "--"
                        ),
                    )
                ),
                "detail": entry_strategy.get("headline")
                or "Atlas is monitoring how aggressively it should rotate capital into new paper ideas.",
            },
        ]

    def _position_shares(self):
        return self._position_shares_with_prices(self._latest_prices())

    def _auto_manage_enabled(self):
        if not self.paper_account.account_file.exists():
            return False
        try:
            return self.paper_account.auto_manage_enabled()
        except ValueError:
            return False

    def _run_autonomous_cycle_if_enabled(
        self,
        latest_prices,
        auto_manage_enabled,
        market_data,
    ):
        if not auto_manage_enabled or not self.paper_account.account_file.exists():
            return {"enabled": False}
        cycle = self.paper_account.run_autonomous_cycle(
            latest_prices=latest_prices,
            source="owner_controls_auto_manage",
            market_data=market_data,
        )
        self.paper_account.save_performance_report()
        return cycle

    def _run_research_autonomy_if_enabled(self, auto_manage_enabled):
        if not auto_manage_enabled:
            return {"enabled": False}
        resolved = []
        for task in self.research_queue.list_tasks(status="awaiting_owner"):
            self.research_queue.record_owner_decision(
                task["id"],
                "approve",
                notes=(
                    "Auto-managed Atlas mode accepted this research recommendation "
                    "without waiting for manual owner review."
                ),
            )
            resolved.append(task["id"])
        if resolved:
            self.research_queue.save_review_outputs()
        return {
            "enabled": True,
            "approved": resolved,
        }

    def _persist_autonomous_updates(self, research_cycle, paper_cycle):
        paths = []
        if (research_cycle.get("approved") or []) and self.research_queue.task_file.exists():
            paths.extend([self.research_queue.task_file, *self._research_outputs()])
        if (
            paper_cycle.get("approved")
            or paper_cycle.get("rejected")
            or paper_cycle.get("executed")
        ) and self.paper_account.account_file.exists():
            paths.extend(
                [
                    self.paper_account.account_file,
                    self.paper_account.ledger_file,
                    self.paper_account.account_file.parent / "performance.md",
                ]
            )
        if paths:
            self.persist(paths)

    def _proposal_model(
        self,
        proposal,
        security,
        position_shares,
        paper_feedback,
        auto_manage_enabled=False,
    ):
        paper_calibration = self._paper_proposal_calibration(
            proposal,
            paper_feedback,
            position_shares,
        )
        research_context = self._latest_research_context(proposal.get("ticker"))
        sell_trigger_summary = ""
        sell_trigger_reasons = []
        if str(proposal.get("side") or "").lower() == "sell":
            sell_trigger_summary, sell_trigger_reasons = self._sell_trigger_context(
                proposal,
                security,
                position_shares,
                paper_calibration,
                research_context=research_context,
            )
        return {
            "proposal_id": proposal["proposal_id"],
            "status": proposal["status"],
            "side": proposal["side"],
            "ticker": proposal["ticker"],
            "timestamp": proposal.get("timestamp"),
            "updated_at": self._proposal_updated_at(proposal["proposal_id"]),
            "shares": proposal["shares"],
            "reference_price": proposal["price"],
            "thesis": proposal["thesis"],
            "rationale": self._proposal_rationale(
                proposal,
                security,
                position_shares,
                paper_calibration,
            ),
            "objections": self._proposal_objections(
                proposal,
                security,
                position_shares,
                paper_calibration,
            ),
            "risk_review": proposal.get("risk_review"),
            "position_shares": position_shares.get(proposal["ticker"], 0.0),
            "action_label": self._proposal_action_label(
                proposal,
                position_shares,
            ),
            "news_summary": self._news_signal_summary(security),
            "paper_calibration": paper_calibration,
            "auto_manage_enabled": bool(auto_manage_enabled),
            "decision_driver": self._proposal_decision_driver(proposal),
            "sell_trigger_summary": sell_trigger_summary,
            "sell_trigger_reasons": sell_trigger_reasons,
        }

    def _position_shares_with_prices(self, prices):
        if not self.paper_account.account_file.exists():
            return {}
        try:
            status = self.paper_account.status(prices=prices)
        except ValueError:
            return {}
        return {
            position.get("ticker"): float(position.get("shares") or 0)
            for position in status.get("positions", [])
            if position.get("ticker")
        }

    def _proposal_decision_driver(self, proposal):
        texts = list(proposal.get("rationale") or [])
        review = proposal.get("risk_review") or {}
        texts.extend(review.get("flags") or [])
        thesis = str(proposal.get("thesis") or "").strip()
        if thesis:
            texts.append(thesis)
        return self._decision_driver(
            texts,
            side=proposal.get("side"),
            action_label=proposal.get("action_label"),
        )

    def _position_decision_driver(self, review, thesis_status):
        review = review or {}
        texts = list(review.get("flags") or [])
        thesis = str(review.get("thesis") or "").strip()
        if thesis:
            texts.append(thesis)
        return self._decision_driver(
            texts,
            side="hold",
            action_label=(thesis_status or {}).get("label"),
        )

    @staticmethod
    def _decision_driver(texts, *, side="", action_label=""):
        return infer_decision_driver(
            texts,
            side=side,
            action_label=action_label,
        )

    @staticmethod
    def _proposal_action_label(proposal, position_shares):
        if proposal.get("side") != "sell":
            return "purchase"
        ticker = proposal.get("ticker")
        held = float(position_shares.get(ticker, 0.0) or 0.0)
        shares = float(proposal.get("shares") or 0.0)
        if held and shares < held:
            return "trim"
        if held:
            return "exit"
        return "sell"

    def _position_models(self, latest_prices, proposals):
        if not self.paper_account.account_file.exists():
            return []
        try:
            status = self.paper_account.status(prices=latest_prices)
        except ValueError:
            return []
        history = self.paper_account.performance_history()
        latest_reviews = self.paper_account.latest_position_reviews()
        securities = self.dashboard_service._latest_snapshot().get("securities", {})
        active_sell_proposals = {
            proposal["ticker"]: proposal
            for proposal in proposals
            if proposal.get("side") == "sell"
            and proposal.get("status") in {"pending", "approved"}
        }
        rows = []
        for position in status.get("positions", []):
            ticker = position.get("ticker")
            review = latest_reviews.get(ticker)
            active_sell = active_sell_proposals.get(ticker)
            thesis_status = self._position_thesis_status(position, review, active_sell)
            decision_driver = self._position_decision_driver(review, thesis_status)
            rows.append(
                {
                    "ticker": ticker,
                    "shares": float(position.get("shares") or 0.0),
                    "market_value": float(position.get("market_value") or 0.0),
                    "unrealized_gain_loss": float(
                        position.get("unrealized_gain_loss") or 0.0
                    ),
                    "review": review,
                    "thesis_status": thesis_status,
                    "decision_driver": decision_driver,
                    "decision_journal": self._position_decision_journal(
                        position,
                        review,
                        active_sell,
                        history,
                    ),
                    "news_summary": self._news_signal_summary(securities.get(ticker, {})),
                    "has_active_sell_proposal": bool(active_sell),
                }
            )
        return rows

    @staticmethod
    def _news_signal_summary(security):
        signal = (security or {}).get("news_signal") or {}
        label = str(signal.get("signal_label") or "").strip().lower()
        if not label:
            return None
        positive = int(signal.get("positive_count") or 0)
        negative = int(signal.get("negative_count") or 0)
        company_headlines = int(signal.get("company_headline_count") or 0)
        score = float(signal.get("signal_score") or 50.0)
        dominant_event = OwnerControlService._friendly_news_event(
            signal.get("dominant_event_type")
        )
        high_impact_negative = int(signal.get("high_impact_negative_count") or 0)
        high_impact_positive = int(signal.get("high_impact_positive_count") or 0)
        examples = []
        for text in signal.get("negative_examples") or []:
            cleaned = str(text).strip()
            if cleaned:
                examples.append(cleaned)
        if not examples:
            for text in signal.get("positive_examples") or []:
                cleaned = str(text).strip()
                if cleaned:
                    examples.append(cleaned)

        tone = label.replace("_", " ")
        headline = (
            f"News tone is {tone} with {positive} positive and {negative} negative "
            f"company headline{'s' if company_headlines != 1 else ''} in the latest scan."
        )
        detail = (
            f"Signal score {score:.0f} across {company_headlines} company-specific "
            f"headline{'s' if company_headlines != 1 else ''}."
        )
        event_detail = f"Main event read: {dominant_event}."
        if high_impact_negative > 0:
            event_detail += " Atlas currently treats this as high-impact downside news."
        elif high_impact_positive > 0:
            event_detail += " Atlas currently treats this as high-impact supportive news."
        return {
            "label": label,
            "headline": headline,
            "detail": detail,
            "event_detail": event_detail,
            "score": score,
            "positive_count": positive,
            "negative_count": negative,
            "company_headline_count": company_headlines,
            "dominant_event_type": str(signal.get("dominant_event_type") or "routine"),
            "example": examples[0] if examples else "",
        }

    @staticmethod
    def _friendly_news_event(value):
        text = str(value or "").strip().lower()
        if not text or text == "routine":
            return "routine mention"
        return text.replace("_", " ")

    def _position_decision_journal(self, position, review, active_sell, history):
        rows = []
        ticker = position.get("ticker") or "This holding"
        average_cost = position.get("average_cost")
        price = position.get("price")
        if average_cost is not None and price is not None:
            rows.append(
                f"Current basis is ${float(average_cost):,.2f} versus latest price ${float(price):,.2f}."
            )
        benchmark_line = self._position_benchmark_line(ticker, history, price)
        if benchmark_line:
            rows.append(benchmark_line)
        if review:
            flags = review.get("flags") or []
            verdict = str(review.get("verdict") or "maintain").replace("_", " ")
            review_date = self._friendly_timestamp(review.get("timestamp"))
            review_line = f"Latest thesis review ({review_date}): {verdict}."
            if flags:
                review_line += f" Main flag: {flags[0]}"
            rows.append(review_line)
        rows.append(self._position_escalation_line(position, review, active_sell))
        return rows[:4]

    def _position_benchmark_line(self, ticker, history, latest_price):
        if latest_price is None:
            return ""
        entry_trade = self._latest_open_buy_trade(ticker)
        if not entry_trade:
            return ""
        start = self.paper_account._first_snapshot_after(
            history,
            entry_trade.get("timestamp"),
        )
        latest = history[-1] if history else None
        if not start or not latest or start.get("timestamp") == latest.get("timestamp"):
            return ""
        security_return = self.paper_account._pct_return(
            entry_trade.get("fill_price"),
            latest_price,
        )
        if security_return is None:
            return ""
        spy_return = self.paper_account._pct_return(
            start.get("benchmark_prices", {}).get("SPY"),
            latest.get("benchmark_prices", {}).get("SPY"),
        )
        qqq_return = self.paper_account._pct_return(
            start.get("benchmark_prices", {}).get("QQQ"),
            latest.get("benchmark_prices", {}).get("QQQ"),
        )
        benchmarks = []
        if spy_return is not None:
            benchmarks.append(f"SPY {spy_return:+.2f}%")
        if qqq_return is not None:
            benchmarks.append(f"QQQ {qqq_return:+.2f}%")
        if not benchmarks:
            return ""
        return (
            f"Since the latest buy fill, {ticker} is {security_return:+.2f}% versus "
            + " and ".join(benchmarks)
            + "."
        )

    def _latest_open_buy_trade(self, ticker):
        ticker = str(ticker or "").strip().upper()
        if not ticker:
            return None
        for trade in reversed(self.paper_account.trade_activity(limit=1000)):
            if str(trade.get("ticker") or "").strip().upper() != ticker:
                continue
            if str(trade.get("side") or "").lower() != "buy":
                continue
            return trade
        return None

    @staticmethod
    def _friendly_timestamp(value):
        text = str(value or "").strip()
        if not text:
            return "recently"
        return text.replace("T", " ")

    def _proposal_updated_at(self, proposal_id):
        proposal_id = str(proposal_id or "").strip()
        if not proposal_id:
            return ""
        latest = ""
        for event in self.paper_account.ledger():
            if event.get("proposal_id") != proposal_id:
                continue
            timestamp = str(event.get("timestamp") or "").strip()
            if timestamp and timestamp > latest:
                latest = timestamp
        return latest

    @staticmethod
    def _position_escalation_line(position, review, active_sell):
        ticker = position.get("ticker") or "This holding"
        if active_sell:
            shares = float(position.get("shares") or 0.0)
            sell_shares = float(active_sell.get("shares") or 0.0)
            if shares and sell_shares < shares:
                return (
                    f"Escalation state: Atlas already wants to trim {sell_shares:g} of {shares:g} simulated shares."
                )
            return "Escalation state: Atlas already has an exit path active for this holding."
        if review:
            verdict = str(review.get("verdict") or "").lower()
            if verdict == "exit":
                return f"Escalation cue: {ticker} has already crossed Atlas's exit threshold on the latest review."
            if verdict == "review":
                return (
                    "Escalation cue: move from hold toward trim or exit if the next thesis review repeats weakness or adds new risk flags."
                )
        return (
            "Escalation cue: stay in hold mode unless a future thesis review downgrades the position or Atlas opens a trim/exit proposal."
        )

    @staticmethod
    def _position_thesis_status(position, review, active_sell):
        shares = float(position.get("shares") or 0.0)
        if active_sell:
            sell_shares = float(active_sell.get("shares") or 0.0)
            if shares and sell_shares < shares:
                return {
                    "label": "trim",
                    "summary": (
                        f"Atlas has an active simulated trim proposal for "
                        f"{sell_shares:g} of {shares:g} shares."
                    ),
                }
            return {
                "label": "exit",
                "summary": "Atlas has an active simulated exit proposal for this holding.",
            }
        if not review:
            return {
                "label": "healthy",
                "summary": "Awaiting the next daily thesis review.",
            }
        verdict = str(review.get("verdict") or "maintain").lower()
        flags = review.get("flags") or []
        score = review.get("atlas_score")
        score_text = f" Atlas score {score:.1f}." if score is not None else ""
        if verdict == "exit":
            return {
                "label": "exit",
                "summary": (
                    (flags[0] if flags else "Atlas marked this holding for simulated exit.")
                    + score_text
                ).strip(),
            }
        if verdict == "review":
            return {
                "label": "watch",
                "summary": (
                    (flags[0] if flags else "Atlas wants a closer thesis review on this holding.")
                    + score_text
                ).strip(),
            }
        return {
            "label": "healthy",
            "summary": (
                (flags[0] if flags else "Latest thesis review remains constructive.")
                + score_text
            ).strip(),
        }

    def _rank_research_reviews(self, tasks):
        reviews = []
        for task in self.research_queue._sorted_tasks(tasks):
            attention = self._attention_score(task)
            calibration = self._outcome_calibration(task)
            calibrated_score = max(
                0,
                min(100, attention["score"] + calibration["adjustment"]),
            )
            reviews.append(
                {
                    "id": task["id"],
                    "role": task.get("role"),
                    "priority": task.get("priority"),
                    "subject": task.get("subject"),
                    "result": task.get("result", {}),
                    "source": task.get("source"),
                    "attention_score": calibrated_score,
                    "attention_label": self._attention_label(calibrated_score),
                    "attention_reasons": (
                        attention["reasons"] + calibration["reasons"]
                    )[:5],
                    "outcome_calibration": calibration,
                }
            )
        return sorted(
            reviews,
            key=lambda item: (-item["attention_score"], item.get("subject") or ""),
        )

    def _owner_outcomes(self, limit=5):
        tasks = [
            task
            for task in self.research_queue.load().get("tasks", [])
            if task.get("owner_decision")
        ]
        decision_counts = {decision: 0 for decision in sorted(VALID_RESEARCH_DECISIONS)}
        recommendation_counts = {}
        recent = []
        for task in sorted(
            tasks,
            key=lambda item: item.get("owner_decision", {}).get("decided_at") or "",
            reverse=True,
        ):
            owner_decision = task.get("owner_decision", {})
            decision = owner_decision.get("decision")
            if decision in decision_counts:
                decision_counts[decision] += 1
            recommendation = task.get("result", {}).get("recommendation")
            if recommendation:
                recommendation_counts[recommendation] = (
                    recommendation_counts.get(recommendation, 0) + 1
                )
            if len(recent) < limit:
                recent.append(
                    {
                        "subject": task.get("subject"),
                        "decision": decision,
                        "recommendation": recommendation,
                        "decided_at": owner_decision.get("decided_at"),
                    }
                )
        total = sum(decision_counts.values())
        approved = decision_counts.get("approve", 0)
        approval_rate = (approved / total * 100) if total else None
        paper_statuses = self._paper_outcomes()
        return {
            "research_decisions": total,
            "research_decision_counts": decision_counts,
            "research_approval_rate_pct": (
                round(approval_rate, 1) if approval_rate is not None else None
            ),
            "recommendation_counts": recommendation_counts,
            "recent_research_decisions": recent,
            "paper_proposal_counts": paper_statuses,
            "learning_signal": self._learning_signal(
                decision_counts,
                recommendation_counts,
                paper_statuses,
            ),
        }

    def _paper_outcomes(self):
        counts = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "executed": 0,
        }
        if not self.paper_account.account_file.exists():
            return counts
        for proposal in self.paper_account.proposals():
            status = proposal.get("status")
            if status in counts:
                counts[status] += 1
        return counts

    @staticmethod
    def _learning_signal(decision_counts, recommendation_counts, paper_statuses):
        total = sum(decision_counts.values())
        if not total:
            return "No owner outcome history yet. Atlas will learn from future approvals, deferrals, and rejections."
        deferred = decision_counts.get("defer", 0)
        rejected = decision_counts.get("reject", 0)
        approved = decision_counts.get("approve", 0)
        if deferred > approved and deferred >= rejected:
            return "Owner decisions currently favor deferring for more evidence."
        if rejected > approved:
            return "Owner decisions currently challenge more recommendations than they approve."
        if paper_statuses.get("executed", 0):
            return "Owner-approved research has reached simulated paper execution; continue comparing outcomes against the audit trail."
        return "Owner decisions currently favor approval, but Atlas still needs more outcome history before increasing confidence."

    def _outcome_calibration(self, task):
        """Conservatively tune attention from prior owner outcomes."""
        result = task.get("result", {})
        recommendation = result.get("recommendation")
        subject = str(task.get("subject") or "").strip().upper()
        adjustment = 0
        reasons = []
        if subject:
            history = self.research_queue.thesis_history_summary(subject)
            counts = (history or {}).get("decision_counts", {})
            reviewed = sum(counts.values())
            if reviewed >= 2:
                deferred = counts.get("defer", 0)
                rejected = counts.get("reject", 0)
                approved = counts.get("approve", 0)
                if deferred + rejected > approved:
                    adjustment -= 8
                    reasons.append("owner history: prior caution for this ticker")
                elif approved >= 2 and result.get("recommendation") == "risk_review":
                    adjustment += 4
                    reasons.append("owner history: prior risk reviews approved")

        recommendation_counts = self._recommendation_decision_counts(recommendation)
        total = sum(recommendation_counts.values())
        if total >= 3:
            approved = recommendation_counts.get("approve", 0)
            deferred = recommendation_counts.get("defer", 0)
            rejected = recommendation_counts.get("reject", 0)
            if deferred + rejected > approved:
                adjustment -= 6
                reasons.append("owner history: similar recommendations need caution")
            elif approved >= 2 and approved > deferred + rejected:
                adjustment += 3
                reasons.append("owner history: similar recommendations often approved")

        adjustment = max(-12, min(6, adjustment))
        return {
            "adjustment": adjustment,
            "reasons": reasons,
        }

    def _paper_proposal_calibration(self, proposal, feedback_rows, position_shares):
        side = str(proposal.get("side") or "buy").lower()
        if side not in {"buy", "sell"}:
            side = "buy"
        ticker = str(proposal.get("ticker") or "").strip().upper()
        action_label = self._proposal_action_label(proposal, position_shares)
        judged_rows = [
            row
            for row in feedback_rows
            if row.get("side") == side and row.get("verdict") != "not_enough_time"
        ]
        ticker_rows = [
            row
            for row in judged_rows
            if str(row.get("ticker") or "").strip().upper() == ticker
            and (
                side != "sell"
                or str(row.get("action_label") or "").strip().lower() == action_label
            )
        ]
        working = sum(1 for row in judged_rows if row.get("verdict") == "working")
        lagging = sum(1 for row in judged_rows if row.get("verdict") == "lagging")
        adjustment = 0
        reasons = []
        label = "neutral"

        if len(judged_rows) >= 2:
            if working > lagging:
                adjustment += 4
                label = "supportive"
                reasons.append(
                    f"recent simulated {self._paper_side_label(side, action_label)} are working more often than lagging"
                )
            elif lagging > working:
                adjustment -= 6
                label = "caution"
                reasons.append(
                    f"recent simulated {self._paper_side_label(side, action_label)} are lagging more often than working"
                )

        if ticker_rows:
            latest = sorted(
                ticker_rows,
                key=lambda row: row.get("filled_at") or "",
                reverse=True,
            )[0]
            if latest.get("verdict") == "working":
                adjustment += 3
                if adjustment >= 0:
                    label = "supportive"
                reasons.append(
                    f"latest judged {ticker} {self._paper_side_label(side, action_label)} outcome was working"
                )
            elif latest.get("verdict") == "lagging":
                adjustment -= 4
                label = "caution"
                reasons.append(
                    f"latest judged {ticker} {self._paper_side_label(side, action_label)} outcome was lagging"
                )

            persistence_rows = [
                item
                for item in (latest.get("horizon_outcomes") or [])
                if item.get("available") and int(item.get("snapshots") or 0) == 3
            ]
            if persistence_rows:
                persistence = persistence_rows[0]
                persistence_verdict = str(
                    persistence.get("verdict") or ""
                ).strip().lower()
                if persistence_verdict == "working":
                    adjustment += 2
                    if adjustment >= 0:
                        label = "supportive"
                    reasons.append(
                        f"latest judged {ticker} {self._paper_side_label(side, action_label)} 3-snapshot persistence stayed working"
                    )
                elif persistence_verdict == "lagging":
                    adjustment -= 3
                    label = "caution"
                    reasons.append(
                        f"latest judged {ticker} {self._paper_side_label(side, action_label)} 3-snapshot persistence stayed lagging"
                    )

        if not judged_rows:
            summary = "Atlas does not have enough judged simulated outcomes yet for this proposal type."
        elif adjustment > 0:
            summary = "Recent paper-learning history is supportive of this proposal type."
        elif adjustment < 0:
            summary = "Recent paper-learning history suggests extra caution for this proposal type."
        else:
            summary = "Recent paper-learning history is mixed for this proposal type."

        return {
            "adjustment": max(-10, min(7, adjustment)),
            "label": label,
            "judged": len(judged_rows),
            "ticker_judged": len(ticker_rows),
            "reasons": reasons[:3],
            "summary": summary,
        }

    def _proposal_rationale(
        self,
        proposal,
        security,
        position_shares,
        paper_calibration,
    ):
        rows = [item for item in proposal.get("rationale", []) if str(item).strip()]
        if rows:
            return rows
        if str(proposal.get("side") or "").lower() == "sell":
            return self._legacy_sell_rationale(
                proposal,
                security,
                position_shares,
                paper_calibration,
            )
        return self._legacy_buy_rationale(proposal, security, paper_calibration)

    def _proposal_objections(
        self,
        proposal,
        security,
        position_shares,
        paper_calibration,
    ):
        side = str(proposal.get("side") or "").lower()
        research_context = self._latest_research_context(proposal.get("ticker"))
        if side == "sell":
            return self._sell_objections(
                proposal,
                security,
                position_shares,
                paper_calibration,
                research_context,
            )
        return self._buy_objections(
            proposal,
            security,
            paper_calibration,
            research_context,
        )

    def _legacy_buy_rationale(self, proposal, security, paper_calibration):
        ticker = str(proposal.get("ticker") or "This security")
        price = security.get("price")
        score = security.get("total_score")
        category = security.get("category") or "Watchlist"
        sector = security.get("sector") or "Unclassified"
        move = security.get("percent_change")
        rows = []
        if score is not None:
            rows.append(
                f"Atlas score {float(score):.1f} keeps {ticker} in the {category} category within {sector}."
            )
        else:
            rows.append(
                f"{ticker} remains tracked in the {category} category within {sector}."
            )
        strongest = self._strongest_score_inputs(security.get("scores"))
        if strongest:
            rows.append(
                "Strongest score inputs: "
                + ", ".join(f"{name} {value:.0f}" for name, value in strongest)
                + "."
            )
        if price is not None and move is not None:
            rows.append(
                f"Latest market read is ${float(price):,.2f} with a {float(move):+.2f}% move, so Atlas still sees a valid paper entry setup."
            )
        elif move is not None:
            rows.append(
                f"Latest market move is {float(move):+.2f}%, which keeps the paper setup active."
            )
        sizing = self._proposal_sizing_context(proposal)
        if sizing:
            rows.append(sizing)
        calibration_reason = self._calibration_reason_text(paper_calibration)
        if calibration_reason:
            rows.append(calibration_reason)
        return rows[:4]

    def _buy_objections(
        self,
        proposal,
        security,
        paper_calibration,
        research_context=None,
    ):
        ticker = str(proposal.get("ticker") or "This security")
        rows = []
        review = proposal.get("risk_review") or {}
        flags = [str(flag).strip() for flag in review.get("flags") or [] if str(flag).strip()]
        move = security.get("percent_change")
        category = security.get("category") or "Watchlist"
        score = security.get("total_score")
        memory_rows = self._research_memory_objections(
            ticker,
            research_context,
            include_history_count=False,
        )
        history_row = self._research_history_count_objection(ticker)
        rows.extend(memory_rows)

        if flags:
            rows.append("Risk review flags: " + ", ".join(flags[:2]) + ".")
        elif review.get("verdict") == "caution":
            rows.append("Risk review is cautionary, so this idea still needs extra skepticism.")

        if move is not None and float(move) <= 0:
            rows.append(
                f"Latest move is {float(move):+.2f}%, so momentum confirmation is not yet strong."
            )
        if score is not None and float(score) < 90:
            rows.append(
                f"Atlas score {float(score):.1f} is investable, but not yet in Atlas's highest-conviction tier."
            )
        if category != "Core" and not memory_rows:
            rows.append(
                f"{ticker} is still categorized as {category}, which means Atlas has not promoted it to a core-conviction name."
            )

        calibration = self._calibration_caution_text(paper_calibration)
        if calibration:
            rows.append(calibration)
        if history_row and len(rows) < 4:
            rows.append(history_row)
        return rows[:4]

    def _legacy_sell_rationale(
        self,
        proposal,
        security,
        position_shares,
        paper_calibration,
    ):
        ticker = str(proposal.get("ticker") or "This position")
        action_label = self._proposal_action_label(proposal, position_shares)
        held = float(position_shares.get(ticker, 0.0) or 0.0)
        shares = float(proposal.get("shares") or 0.0)
        category = security.get("category") or "Watchlist"
        score = security.get("total_score")
        move = security.get("percent_change")
        review = proposal.get("risk_review") or {}
        flags = [str(flag).strip() for flag in review.get("flags") or [] if str(flag).strip()]
        rows = []
        if action_label == "trim" and held:
            rows.append(
                f"Atlas is proposing a trim of {shares:g} out of {held:g} simulated {ticker} shares to reduce paper exposure without closing the position."
            )
        elif action_label == "exit" and held:
            rows.append(
                f"Atlas is proposing an exit of the full simulated {ticker} position after the latest risk review."
            )
        else:
            rows.append(
                f"Atlas is reviewing {ticker} for a simulated {action_label} based on current risk-monitoring signals."
            )
        if score is not None and move is not None:
            rows.append(
                f"Current read: Atlas score {float(score):.1f}, category {category}, and latest move {float(move):+.2f}%."
            )
        elif score is not None:
            rows.append(f"Current read: Atlas score {float(score):.1f} and category {category}.")
        elif move is not None:
            rows.append(f"Current read: category {category} with a {float(move):+.2f}% latest move.")
        if flags:
            rows.append("Risk review flags: " + ", ".join(flags[:3]) + ".")
        elif review.get("verdict"):
            rows.append(
                f"Risk review verdict is {str(review.get('verdict')).replace('_', ' ')}."
            )
        calibration_reason = self._calibration_reason_text(paper_calibration)
        if calibration_reason:
            rows.append(calibration_reason)
        return rows[:4]

    def _sell_trigger_context(
        self,
        proposal,
        security,
        position_shares,
        paper_calibration,
        research_context=None,
    ):
        ticker = str(proposal.get("ticker") or "This position")
        action_label = self._proposal_action_label(proposal, position_shares)
        review = proposal.get("risk_review") or {}
        flags = [
            str(flag).strip()
            for flag in review.get("flags") or []
            if str(flag).strip()
        ]
        score = security.get("total_score")
        move = security.get("percent_change")
        reasons = []
        if research_context and research_context.get("thesis_alignment") == "risk_to_thesis":
            reasons.append(
                f"Latest Atlas research tagged {ticker} as risk to thesis."
            )
        if flags:
            reasons.append("Risk review flags: " + ", ".join(flags[:2]) + ".")
        if score is not None:
            reasons.append(
                f"Atlas score is now {float(score):.1f}, which keeps this holding in active thesis review."
            )
        if move is not None and float(move) < 0:
            reasons.append(
                f"Latest move is {float(move):+.2f}%, which supports a more defensive posture."
            )
        calibration_summary = str((paper_calibration or {}).get("summary") or "").strip()
        if calibration_summary:
            reasons.append("Paper learning: " + calibration_summary)

        if action_label == "trim":
            summary = (
                "Trim trigger: Atlas sees enough thesis or confirmation weakness to reduce exposure, "
                "but not enough to close the simulated position entirely."
            )
        else:
            summary = (
                "Exit trigger: Atlas sees enough thesis or confirmation weakness to close the simulated "
                "position rather than keep partial exposure."
            )
        return summary, reasons[:4]

    def _sell_objections(
        self,
        proposal,
        security,
        position_shares,
        paper_calibration,
        research_context=None,
    ):
        ticker = str(proposal.get("ticker") or "This position")
        action_label = self._proposal_action_label(proposal, position_shares)
        held = float(position_shares.get(ticker, 0.0) or 0.0)
        shares = float(proposal.get("shares") or 0.0)
        move = security.get("percent_change")
        review = proposal.get("risk_review") or {}
        flags = [str(flag).strip() for flag in review.get("flags") or [] if str(flag).strip()]
        rows = self._research_memory_objections(
            ticker,
            research_context,
            include_history_count=False,
        )
        history_row = self._research_history_count_objection(ticker)

        if move is not None and float(move) > 0:
            rows.append(
                f"Latest move is {float(move):+.2f}%, so trimming or exiting now could surrender further upside if the thesis stabilizes."
            )
        if action_label == "trim" and held and shares < held:
            rows.append(
                f"A trim would still leave {max(held - shares, 0):g} simulated shares exposed if the thesis keeps weakening."
            )
        elif action_label == "exit" and held:
            rows.append(
                "A full exit removes exposure completely, so Atlas needs to be right about the thesis deterioration."
            )
        if flags:
            rows.append("Exit case depends on risk flags: " + ", ".join(flags[:2]) + ".")
        calibration = self._calibration_caution_text(paper_calibration)
        if calibration:
            rows.append(calibration)
        if history_row and len(rows) < 4:
            rows.append(history_row)
        return rows[:4]

    def _latest_research_context(self, ticker):
        ticker = str(ticker or "").strip().upper()
        if not ticker:
            return None
        latest = None
        for task in reversed(self.research_queue.load().get("tasks", [])):
            if str(task.get("subject") or "").strip().upper() != ticker:
                continue
            if not task.get("result"):
                continue
            latest = task
            break
        if not latest:
            return None
        result = latest.get("result", {})
        evidence_titles = []
        for item in result.get("evidence", []) or []:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    evidence_titles.append(text[:90])
            else:
                title = str(item.get("title") or item.get("detail") or "").strip()
                if title:
                    evidence_titles.append(title[:90])
        return {
            "catalyst_type": result.get("catalyst_type"),
            "thesis_alignment": result.get("thesis_alignment"),
            "thesis_drift": result.get("thesis_drift"),
            "evidence_titles": evidence_titles[:2],
        }

    def _research_memory_objections(self, ticker, research_context, include_history_count=True):
        rows = []
        if research_context:
            if research_context.get("thesis_alignment") == "risk_to_thesis":
                catalyst = str(research_context.get("catalyst_type") or "recent review").replace("_", " ")
                rows.append(
                    f"Latest stored Atlas review tagged {ticker} as risk to thesis via {catalyst} after a prior risk-to-thesis review."
                )
            evidence_titles = research_context.get("evidence_titles") or []
            if evidence_titles:
                rows.append(
                    "Recent disconfirming evidence: " + ", ".join(evidence_titles[:2]) + "."
                )
        if include_history_count:
            history_row = self._research_history_count_objection(ticker)
            if history_row:
                rows.append(history_row)
        return rows

    def _research_history_count_objection(self, ticker):
        history = self.research_queue.thesis_history_summary(ticker)
        if history and history.get("risk_to_thesis_count"):
            count = int(history["risk_to_thesis_count"])
            return (
                f"Atlas research memory shows {count} prior risk-to-thesis review"
                f"{'s' if count != 1 else ''} for {ticker}."
            )
        return ""

    def _proposal_sizing_context(self, proposal):
        if not self.paper_account.account_file.exists():
            return ""
        try:
            account = self.paper_account.load()
        except ValueError:
            return ""
        starting_cash = float(account.get("starting_cash") or 0.0)
        shares = float(proposal.get("shares") or 0.0)
        price = float(proposal.get("price") or 0.0)
        notional = shares * price
        if not starting_cash or not notional:
            return ""
        allocation = notional / starting_cash * 100
        return (
            f"Suggested size is {shares:g} shares, or about ${notional:,.2f} ({allocation:.1f}% of starting simulated cash)."
        )

    @staticmethod
    def _strongest_score_inputs(scores):
        if not isinstance(scores, dict):
            return []
        return sorted(
            (
                (str(name), float(value))
                for name, value in scores.items()
                if value is not None
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:2]

    @staticmethod
    def _calibration_reason_text(paper_calibration):
        reasons = paper_calibration.get("reasons") or []
        if reasons:
            reason = str(reasons[0]).strip()
            if reason:
                return "Paper learning context: " + reason[:1].upper() + reason[1:] + "."
        summary = str(paper_calibration.get("summary") or "").strip()
        return f"Paper learning context: {summary}" if summary else ""

    @staticmethod
    def _calibration_caution_text(paper_calibration):
        judged = int(paper_calibration.get("judged") or 0)
        adjustment = float(paper_calibration.get("adjustment") or 0)
        summary = str(paper_calibration.get("summary") or "").strip()
        if adjustment < 0 and summary:
            return f"Paper-learning caution: {summary}"
        if judged == 0:
            return "Paper-learning caution: Atlas still lacks enough judged simulated outcomes for this setup."
        if judged < 3:
            return f"Paper-learning caution: only {judged} judged simulated outcome{'s' if judged != 1 else ''} support this setup so far."
        return ""

    @staticmethod
    def _paper_side_label(side, action_label):
        if side == "sell":
            return action_label if action_label in {"trim", "exit"} else "sell decisions"
        return "buy ideas"

    def _recommendation_decision_counts(self, recommendation):
        counts = {decision: 0 for decision in sorted(VALID_RESEARCH_DECISIONS)}
        if not recommendation:
            return counts
        for task in self.research_queue.load().get("tasks", []):
            if task.get("status") == "awaiting_owner":
                continue
            if task.get("result", {}).get("recommendation") != recommendation:
                continue
            decision = task.get("owner_decision", {}).get("decision")
            if decision in counts:
                counts[decision] += 1
        return counts

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
                    "outcome_calibration": review.get("outcome_calibration", {}),
                    "thesis_drift": result.get("thesis_drift"),
                    "thesis_alignment": result.get("thesis_alignment"),
                    "recommendation": result.get("recommendation"),
                }
            )
        return actions

    def _portfolio_action_queue(
        self,
        proposal_models,
        position_models,
        action_context=None,
        limit=8,
    ):
        action_context = action_context or {}
        queue = []
        for proposal in proposal_models:
            ticker = str(proposal.get("ticker") or "")
            ticker_context = action_context.get("tickers", {}).get(ticker, {})
            queue.append(
                {
                    "kind": "proposal",
                    "kind_label": "Paper proposal",
                    "subject": ticker,
                    "title": self._proposal_queue_title(proposal),
                    "attention_score": self._proposal_action_score(proposal),
                    "attention_label": self._attention_label(
                        self._proposal_action_score(proposal)
                    ),
                    "summary": self._proposal_queue_summary(proposal),
                    "evidence_anchor": self._proposal_queue_evidence(proposal),
                    "portfolio_context": ticker_context.get(
                        "portfolio_context",
                        action_context.get("default_portfolio_context", ""),
                    ),
                    "paper_context": ticker_context.get(
                        "paper_context",
                        action_context.get("default_paper_context", ""),
                    ),
                    "decision_driver": proposal.get("decision_driver"),
                    "news_summary": proposal.get("news_summary") or {},
                    "next_step": self._proposal_queue_next_step(proposal),
                    "status_label": self._proposal_queue_status_label(proposal),
                    "anchor_id": self._controls_anchor_id("queue", ticker),
                }
            )

        for position in position_models:
            thesis = position.get("thesis_status") or {}
            label = thesis.get("label") or "healthy"
            if label == "healthy" or position.get("has_active_sell_proposal"):
                continue
            ticker = str(position.get("ticker") or "")
            ticker_context = action_context.get("tickers", {}).get(ticker, {})
            queue.append(
                {
                    "kind": "position",
                    "kind_label": "Open holding",
                    "subject": ticker,
                    "title": f"{ticker} open position",
                    "attention_score": self._position_action_score(position),
                    "attention_label": self._attention_label(
                        self._position_action_score(position)
                    ),
                    "summary": thesis.get("summary")
                    or "Atlas wants fresh attention on this simulated holding.",
                    "evidence_anchor": self._position_queue_evidence(position),
                    "portfolio_context": ticker_context.get(
                        "portfolio_context",
                        action_context.get("default_portfolio_context", ""),
                    ),
                    "paper_context": ticker_context.get(
                        "paper_context",
                        action_context.get("default_paper_context", ""),
                    ),
                    "decision_driver": position.get("decision_driver"),
                    "news_summary": position.get("news_summary") or {},
                    "next_step": self._position_queue_next_step(position),
                    "status_label": self._position_status_label(position),
                    "anchor_id": self._controls_anchor_id("queue", ticker),
                }
            )

        queue.sort(
            key=lambda item: (
                -float(item.get("attention_score") or 0),
                0 if item.get("kind") == "proposal" else 1,
                item.get("subject") or "",
            )
        )
        return queue[:limit]

    def _healthy_holdings_summary(
        self,
        position_models,
        action_context=None,
        limit=6,
    ):
        action_context = action_context or {}
        rows = []
        for position in position_models:
            thesis = position.get("thesis_status") or {}
            if str(thesis.get("label") or "").lower() != "healthy":
                continue
            ticker = str(position.get("ticker") or "")
            ticker_context = action_context.get("tickers", {}).get(ticker, {})
            rows.append(
                {
                    "ticker": ticker,
                    "summary": thesis.get("summary")
                    or "Latest thesis review remains constructive.",
                    "journal": list(position.get("decision_journal") or [])[:2],
                    "portfolio_context": ticker_context.get(
                        "portfolio_context",
                        action_context.get("default_portfolio_context", ""),
                    ),
                    "paper_context": ticker_context.get(
                        "paper_context",
                        action_context.get("default_paper_context", ""),
                    ),
                    "decision_driver": position.get("decision_driver"),
                    "news_summary": position.get("news_summary") or {},
                    "unrealized_gain_loss": float(
                        position.get("unrealized_gain_loss") or 0.0
                    ),
                    "market_value": float(position.get("market_value") or 0.0),
                    "anchor_id": self._controls_anchor_id("healthy", ticker),
                }
            )
        rows.sort(
            key=lambda item: (
                -float(item.get("market_value") or 0.0),
                item.get("ticker") or "",
            )
        )
        headline = (
            "No open simulated holdings are currently in hold-steady mode."
            if not rows
            else "These open simulated holdings remain healthy and are intentionally absent from the ranked action queue."
        )
        return {
            "count": len(rows),
            "headline": headline,
            "items": rows[:limit],
        }

    def _controls_summary(
        self,
        ranked_reviews,
        proposal_models,
        position_models,
    ):
        queue = self._portfolio_action_queue(
            proposal_models,
            position_models,
            {},
            limit=100,
        )
        healthy = self._healthy_holdings_summary(
            position_models,
            {},
            limit=100,
        )
        open_positions = len(position_models)
        buy_proposals = sum(1 for item in proposal_models if item.get("side") == "buy")
        sell_proposals = sum(1 for item in proposal_models if item.get("side") == "sell")
        research_reviews = len(ranked_reviews)
        queue_count = len(queue)
        healthy_count = int(healthy.get("count") or 0)
        freshest_change = self._controls_freshest_change(
            proposal_models,
            position_models,
        )

        if queue_count and healthy_count:
            headline = (
                f"Atlas is actively tracking {queue_count} action item"
                f"{'' if queue_count == 1 else 's'} while {healthy_count} holding"
                f"{'' if healthy_count == 1 else 's'} remain steady."
            )
        elif queue_count:
            headline = (
                f"Atlas is actively tracking {queue_count} action item"
                f"{'' if queue_count == 1 else 's'} across the current paper book."
            )
        elif healthy_count:
            headline = (
                f"No paper-book actions are currently ranked; {healthy_count} holding"
                f"{'' if healthy_count == 1 else 's'} remain steady."
            )
        else:
            headline = "No open paper positions or action items are currently tracked."

        if sell_proposals:
            posture = "Reduction paths are active in the paper workflow."
        elif buy_proposals:
            posture = "Paper workflow is currently entry-led."
        elif healthy_count:
            posture = "Current paper posture is mostly hold steady."
        else:
            posture = "Paper workflow is waiting for the next actionable signal."

        return {
            "headline": headline,
            "posture": posture,
            "counts": {
                "queue": queue_count,
                "healthy": healthy_count,
                "open_positions": open_positions,
                "research_reviews": research_reviews,
                "buy_proposals": buy_proposals,
                "sell_proposals": sell_proposals,
            },
            "freshest_change": freshest_change,
        }

    def _controls_freshest_change(self, proposal_models, position_models):
        candidates = []
        for proposal in proposal_models:
            timestamp = str(
                proposal.get("updated_at") or proposal.get("timestamp") or ""
            ).strip()
            if not timestamp:
                continue
            ticker = str(proposal.get("ticker") or "Proposal")
            status_label = self._proposal_queue_status_label(proposal)
            if proposal.get("side") == "sell":
                detail = (
                    f"{ticker} is the newest {status_label.lower()} in the ranked action queue."
                )
            else:
                detail = (
                    f"{ticker} is the newest {status_label.lower()} in the ranked action queue."
                )
            candidates.append(
                {
                    "bucket": "queue",
                    "bucket_label": "Portfolio action queue",
                    "timestamp": timestamp,
                    "subject": ticker,
                    "detail": detail,
                    "anchor_id": self._controls_anchor_id("queue", ticker),
                }
            )
        for position in position_models:
            thesis = position.get("thesis_status") or {}
            label = str(thesis.get("label") or "healthy").lower()
            review = position.get("review") or {}
            timestamp = str(review.get("timestamp") or "").strip()
            if not timestamp:
                continue
            ticker = str(position.get("ticker") or "Holding")
            if label == "healthy":
                detail = f"{ticker} was most recently reaffirmed as hold steady."
                bucket = {
                    "bucket": "healthy",
                    "bucket_label": "Hold-steady holdings",
                }
            elif position.get("has_active_sell_proposal"):
                continue
            else:
                detail = (
                    f"{ticker} most recently shifted into {self._position_status_label(position).lower()} review."
                )
                bucket = {
                    "bucket": "queue",
                    "bucket_label": "Portfolio action queue",
                }
            candidates.append(
                {
                    **bucket,
                    "timestamp": timestamp,
                    "subject": ticker,
                    "detail": detail,
                    "anchor_id": self._controls_anchor_id(bucket["bucket"], ticker),
                }
            )
        if not candidates:
            return {}
        latest = max(candidates, key=lambda item: item.get("timestamp") or "")
        return {
            **latest,
            "timestamp_label": self._friendly_timestamp(latest.get("timestamp")),
        }

    @staticmethod
    def _controls_anchor_id(bucket, subject):
        bucket = str(bucket or "").strip().lower() or "controls"
        subject = str(subject or "").strip().lower()
        safe_subject = "".join(
            char if char.isalnum() else "-"
            for char in subject
        ).strip("-") or "item"
        return f"controls-{bucket}-{safe_subject}"

    def _apply_controls_freshness(
        self,
        portfolio_action_queue,
        healthy_holdings_summary,
        controls_summary,
    ):
        freshest = controls_summary.get("freshest_change") or {}
        freshest_bucket = str(freshest.get("bucket") or "").strip().lower()
        freshest_subject = str(freshest.get("subject") or "").strip().upper()
        freshest_label = (
            f"Freshest shift as of {freshest.get('timestamp_label')}"
            if freshest.get("timestamp_label")
            else "Freshest shift"
        )
        queue = []
        for item in portfolio_action_queue:
            subject = str(item.get("subject") or "").strip().upper()
            is_freshest = (
                freshest_bucket == "queue"
                and freshest_subject
                and subject == freshest_subject
            )
            queue.append(
                {
                    **item,
                    "is_freshest_shift": is_freshest,
                    "freshness_label": freshest_label if is_freshest else "",
                }
            )
        items = []
        for item in healthy_holdings_summary.get("items", []):
            ticker = str(item.get("ticker") or "").strip().upper()
            is_freshest = (
                freshest_bucket == "healthy"
                and freshest_subject
                and ticker == freshest_subject
            )
            items.append(
                {
                    **item,
                    "is_freshest_shift": is_freshest,
                    "freshness_label": freshest_label if is_freshest else "",
                }
            )
        return queue, {
            **healthy_holdings_summary,
            "items": items,
        }

    def _proposal_action_score(self, proposal):
        side = str(proposal.get("side") or "buy").lower()
        status = str(proposal.get("status") or "pending").lower()
        action_label = str(proposal.get("action_label") or "purchase").lower()
        adjustment = float((proposal.get("paper_calibration") or {}).get("adjustment") or 0)
        if side == "sell":
            base = 90 if action_label == "exit" else 84
            if status == "approved":
                base += 4
        else:
            base = 76 if status == "approved" else 70
        return max(0, min(100, round(base + adjustment, 1)))

    def _proposal_queue_title(self, proposal):
        ticker = str(proposal.get("ticker") or "Proposal")
        action = self._proposal_queue_status_label(proposal)
        return f"{ticker} {action.lower()}"

    @staticmethod
    def _proposal_queue_status_label(proposal):
        if proposal.get("auto_manage_enabled"):
            if proposal.get("status") == "approved":
                return "Auto-execution queued"
            return "Atlas auto-review queue"
        if proposal.get("side") == "sell":
            action = str(proposal.get("action_label") or "sell").lower()
            return "Trim candidate" if action == "trim" else "Exit candidate"
        return "Ready to simulate" if proposal.get("status") == "approved" else "Buy candidate"

    @staticmethod
    def _proposal_queue_summary(proposal):
        rationale = proposal.get("rationale") or []
        thesis = str(proposal.get("thesis") or "").strip()
        if rationale:
            return str(rationale[0]).strip()
        if thesis:
            return thesis
        if proposal.get("auto_manage_enabled"):
            return "Atlas will auto-review and auto-execute this paper proposal when the risk and pricing checks pass."
        return "Atlas has a paper proposal awaiting owner attention."

    @staticmethod
    def _proposal_queue_evidence(proposal):
        driver = proposal.get("decision_driver") or {}
        if driver.get("evidence"):
            return str(driver["evidence"]).strip()
        calibration = proposal.get("paper_calibration") or {}
        reasons = calibration.get("reasons") or []
        if reasons:
            return str(reasons[0]).strip()
        objections = proposal.get("objections") or []
        if objections:
            return str(objections[0]).strip()
        return ""

    @staticmethod
    def _proposal_queue_next_step(proposal):
        if proposal.get("auto_manage_enabled"):
            if proposal.get("status") == "approved":
                return "Atlas will record the simulated fill automatically on the next autonomous cycle with a usable market price."
            if proposal.get("side") == "sell":
                return "Atlas will auto-review this simulated trim or exit proposal after the risk gate runs."
            return "Atlas will auto-review this simulated buy proposal after the risk gate runs."
        if proposal.get("status") == "approved":
            if proposal.get("side") == "sell":
                return "Use Simulate fill when you are ready to record the paper trim or exit."
            return "Use Simulate fill when you are ready to add the paper position."
        if proposal.get("side") == "sell":
            return "Approve or reject this simulated trim or exit proposal."
        return "Approve or reject this simulated buy proposal."

    def _position_action_score(self, position):
        label = str((position.get("thesis_status") or {}).get("label") or "healthy").lower()
        base = {"exit": 88, "trim": 82, "watch": 68, "healthy": 40}.get(label, 40)
        review = position.get("review") or {}
        flags = review.get("flags") or []
        return max(0, min(100, round(base + min(len(flags), 2) * 2, 1)))

    @staticmethod
    def _position_status_label(position):
        label = str((position.get("thesis_status") or {}).get("label") or "healthy").lower()
        return {
            "watch": "Watch closely",
            "trim": "Trim candidate",
            "exit": "Exit candidate",
        }.get(label, "Hold steady")

    @staticmethod
    def _position_queue_evidence(position):
        driver = position.get("decision_driver") or {}
        if driver.get("evidence"):
            return str(driver["evidence"]).strip()
        review = position.get("review") or {}
        flags = review.get("flags") or []
        if flags:
            return str(flags[0]).strip()
        thesis = str(review.get("thesis") or "").strip()
        return thesis[:180] if thesis else ""

    def _position_queue_next_step(self, position):
        label = str((position.get("thesis_status") or {}).get("label") or "healthy").lower()
        if label == "exit":
            return "Review this holding now and confirm whether Atlas should open or refresh an exit path."
        if label == "trim":
            return "Review this holding now and decide whether a trim proposal is still appropriate."
        if label == "watch":
            return "Review the latest thesis signals and wait for confirmation before Atlas escalates."
        return "Continue monitoring this simulated holding."

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
        trade_pressure = self.paper_account.trade_pressure_profile(
            latest_prices=self._latest_prices()
        )
        benchmark_preference = self.paper_account.benchmark_preference_profile(
            latest_prices=self._latest_prices()
        )
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
                trade_pressure,
                benchmark_preference,
            )
            ticker_context[ticker] = {
                "portfolio_context": portfolio_context,
                "paper_context": paper_context,
            }
        return {
            "tickers": ticker_context,
            "default_portfolio_context": "No open simulated position is currently tracked.",
            "default_paper_context": self._paper_context(
                None,
                performance,
                None,
                trade_pressure,
                benchmark_preference,
            ),
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
    def _paper_context(
        ticker,
        performance,
        review,
        trade_pressure=None,
        benchmark_preference=None,
    ):
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
        if trade_pressure:
            trade_cap = trade_pressure.get("policy_overrides", {}).get(
                "maximum_daily_trades",
                trade_pressure.get("baseline", {}).get("maximum_daily_trades"),
            )
            if trade_cap is not None:
                state = (
                    "active" if trade_pressure.get("active") else "watching"
                )
                pieces.append(
                    f"adaptive daily trade pressure: {trade_cap} trades ({state})"
                )
        if benchmark_preference:
            benchmark_bar = str(
                benchmark_preference.get("strategy_overrides", {}).get(
                    "strategy_preferred_benchmark",
                    benchmark_preference.get("baseline", {}).get(
                        "strategy_preferred_benchmark",
                        "auto",
                    ),
                )
            ).upper()
            state = "active" if benchmark_preference.get("active") else "watching"
            pieces.append(
                f"adaptive benchmark trust: {benchmark_bar} ({state})"
            )
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
        return {
            "score": score,
            "label": self._attention_label(score),
            "reasons": reasons[:4],
        }

    @staticmethod
    def _attention_label(score):
        if score >= 80:
            return "Urgent"
        if score >= 55:
            return "High"
        if score >= 30:
            return "Medium"
        return "Low"

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
                elif action == "paper-policy":
                    result = self._paper_policy(payload)
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
        action_label = self._proposal_action_label(
            proposal,
            self._position_shares(),
        )
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
            "action_label": action_label,
            "shares": event["shares"],
            "price": event["price"],
            "simulation_only": True,
        }

    def _paper_policy(self, payload):
        if not self.paper_account.account_file.exists():
            raise ValueError("Paper account is not initialized")
        updates = {
            key: payload[key]
            for key in PAPER_POLICY_FIELDS
            if key in payload
        }
        if not updates:
            raise ValueError("No paper policy updates were supplied")
        policy = self.paper_account.update_policy(
            updates,
            source="owner_cloud_policy",
        )
        return {
            "action": "paper-policy",
            "policy": {
                key: policy.get(key)
                for key in PAPER_POLICY_FIELDS
            },
            "auto_manage_enabled": bool(policy.get("auto_manage_enabled")),
        }

    def _affected_paths(self, action):
        if action == "research-decision":
            return [self.research_queue.task_file, *self._research_outputs()]
        if action in {"paper-decision", "paper-fill", "paper-policy"}:
            return [
                self.paper_account.account_file,
                self.paper_account.ledger_file,
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
