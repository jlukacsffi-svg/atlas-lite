"""Transparent Atlas Scoring Engine v1."""


SCORE_WEIGHTS = {
    "growth": 0.40,
    "quality": 0.20,
    "moat": 0.15,
    "momentum": 0.15,
    "risk": 0.10,
}


class ScoringEngine:
    """Calculate weighted 0-100 security scores from component inputs."""

    def __init__(self, weights=None):
        self.weights = weights or SCORE_WEIGHTS
        self._validate_weights()

    def _validate_weights(self):
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.000001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")

    def score(self, component_scores):
        missing = set(self.weights) - set(component_scores)
        if missing:
            raise ValueError(f"Missing scoring components: {', '.join(sorted(missing))}")

        weighted_total = sum(
            float(component_scores[component]) * weight
            for component, weight in self.weights.items()
        )
        return round(weighted_total, 1)

    def score_security(self, security):
        return {
            "ticker": security["ticker"],
            "total_score": self.score(security["scores"]),
            "scores": dict(security["scores"]),
            "score_source": security.get("score_source", "manual_v1"),
        }
