"""Structured historical research memory for Atlas Lite."""

from datetime import datetime
import json
from pathlib import Path

from app.scoring import ScoringEngine


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ARCHIVE_DIR = PROJECT_ROOT / "research_archive"
SNAPSHOT_FIELDS = [
    "company_name",
    "sector",
    "category",
    "notes",
    "price",
    "previous_close",
    "change",
    "percent_change",
    "volume",
    "status",
    "source",
    "scores",
    "score_source",
    "automated_scores",
    "profile",
    "growth_metrics",
    "quality_metrics",
    "momentum_metrics",
]


class ResearchMemory:
    """Save and retrieve structured daily Atlas research snapshots."""

    def __init__(self, archive_dir=DEFAULT_ARCHIVE_DIR):
        self.archive_dir = Path(archive_dir)
        self.scoring_engine = ScoringEngine()

    def save_snapshot(self, market_data, market_summary, universe_version, timestamp=None):
        timestamp = timestamp or datetime.now()
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        snapshot = self.build_snapshot(
            market_data=market_data,
            market_summary=market_summary,
            universe_version=universe_version,
            timestamp=timestamp,
        )
        filename = timestamp.strftime("snapshot_%Y%m%d_%H%M%S.json")
        filepath = self.archive_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, sort_keys=True)

        return filepath

    def build_snapshot(self, market_data, market_summary, universe_version, timestamp=None):
        timestamp = timestamp or datetime.now()
        securities = {}

        for ticker, data in market_data.items():
            record = {
                field: self._to_json_value(data.get(field))
                for field in SNAPSHOT_FIELDS
                if field in data
            }
            scores = data.get("scores")
            record["total_score"] = (
                self.scoring_engine.score(scores)
                if scores
                else None
            )
            securities[ticker] = record

        summary = {
            ticker: {
                key: self._to_json_value(value)
                for key, value in data.items()
            }
            for ticker, data in market_summary.items()
        }

        return {
            "snapshot_version": "1.0",
            "generated_at": timestamp.isoformat(timespec="seconds"),
            "universe_version": universe_version,
            "market_summary": summary,
            "securities": securities,
        }

    def load_latest_snapshot(self):
        if not self.archive_dir.exists():
            return None

        snapshot_files = sorted(self.archive_dir.glob("snapshot_*.json"), reverse=True)
        if not snapshot_files:
            return None

        with open(snapshot_files[0], "r", encoding="utf-8") as f:
            return json.load(f)

    def _to_json_value(self, value):
        if hasattr(value, "item"):
            value = value.item()

        if isinstance(value, dict):
            return {
                str(key): self._to_json_value(item)
                for key, item in value.items()
            }
        if isinstance(value, (list, tuple)):
            return [self._to_json_value(item) for item in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)
