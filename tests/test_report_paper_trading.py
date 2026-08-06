import unittest

from app.report_generator import ReportGenerator


class ReportPaperTradingTests(unittest.TestCase):
    def test_paper_section_explains_dormant_account(self):
        generator = ReportGenerator({}, {}, paper_summary={"configured": False})

        section = generator._generate_paper_performance()

        self.assertIn("## Paper Trading Performance", section)
        self.assertIn("No simulated paper account", section)
        self.assertIn("No brokerage connection exists", section)

    def test_paper_section_renders_benchmark_comparison(self):
        generator = ReportGenerator(
            {},
            {},
            paper_summary={
                "configured": True,
                "available": True,
                "snapshots": 3,
                "latest": {
                    "equity": 101000,
                    "total_return_pct": 1.0,
                    "realized_gain_loss": 200,
                    "unrealized_gain_loss": 800,
                    "benchmark_returns_pct": {"QQQ": 2.0, "SPY": 0.5},
                },
                "excess_return_pct": {"QQQ": -1.0, "SPY": 0.5},
                "trade_statistics": {
                    "recommendations": 3,
                    "trades": 2,
                    "wins": 1,
                    "losses": 0,
                    "proposal_statuses": {"pending": 1},
                },
                "pending_proposals": [
                    {
                        "proposal_id": "proposal_test",
                        "side": "buy",
                        "ticker": "NVDA",
                        "shares": 10,
                        "price": 150,
                        "source": "paper_strategy_v1",
                        "thesis": "High Atlas score.",
                        "risk_review": {
                            "verdict": "caution",
                            "flags": ["Elevated daily volatility."],
                        },
                    }
                ],
                "position_reviews": {
                    "NVDA": {
                        "verdict": "maintain",
                        "return_pct": 2.5,
                        "atlas_score": 89.7,
                        "flags": [],
                        "thesis": "NVDA thesis remains intact.",
                    }
                },
            },
        )

        section = generator._generate_paper_performance()

        self.assertIn("$101,000.00", section)
        self.assertIn("| QQQ | +2.00% | -1.00% |", section)
        self.assertIn("| SPY | +0.50% | +0.50% |", section)
        self.assertIn("Recommendations / Simulated Trades", section)
        self.assertIn("Pending Paper Proposals", section)
        self.assertIn("| proposal_test | Buy | NVDA | 10 | $150.00 | Caution |", section)
        self.assertIn("Elevated daily volatility.", section)
        self.assertIn("cannot execute without a separate simulation approval", section)
        self.assertIn("Open Position Thesis Reviews", section)
        self.assertIn("| NVDA | Maintain | +2.50% | 89.7 |", section)
        self.assertIn("Simulated performance only", section)

    def test_defensive_review_section_renders_recent_transition_digest(self):
        generator = ReportGenerator(
            {},
            {},
            paper_summary={
                "prospective_review_tracker": {
                    "available": True,
                    "activated": True,
                    "review_queue": [
                        {
                            "ticker": "TSM",
                            "status_label": "Weakness persists",
                            "review_priority_label": "Review now",
                            "review_priority_score": 100,
                            "review_priority_rationale": [
                                "Weakness persisted.",
                                "The holding trails its benchmark.",
                            ],
                        }
                    ],
                    "latest_priority_escalations": [
                        {
                            "ticker": "TSM",
                            "previous_review_priority_label": "Watch",
                            "review_priority_label": "Review now",
                            "review_priority_score": 100,
                        }
                    ],
                    "recent_transitions": [
                        {
                            "ticker": "TSM",
                            "status": "persistent_weakness",
                            "status_label": "Weakness persists",
                            "latest_return_pct": -4.25,
                            "latest_lag_pct": -5.75,
                            "snapshots_observed": 3,
                        },
                        {
                            "ticker": "AMD",
                            "status": "recovered",
                            "status_label": "Recovered above trigger",
                            "latest_return_pct": -1.25,
                            "latest_lag_pct": -2.0,
                            "snapshots_observed": 4,
                        },
                    ],
                },
                "prospective_review_effectiveness": {
                    "available": True,
                    "resolved_signals": 2,
                    "confirmed_weakness": 1,
                    "false_alarms": 1,
                    "evidence_progress_pct": 20.0,
                    "outcome_comparison": {
                        "outcome_separation_pct": 12.5,
                        "benchmark_adjusted_separation_pct": 8.25,
                        "confirmed_avg_warning_span_snapshots": 3.0,
                        "confirmed_avg_warning_span_days": 2.0,
                        "false_alarm_avg_snapshots_to_recovery": 2.0,
                        "false_alarm_avg_days_to_recovery": 1.0,
                        "confirmed_avg_recovery_durability_pct": 50.0,
                        "false_alarm_avg_recovery_durability_pct": 90.0,
                        "recovery_durability_separation_pct": 40.0,
                        "confirmed_total_relapses": 1,
                        "false_alarm_total_relapses": 0,
                    },
                    "outcomes": [
                        {
                            "ticker": "TSM",
                            "classification_label": "Warning confirmed",
                            "post_trigger_move_pct": -3.5,
                            "worst_post_trigger_move_pct": -4.0,
                            "best_post_trigger_move_pct": 0.0,
                            "comparison_benchmark": "SPY",
                            "comparison_benchmark_move_pct": 2.0,
                            "benchmark_relative_move_pct": -5.5,
                            "benchmark_attribution_label": "Lagged stronger benchmark",
                            "warning_span_days": 2.0,
                            "snapshots_to_first_recovery": None,
                            "days_to_first_recovery": None,
                            "recovery_durability_pct": 50.0,
                            "relapse_count": 1,
                            "recovery_quality_label": "Relapsed below trigger",
                            "snapshots_observed": 3,
                        },
                        {
                            "ticker": "AMD",
                            "classification_label": "Recovery / false alarm",
                            "post_trigger_move_pct": 9.0,
                            "worst_post_trigger_move_pct": 0.0,
                            "best_post_trigger_move_pct": 10.0,
                            "comparison_benchmark": "QQQ",
                            "comparison_benchmark_move_pct": 4.0,
                            "benchmark_relative_move_pct": 5.0,
                            "benchmark_attribution_label": "Outpaced stronger benchmark",
                            "warning_span_days": 3.0,
                            "snapshots_to_first_recovery": 2,
                            "days_to_first_recovery": 1.0,
                            "recovery_durability_pct": 90.0,
                            "relapse_count": 0,
                            "recovery_quality_label": "Recovery remains above trigger",
                            "snapshots_observed": 4,
                        },
                    ],
                },
            },
        )

        section = generator._generate_paper_review_evidence()

        self.assertIn("## Defensive Review Evidence", section)
        self.assertIn("### Owner Review Priority", section)
        self.assertIn("| Review now (100/100) | TSM | Weakness persists |", section)
        self.assertIn("Priority ranks owner attention only", section)
        self.assertIn("### Priority Escalation Watch", section)
        self.assertIn("| TSM | Watch | Review now | 100/100 |", section)
        self.assertIn("Routine score drift", section)
        self.assertIn(
            "| TSM | Weakness persists | -4.25% | -5.75% | 3 |",
            section,
        )
        self.assertIn(
            "| AMD | Recovered above trigger | -1.25% | -2.00% | 4 |",
            section,
        )
        self.assertIn("do not change policy", section)
        self.assertIn("only the latest state", section)
        self.assertIn("### Forward Study Scorecard", section)
        self.assertIn("**Post-warning outcome separation**: +12.50 points", section)
        self.assertIn("**Benchmark-adjusted separation**: +8.25 points", section)
        self.assertIn("**Confirmed-outcome observation span**: 3.0 snapshots / 2.0 days", section)
        self.assertIn("**Recovery first appeared**: 2.0 snapshots / 1.0 days", section)
        self.assertIn(
            "**Recovery durability separation**: +40.0 points (1 confirmed-outcome relapses / 0 recovery relapses)",
            section,
        )
        self.assertIn(
            "| TSM | Warning confirmed | -3.50% | -4.00% | +0.00% | 3 |",
            section,
        )
        self.assertIn(
            "| AMD | Recovery / false alarm | +9.00% | +0.00% | +10.00% | 4 |",
            section,
        )
        self.assertIn("#### Benchmark Attribution", section)
        self.assertIn(
            "| TSM | SPY | +2.00% | -5.50% | Lagged stronger benchmark |",
            section,
        )
        self.assertIn(
            "| AMD | QQQ | +4.00% | +5.00% | Outpaced stronger benchmark |",
            section,
        )
        self.assertIn("does not claim causation", section)
        self.assertIn("#### Warning Timing", section)
        self.assertIn(
            "| TSM | 3 snapshots / 2.0 days | Not observed | 50.0% above trigger / 1 relapses | Warning confirmed |",
            section,
        )
        self.assertIn(
            "| AMD | 4 snapshots / 3.0 days | 2 snapshots / 1.0 days | 90.0% above trigger / 0 relapses | Recovery / false alarm |",
            section,
        )
        self.assertIn("can be temporary", section)
        self.assertIn("sustained recovery and relapse frequency", section)
        self.assertIn("not hypothetical fills", section)

    def test_defensive_review_section_explains_forward_start(self):
        generator = ReportGenerator(
            {},
            {},
            paper_summary={
                "prospective_review_tracker": {
                    "available": True,
                    "activated": False,
                    "recent_transitions": [],
                }
            },
        )

        section = generator._generate_paper_review_evidence()

        self.assertIn("starts with the next scheduled paper snapshot", section)
        self.assertNotIn("| Ticker |", section)


if __name__ == "__main__":
    unittest.main()
