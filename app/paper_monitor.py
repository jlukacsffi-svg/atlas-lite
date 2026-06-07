"""Daily thesis monitoring for open Atlas paper positions."""

from app.scoring import ScoringEngine


class PaperPositionMonitor:
    """Record holding reviews and create reviewable exit proposals."""

    def __init__(self, exit_score=60.0, review_score=70.0, drawdown_review_pct=-10.0):
        self.exit_score = float(exit_score)
        self.review_score = float(review_score)
        self.drawdown_review_pct = float(drawdown_review_pct)
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

            if category == "Avoid" or (score is not None and score <= self.exit_score):
                verdict = "exit"
                flags.append(
                    f"Exit rule triggered: category {category}, Atlas score "
                    f"{score_text}."
                )
            elif score is None:
                verdict = "review"
                flags.append("Atlas score is unavailable.")
            elif score <= self.review_score:
                verdict = "review"
                flags.append(f"Atlas score {score:.1f} is below review threshold.")
            elif return_pct <= self.drawdown_review_pct:
                verdict = "review"
                flags.append(
                    f"Position return {return_pct:+.2f}% is below "
                    f"{self.drawdown_review_pct:.2f}% review threshold."
                )
            else:
                verdict = "maintain"

            thesis = (
                f"Daily paper thesis review for {ticker}: category {category}, "
                f"Atlas score {score_text}, "
                f"position return {return_pct:+.2f}%."
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
                        shares=position["shares"],
                        reference_price=price,
                        thesis=thesis,
                        source="paper_monitor_v1",
                    )
                )

        return {"reviews": reviews, "exit_proposals": exit_proposals}

    def _score(self, data):
        scores = data.get("scores")
        if not scores:
            return None
        try:
            return self.scoring_engine.score(scores)
        except (TypeError, ValueError):
            return None
