"""Transparent Stage 5 strategy for generating paper proposals."""

import math

from app.data_quality import has_reliable_daily_change
from app.scoring import ScoringEngine


class PaperStrategy:
    """Generate reviewable proposals; never execute orders."""

    def __init__(
        self,
        minimum_buy_score=88.0,
        maximum_exit_score=60.0,
        target_position_pct=5.0,
        maximum_new_proposals=3,
        minimum_daily_move_pct=-8.0,
        benchmark_excess_weight=1.5,
        preferred_benchmark="auto",
        trend_quality_weight=0.2,
        sector_repeat_penalty=3.0,
    ):
        self.minimum_buy_score = float(minimum_buy_score)
        self.maximum_exit_score = float(maximum_exit_score)
        self.target_position_pct = float(target_position_pct)
        self.maximum_new_proposals = int(maximum_new_proposals)
        self.minimum_daily_move_pct = float(minimum_daily_move_pct)
        self.benchmark_excess_weight = float(benchmark_excess_weight)
        preferred = str(preferred_benchmark or "auto").strip().upper()
        self.preferred_benchmark = preferred if preferred in {"SPY", "QQQ"} else "auto"
        self.trend_quality_weight = float(trend_quality_weight)
        self.sector_repeat_penalty = float(sector_repeat_penalty)
        self.scoring_engine = ScoringEngine()

    @staticmethod
    def _value_or_default(value, default):
        return default if value is None else float(value)

    @classmethod
    def from_account_policy(cls, account):
        policy = dict(getattr(account, "policy", {}))
        if getattr(account, "account_file", None) and account.account_file.exists():
            try:
                current = account.load().get("policy", {})
            except ValueError:
                current = {}
            policy.update(current)
        if hasattr(account, "entry_strategy_profile"):
            profile = account.entry_strategy_profile()
            policy.update(profile.get("strategy_overrides", {}))
        if hasattr(account, "benchmark_preference_profile"):
            profile = account.benchmark_preference_profile()
            policy.update(profile.get("strategy_overrides", {}))
        return cls(
            minimum_buy_score=policy.get("strategy_minimum_buy_score", 88.0),
            maximum_exit_score=policy.get("strategy_maximum_exit_score", 60.0),
            target_position_pct=policy.get("strategy_target_position_pct", 5.0),
            maximum_new_proposals=policy.get("strategy_maximum_new_proposals", 3),
            minimum_daily_move_pct=policy.get("strategy_minimum_daily_move_pct", -8.0),
            benchmark_excess_weight=policy.get("strategy_benchmark_excess_weight", 1.5),
            preferred_benchmark=policy.get("strategy_preferred_benchmark", "auto"),
            trend_quality_weight=policy.get("strategy_trend_quality_weight", 0.2),
            sector_repeat_penalty=policy.get("strategy_sector_repeat_penalty", 3.0),
        )

    def generate(self, account, market_data):
        """Create deduplicated pending proposals from current Atlas signals."""
        state = account.load()
        positions = state.get("positions", {})
        existing = {
            (proposal["side"], proposal["ticker"])
            for proposal in account.proposals()
            if proposal["status"] in {"pending", "approved"}
        }
        active_buy_count = sum(1 for side, _ticker in existing if side == "buy")
        available_buy_slots = max(
            0,
            self.maximum_new_proposals - active_buy_count,
        )
        benchmark_context = self._benchmark_context(
            market_data,
            preferred_benchmark=self.preferred_benchmark,
        )
        learning_context = self._paper_learning_context(account, market_data)
        candidates = self._candidate_rows(
            market_data,
            benchmark_context,
            learning_context,
        )
        created = []
        created_buys = 0

        chosen_sectors = set()

        for row in self._preferred_candidate_order(candidates):
            ticker = row["ticker"]
            if ticker in positions:
                if self._should_create_exit(row):
                    if ("sell", ticker) in existing:
                        continue
                    position = positions[ticker]
                    thesis = self._sell_thesis(row)
                    recommendation = account.record_recommendation(
                        side="sell",
                        ticker=ticker,
                        shares=position["shares"],
                        reference_price=row["price"],
                        thesis=thesis,
                        confidence="high",
                        source="paper_strategy_v1",
                    )
                    created.append(
                        account.create_proposal(
                            side="sell",
                            ticker=ticker,
                            shares=position["shares"],
                            reference_price=row["price"],
                            thesis=thesis,
                            recommendation_id=recommendation["recommendation_id"],
                            source="paper_strategy_v1",
                        )
                    )
                continue

            if created_buys >= available_buy_slots:
                break
            if not self._can_open_buy(row):
                continue
            if ("buy", ticker) in existing:
                continue

            shares = self._target_shares(state["starting_cash"], row["price"])
            if shares <= 0:
                continue
            preview = account.preview_order(
                "buy",
                ticker,
                shares,
                row["price"],
                self._buy_thesis(row),
            )
            if not preview["valid"]:
                continue

            thesis = self._buy_thesis(row)
            rationale = self._buy_rationale(row)
            recommendation = account.record_recommendation(
                side="buy",
                ticker=ticker,
                shares=shares,
                reference_price=row["price"],
                thesis=thesis,
                confidence="high" if row["score"] >= 92 else "medium",
                source="paper_strategy_v1",
                rationale=rationale,
            )
            created.append(
                account.create_proposal(
                    side="buy",
                    ticker=ticker,
                    shares=shares,
                    reference_price=row["price"],
                    thesis=thesis,
                    recommendation_id=recommendation["recommendation_id"],
                    source="paper_strategy_v1",
                    rationale=rationale,
                )
            )
            created_buys += 1
            chosen_sectors.add(row["sector"])

        return created

    def _candidate_rows(self, market_data, benchmark_context, learning_context=None):
        sector_context = self._sector_context(market_data, benchmark_context)
        breadth_context = self._breadth_context(market_data)
        learning_context = learning_context or {"tickers": {}, "sectors": {}}
        rows = []
        for ticker, data in market_data.items():
            if data.get("status") != "available" or data.get("price") is None:
                continue
            if data.get("sector") == "Benchmark ETF":
                continue
            scores = data.get("scores")
            if not scores:
                continue
            try:
                score = self.scoring_engine.score(scores)
            except (TypeError, ValueError):
                continue
            persistence_score = self._persistence_score(data)
            sector = data.get("sector", "Unclassified")
            ticker_learning = learning_context.get("tickers", {}).get(ticker, {})
            sector_learning = learning_context.get("sectors", {}).get(sector, {})
            paper_learning_adjustment = round(
                float(ticker_learning.get("adjustment") or 0.0)
                + float(sector_learning.get("adjustment") or 0.0),
                4,
            )
            daily_change_reliable = has_reliable_daily_change(data)
            daily_change = (
                float(data.get("percent_change") or 0.0)
                if daily_change_reliable
                else 0.0
            )
            benchmark_excess_pct = round(
                daily_change
                - benchmark_context["reference_change"],
                4,
            )
            sector_relative_strength_pct = sector_context["relative_strength"].get(
                data.get("sector", "Unclassified"),
                0.0,
            )
            sector_breadth_pct = sector_context["breadth"].get(
                data.get("sector", "Unclassified"),
                0.0,
            )
            trend_quality_score = self._trend_quality_score(data)
            trend_regime_score = self._trend_regime_score(data)
            follow_through_score = self._follow_through_score(
                score=score,
                percent_change=daily_change,
                benchmark_excess_pct=benchmark_excess_pct,
                sector_relative_strength_pct=sector_relative_strength_pct,
                sector_breadth_pct=sector_breadth_pct,
                benchmark_breadth=breadth_context["benchmark_breadth"],
                persistence_score=persistence_score,
                trend_quality_score=trend_quality_score,
                trend_regime_score=trend_regime_score,
            )
            row = {
                "ticker": ticker,
                "price": float(data["price"]),
                "score": score,
                "scores": dict(scores),
                "category": data.get("category", "Watchlist"),
                "sector": sector,
                "percent_change": daily_change,
                "daily_change_reliable": daily_change_reliable,
                "benchmark_reference": benchmark_context["reference_label"],
                "benchmark_reference_change": benchmark_context["reference_change"],
                "market_regime": benchmark_context["market_regime"],
                "market_regime_description": benchmark_context["market_regime_description"],
                "benchmark_breadth": breadth_context["benchmark_breadth"],
                "benchmark_breadth_label": breadth_context["benchmark_breadth_label"],
                "benchmark_excess_pct": benchmark_excess_pct,
                "sector_average_change": sector_context["averages"].get(
                    data.get("sector", "Unclassified"),
                    0.0,
                ),
                "sector_relative_strength_pct": sector_relative_strength_pct,
                "sector_rank": sector_context["ranks"].get(
                    data.get("sector", "Unclassified"),
                    len(sector_context["ranks"]) + 1,
                ),
                "sector_breadth_pct": sector_breadth_pct,
                "trend_quality_score": trend_quality_score,
                "trend_state": self._trend_state(data),
                "trend_regime": self._trend_regime(data),
                "trend_regime_score": trend_regime_score,
                "persistence_score": persistence_score,
                "news_signal_score": self._news_signal_score(data),
                "news_signal_label": self._news_signal_label(data),
                "news_negative_count": self._news_negative_count(data),
                "news_positive_count": self._news_positive_count(data),
                "news_negative_weight": self._news_negative_weight(data),
                "news_positive_weight": self._news_positive_weight(data),
                "news_high_impact_negative_count": self._news_high_impact_negative_count(data),
                "news_high_impact_positive_count": self._news_high_impact_positive_count(data),
                "news_dominant_event_type": self._news_dominant_event_type(data),
                "follow_through_score": follow_through_score,
                "paper_learning_adjustment": paper_learning_adjustment,
                "paper_learning_summary": self._paper_learning_summary(
                    ticker_learning,
                    sector_learning,
                ),
            }
            row["sector_learning_gate"] = self._sector_learning_gate(row)
            rows.append(
                row
            )
        return sorted(
            rows,
            key=lambda item: (
                self._selection_score(item),
                item["score"],
                item["percent_change"],
                item["ticker"],
            ),
            reverse=True,
        )

    def _preferred_candidate_order(self, rows):
        if self.sector_repeat_penalty <= 0:
            return list(rows)
        primary = []
        secondary = []
        seen_sectors = set()
        for row in rows:
            sector = str(row.get("sector") or "Unclassified")
            if sector not in seen_sectors:
                primary.append(row)
                seen_sectors.add(sector)
            else:
                row = {
                    **row,
                    "selection_score_after_sector_penalty": round(
                        self._selection_score(row) - self.sector_repeat_penalty,
                        4,
                    ),
                }
                secondary.append(row)
        secondary.sort(
            key=lambda item: (
                float(item.get("selection_score_after_sector_penalty") or self._selection_score(item)),
                item["score"],
                item["percent_change"],
                item["ticker"],
            ),
            reverse=True,
        )
        return primary + secondary

    @staticmethod
    def _benchmark_context(market_data, preferred_benchmark="auto"):
        spy = market_data.get("SPY", {})
        qqq = market_data.get("QQQ", {})
        iwm = market_data.get("IWM", {})
        rsp = market_data.get("RSP", {})
        spy_change = (
            float(spy.get("percent_change") or 0.0)
            if has_reliable_daily_change(spy)
            else 0.0
        )
        qqq_change = (
            float(qqq.get("percent_change") or 0.0)
            if has_reliable_daily_change(qqq)
            else 0.0
        )
        iwm_change = (
            float(iwm.get("percent_change") or 0.0)
            if has_reliable_daily_change(iwm)
            else 0.0
        )
        rsp_change = (
            float(rsp.get("percent_change") or 0.0)
            if has_reliable_daily_change(rsp)
            else 0.0
        )
        breadth_change = (
            spy_change
            + qqq_change
            + iwm_change
            + rsp_change
        ) / 4.0
        positive_states = {"uptrend", "extended_uptrend", "improving"}
        weak_states = {"mixed", "downtrend", "unknown"}
        spy_state = PaperStrategy._trend_state(spy)
        qqq_state = PaperStrategy._trend_state(qqq)
        if spy_state in positive_states and qqq_state in positive_states and breadth_change >= 0:
            market_regime = "risk_on"
            description = "Broad benchmarks are constructive, so Atlas can lean into leadership."
        elif spy_state in weak_states and qqq_state in weak_states and breadth_change < 0:
            market_regime = "risk_off"
            description = "Broad benchmarks are weakening, so Atlas should demand stronger setups and cut laggards faster."
        else:
            market_regime = "cautious"
            description = "Benchmarks are mixed, so Atlas should favor resilient leaders over average setups."
        preferred = str(preferred_benchmark or "auto").strip().upper()
        if preferred == "SPY":
            return {
                "reference_label": "SPY",
                "reference_change": spy_change,
                "market_regime": market_regime,
                "market_regime_description": description,
            }
        if preferred == "QQQ":
            return {
                "reference_label": "QQQ",
                "reference_change": qqq_change,
                "market_regime": market_regime,
                "market_regime_description": description,
            }
        if qqq_change >= spy_change:
            return {
                "reference_label": "QQQ",
                "reference_change": qqq_change,
                "market_regime": market_regime,
                "market_regime_description": description,
            }
        return {
            "reference_label": "SPY",
            "reference_change": spy_change,
            "market_regime": market_regime,
            "market_regime_description": description,
        }

    @staticmethod
    def _sector_context(market_data, benchmark_context):
        by_sector = {}
        breadth = {}
        for _ticker, data in market_data.items():
            if (
                data.get("status") != "available"
                or not has_reliable_daily_change(data)
            ):
                continue
            sector = str(data.get("sector") or "Unclassified")
            if sector == "Benchmark ETF":
                continue
            by_sector.setdefault(sector, []).append(float(data.get("percent_change") or 0.0))
        averages = {
            sector: (sum(changes) / len(changes))
            for sector, changes in by_sector.items()
            if changes
        }
        breadth = {
            sector: round(
                (sum(1 for value in changes if value > 0) / len(changes)) * 100.0,
                2,
            )
            for sector, changes in by_sector.items()
            if changes
        }
        relative_strength = {
            sector: round(avg - float(benchmark_context.get("reference_change") or 0.0), 4)
            for sector, avg in averages.items()
        }
        ranked = sorted(
            averages.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        ranks = {sector: index + 1 for index, (sector, _avg) in enumerate(ranked)}
        return {
            "averages": averages,
            "relative_strength": relative_strength,
            "ranks": ranks,
            "breadth": breadth,
        }

    @staticmethod
    def _breadth_context(market_data):
        benchmark_changes = []
        for ticker in ("SPY", "QQQ", "IWM", "RSP"):
            data = market_data.get(ticker, {})
            if (
                data.get("status") != "available"
                or not has_reliable_daily_change(data)
            ):
                continue
            benchmark_changes.append(float(data.get("percent_change") or 0.0))
        if not benchmark_changes:
            return {"benchmark_breadth": 50.0, "benchmark_breadth_label": "mixed"}
        positive = sum(1 for value in benchmark_changes if value > 0)
        breadth = round((positive / len(benchmark_changes)) * 100.0, 2)
        if breadth >= 75.0:
            label = "broad_strength"
        elif breadth <= 25.0:
            label = "broad_weakness"
        else:
            label = "mixed"
        return {"benchmark_breadth": breadth, "benchmark_breadth_label": label}

    def _selection_score(self, row):
        return round(
            self._value_or_default(row.get("score"), 0.0)
            + (self._value_or_default(row.get("trend_quality_score"), 50.0) - 50.0)
            * self.trend_quality_weight
            + self._value_or_default(row.get("benchmark_excess_pct"), 0.0)
            * self.benchmark_excess_weight
            + self._value_or_default(row.get("sector_relative_strength_pct"), 0.0) * 0.9
            + ((self._value_or_default(row.get("sector_breadth_pct"), 50.0) - 50.0) * 0.04)
            + self._regime_alignment_bonus(row)
            + ((self._value_or_default(row.get("persistence_score"), 50.0) - 50.0) * 0.12)
            + ((self._value_or_default(row.get("trend_regime_score"), 50.0) - 50.0) * 0.12)
            + ((self._value_or_default(row.get("follow_through_score"), 50.0) - 50.0) * 0.18)
            + self._value_or_default(row.get("paper_learning_adjustment"), 0.0)
            + ((self._value_or_default(row.get("news_signal_score"), 50.0) - 50.0) * 0.08),
            4,
        )

    def _sector_learning_gate(self, row):
        paper_learning = self._value_or_default(
            row.get("paper_learning_adjustment"),
            0.0,
        )
        if paper_learning <= -2.0:
            market_regime = str(row.get("market_regime") or "cautious")
            if market_regime == "risk_off":
                thresholds = {
                    "benchmark_excess_pct": 0.5,
                    "sector_relative_strength_pct": 0.0,
                    "sector_breadth_pct": 55.0,
                    "trend_quality_score": 72.0,
                    "persistence_score": 68.0,
                    "follow_through_score": 67.0,
                }
            elif market_regime == "cautious":
                thresholds = {
                    "benchmark_excess_pct": 0.25,
                    "sector_relative_strength_pct": 0.25,
                    "sector_breadth_pct": 55.0,
                    "trend_quality_score": 64.0,
                    "persistence_score": 58.0,
                    "follow_through_score": 62.0,
                }
            else:
                thresholds = {
                    "benchmark_excess_pct": 0.0,
                    "sector_relative_strength_pct": 0.25,
                    "sector_breadth_pct": 50.0,
                    "trend_quality_score": 60.0,
                    "persistence_score": 56.0,
                    "follow_through_score": 58.0,
                }
            checks = []
            for key, minimum in thresholds.items():
                value = self._value_or_default(row.get(key), 0.0)
                checks.append(
                    {
                        "metric": key,
                        "value": round(value, 4),
                        "minimum": minimum,
                        "passed": value >= minimum,
                    }
                )
            passed = all(item["passed"] for item in checks)
            return {
                "active": True,
                "posture": "caution",
                "status": "cleared" if passed else "tightened",
                "adjustment": paper_learning,
                "headline": (
                    f"{row.get('sector') or 'This sector'} has lagging paper-learning evidence, "
                    "so Atlas requires stronger confirmation before adding another simulated buy."
                ),
                "summary": (
                    "Cleared stronger lagging-sector confirmation."
                    if passed
                    else "Lagging-sector evidence tightened the simulated entry gate."
                ),
                "checks": checks,
            }
        if paper_learning >= 1.5:
            return {
                "active": True,
                "posture": "boost",
                "status": "modest_boost",
                "adjustment": paper_learning,
                "headline": (
                    f"{row.get('sector') or 'This sector'} has constructive paper-learning evidence, "
                    "so Atlas allows a small simulated-entry tilt without bypassing core filters."
                ),
                "summary": "Constructive sector evidence provided a small simulated-entry tilt.",
                "checks": [],
            }
        return {
            "active": False,
            "posture": "watch",
            "status": "watch",
            "adjustment": paper_learning,
            "headline": "No active sector-learning gate for this candidate.",
            "summary": "Atlas is watching for enough sector evidence to adjust this gate.",
            "checks": [],
        }

    def _can_open_buy(self, row):
        if not row.get("daily_change_reliable", True):
            return False
        if row["category"] == "Avoid" or row["score"] < self.minimum_buy_score:
            return False
        if row["percent_change"] <= self.minimum_daily_move_pct:
            return False

        trend_state = str(row.get("trend_state") or "unknown")
        trend_regime = str(row.get("trend_regime") or "unknown")
        market_regime = str(row.get("market_regime") or "cautious")
        benchmark_excess = self._value_or_default(row.get("benchmark_excess_pct"), 0.0)
        sector_relative = self._value_or_default(row.get("sector_relative_strength_pct"), 0.0)
        sector_breadth = self._value_or_default(row.get("sector_breadth_pct"), 0.0)
        benchmark_breadth = self._value_or_default(row.get("benchmark_breadth"), 50.0)
        trend_quality = self._value_or_default(row.get("trend_quality_score"), 50.0)
        persistence = self._value_or_default(row.get("persistence_score"), 50.0)
        follow_through = self._value_or_default(row.get("follow_through_score"), 50.0)
        paper_learning = self._value_or_default(
            row.get("paper_learning_adjustment"), 0.0
        )
        sector_caution = paper_learning <= -2.0
        sector_boost = paper_learning >= 1.5
        news_label = str(row.get("news_signal_label") or "neutral")
        news_negative_count = int(row.get("news_negative_count") or 0)
        has_trend_metadata = not (
            trend_state == "unknown" and trend_regime == "unknown"
        )

        news_negative_weight = self._value_or_default(row.get("news_negative_weight"), 0.0)
        news_high_impact_negative_count = int(
            row.get("news_high_impact_negative_count") or 0
        )
        if (
            news_label == "adverse"
            and (
                news_negative_count >= 2
                or news_negative_weight >= 3.0
                or news_high_impact_negative_count >= 1
            )
        ):
            return False

        if not has_trend_metadata:
            if sector_caution and (
                benchmark_excess < 0.5
                or sector_relative < 0.5
                or sector_breadth < 55.0
                or row["score"] < (self.minimum_buy_score + 4.0)
            ):
                return False
            if market_regime == "risk_off":
                return (
                    benchmark_excess >= 0.25
                    and sector_relative >= 0.0
                    and sector_breadth >= 50.0
                    and row["score"] >= (self.minimum_buy_score + 2.0)
                )
            return (
                benchmark_excess >= -0.25
                and sector_relative >= -0.5
                and sector_breadth >= 40.0
            )

        if trend_state == "downtrend" or trend_regime == "breakdown":
            return False
        if (
            sector_caution
            and follow_through < 62.0
            and benchmark_excess < 0.5
        ):
            return False
        if sector_caution and (
            benchmark_excess < 0.0
            or sector_relative < 0.25
            or sector_breadth < 50.0
        ):
            return False
        if market_regime == "risk_off":
            return (
                trend_state in {"uptrend", "extended_uptrend"}
                and trend_regime in {"leadership", "constructive"}
                and trend_quality >= (72.0 if sector_caution else 68.0)
                and persistence >= (68.0 if sector_caution else (62.0 if sector_boost else 64.0))
                and benchmark_excess >= (0.5 if sector_caution else 0.0)
                and sector_relative >= 0.0
                and sector_breadth >= 55.0
                and benchmark_breadth >= 25.0
                and follow_through >= (67.0 if sector_caution else (61.0 if sector_boost else 63.0))
            )
        if market_regime == "cautious":
            return (
                trend_state in {"uptrend", "extended_uptrend", "improving"}
                and trend_regime in {"leadership", "constructive", "repair"}
                and trend_quality >= (64.0 if sector_caution else (58.0 if sector_boost else 60.0))
                and persistence >= (58.0 if sector_caution else (52.0 if sector_boost else 54.0))
                and benchmark_excess >= (0.25 if sector_caution else -0.25)
                and sector_relative >= (0.25 if sector_caution else -0.25)
                and sector_breadth >= (55.0 if sector_caution else 45.0)
                and follow_through >= (62.0 if sector_caution else (54.0 if sector_boost else 56.0))
            )
        return (
            trend_state in {"uptrend", "extended_uptrend", "improving"}
            and trend_quality >= (60.0 if sector_caution else (53.0 if sector_boost else 55.0))
            and persistence >= (56.0 if sector_caution else (50.0 if sector_boost else 52.0))
            and sector_breadth >= (50.0 if sector_caution else 40.0)
            and follow_through >= (58.0 if sector_caution else (50.0 if sector_boost else 52.0))
        )

    def _should_create_exit(self, row):
        if row["category"] == "Avoid" or row["score"] <= self.maximum_exit_score:
            return True
        if (
            str(row.get("trend_state") or "unknown") == "downtrend"
            and self._value_or_default(row.get("benchmark_excess_pct"), 0.0) <= -2.0
            and self._value_or_default(row.get("trend_quality_score"), 50.0) < 48.0
        ):
            return True
        if (
            self._value_or_default(row.get("persistence_score"), 50.0) <= 42.0
            and self._value_or_default(row.get("benchmark_breadth"), 50.0) <= 25.0
            and self._value_or_default(row.get("benchmark_excess_pct"), 0.0) <= -0.75
        ):
            return True
        if (
            str(row.get("news_signal_label") or "neutral") == "adverse"
            and (
                int(row.get("news_negative_count") or 0) >= 2
                or self._value_or_default(row.get("news_negative_weight"), 0.0) >= 3.0
                or int(row.get("news_high_impact_negative_count") or 0) >= 1
            )
            and self._value_or_default(row.get("benchmark_excess_pct"), 0.0) <= -0.5
        ):
            return True
        if (
            self._value_or_default(row.get("follow_through_score"), 50.0) <= 60.0
            and self._value_or_default(row.get("sector_relative_strength_pct"), 0.0) <= -1.0
            and self._value_or_default(row.get("sector_breadth_pct"), 50.0) <= 25.0
        ):
            return True
        return (
            str(row.get("market_regime") or "cautious") == "risk_off"
            and str(row.get("trend_regime") or "unknown") == "breakdown"
            and self._value_or_default(row.get("benchmark_excess_pct"), 0.0) <= -1.0
        )

    def _regime_alignment_bonus(self, row):
        market_regime = str(row.get("market_regime") or "cautious")
        trend_state = str(row.get("trend_state") or "unknown")
        trend_regime = str(row.get("trend_regime") or "unknown")
        bonus = 0.0
        if market_regime == "risk_on":
            if trend_state in {"uptrend", "extended_uptrend"}:
                bonus += 4.0
            if trend_regime == "leadership":
                bonus += 3.0
        elif market_regime == "cautious":
            if trend_state == "uptrend":
                bonus += 2.0
            elif trend_state == "mixed":
                bonus -= 2.0
            if trend_regime == "repair":
                bonus += 1.0
        else:
            if trend_state in {"mixed", "downtrend"}:
                bonus -= 4.0
            if trend_regime == "breakdown":
                bonus -= 5.0
            if trend_regime == "leadership":
                bonus += 2.0
        return bonus

    def _target_shares(self, cash, price):
        target_value = float(cash) * self.target_position_pct / 100
        return math.floor(target_value / price)

    def _buy_thesis(self, row):
        news_event = self._friendly_news_event(row.get("news_dominant_event_type"))
        return (
            f"Atlas paper entry rule: {row['ticker']} qualifies because its "
            f"{row['score']:.1f} Atlas score is above the "
            f"{self.minimum_buy_score:.1f} buy threshold, it is categorized as "
            f"{row['category']}, it is in {row['sector']}, and today's "
            f"{row['percent_change']:+.2f}% move does not breach the downside "
            f"filter. It is also {row['benchmark_excess_pct']:+.2f}% versus "
            f"{row['benchmark_reference']} today. Atlas reads the market regime "
            f"as {row['market_regime'].replace('_', ' ')} with a "
            f"{row['trend_regime']} internal trend regime, and the dominant news "
            f"event is {news_event}. Target size is "
            f"{self.target_position_pct:.1f}% of starting simulated cash."
        )

    def _buy_rationale(self, row):
        scores = row.get("scores") or {}
        strongest = sorted(
            (
                (name, float(value))
                for name, value in scores.items()
                if value is not None
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:2]
        rationale = [
            (
                f"Atlas score {row['score']:.1f} is above the "
                f"{self.minimum_buy_score:.1f} paper-buy threshold."
            ),
            (
                f"Today's move is {row['benchmark_excess_pct']:+.2f}% versus "
                f"{row['benchmark_reference']}, which helps Atlas target names that "
                "are outperforming the stronger benchmark."
            ),
            (
                f"Trend quality is {row['trend_quality_score']:.1f} with a current "
                f"state of {row['trend_state'].replace('_', ' ')}."
            ),
            (
                f"Sector rotation is {row['sector_relative_strength_pct']:+.2f}% "
                f"versus {row['benchmark_reference']} and ranks #{int(row['sector_rank'])} across tracked sectors."
            ),
            (
                f"Sector breadth is {row['sector_breadth_pct']:.0f}% positive while benchmark breadth is {row['benchmark_breadth']:.0f}% positive."
            ),
            (
                f"Multi-day persistence score is {row['persistence_score']:.1f}, which helps Atlas prefer setups that have held up beyond a single day."
            ),
            (
                f"Follow-through score is {row['follow_through_score']:.1f}, which helps Atlas prefer moves backed by sector and benchmark confirmation."
            ),
            (
                f"News tone is {row['news_signal_label'].replace('_', ' ')} with "
                f"{int(row['news_positive_count'])} positive and {int(row['news_negative_count'])} negative company headlines."
                f" Atlas classifies the dominant event as {row['news_dominant_event_type'].replace('_', ' ')}."
            ),
            (
                f"Trend regime is {row['trend_regime'].replace('_', ' ')} while "
                f"the broader market regime is {row['market_regime'].replace('_', ' ')}."
            ),
            f"Current category is {row['category']}; sector is {row['sector']}.",
            (
                f"Latest move is {row['percent_change']:+.2f}%, above the "
                f"{self.minimum_daily_move_pct:+.2f}% downside filter."
            ),
            (
                f"Suggested size is limited to {self.target_position_pct:.1f}% "
                "of starting simulated cash."
            ),
        ]
        if strongest:
            rationale.insert(
                1,
                "Strongest score inputs: "
                + ", ".join(f"{name} {value:.0f}" for name, value in strongest)
                + ".",
            )
        paper_learning_summary = str(row.get("paper_learning_summary") or "").strip()
        if paper_learning_summary:
            rationale.insert(
                2,
                paper_learning_summary,
            )
        sector_gate_summary = self._sector_learning_gate_rationale(
            row.get("sector_learning_gate") or {}
        )
        if sector_gate_summary:
            rationale.insert(
                3 if paper_learning_summary else 2,
                sector_gate_summary,
            )
        return rationale

    @staticmethod
    def _sector_learning_gate_rationale(gate):
        if not gate or not gate.get("active"):
            return ""
        posture = str(gate.get("posture") or "watch")
        if posture == "caution":
            passed_checks = [
                item
                for item in gate.get("checks") or []
                if item.get("passed")
            ]
            total_checks = len(gate.get("checks") or [])
            return (
                f"Sector learning gate: {gate.get('summary')} "
                f"{len(passed_checks)} of {total_checks} stronger confirmation checks passed."
            )
        if posture == "boost":
            return f"Sector learning gate: {gate.get('summary')}"
        return ""

    @staticmethod
    def _paper_learning_context(account, market_data):
        prices = {
            ticker: float(data.get("price"))
            for ticker, data in market_data.items()
            if data.get("status") == "available" and data.get("price") is not None
        }
        feedback_rows = account.proposal_feedback(latest_prices=prices)
        ticker_context = {}
        sector_stats = {}
        for row in feedback_rows:
            if str(row.get("side") or "").lower() != "buy":
                continue
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            sector = str((market_data.get(ticker) or {}).get("sector") or "Unclassified")
            horizons = [
                item
                for item in (row.get("horizon_outcomes") or [])
                if item.get("available") and int(item.get("snapshots") or 0) == 3
            ]
            latest = ticker_context.get(ticker)
            if latest is None or str(row.get("filled_at") or "") > str(latest.get("filled_at") or ""):
                adjustment = 0.0
                summary = ""
                if horizons:
                    verdict = str(horizons[0].get("verdict") or "").strip().lower()
                    if verdict == "working":
                        adjustment += 3.0
                        summary = (
                            f"Paper learning boost +3.0: the latest judged {ticker} buy stayed working through the 3-snapshot checkpoint."
                        )
                    elif verdict == "lagging":
                        adjustment -= 4.0
                        summary = (
                            f"Paper learning caution -4.0: the latest judged {ticker} buy stayed lagging through the 3-snapshot checkpoint."
                        )
                ticker_context[ticker] = {
                    "filled_at": row.get("filled_at"),
                    "adjustment": adjustment,
                    "summary": summary,
                }
            if horizons:
                stats = sector_stats.setdefault(
                    sector,
                    {"working": 0, "lagging": 0, "judged": 0},
                )
                verdict = str(horizons[0].get("verdict") or "").strip().lower()
                if verdict in {"working", "lagging", "mixed"}:
                    stats["judged"] += 1
                    if verdict == "working":
                        stats["working"] += 1
                    elif verdict == "lagging":
                        stats["lagging"] += 1
        sector_context = {}
        for item in PaperStrategy._sector_learning_cards_from_stats(sector_stats):
            sector_context[item["sector"]] = {
                "adjustment": item["adjustment"],
                "summary": item["summary"],
            }
        return {"tickers": ticker_context, "sectors": sector_context}

    @staticmethod
    def sector_learning_summary_from_feedback(feedback_rows, market_data):
        """Expose the sector-level paper-learning adjustment used by strategy."""
        sector_stats = {}
        for row in feedback_rows or []:
            if str(row.get("side") or "").lower() != "buy":
                continue
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            sector = str((market_data.get(ticker) or {}).get("sector") or "Unclassified")
            horizons = [
                item
                for item in (row.get("horizon_outcomes") or [])
                if item.get("available") and int(item.get("snapshots") or 0) == 3
            ]
            if not horizons:
                continue
            verdict = str(horizons[0].get("verdict") or "").strip().lower()
            if verdict not in {"working", "mixed", "lagging"}:
                continue
            stats = sector_stats.setdefault(
                sector,
                {"working": 0, "mixed": 0, "lagging": 0, "judged": 0},
            )
            stats["judged"] += 1
            stats[verdict] += 1

        sectors = PaperStrategy._sector_learning_cards_from_stats(sector_stats)
        active = any(float(item.get("adjustment") or 0.0) != 0.0 for item in sectors)
        if active:
            headline = (
                "Atlas has sector-level paper learning that can tilt new simulated "
                "entries and tighten confirmation for lagging sectors."
            )
        elif sectors:
            headline = "Atlas is tracking sector-level paper learning, but no sector has earned a boost or caution yet."
        else:
            headline = "Atlas is waiting for enough 3-snapshot buy evidence to score sector learning."
        return {
            "enabled": True,
            "active": active,
            "headline": headline,
            "checkpoint": "3-snapshot persistence",
            "minimum_judged_buys": 2,
            "sectors": sectors,
        }

    @classmethod
    def sector_gate_audit(cls, account, market_data):
        """Summarize how sector-learning gates affect candidates and accepted buys."""
        strategy = cls.from_account_policy(account)
        benchmark_context = strategy._benchmark_context(
            market_data,
            preferred_benchmark=strategy.preferred_benchmark,
        )
        learning_context = strategy._paper_learning_context(account, market_data)
        candidates = strategy._candidate_rows(
            market_data,
            benchmark_context,
            learning_context,
        )
        candidate_rows = []
        sectors = {}
        candidate_counts = {
            "total": len(candidates),
            "active": 0,
            "caution": 0,
            "cleared": 0,
            "tightened": 0,
            "boost": 0,
            "watch": 0,
            "buy_eligible": 0,
        }
        for row in candidates:
            gate = row.get("sector_learning_gate") or {}
            posture = str(gate.get("posture") or "watch")
            status = str(gate.get("status") or "watch")
            active = bool(gate.get("active"))
            buy_eligible = strategy._can_open_buy(row)
            if buy_eligible:
                candidate_counts["buy_eligible"] += 1
            if active:
                candidate_counts["active"] += 1
            if posture == "caution":
                candidate_counts["caution"] += 1
            elif posture == "boost":
                candidate_counts["boost"] += 1
            else:
                candidate_counts["watch"] += 1
            if status == "cleared":
                candidate_counts["cleared"] += 1
            elif status == "tightened":
                candidate_counts["tightened"] += 1

            sector_name = str(row.get("sector") or "Unclassified")
            sector = sectors.setdefault(
                sector_name,
                {
                    "sector": sector_name,
                    "total": 0,
                    "active": 0,
                    "caution": 0,
                    "cleared": 0,
                    "tightened": 0,
                    "boost": 0,
                    "buy_eligible": 0,
                },
            )
            sector["total"] += 1
            if active:
                sector["active"] += 1
            if posture in {"caution", "boost"}:
                sector[posture] += 1
            if status in {"cleared", "tightened"}:
                sector[status] += 1
            if buy_eligible:
                sector["buy_eligible"] += 1

            if active:
                checks = gate.get("checks") or []
                passed = sum(1 for item in checks if item.get("passed"))
                candidate_rows.append(
                    {
                        "ticker": row.get("ticker"),
                        "sector": sector_name,
                        "posture": posture,
                        "status": status,
                        "summary": gate.get("summary"),
                        "passed_checks": passed,
                        "total_checks": len(checks),
                        "buy_eligible": buy_eligible,
                        "selection_score": strategy._selection_score(row),
                    }
                )

        accepted = cls._accepted_sector_gate_decisions(account)
        active = candidate_counts["active"] > 0 or accepted["with_gate"] > 0
        if candidate_counts["tightened"]:
            headline = (
                "Sector learning is actively tightening simulated entries where "
                "recent sector evidence has lagged."
            )
        elif candidate_counts["cleared"]:
            headline = (
                "Some lagging-sector candidates are clearing the stronger "
                "confirmation bar."
            )
        elif candidate_counts["boost"]:
            headline = (
                "Constructive sector learning is providing modest simulated-entry "
                "support without bypassing core filters."
            )
        else:
            headline = "Atlas is monitoring sector gates, but no active gate is affecting today's candidates."
        return {
            "enabled": True,
            "active": active,
            "headline": headline,
            "candidate_counts": candidate_counts,
            "accepted_decision_counts": {
                key: accepted[key]
                for key in (
                    "total_buy_recommendations",
                    "with_gate",
                    "cleared",
                    "tightened",
                    "boost",
                )
            },
            "sectors": sorted(
                sectors.values(),
                key=lambda item: (
                    int(item.get("active") or 0),
                    int(item.get("tightened") or 0),
                    int(item.get("cleared") or 0),
                    int(item.get("buy_eligible") or 0),
                    item.get("sector") or "",
                ),
                reverse=True,
            ),
            "candidate_examples": sorted(
                candidate_rows,
                key=lambda item: (
                    item.get("status") == "tightened",
                    item.get("status") == "cleared",
                    float(item.get("selection_score") or 0.0),
                ),
                reverse=True,
            )[:8],
            "accepted_examples": accepted["examples"][:8],
        }

    @staticmethod
    def _accepted_sector_gate_decisions(account):
        summary = {
            "total_buy_recommendations": 0,
            "with_gate": 0,
            "cleared": 0,
            "tightened": 0,
            "boost": 0,
            "examples": [],
        }
        recommendations = (
            account.recommendations()
            if hasattr(account, "recommendations")
            else []
        )
        for recommendation in recommendations:
            if str(recommendation.get("side") or "").lower() != "buy":
                continue
            summary["total_buy_recommendations"] += 1
            rationale = recommendation.get("rationale") or []
            gate_lines = [
                str(line)
                for line in rationale
                if str(line).startswith("Sector learning gate:")
            ]
            if not gate_lines:
                continue
            line = gate_lines[0]
            lower_line = line.lower()
            status = "watch"
            if "cleared" in lower_line:
                status = "cleared"
            elif "tightened" in lower_line:
                status = "tightened"
            elif "constructive" in lower_line or "boost" in lower_line:
                status = "boost"
            summary["with_gate"] += 1
            if status in {"cleared", "tightened", "boost"}:
                summary[status] += 1
            summary["examples"].append(
                {
                    "ticker": recommendation.get("ticker"),
                    "status": status,
                    "rationale": line,
                    "created_at": recommendation.get("created_at"),
                    "recommendation_id": recommendation.get("recommendation_id"),
                }
            )
        summary["examples"] = sorted(
            summary["examples"],
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )
        return summary

    @staticmethod
    def _sector_learning_cards_from_stats(sector_stats):
        sectors = []
        for sector, stats in sector_stats.items():
            judged = int(stats.get("judged") or 0)
            working = int(stats.get("working") or 0)
            mixed = int(stats.get("mixed") or 0)
            lagging = int(stats.get("lagging") or 0)
            adjustment = 0.0
            posture = "watch"
            summary = ""
            if judged >= 2:
                if working > lagging:
                    adjustment = 1.5
                    posture = "boost"
                    summary = (
                        f"Paper learning sector boost +1.5: recent judged buys in {sector} stayed constructive through the 3-snapshot checkpoint."
                    )
                elif lagging > working:
                    adjustment = -2.0
                    posture = "caution"
                    summary = (
                        f"Paper learning sector caution -2.0: recent judged buys in {sector} lost follow-through by the 3-snapshot checkpoint."
                        " Atlas now requires stronger confirmation before adding another simulated entry there."
                    )
            if not summary:
                summary = (
                    f"Atlas is watching {sector}: {judged} judged buy"
                    f"{'' if judged == 1 else 's'} have reached the 3-snapshot checkpoint."
                )
            sectors.append(
                {
                    "sector": sector,
                    "posture": posture,
                    "adjustment": adjustment,
                    "judged": judged,
                    "working": working,
                    "mixed": mixed,
                    "lagging": lagging,
                    "working_rate_pct": (
                        round((working / judged) * 100.0, 1) if judged else None
                    ),
                    "summary": summary,
                }
            )
        return sorted(
            sectors,
            key=lambda item: (
                abs(float(item.get("adjustment") or 0.0)),
                int(item.get("judged") or 0),
                float(item.get("working_rate_pct") or 0.0),
                item.get("sector") or "",
            ),
            reverse=True,
        )

    @staticmethod
    def _paper_learning_summary(ticker_learning, sector_learning):
        parts = []
        ticker_summary = str((ticker_learning or {}).get("summary") or "").strip()
        sector_summary = str((sector_learning or {}).get("summary") or "").strip()
        if ticker_summary:
            parts.append(ticker_summary)
        if sector_summary:
            parts.append(sector_summary)
        return " ".join(parts)

    @staticmethod
    def _trend_quality_score(data):
        metrics = data.get("momentum_metrics") or {}
        value = metrics.get("trend_quality_score")
        if value is None:
            value = metrics.get("momentum_score")
        try:
            return float(value) if value is not None else 50.0
        except (TypeError, ValueError):
            return 50.0

    @staticmethod
    def _trend_state(data):
        metrics = data.get("momentum_metrics") or {}
        value = metrics.get("trend_state")
        return str(value or "unknown")

    @staticmethod
    def _trend_regime(data):
        metrics = data.get("momentum_metrics") or {}
        value = metrics.get("trend_regime")
        return str(value or "unknown")

    @staticmethod
    def _trend_regime_score(data):
        metrics = data.get("momentum_metrics") or {}
        value = metrics.get("trend_regime_score")
        try:
            return float(value) if value is not None else 50.0
        except (TypeError, ValueError):
            return 50.0

    def _sell_thesis(self, row):
        news_event = self._friendly_news_event(row.get("news_dominant_event_type"))
        if row["category"] == "Avoid" or row["score"] <= self.maximum_exit_score:
            return (
                f"Atlas paper exit rule: {row['ticker']} has score "
                f"{row['score']:.1f} and category {row['category']}. "
                f"Atlas reads the dominant news event as {news_event}."
            )
        return (
            f"Atlas paper exit rule: {row['ticker']} is in {row['trend_state']} / "
            f"{row['trend_regime']} trend posture and is underperforming "
            f"{row['benchmark_reference']} by {row['benchmark_excess_pct']:+.2f}% "
            f"during a {row['market_regime'].replace('_', ' ')} market regime. "
            f"Its sector rotation is {row['sector_relative_strength_pct']:+.2f}% and "
            f"sector breadth is {row['sector_breadth_pct']:.0f}%, persistence is "
            f"{row['persistence_score']:.1f}, follow-through score is "
            f"{row['follow_through_score']:.1f}, and news tone is "
            f"{row['news_signal_label'].replace('_', ' ')} with dominant event "
            f"{news_event}."
        )

    @staticmethod
    def _news_signal_score(data):
        signal = data.get("news_signal") or {}
        value = signal.get("signal_score")
        try:
            return float(value) if value is not None else 50.0
        except (TypeError, ValueError):
            return 50.0

    @staticmethod
    def _news_signal_label(data):
        signal = data.get("news_signal") or {}
        return str(signal.get("signal_label") or "neutral")

    @staticmethod
    def _news_negative_count(data):
        signal = data.get("news_signal") or {}
        try:
            return int(signal.get("negative_count") or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _news_positive_count(data):
        signal = data.get("news_signal") or {}
        try:
            return int(signal.get("positive_count") or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _news_negative_weight(data):
        signal = data.get("news_signal") or {}
        try:
            return float(signal.get("negative_weight") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _news_positive_weight(data):
        signal = data.get("news_signal") or {}
        try:
            return float(signal.get("positive_weight") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _news_high_impact_negative_count(data):
        signal = data.get("news_signal") or {}
        try:
            return int(signal.get("high_impact_negative_count") or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _news_high_impact_positive_count(data):
        signal = data.get("news_signal") or {}
        try:
            return int(signal.get("high_impact_positive_count") or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _news_dominant_event_type(data):
        signal = data.get("news_signal") or {}
        return str(signal.get("dominant_event_type") or "routine")

    @staticmethod
    def _friendly_news_event(value):
        text = str(value or "").strip().lower()
        if not text or text == "routine":
            return "routine mention"
        return text.replace("_", " ")

    @staticmethod
    def _persistence_score(data):
        metrics = data.get("momentum_metrics") or {}
        weights = (
            (metrics.get("return_1m"), 0.20, 50.0),
            (metrics.get("return_3m"), 0.20, 50.0),
            (metrics.get("return_6m"), 0.15, 50.0),
            (metrics.get("ema_20_slope_pct"), 0.15, 45.0),
            (metrics.get("price_vs_sma_20_pct"), 0.10, 40.0),
            (metrics.get("price_vs_sma_50_pct"), 0.10, 40.0),
            (metrics.get("drawdown_63d_pct"), 0.10, 55.0),
        )
        total = 0.0
        total_weight = 0.0
        for value, weight, center in weights:
            if value is None:
                continue
            if center == 55.0:
                scaled = 55.0 + max(-20.0, min(20.0, float(value) * 1.2))
            elif center == 45.0:
                scaled = 45.0 + max(-20.0, min(20.0, float(value) * 4.0))
            else:
                scaled = center + max(-20.0, min(20.0, float(value) * 1.8))
            total += max(0.0, min(100.0, scaled)) * weight
            total_weight += weight
        if total_weight == 0.0:
            return 50.0
        return round(total / total_weight, 1)

    @staticmethod
    def _follow_through_score(
        *,
        score,
        percent_change,
        benchmark_excess_pct,
        sector_relative_strength_pct,
        sector_breadth_pct,
        benchmark_breadth,
        persistence_score,
        trend_quality_score,
        trend_regime_score,
    ):
        composite = (
            (PaperStrategy._value_or_default(score, 50.0) * 0.18)
            + ((50.0 + max(-8.0, min(8.0, PaperStrategy._value_or_default(percent_change, 0.0) * 4.0))) * 0.12)
            + ((50.0 + max(-10.0, min(10.0, PaperStrategy._value_or_default(benchmark_excess_pct, 0.0) * 5.0))) * 0.24)
            + ((50.0 + max(-10.0, min(10.0, PaperStrategy._value_or_default(sector_relative_strength_pct, 0.0) * 5.0))) * 0.18)
            + (PaperStrategy._value_or_default(sector_breadth_pct, 50.0) * 0.08)
            + (PaperStrategy._value_or_default(benchmark_breadth, 50.0) * 0.06)
            + (PaperStrategy._value_or_default(persistence_score, 50.0) * 0.12)
            + (PaperStrategy._value_or_default(trend_quality_score, 50.0) * 0.12)
            + (PaperStrategy._value_or_default(trend_regime_score, 50.0) * 0.10)
        )
        return round(max(0.0, min(100.0, composite)), 1)
