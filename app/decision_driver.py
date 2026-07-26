"""Shared decision-driver labeling for owner-visible Atlas explanations."""


def infer_decision_driver(texts, *, side="", action_label=""):
    normalized = []
    for text in texts or []:
        cleaned = str(text).strip()
        if cleaned:
            normalized.append(cleaned)
    if not normalized:
        return None

    lower_side = str(side or "").strip().lower()
    lower_action = str(action_label or "").strip().lower()
    for text in normalized:
        lowered = text.lower()
        if "projection de-risk triggered" in lowered:
            return {
                "family": "projection",
                "code": "projection_de_risk",
                "label": "Projection de-risk",
                "summary": (
                    "Atlas is reducing risk because benchmark lag, sector breadth, "
                    "and trend posture have weakened together."
                ),
                "evidence": text,
            }
        if "projection caution triggered" in lowered:
            return {
                "family": "projection",
                "code": "projection_caution",
                "label": "Projection caution",
                "summary": (
                    "Atlas wants more proof before trusting upside because "
                    "confirmation is no longer clearly supportive."
                ),
                "evidence": text,
            }
        if "projection watch remains supportive" in lowered:
            return {
                "family": "projection",
                "code": "projection_supported_add",
                "label": "Projection-supported add",
                "summary": (
                    "Atlas still sees enough breadth and trend confirmation to "
                    "support adding to a winner."
                ),
                "evidence": text,
            }
        if "projection posture is continued leadership" in lowered:
            label = (
                "Projection-supported add"
                if lower_side == "buy" or lower_action == "buy"
                else "Projection leadership"
            )
            summary = (
                "Atlas still sees enough breadth and trend confirmation to "
                "support adding to a winner."
                if label == "Projection-supported add"
                else "Atlas still sees supportive continuation rather than an "
                "immediate de-risk signal."
            )
            return {
                "family": "projection",
                "code": "projection_continued_leadership",
                "label": label,
                "summary": summary,
                "evidence": text,
            }
        if "projection posture is needs proof" in lowered:
            return {
                "family": "projection",
                "code": "projection_needs_proof",
                "label": "Projection caution",
                "summary": (
                    "Atlas wants more proof before trusting upside because "
                    "confirmation has softened."
                ),
                "evidence": text,
            }
    return None
