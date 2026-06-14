"""Conservative automated completion of selected Atlas research tasks."""

from app.news_data import NewsFetcher


SUPPORTED_SIGNALS = {"downside_move", "catalyst_move"}


class ResearchAnalyst:
    """Turn a small number of current market signals into owner-review work."""

    def __init__(self, news_fetcher=None, max_tasks=3):
        self.news_fetcher = news_fetcher or NewsFetcher(max_headlines=3)
        self.max_tasks = max_tasks

    def complete_priority_tasks(self, queue, market_data):
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
            result = self._analyze(task, security)
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

    def _analyze(self, task, security):
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
        evidence.extend(
            {
                "title": headline.get("title"),
                "source": headline.get("publisher"),
                "url": headline.get("url"),
                "detail": "Company-specific headline",
            }
            for headline in company_headlines
        )

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
        elif company_headlines:
            conclusion = (
                f"{ticker} moved {percent_change:+.2f}%. Recent company-specific "
                "headlines provide a plausible catalyst, but the durability of "
                "the move still requires owner review."
            )
            recommendation = "monitor"
            confidence = "medium"
        else:
            conclusion = (
                f"{ticker} moved {percent_change:+.2f}% without a retrieved "
                "company-specific headline that confirms the catalyst."
            )
            recommendation = "research_further"
            confidence = "low"

        return {
            "conclusion": conclusion,
            "recommendation": recommendation,
            "confidence": confidence,
            "evidence": evidence,
        }
