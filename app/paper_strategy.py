"""Transparent Stage 5 strategy for generating paper proposals."""

import math

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
    ):
        self.minimum_buy_score = float(minimum_buy_score)
        self.maximum_exit_score = float(maximum_exit_score)
        self.target_position_pct = float(target_position_pct)
        self.maximum_new_proposals = int(maximum_new_proposals)
        self.minimum_daily_move_pct = float(minimum_daily_move_pct)
        self.scoring_engine = ScoringEngine()

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
        candidates = self._candidate_rows(market_data)
        created = []
        created_buys = 0

        for row in candidates:
            ticker = row["ticker"]
            if ticker in positions:
                if row["category"] == "Avoid" or row["score"] <= self.maximum_exit_score:
                    if ("sell", ticker) in existing:
                        continue
                    position = positions[ticker]
                    thesis = (
                        f"Atlas paper exit rule: {ticker} has score "
                        f"{row['score']:.1f} and category {row['category']}."
                    )
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
            if row["category"] == "Avoid" or row["score"] < self.minimum_buy_score:
                continue
            if row["percent_change"] <= self.minimum_daily_move_pct:
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
            recommendation = account.record_recommendation(
                side="buy",
                ticker=ticker,
                shares=shares,
                reference_price=row["price"],
                thesis=thesis,
                confidence="high" if row["score"] >= 92 else "medium",
                source="paper_strategy_v1",
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
                )
            )
            created_buys += 1

        return created

    def _candidate_rows(self, market_data):
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
            rows.append(
                {
                    "ticker": ticker,
                    "price": float(data["price"]),
                    "score": score,
                    "category": data.get("category", "Watchlist"),
                    "sector": data.get("sector", "Unclassified"),
                    "percent_change": float(data.get("percent_change") or 0),
                }
            )
        return sorted(
            rows,
            key=lambda item: (item["score"], item["percent_change"]),
            reverse=True,
        )

    def _target_shares(self, cash, price):
        target_value = float(cash) * self.target_position_pct / 100
        return math.floor(target_value / price)

    def _buy_thesis(self, row):
        return (
            f"Atlas paper entry rule: {row['ticker']} has score {row['score']:.1f}, "
            f"category {row['category']}, sector {row['sector']}, and a "
            f"{row['percent_change']:+.2f}% current move. Target size is "
            f"{self.target_position_pct:.1f}% of starting simulated cash."
        )
