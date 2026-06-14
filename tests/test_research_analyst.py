import tempfile
import unittest
from pathlib import Path

from app.research_analyst import ResearchAnalyst
from app.research_tasks import ResearchTaskQueue


class StubNewsFetcher:
    def __init__(self, headlines_by_ticker=None):
        self.headlines_by_ticker = headlines_by_ticker or {}
        self.calls = []

    def fetch_headlines(self, ticker, company_name=None):
        self.calls.append((ticker, company_name))
        return self.headlines_by_ticker.get(ticker, [])


class ResearchAnalystTests(unittest.TestCase):
    def _queue_with_signal(self, root, ticker="MU", signal_type="downside_move"):
        queue = ResearchTaskQueue(root / "tasks.json")
        queue.refresh_generated_tasks(
            [
                {
                    "role": "CRO" if signal_type == "downside_move" else "CIO",
                    "subject": ticker,
                    "priority": "high",
                    "signal_type": signal_type,
                    "prompt": "Review the current market move.",
                }
            ],
            source="daily_run",
            generated_scope="daily_market",
        )
        return queue

    def test_company_headline_routes_downside_move_to_risk_review(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._queue_with_signal(root)
            news = StubNewsFetcher(
                {
                    "MU": [
                        {
                            "title": "Micron updates its outlook",
                            "publisher": "Example News",
                            "url": "https://example.com/mu",
                            "relevance": "company",
                        }
                    ]
                }
            )

            completed = ResearchAnalyst(news_fetcher=news).complete_priority_tasks(
                queue,
                {
                    "MU": {
                        "status": "available",
                        "company_name": "Micron Technology",
                        "price": 190.0,
                        "percent_change": -6.5,
                    }
                },
            )

        result = completed[0]["result"]
        self.assertEqual(result["recommendation"], "risk_review")
        self.assertEqual(result["confidence"], "medium")
        self.assertEqual(result["evidence"][1]["url"], "https://example.com/mu")

    def test_missing_company_headline_uses_low_confidence_research_further(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._queue_with_signal(root)

            completed = ResearchAnalyst(
                news_fetcher=StubNewsFetcher()
            ).complete_priority_tasks(
                queue,
                {
                    "MU": {
                        "status": "available",
                        "company_name": "Micron Technology",
                        "price": 190.0,
                        "percent_change": -6.5,
                    }
                },
            )

        result = completed[0]["result"]
        self.assertEqual(result["recommendation"], "research_further")
        self.assertEqual(result["confidence"], "low")
        self.assertIn("unconfirmed", result["conclusion"])

    def test_broad_headlines_are_not_used_as_review_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._queue_with_signal(root)
            news = StubNewsFetcher(
                {
                    "MU": [
                        {
                            "title": "Broad market update",
                            "publisher": "Example News",
                            "url": "https://example.com/market",
                            "relevance": "broad",
                        }
                    ]
                }
            )

            completed = ResearchAnalyst(news_fetcher=news).complete_priority_tasks(
                queue,
                {
                    "MU": {
                        "status": "available",
                        "company_name": "Micron Technology",
                        "price": 190.0,
                        "percent_change": -6.5,
                    }
                },
            )

        result = completed[0]["result"]
        self.assertEqual(len(result["evidence"]), 1)
        self.assertEqual(result["recommendation"], "research_further")

    def test_only_high_priority_supported_generated_tasks_are_completed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = ResearchTaskQueue(root / "tasks.json")
            suggestions = [
                {
                    "role": "CRO",
                    "subject": ticker,
                    "priority": "high",
                    "signal_type": "downside_move",
                    "prompt": "Review downside risk.",
                }
                for ticker in ("AAA", "BBB", "CCC", "DDD")
            ]
            suggestions.append(
                {
                    "role": "CIO",
                    "subject": "SCORE",
                    "priority": "medium",
                    "signal_type": "score_leader",
                    "prompt": "Maintain thesis.",
                }
            )
            queue.refresh_generated_tasks(
                suggestions,
                source="daily_run",
                generated_scope="daily_market",
                limit=8,
            )
            market_data = {
                ticker: {
                    "status": "available",
                    "company_name": ticker,
                    "price": 100,
                    "percent_change": -5,
                }
                for ticker in ("AAA", "BBB", "CCC", "DDD", "SCORE")
            }

            completed = ResearchAnalyst(
                news_fetcher=StubNewsFetcher(),
                max_tasks=3,
            ).complete_priority_tasks(queue, market_data)
            open_tasks = queue.list_tasks(status="open")

        self.assertEqual(len(completed), 3)
        self.assertEqual(len(open_tasks), 2)
        self.assertIn("SCORE", {task["subject"] for task in open_tasks})
