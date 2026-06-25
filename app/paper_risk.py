"""CRO-style risk review for Stage 5 paper proposals."""

from collections import Counter

from app.scoring import ScoringEngine


class PaperRiskReviewer:
    """Review pending proposals and append non-executing risk verdicts."""

    def __init__(
        self,
        sharp_downside_pct=-8.0,
        elevated_move_pct=6.0,
        sector_proposal_limit=2,
        sector_capital_limit_pct=10.0,
    ):
        self.sharp_downside_pct = float(sharp_downside_pct)
        self.elevated_move_pct = float(elevated_move_pct)
        self.sector_proposal_limit = int(sector_proposal_limit)
        self.sector_capital_limit_pct = float(sector_capital_limit_pct)
        self.scoring_engine = ScoringEngine()

    def review_pending(self, account, market_data, enforce_holds=True):
        pending = account.proposals(status="pending")
        if not pending:
            return []
        state = account.load()
        reviews = []
        survivors = []

        for proposal in pending:
            data = market_data.get(proposal["ticker"], {})
            side = str(proposal.get("side") or "").lower()
            flags = []
            high_risk = False
            pct = data.get("percent_change")
            if pct is None:
                flags.append("Missing current price-move data.")
                high_risk = side != "sell"
            elif float(pct) <= self.sharp_downside_pct:
                if side == "sell":
                    flags.append(
                        f"Sharp downside move supports reducing simulated exposure: "
                        f"{float(pct):+.2f}%."
                    )
                else:
                    flags.append(
                        f"Sharp downside move: {float(pct):+.2f}% is below "
                        f"{self.sharp_downside_pct:.2f}% review threshold."
                    )
                    high_risk = True
            elif abs(float(pct)) >= self.elevated_move_pct:
                flags.append(f"Elevated daily volatility: {float(pct):+.2f}%.")

            scores = data.get("scores")
            if scores:
                score = self.scoring_engine.score(scores)
                if score < 70:
                    if side == "sell":
                        flags.append(
                            f"Atlas score is only {score:.1f}; this supports the exit review."
                        )
                    else:
                        flags.append(f"Atlas score is only {score:.1f}.")
                        high_risk = True
            else:
                flags.append("Atlas component scores are unavailable.")
                high_risk = side != "sell"

            if high_risk:
                review = account.record_proposal_risk_review(
                    proposal["proposal_id"],
                    verdict="hold",
                    flags=flags,
                )
                reviews.append(review)
                if enforce_holds:
                    account.decide_proposal(
                        proposal["proposal_id"],
                        "reject",
                        notes="Automatically rejected by paper_risk_v1 hard-hold policy.",
                    )
            else:
                survivors.append((proposal, data, flags))

        sector_counts = Counter()
        sector_notionals = Counter()
        proposal_sectors = {}

        for proposal, data, _flags in survivors:
            sector = data.get("sector", "Unclassified")
            proposal_sectors[proposal["proposal_id"]] = sector
            sector_counts[sector] += 1
            sector_notionals[sector] += float(proposal.get("notional") or 0)

        for proposal, _data, flags in survivors:
            sector = proposal_sectors[proposal["proposal_id"]]
            if sector_counts[sector] > self.sector_proposal_limit:
                flags.append(
                    f"Proposal concentration: {sector_counts[sector]} pending "
                    f"proposals are in {sector}."
                )
            sector_pct = (
                sector_notionals[sector] / float(state["starting_cash"]) * 100
                if state["starting_cash"]
                else 0
            )
            if sector_pct > self.sector_capital_limit_pct:
                flags.append(
                    f"Pending {sector} proposals total {sector_pct:.1f}% of "
                    "starting simulated capital."
                )

            verdict = "caution" if flags else "clear"
            review = account.record_proposal_risk_review(
                proposal["proposal_id"],
                verdict=verdict,
                flags=flags,
            )
            reviews.append(review)
        return reviews
