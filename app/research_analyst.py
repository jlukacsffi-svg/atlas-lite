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
            )
            result = self._analyze(task, security, context)
            completed.append(
                queue.complete_research(
                    task["id"],
                    conclusion=result["conclusion"],
                    recommendation=result["recommendation"],
                    confidence=result["confidence"],
                    evidence=result["evidence"],
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
        return {
            "score": score,
            "category": security.get("category"),
            "sector": security.get("sector"),
            "earnings": earnings,
            "analyst_actions": analyst,
            "insider_transactions": insiders,
            "portfolio_positions": positions,
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

        context_phrases = self._context_phrases(context)
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
            if context_phrases:
                conclusion = f"{conclusion} Context: {'; '.join(context_phrases)}."
        else:
            conclusion = (
                f"{ticker} moved {percent_change:+.2f}% without a retrieved "
                "company-specific headline that confirms the catalyst."
            )
            recommendation = "research_further"
            confidence = "low"
            if context_phrases:
                conclusion = f"{conclusion} Context: {'; '.join(context_phrases)}."

        return {
            "conclusion": conclusion,
            "recommendation": recommendation,
            "confidence": confidence,
            "evidence": evidence,
        }

    def _append_context_evidence(self, ticker, evidence, context):
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
        return phrases
