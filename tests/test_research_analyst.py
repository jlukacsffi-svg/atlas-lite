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
        self.assertEqual(result["catalyst_type"], "company_news")
        self.assertIn("thesis_action", result)
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
        self.assertEqual(result["catalyst_type"], "unconfirmed")
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

    def test_context_sources_are_added_to_owner_review_evidence(self):
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
                        "category": "Watchlist",
                        "sector": "AI & Semiconductors",
                        "profile": {
                            "thesis": "Memory-cycle beneficiary with AI infrastructure exposure.",
                            "key_driver": "HBM demand and data-center memory growth.",
                            "key_risk": "Commodity cycles and volatile margins.",
                        },
                        "scores": {
                            "growth": 80,
                            "quality": 75,
                            "moat": 70,
                            "momentum": 65,
                            "risk": 60,
                        },
                    }
                },
                earnings_events=[
                    {
                        "ticker": "MU",
                        "date": "2026-06-25",
                        "time": "After hours",
                        "eps_forecast": "1.58",
                    }
                ],
                analyst_actions=[
                    {
                        "ticker": "MU",
                        "action_type": "Price target raised",
                        "title": "Analyst raises Micron price target",
                        "publisher": "Example Research",
                        "url": "https://example.com/pt",
                    }
                ],
                insider_transactions=[
                    {
                        "ticker": "MU",
                        "transaction_label": "Sale",
                        "transaction_date": "2026-06-20",
                        "owner_name": "Insider Name",
                        "filing_url": "https://sec.gov/example",
                    }
                ],
                portfolio_summary={
                    "configured": True,
                    "positions": [
                        {"ticker": "MU", "allocation_pct": 12.5}
                    ],
                },
            )

        result = completed[0]["result"]
        evidence_titles = {item["title"] for item in result["evidence"]}
        self.assertIn("MU Atlas score", evidence_titles)
        self.assertIn("MU thesis profile", evidence_titles)
        self.assertIn("MU upcoming earnings", evidence_titles)
        self.assertIn("Analyst raises Micron price target", evidence_titles)
        self.assertIn("MU insider Sale", evidence_titles)
        self.assertIn("MU tracked portfolio exposure", evidence_titles)
        self.assertIn("upcoming earnings", result["conclusion"])
        self.assertIn("tracked portfolio exposure", result["conclusion"])
        self.assertIn("stored thesis profile", result["conclusion"])
        self.assertIn("thesis_alignment", result)

    def test_low_score_downside_move_is_classified_as_score_risk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._queue_with_signal(root, ticker="AVAV")
            prior, _ = queue.add_task(role="CRO", subject="AVAV", prompt="Review prior risk.")
            queue.complete_research(
                prior["id"],
                conclusion="Prior risk-to-thesis review.",
                recommendation="risk_review",
                thesis_alignment="risk_to_thesis",
                thesis_drift="new_risk",
            )

            completed = ResearchAnalyst(
                news_fetcher=StubNewsFetcher(
                    {
                        "AVAV": [
                            {
                                "title": "AeroVironment operational update",
                                "publisher": "Example News",
                                "url": "https://example.com/avav",
                                "relevance": "company",
                            }
                        ]
                    }
                )
            ).complete_priority_tasks(
                queue,
                {
                    "AVAV": {
                        "status": "available",
                        "company_name": "AeroVironment",
                        "price": 150.0,
                        "percent_change": -8.0,
                        "category": "Emerging",
                        "sector": "Defense & Aerospace",
                        "profile": {
                            "thesis": "Unmanned systems specialist aligned to defense modernization.",
                            "key_driver": "Drone demand and defense program wins.",
                            "key_risk": "Contract lumpiness and elevated expectations.",
                        },
                        "scores": {
                            "growth": 55,
                            "quality": 60,
                            "moat": 55,
                            "momentum": 45,
                            "risk": 50,
                        },
                    }
                },
            )

        result = completed[0]["result"]
        self.assertEqual(result["catalyst_type"], "score_risk")
        self.assertEqual(result["thesis_alignment"], "risk_to_thesis")
        self.assertEqual(result["thesis_drift"], "recurring_risk")
        self.assertIn("Recheck thesis quality", result["thesis_action"])
        self.assertIn("Thesis alignment: risk to thesis", result["conclusion"])
        self.assertIn("Thesis drift: recurring risk", result["conclusion"])
        self.assertIn("Catalyst classification: score risk", result["conclusion"])
        evidence_titles = {item["title"] for item in result["evidence"]}
        self.assertIn("AVAV thesis history", evidence_titles)

    def test_positive_company_news_can_support_stored_driver(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._queue_with_signal(root, ticker="NVDA", signal_type="catalyst_move")
            news = StubNewsFetcher(
                {
                    "NVDA": [
                        {
                            "title": "Nvidia data-center platform demand accelerates",
                            "publisher": "Example News",
                            "url": "https://example.com/nvda",
                            "relevance": "company",
                        }
                    ]
                }
            )

            completed = ResearchAnalyst(news_fetcher=news).complete_priority_tasks(
                queue,
                {
                    "NVDA": {
                        "status": "available",
                        "company_name": "NVIDIA",
                        "price": 220.0,
                        "percent_change": 5.0,
                        "profile": {
                            "thesis": "Core AI infrastructure leader.",
                            "key_driver": "AI data-center demand and platform adoption.",
                            "key_risk": "Valuation pressure.",
                        },
                    }
                },
            )

        result = completed[0]["result"]
        self.assertEqual(result["catalyst_type"], "company_news")
        self.assertEqual(result["thesis_alignment"], "supports_driver")
        self.assertEqual(result["thesis_drift"], "new_support")
        self.assertIn("Thesis alignment: supports driver", result["conclusion"])

    def test_analyst_action_classification_takes_precedence_after_score(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            queue = self._queue_with_signal(root, ticker="ARM")

            completed = ResearchAnalyst(news_fetcher=StubNewsFetcher()).complete_priority_tasks(
                queue,
                {
                    "ARM": {
                        "status": "available",
                        "company_name": "Arm Holdings",
                        "price": 400.0,
                        "percent_change": -5.0,
                        "scores": {
                            "growth": 90,
                            "quality": 85,
                            "moat": 85,
                            "momentum": 80,
                            "risk": 75,
                        },
                    }
                },
                analyst_actions=[
                    {
                        "ticker": "ARM",
                        "action_type": "Downgrade",
                        "title": "Research firm downgrades ARM",
                        "publisher": "Example Research",
                    }
                ],
            )

        result = completed[0]["result"]
        self.assertEqual(result["catalyst_type"], "analyst_negative")
        self.assertIn("external estimates", result["thesis_action"])

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
