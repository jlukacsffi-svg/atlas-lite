"""Conservative automated completion of selected Atlas research tasks."""

from app.news_data import NewsFetcher
from app.scoring import ScoringEngine


SUPPORTED_SIGNALS = {"downside_move", "catalyst_move"}


class ResearchAnalyst:
    """Turn a small number of current market signals into owner-review work."""

    def __init__(self, news_fetcher=None, max_tasks=3):
        self.news_fetcher = news_fetcher or NewsFetcher(max_headlines=3)
        self.max_tasks = max_tasks
        self.scoring_engine = ScoringEngine()

    def complete_priority_tasks(
        self,
        queue,
        market_data,
        earnings_events=None,
        analyst_actions=None,
        insider_transactions=None,
        portfolio_summary=None,
    ):
        candidates = [
            task
            for task in queue._sorted_tasks(queue.list_tasks(status="open"))
            if task.get("generated_scope") == "daily_market"
            and task.get("signal_type") in SUPPORTED_SIGNALS
            and task.get("priority") == "high"
        ][:self.max_tasks]

        completed = []
        for task in candidates:
            ticker = task.get("subject")
            security = market_data.get(ticker, {})
            if security.get("status") != "available":
                continue
            context = self._context(
                ticker=ticker,
                security=security,
                earnings_events=earnings_events,
                analyst_actions=analyst_actions,
                insider_transactions=insider_transactions,
                portfolio_summary=portfolio_summary,
                thesis_history=queue.thesis_history_summary(ticker),
            )
            result = self._analyze(task, security, context)
            completed.append(
                queue.complete_research(
                    task["id"],
                    conclusion=result["conclusion"],
                    recommendation=result["recommendation"],
                    confidence=result["confidence"],
                    evidence=result["evidence"],
                    catalyst_type=result["catalyst_type"],
                    thesis_action=result["thesis_action"],
                    thesis_alignment=result["thesis_alignment"],
                    thesis_drift=result["thesis_drift"],
                )
            )
        return completed

    def _context(
        self,
        ticker,
        security,
        earnings_events=None,
        analyst_actions=None,
        insider_transactions=None,
        portfolio_summary=None,
        thesis_history=None,
    ):
        earnings = [
            event
            for event in earnings_events or []
            if event.get("ticker") == ticker
        ]
        analyst = [
            action
            for action in analyst_actions or []
            if action.get("ticker") == ticker
        ]
        insiders = [
            transaction
            for transaction in insider_transactions or []
            if transaction.get("ticker") == ticker
        ]
        positions = [
            position
            for position in (portfolio_summary or {}).get("positions", [])
            if position.get("ticker") == ticker
        ]
        score = None
        scores = security.get("scores")
        if scores:
            try:
                score = self.scoring_engine.score(scores)
            except (TypeError, ValueError):
                score = None
        profile = security.get("profile") or {}
        return {
            "score": score,
            "category": security.get("category"),
            "sector": security.get("sector"),
            "profile": {
                "thesis": str(profile.get("thesis") or "").strip(),
                "key_driver": str(profile.get("key_driver") or "").strip(),
                "key_risk": str(profile.get("key_risk") or "").strip(),
            },
            "earnings": earnings,
            "analyst_actions": analyst,
            "insider_transactions": insiders,
            "portfolio_positions": positions,
            "thesis_history": thesis_history,
        }

    def _analyze(self, task, security, context=None):
        context = context or {}
        ticker = task["subject"]
        percent_change = float(security.get("percent_change") or 0)
        price = security.get("price")
        company_name = security.get("company_name") or ticker
        headlines = self.news_fetcher.fetch_headlines(ticker, company_name)
        company_headlines = [
            headline
            for headline in headlines
            if headline.get("relevance") == "company"
        ]

        evidence = [
            {
                "title": f"{ticker} market move",
                "source": "Atlas market data",
                "detail": (
                    f"{percent_change:+.2f}% daily move"
                    + (f" at ${float(price):,.2f}" if price is not None else "")
                ),
            }
        ]
        self._append_context_evidence(ticker, evidence, context)
        evidence.extend(
            {
                "title": headline.get("title"),
                "source": headline.get("publisher"),
                "url": headline.get("url"),
                "detail": "Company-specific headline",
            }
            for headline in company_headlines
        )

        catalyst_type = self._classify_catalyst(
            task=task,
            context=context,
            company_headlines=company_headlines,
        )
        thesis_action = self._thesis_action(task, context, catalyst_type)
        thesis_alignment = self._thesis_alignment(
            task=task,
            context=context,
            catalyst_type=catalyst_type,
            company_headlines=company_headlines,
        )
        thesis_drift = self._thesis_drift(context, thesis_alignment)
        context_phrases = self._context_phrases(context)
        catalyst_text = catalyst_type.replace("_", " ")
        alignment_text = thesis_alignment.replace("_", " ")
        drift_text = thesis_drift.replace("_", " ")
        if task.get("signal_type") == "downside_move":
            if company_headlines:
                conclusion = (
                    f"{ticker} declined {abs(percent_change):.2f}%. Atlas found "
                    f"{len(company_headlines)} company-specific recent headline"
                    f"{'' if len(company_headlines) == 1 else 's'} relevant to "
                    "review. The retrieved headline set does not by itself establish "
                    "why the stock declined."
                )
                recommendation = "risk_review"
                confidence = "medium"
            else:
                conclusion = (
                    f"{ticker} declined {abs(percent_change):.2f}%, but Atlas did "
                    "not retrieve a company-specific recent headline that reliably "
                    "explains the move. The catalyst remains unconfirmed."
                )
                recommendation = "research_further"
                confidence = "low"
            conclusion = (
                f"{conclusion} Catalyst classification: {catalyst_text}. "
                f"Thesis alignment: {alignment_text}. Thesis drift: {drift_text}. "
                f"Thesis action: {thesis_action}."
            )
            if context_phrases:
                conclusion = f"{conclusion} Context: {'; '.join(context_phrases)}."
        elif company_headlines:
            conclusion = (
                f"{ticker} moved {percent_change:+.2f}%. Recent company-specific "
                "headlines provide a plausible catalyst, but the durability of "
                "the move still requires owner review."
            )
            recommendation = "monitor"
            confidence = "medium"
            conclusion = (
                f"{conclusion} Catalyst classification: {catalyst_text}. "
                f"Thesis alignment: {alignment_text}. Thesis drift: {drift_text}. "
                f"Thesis action: {thesis_action}."
            )
            if context_phrases:
                conclusion = f"{conclusion} Context: {'; '.join(context_phrases)}."
        else:
            conclusion = (
                f"{ticker} moved {percent_change:+.2f}% without a retrieved "
                "company-specific headline that confirms the catalyst."
            )
            recommendation = "research_further"
            confidence = "low"
            conclusion = (
                f"{conclusion} Catalyst classification: {catalyst_text}. "
                f"Thesis alignment: {alignment_text}. Thesis drift: {drift_text}. "
                f"Thesis action: {thesis_action}."
            )
            if context_phrases:
                conclusion = f"{conclusion} Context: {'; '.join(context_phrases)}."

        return {
            "conclusion": conclusion,
            "recommendation": recommendation,
            "confidence": confidence,
            "evidence": evidence,
            "catalyst_type": catalyst_type,
            "thesis_action": thesis_action,
            "thesis_alignment": thesis_alignment,
            "thesis_drift": thesis_drift,
        }

    def _classify_catalyst(self, task, context, company_headlines):
        score = context.get("score")
        analyst_actions = context.get("analyst_actions", [])
        if task.get("signal_type") == "downside_move" and score is not None and score < 65:
            return "score_risk"
        if analyst_actions:
            action_text = " ".join(
                str(action.get("action_type") or "").lower()
                for action in analyst_actions
            )
            if any(word in action_text for word in ("downgrade", "cut")):
                return "analyst_negative"
            if any(word in action_text for word in ("upgrade", "raised", "initiated")):
                return "analyst_positive"
            return "analyst_action"
        if context.get("earnings"):
            return "upcoming_earnings"
        if context.get("insider_transactions"):
            return "insider_activity"
        if company_headlines:
            return "company_news"
        return "unconfirmed"

    def _thesis_action(self, task, context, catalyst_type):
        score = context.get("score")
        if catalyst_type == "score_risk":
            return "Recheck thesis quality and risk controls before adding exposure"
        if catalyst_type == "analyst_negative":
            return "Review whether external estimates changed the risk/reward"
        if catalyst_type == "analyst_positive":
            return "Monitor for confirmation before raising conviction"
        if catalyst_type == "upcoming_earnings":
            return "Defer conviction change until earnings details are reviewed"
        if catalyst_type == "insider_activity":
            return "Review Form 4 context before changing thesis status"
        if catalyst_type == "company_news":
            if task.get("signal_type") == "downside_move":
                return "Review company news for thesis damage versus temporary volatility"
            return "Monitor whether the catalyst improves durable conviction"
        if score is not None and score >= 80:
            return "Maintain thesis but verify catalyst quality"
        return "Research further before changing thesis status"

    def _thesis_alignment(self, task, context, catalyst_type, company_headlines):
        profile = context.get("profile") or {}
        if not any(profile.values()):
            return "unprofiled"
        if catalyst_type in {"score_risk", "analyst_negative"}:
            return "risk_to_thesis"
        if task.get("signal_type") == "downside_move":
            return "risk_to_thesis"
        if catalyst_type == "upcoming_earnings":
            return "pending_validation"
        if catalyst_type in {"analyst_positive", "company_news"}:
            driver_tokens = self._meaningful_tokens(profile.get("key_driver"))
            headline_tokens = self._meaningful_tokens(
                " ".join(str(headline.get("title") or "") for headline in company_headlines)
            )
            if driver_tokens and driver_tokens.intersection(headline_tokens):
                return "supports_driver"
            return "neutral_context"
        return "unconfirmed"

    def _meaningful_tokens(self, text):
        stop_words = {
            "and",
            "the",
            "for",
            "from",
            "with",
            "into",
            "its",
            "are",
            "but",
            "this",
            "that",
            "growth",
            "demand",
        }
        normalized = "".join(
            character.lower() if character.isalnum() else " "
            for character in str(text or "")
        )
        return {
            token
            for token in normalized.split()
            if len(token) >= 4 and token not in stop_words
        }

    def _thesis_drift(self, context, thesis_alignment):
        history = context.get("thesis_history") or {}
        if not history:
            if thesis_alignment == "risk_to_thesis":
                return "new_risk"
            if thesis_alignment == "supports_driver":
                return "new_support"
            return "no_history"
        if thesis_alignment == "risk_to_thesis":
            if int(history.get("risk_to_thesis_count") or 0) > 0:
                return "recurring_risk"
            return "new_risk"
        if thesis_alignment == "supports_driver":
            if int(history.get("supports_driver_count") or 0) > 0:
                return "reinforcing_support"
            return "new_support"
        if thesis_alignment == "pending_validation":
            return "pending_validation"
        return "stable_monitoring"

    def _append_context_evidence(self, ticker, evidence, context):
        profile = context.get("profile") or {}
        if any(profile.values()):
            detail_parts = []
            if profile.get("thesis"):
                detail_parts.append(f"Thesis: {profile['thesis']}")
            if profile.get("key_driver"):
                detail_parts.append(f"Driver: {profile['key_driver']}")
            if profile.get("key_risk"):
                detail_parts.append(f"Risk: {profile['key_risk']}")
            evidence.append(
                {
                    "title": f"{ticker} thesis profile",
                    "source": "Atlas security universe",
                    "detail": " | ".join(detail_parts),
                }
            )

        thesis_history = context.get("thesis_history") or {}
        if thesis_history:
            detail = (
                f"{thesis_history.get('review_count', 0)} prior review"
                f"{'' if thesis_history.get('review_count') == 1 else 's'}"
            )
            if thesis_history.get("risk_to_thesis_count"):
                detail = f"{detail} | {thesis_history['risk_to_thesis_count']} prior risk-to-thesis"
            if thesis_history.get("supports_driver_count"):
                detail = f"{detail} | {thesis_history['supports_driver_count']} prior support signal"
            if thesis_history.get("latest_decision"):
                detail = f"{detail} | latest owner decision: {thesis_history['latest_decision']}"
            evidence.append(
                {
                    "title": f"{ticker} thesis history",
                    "source": "Atlas research task memory",
                    "detail": detail,
                }
            )

        score = context.get("score")
        if score is not None:
            evidence.append(
                {
                    "title": f"{ticker} Atlas score",
                    "source": "Atlas scoring engine",
                    "detail": (
                        f"Score {score:.1f}"
                        + (
                            f" · {context.get('category')}"
                            if context.get("category")
                            else ""
                        )
                        + (
                            f" · {context.get('sector')}"
                            if context.get("sector")
                            else ""
                        )
                    ),
                }
            )

        for event in context.get("earnings", [])[:2]:
            evidence.append(
                {
                    "title": f"{ticker} upcoming earnings",
                    "source": "Nasdaq earnings calendar",
                    "detail": (
                        f"{event.get('date')} · {event.get('time')} · "
                        f"EPS forecast {event.get('eps_forecast', 'N/A')}"
                    ),
                }
            )

        for action in context.get("analyst_actions", [])[:2]:
            evidence.append(
                {
                    "title": action.get("title"),
                    "source": action.get("publisher") or "Analyst action",
                    "url": action.get("url") or "",
                    "detail": action.get("action_type") or "Analyst action",
                }
            )

        for transaction in context.get("insider_transactions", [])[:2]:
            evidence.append(
                {
                    "title": f"{ticker} insider {transaction.get('transaction_label', 'transaction')}",
                    "source": "SEC Form 4",
                    "url": transaction.get("filing_url") or "",
                    "detail": (
                        f"{transaction.get('transaction_date', 'N/A')} · "
                        f"{transaction.get('owner_name', 'Unknown owner')}"
                    ),
                }
            )

        for position in context.get("portfolio_positions", [])[:1]:
            allocation = position.get("allocation_pct")
            allocation_text = (
                f"{float(allocation):.1f}% allocation"
                if allocation is not None
                else "allocation unavailable"
            )
            evidence.append(
                {
                    "title": f"{ticker} tracked portfolio exposure",
                    "source": "Atlas portfolio monitor",
                    "detail": allocation_text,
                }
            )

    def _context_phrases(self, context):
        phrases = []
        score = context.get("score")
        if score is not None:
            phrases.append(f"Atlas score {score:.1f}")
        if context.get("earnings"):
            phrases.append("upcoming earnings are on the calendar")
        if context.get("analyst_actions"):
            action_types = {
                action.get("action_type")
                for action in context["analyst_actions"]
                if action.get("action_type")
            }
            phrases.append(
                "recent analyst action"
                + (f" ({', '.join(sorted(action_types))})" if action_types else "")
            )
        if context.get("insider_transactions"):
            phrases.append("recent insider Form 4 activity")
        if context.get("portfolio_positions"):
            phrases.append("tracked portfolio exposure exists")
        profile = context.get("profile") or {}
        if any(profile.values()):
            phrases.append("stored thesis profile is available")
        thesis_history = context.get("thesis_history") or {}
        if thesis_history:
            phrases.append(
                f"{thesis_history.get('review_count', 0)} prior thesis review"
                f"{'' if thesis_history.get('review_count') == 1 else 's'} recorded"
            )
        return phrases
