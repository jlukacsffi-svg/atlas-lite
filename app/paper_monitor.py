"""Daily thesis monitoring for open Atlas paper positions."""

from app.scoring import ScoringEngine


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
    ):
        self.exit_score = float(exit_score)
        self.review_score = float(review_score)
        self.drawdown_review_pct = float(drawdown_review_pct)
        self.benchmark_lag_review_pct = float(benchmark_lag_review_pct)
        self.benchmark_lag_trim_pct = float(benchmark_lag_trim_pct)
        self.benchmark_lag_min_snapshots = int(benchmark_lag_min_snapshots)
        self.scoring_engine = ScoringEngine()

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
        benchmark_lag = self._benchmark_lag(account.proposal_feedback())
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
            verdict, flags, sell_shares = self._review_decision(
                category=category,
                score=score,
                score_text=score_text,
                return_pct=return_pct,
                lag=lag,
                current_shares=position["shares"],
            )
            thesis = self._review_thesis(
                ticker=ticker,
                verdict=verdict,
                category=category,
                score_text=score_text,
                return_pct=return_pct,
                lag=lag,
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

        return verdict, flags, sell_shares

    @staticmethod
    def _review_thesis(ticker, verdict, category, score_text, return_pct, lag):
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
    def _trim_shares(shares):
        return max(round(float(shares) / 2, 6), 0.000001)

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
