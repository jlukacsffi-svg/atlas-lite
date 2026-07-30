"""Daily thesis monitoring for open Atlas paper positions."""

from app.data_quality import has_reliable_daily_change
from app.scoring import ScoringEngine

DEFAULT_PROJECTION_TRIM_EXCESS_PCT = -2.5
DEFAULT_PROJECTION_TRIM_SECTOR_BREADTH_PCT = 35.0
DEFAULT_PROJECTION_REVIEW_EXCESS_PCT = 0.0
DEFAULT_PROJECTION_REVIEW_SECTOR_BREADTH_PCT = 45.0
DEFAULT_PROJECTION_ADD_SECTOR_BREADTH_PCT = 60.0
DEFAULT_PROJECTION_ADD_TREND_QUALITY = 70.0


class PaperPositionMonitor:
    """Record holding reviews and create reviewable exit proposals."""

    def __init__(
        self,
        exit_score=60.0,
        review_score=70.0,
        drawdown_review_pct=-10.0,
        benchmark_lag_review_pct=-3.0,
        benchmark_lag_trim_pct=-8.0,
        benchmark_lag_min_snapshots=2,
        add_score=92.0,
        add_return_pct=6.0,
        add_excess_pct=2.0,
        add_min_snapshots=3,
        add_fraction_of_target=0.5,
        repeated_review_trim_count=2,
        maximum_partial_trims_per_position=2,
        projection_trim_excess_pct=DEFAULT_PROJECTION_TRIM_EXCESS_PCT,
        projection_trim_sector_breadth_pct=DEFAULT_PROJECTION_TRIM_SECTOR_BREADTH_PCT,
        projection_review_excess_pct=DEFAULT_PROJECTION_REVIEW_EXCESS_PCT,
        projection_review_sector_breadth_pct=DEFAULT_PROJECTION_REVIEW_SECTOR_BREADTH_PCT,
        projection_add_sector_breadth_pct=DEFAULT_PROJECTION_ADD_SECTOR_BREADTH_PCT,
        projection_add_trend_quality=DEFAULT_PROJECTION_ADD_TREND_QUALITY,
    ):
        self.exit_score = float(exit_score)
        self.review_score = float(review_score)
        self.drawdown_review_pct = float(drawdown_review_pct)
        self.benchmark_lag_review_pct = float(benchmark_lag_review_pct)
        self.benchmark_lag_trim_pct = float(benchmark_lag_trim_pct)
        self.benchmark_lag_min_snapshots = int(benchmark_lag_min_snapshots)
        self.add_score = float(add_score)
        self.add_return_pct = float(add_return_pct)
        self.add_excess_pct = float(add_excess_pct)
        self.add_min_snapshots = int(add_min_snapshots)
        self.add_fraction_of_target = float(add_fraction_of_target)
        self.repeated_review_trim_count = int(repeated_review_trim_count)
        self.maximum_partial_trims_per_position = max(
            int(maximum_partial_trims_per_position),
            0,
        )
        self.projection_trim_excess_pct = float(projection_trim_excess_pct)
        self.projection_trim_sector_breadth_pct = float(
            projection_trim_sector_breadth_pct
        )
        self.projection_review_excess_pct = float(projection_review_excess_pct)
        self.projection_review_sector_breadth_pct = float(
            projection_review_sector_breadth_pct
        )
        self.projection_add_sector_breadth_pct = float(
            projection_add_sector_breadth_pct
        )
        self.projection_add_trend_quality = float(projection_add_trend_quality)
        self.scoring_engine = ScoringEngine()

    @classmethod
    def from_account(cls, account, latest_prices=None):
        overrides = {}
        if hasattr(account, "effective_policy"):
            policy = account.effective_policy()
            overrides["maximum_partial_trims_per_position"] = int(
                policy.get("maximum_partial_trims_per_position", 2)
            )
        if hasattr(account, "projection_threshold_profile"):
            profile = account.projection_threshold_profile(latest_prices=latest_prices)
            overrides.update(profile.get("monitor_overrides", {}))
        return cls(**overrides)

    def review(self, account, market_data):
        state = account.load()
        today = account.clock().date().isoformat()
        reviewed_today = {
            review["ticker"]
            for review in account.position_reviews()
            if str(review.get("timestamp", "")).startswith(today)
        }
        active_sells = {
            proposal["ticker"]
            for proposal in account.proposals()
            if proposal["side"] == "sell"
            and proposal["status"] in {"pending", "approved"}
        }
        active_buys = {
            proposal["ticker"]
            for proposal in account.proposals()
            if proposal["side"] == "buy"
            and proposal["status"] in {"pending", "approved"}
        }
        benchmark_lag = self._benchmark_lag(
            account.proposal_feedback(
                latest_prices={
                    ticker: data.get("price")
                    for ticker, data in market_data.items()
                    if data.get("price") is not None
                }
            )
        )
        sector_breadth = self._sector_breadth(market_data)
        benchmark_day = self._benchmark_day_context(market_data)
        reviews = []
        exit_proposals = []

        for ticker, position in sorted(state.get("positions", {}).items()):
            if ticker in reviewed_today:
                continue
            data = market_data.get(ticker, {})
            price = data.get("price")
            flags = []
            if data.get("status") != "available" or price is None:
                continue

            return_pct = (
                (float(price) / float(position["average_cost"]) - 1) * 100
                if position["average_cost"]
                else 0.0
            )
            score = self._score(data)
            category = data.get("category", "Watchlist")
            score_text = f"{score:.1f}" if score is not None else "N/A"
            lag = benchmark_lag.get(ticker)
            sell_shares = position["shares"]
            news_signal = data.get("news_signal") or {}
            benchmark_context = self._position_benchmark_context(
                account,
                ticker=ticker,
                current_price=price,
            )
            projection = self._projection_signals(
                data=data,
                benchmark_context=benchmark_context,
                sector_breadth=sector_breadth.get(
                    str(data.get("sector") or "Unclassified")
                ),
                benchmark_day=benchmark_day,
                news_signal=news_signal,
            )
            verdict, flags, sell_shares = self._review_decision(
                category=category,
                score=score,
                score_text=score_text,
                return_pct=return_pct,
                lag=lag,
                current_shares=position["shares"],
                account=account,
                ticker=ticker,
                news_signal=news_signal,
                projection=projection,
            )
            thesis = self._review_thesis(
                ticker=ticker,
                verdict=verdict,
                category=category,
                score_text=score_text,
                return_pct=return_pct,
                lag=lag,
                projection=projection,
            )
            review = account.record_position_review(
                ticker=ticker,
                verdict=verdict,
                current_price=price,
                return_pct=return_pct,
                atlas_score=score,
                flags=flags,
                thesis=thesis,
            )
            reviews.append(review)

            if verdict == "exit" and ticker not in active_sells:
                exit_proposals.append(
                    account.create_proposal(
                        side="sell",
                        ticker=ticker,
                        shares=sell_shares,
                        reference_price=price,
                        thesis=thesis,
                        source="paper_monitor_v1",
                        rationale=flags,
                    )
                )
            elif (
                verdict == "maintain"
                and ticker not in active_buys
                and self._should_add_to_winner(
                    account,
                    position=position,
                    current_price=price,
                    score=score,
                    benchmark_context=benchmark_context,
                    projection=projection,
                )
            ):
                add_shares = self._add_shares(account, current_price=price)
                if add_shares > 0:
                    thesis = self._add_thesis(
                        ticker=ticker,
                        score=score,
                        return_pct=return_pct,
                        benchmark_context=benchmark_context,
                    )
                    preview = account.preview_order(
                        "buy",
                        ticker,
                        add_shares,
                        price,
                        thesis,
                    )
                    if preview["valid"]:
                        exit_proposals.append(
                            account.create_proposal(
                                side="buy",
                                ticker=ticker,
                                shares=add_shares,
                                reference_price=price,
                                thesis=thesis,
                                source="paper_monitor_v1",
                                rationale=self._add_rationale(
                                    score=score,
                                    return_pct=return_pct,
                                    benchmark_context=benchmark_context,
                                    projection=projection,
                                ),
                            )
                        )

        return {"reviews": reviews, "exit_proposals": exit_proposals}

    def _review_decision(
        self,
        *,
        category,
        score,
        score_text,
        return_pct,
        lag,
        current_shares,
        account,
        ticker,
        news_signal,
        projection,
    ):
        flags = []
        verdict = "maintain"
        sell_shares = current_shares

        hard_exit = category == "Avoid" or (
            score is not None and score <= self.exit_score
        )
        if hard_exit:
            verdict = "exit"
            reasons = []
            if category == "Avoid":
                reasons.append(f"category is {category}")
            if score is not None and score <= self.exit_score:
                reasons.append(
                    f"Atlas score {score_text} is at or below the {self.exit_score:.1f} exit threshold"
                )
            flags.append("Exit rule triggered: " + "; ".join(reasons) + ".")

        if score is None:
            verdict = "review" if verdict == "maintain" else verdict
            flags.append("Atlas score is unavailable, so the thesis needs review.")
        elif score <= self.review_score and not hard_exit:
            verdict = "review" if verdict == "maintain" else verdict
            flags.append(
                f"Atlas score {score:.1f} is below the {self.review_score:.1f} review threshold."
            )

        if return_pct <= self.drawdown_review_pct:
            verdict = "review" if verdict == "maintain" else verdict
            flags.append(
                f"Position return {return_pct:+.2f}% is below the {self.drawdown_review_pct:.2f}% review threshold."
            )

        if lag and lag["lag_pct"] <= self.benchmark_lag_trim_pct and not hard_exit:
            verdict = "exit"
            sell_shares = self._trim_shares(current_shares)
            flags.append(self._lag_flag(lag, "Trim rule triggered"))
        elif lag and lag["lag_pct"] <= self.benchmark_lag_review_pct:
            verdict = "review" if verdict == "maintain" else verdict
            flags.append(self._lag_flag(lag, "Benchmark review triggered"))

        if (
            verdict == "review"
            and not hard_exit
            and self._has_repeated_review_weakness(account, ticker)
        ):
            verdict = "exit"
            sell_shares = self._trim_shares(current_shares)
            flags.append(
                "Repeated review trim triggered: Atlas has now seen multiple recent review-level weakness signals in this holding."
            )

        adverse_news = str(news_signal.get("signal_label") or "neutral") == "adverse"
        negative_count = int(news_signal.get("negative_count") or 0)
        negative_weight = float(news_signal.get("negative_weight") or 0.0)
        high_impact_negative_count = int(
            news_signal.get("high_impact_negative_count") or 0
        )
        dominant_event = self._friendly_news_event(
            news_signal.get("dominant_event_type")
        )
        if adverse_news and (
            negative_count >= 2
            or negative_weight >= 3.0
            or high_impact_negative_count >= 1
        ):
            if return_pct <= 0 and not hard_exit:
                verdict = "exit"
                sell_shares = self._trim_shares(current_shares)
                flags.append(
                    f"News risk trim triggered: recent company-specific negative news is reinforcing the weak thesis, led by {dominant_event}."
                )
            else:
                verdict = "review" if verdict == "maintain" else verdict
                flags.append(
                    f"News caution triggered: recent company-specific negative news requires closer thesis review, led by {dominant_event}."
                )

        if (
            not hard_exit
            and projection.get("sector_breadth_pct") is not None
            and projection.get("excess_vs_best_pct") is not None
        ):
            sector_breadth = float(projection["sector_breadth_pct"])
            excess = float(projection["excess_vs_best_pct"])
            trend_regime = str(projection.get("trend_regime") or "unknown")
            news_label = str(projection.get("news_label") or "neutral")
            if (
                excess <= self.projection_trim_excess_pct
                and sector_breadth <= self.projection_trim_sector_breadth_pct
                and trend_regime in {"repair", "fragile", "breakdown"}
            ):
                verdict = "exit"
                sell_shares = self._trim_shares(current_shares)
                flags.append(
                    "Projection de-risk triggered: post-entry benchmark lag, weak sector breadth, and a damaged trend posture now align against this holding."
                )
            elif (
                verdict == "maintain"
                and (
                    excess <= self.projection_review_excess_pct
                    or sector_breadth <= self.projection_review_sector_breadth_pct
                    or news_label == "cautious"
                )
            ):
                verdict = "review"
                flags.append(
                    "Projection caution triggered: Atlas wants more proof because benchmark leadership, sector participation, or news tone is no longer clearly supportive."
                )

        if verdict == "exit" and float(sell_shares) < float(current_shares):
            prior_trims = self._partial_trims_since_entry(account, ticker)
            if prior_trims >= self.maximum_partial_trims_per_position:
                sell_shares = current_shares
                flags.append(
                    "Trim escalation exit triggered: Atlas already reduced this "
                    f"position {prior_trims} times during the current holding cycle, "
                    "so another independent risk signal now closes the remaining "
                    "simulated position instead of creating a fractional remnant."
                )

        return verdict, flags, sell_shares

    @staticmethod
    def _review_thesis(
        ticker,
        verdict,
        category,
        score_text,
        return_pct,
        lag,
        projection=None,
    ):
        action = {
            "maintain": "maintain",
            "review": "review",
            "exit": "reduce or exit",
        }.get(verdict, "review")
        thesis = (
            f"Daily paper thesis review for {ticker}: Atlas currently wants to "
            f"{action} this simulated holding. Category {category}, Atlas score "
            f"{score_text}, position return {return_pct:+.2f}%."
        )
        if lag:
            thesis += (
                f" Benchmark lag is {abs(lag['lag_pct']):.2f} percentage points "
                f"behind {lag['weakest_benchmark']} across {lag['snapshots']} "
                f"snapshots ({lag['security_return_pct']:+.2f}% versus "
                f"{lag['weakest_benchmark_return_pct']:+.2f}%)."
            )
        if projection and projection.get("excess_vs_best_pct") is not None:
            thesis += (
                f" Projection posture is {str(projection.get('projection_state') or 'mixed').replace('_', ' ')} "
                f"with {float(projection['excess_vs_best_pct']):+.2f}% excess return versus "
                f"{projection.get('best_benchmark', 'benchmark')} since entry."
            )
            if projection.get("sector_breadth_pct") is not None:
                thesis += (
                    f" Sector breadth is {float(projection['sector_breadth_pct']):.0f}%."
                )
        return thesis

    def _benchmark_lag(self, feedback_rows):
        lagging = {}
        for row in feedback_rows:
            if row.get("verdict") != "lagging":
                continue
            if int(row.get("snapshots") or 0) < self.benchmark_lag_min_snapshots:
                continue
            security_return = row.get("security_return_pct")
            benchmark_returns = {
                ticker: value
                for ticker, value in row.get("benchmark_returns_pct", {}).items()
                if value is not None
            }
            if security_return is None or not benchmark_returns:
                continue
            weakest_benchmark = min(
                benchmark_returns,
                key=lambda ticker: benchmark_returns[ticker],
            )
            weakest_return = benchmark_returns[weakest_benchmark]
            lag_pct = round(float(security_return) - float(weakest_return), 4)
            ticker = row.get("ticker")
            current = lagging.get(ticker)
            if ticker and (current is None or lag_pct < current["lag_pct"]):
                lagging[ticker] = {
                    "lag_pct": lag_pct,
                    "snapshots": int(row.get("snapshots") or 0),
                    "security_return_pct": float(security_return),
                    "weakest_benchmark": weakest_benchmark,
                    "weakest_benchmark_return_pct": float(weakest_return),
                }
        return lagging

    @staticmethod
    def _friendly_news_event(value):
        text = str(value or "").strip().lower()
        if not text or text == "routine":
            return "routine mention"
        return text.replace("_", " ")

    @staticmethod
    def _trim_shares(shares):
        return max(round(float(shares) / 2, 6), 0.000001)

    @staticmethod
    def _partial_trims_since_entry(account, ticker):
        count = 0
        target = str(ticker or "").strip().upper()
        for event in reversed(account.ledger()):
            if event.get("event") != "paper_trade":
                continue
            if str(event.get("ticker") or "").strip().upper() != target:
                continue
            side = str(event.get("side") or "").strip().lower()
            if side == "buy":
                break
            if side == "sell":
                if float(event.get("position_shares_after") or 0.0) <= 0.0000001:
                    break
                count += 1
        return count

    @staticmethod
    def _lag_flag(lag, prefix):
        return (
            f"{prefix}: simulated return {lag['security_return_pct']:+.2f}% "
            f"trails weaker benchmark {lag['weakest_benchmark']} by "
            f"{abs(lag['lag_pct']):.2f} percentage points across "
            f"{lag['snapshots']} snapshots."
        )

    def _score(self, data):
        scores = data.get("scores")
        if not scores:
            return None
        try:
            return self.scoring_engine.score(scores)
        except (TypeError, ValueError):
            return None

    def _has_repeated_review_weakness(self, account, ticker):
        dates = []
        for review in reversed(account.position_reviews(ticker=ticker)):
            if str(review.get("verdict") or "").lower() != "review":
                continue
            timestamp = str(review.get("timestamp") or "")
            if not timestamp:
                continue
            review_date = timestamp.split("T", 1)[0]
            if review_date in dates:
                continue
            dates.append(review_date)
            if len(dates) >= self.repeated_review_trim_count:
                return True
        return False

    def _position_benchmark_context(self, account, *, ticker, current_price):
        latest_buy = None
        for event in reversed(account.ledger()):
            if event.get("event") != "paper_trade":
                continue
            if str(event.get("ticker") or "").strip().upper() != str(ticker).strip().upper():
                continue
            if str(event.get("side") or "").lower() != "buy":
                continue
            latest_buy = event
            break
        history = account.performance_history()
        latest = history[-1] if history else None
        if not latest_buy or not latest or current_price is None:
            return None
        start = account._first_snapshot_after(history, latest_buy.get("timestamp"))
        if not start or start.get("timestamp") == latest.get("timestamp"):
            return None
        security_return = account._pct_return(latest_buy.get("price"), current_price)
        benchmark_returns = {
            benchmark: account._pct_return(
                start.get("benchmark_prices", {}).get(benchmark),
                latest.get("benchmark_prices", {}).get(benchmark),
            )
            for benchmark in ("SPY", "QQQ")
        }
        usable = {
            benchmark: value
            for benchmark, value in benchmark_returns.items()
            if value is not None
        }
        if security_return is None or not usable:
            return None
        best_benchmark = max(usable, key=lambda benchmark: usable[benchmark])
        return {
            "security_return_pct": float(security_return),
            "benchmark_returns_pct": usable,
            "best_benchmark": best_benchmark,
            "best_benchmark_return_pct": float(usable[best_benchmark]),
            "excess_vs_best_pct": round(
                float(security_return) - float(usable[best_benchmark]),
                4,
            ),
            "snapshots": account._snapshots_since(history, latest_buy.get("timestamp")),
        }

    @staticmethod
    def _sector_breadth(market_data):
        by_sector = {}
        for data in market_data.values():
            if (
                data.get("status") != "available"
                or not has_reliable_daily_change(data)
            ):
                continue
            sector = str(data.get("sector") or "Unclassified")
            if sector == "Benchmark ETF":
                continue
            by_sector.setdefault(sector, []).append(
                float(data.get("percent_change") or 0.0)
            )
        return {
            sector: round(
                (sum(1 for value in changes if value > 0) / len(changes)) * 100.0,
                2,
            )
            for sector, changes in by_sector.items()
            if changes
        }

    @staticmethod
    def _benchmark_day_context(market_data):
        benchmarks = []
        for label in ("SPY", "QQQ", "IWM", "RSP"):
            data = market_data.get(label, {})
            if (
                data.get("status") != "available"
                or not has_reliable_daily_change(data)
            ):
                continue
            benchmarks.append((label, float(data.get("percent_change") or 0.0)))
        if not benchmarks:
            return None
        strongest = max(benchmarks, key=lambda item: item[1])
        return {
            "strongest_benchmark": strongest[0],
            "strongest_change_pct": strongest[1],
        }

    def _projection_signals(
        self,
        *,
        data,
        benchmark_context,
        sector_breadth,
        benchmark_day,
        news_signal,
    ):
        metrics = data.get("momentum_metrics") or {}
        trend_regime = str(metrics.get("trend_regime") or "unknown").strip().lower()
        trend_quality = self._as_float(metrics.get("trend_quality_score"), 50.0)
        news_label = str(news_signal.get("signal_label") or "neutral").strip().lower()
        daily_change_reliable = has_reliable_daily_change(data)
        current_change = (
            self._as_float(data.get("percent_change"), 0.0)
            if daily_change_reliable
            else 0.0
        )
        daily_excess = None
        strongest_benchmark = ""
        if (
            daily_change_reliable
            and benchmark_day
            and benchmark_day.get("strongest_change_pct") is not None
        ):
            daily_excess = round(
                current_change - float(benchmark_day["strongest_change_pct"]),
                4,
            )
            strongest_benchmark = str(
                benchmark_day.get("strongest_benchmark") or ""
            ).strip()

        if (
            benchmark_context
            and benchmark_context.get("excess_vs_best_pct") is not None
            and trend_regime in {"leadership", "constructive"}
            and news_label not in {"adverse", "cautious"}
            and self._as_float(sector_breadth, 0.0)
            >= self.projection_add_sector_breadth_pct
        ):
            projection_state = "continued_leadership"
        elif (
            benchmark_context
            and benchmark_context.get("excess_vs_best_pct") is not None
            and (
                float(benchmark_context["excess_vs_best_pct"])
                <= self.projection_trim_excess_pct
                or trend_regime in {"fragile", "breakdown"}
                or news_label == "adverse"
            )
        ):
            projection_state = "de_risk"
        elif news_label == "cautious":
            projection_state = "needs_proof"
        else:
            projection_state = "mixed"

        return {
            "projection_state": projection_state,
            "trend_regime": trend_regime,
            "trend_quality_score": trend_quality,
            "sector_breadth_pct": sector_breadth,
            "news_label": news_label,
            "best_benchmark": (
                benchmark_context.get("best_benchmark") if benchmark_context else None
            ),
            "excess_vs_best_pct": (
                benchmark_context.get("excess_vs_best_pct") if benchmark_context else None
            ),
            "daily_excess_pct": daily_excess,
            "strongest_benchmark": strongest_benchmark,
        }

    @staticmethod
    def _as_float(value, default=None):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _should_add_to_winner(
        self,
        account,
        *,
        position,
        current_price,
        score,
        benchmark_context,
        projection,
    ):
        if score is None or score < self.add_score or benchmark_context is None:
            return False
        if benchmark_context["snapshots"] < self.add_min_snapshots:
            return False
        if benchmark_context["security_return_pct"] < self.add_return_pct:
            return False
        if benchmark_context["excess_vs_best_pct"] < self.add_excess_pct:
            return False
        if projection:
            if (
                str(projection.get("projection_state") or "mixed")
                != "continued_leadership"
            ):
                return False
            if (
                self._as_float(projection.get("sector_breadth_pct"), 0.0)
                < self.projection_add_sector_breadth_pct
            ):
                return False
            if (
                self._as_float(projection.get("trend_quality_score"), 50.0)
                < self.projection_add_trend_quality
            ):
                return False
        state = account.load()
        target_pct = float(
            state.get("policy", {}).get("strategy_target_position_pct", 5.0)
        )
        starting_cash = float(state.get("starting_cash") or 0.0)
        if starting_cash <= 0:
            return False
        current_value = float(position.get("shares") or 0.0) * float(current_price)
        current_pct = (current_value / starting_cash) * 100.0
        return current_pct <= max(target_pct * 1.25, target_pct + 1.0)

    def _add_shares(self, account, *, current_price):
        state = account.load()
        target_pct = float(
            state.get("policy", {}).get("strategy_target_position_pct", 5.0)
        )
        add_value = (
            float(state.get("starting_cash") or 0.0)
            * (target_pct / 100.0)
            * self.add_fraction_of_target
        )
        if add_value <= 0 or float(current_price or 0.0) <= 0:
            return 0
        return max(int(add_value // float(current_price)), 0)

    @staticmethod
    def _add_thesis(ticker, score, return_pct, benchmark_context):
        return (
            f"Atlas winner add rule: {ticker} remains a strong simulated holding with "
            f"Atlas score {score:.1f}, open return {return_pct:+.2f}%, and "
            f"{benchmark_context['excess_vs_best_pct']:+.2f}% excess return versus "
            f"{benchmark_context['best_benchmark']} across {benchmark_context['snapshots']} snapshots since entry."
        )

    def _add_rationale(self, *, score, return_pct, benchmark_context, projection=None):
        rationale = [
            (
                f"Winner add rule triggered: Atlas score {score:.1f} is at or above the {self.add_score:.1f} add threshold."
            ),
            (
                f"Open return is {return_pct:+.2f}% and is beating {benchmark_context['best_benchmark']} by "
                f"{benchmark_context['excess_vs_best_pct']:+.2f}% since entry."
            ),
            (
                f"Atlas has {benchmark_context['snapshots']} post-entry snapshots confirming the move."
            ),
        ]
        if projection and projection.get("sector_breadth_pct") is not None:
            rationale.append(
                f"Projection watch remains supportive with {float(projection['sector_breadth_pct']):.0f}% sector breadth and a {str(projection.get('trend_regime') or 'unknown').replace('_', ' ')} trend posture."
            )
        return rationale
