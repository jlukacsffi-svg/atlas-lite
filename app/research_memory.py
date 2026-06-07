"""Structured historical research memory for Atlas Lite."""

from datetime import datetime
import json
import os
from pathlib import Path

from app.scoring import ScoringEngine
from app.paths import data_path


DEFAULT_ARCHIVE_DIR = data_path("research_archive")
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

    def update_archive_index(
        self,
        snapshot_path,
        report_path=None,
        html_report_path=None,
        max_entries=50,
    ):
        """Update JSON and Markdown archive indexes for recent research runs."""
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        snapshot = self._read_json(snapshot_path)
        if not snapshot:
            return None

        index_path = self.archive_dir / "archive_index.json"
        existing_index = self._read_json(index_path) or {"index_version": "1.0", "entries": []}
        entries = existing_index.get("entries", [])
        entry = self._build_index_entry(snapshot, snapshot_path, report_path, html_report_path)

        entries = [
            self._normalize_index_entry_paths(item) for item in entries
            if item.get("snapshot_path") != entry["snapshot_path"]
        ]
        entries.append(entry)
        entries = sorted(entries, key=lambda item: item.get("generated_at", ""), reverse=True)[:max_entries]

        index_payload = {
            "index_version": "1.0",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "entries": entries,
        }

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_payload, f, indent=2, sort_keys=True)

        markdown_path = self.archive_dir / "archive_index.md"
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(self._render_markdown_index(index_payload))

        return index_path

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

    def _build_index_entry(self, snapshot, snapshot_path, report_path, html_report_path):
        securities = snapshot.get("securities", {})
        available = [
            (ticker, data)
            for ticker, data in securities.items()
            if data.get("status") == "available"
            and data.get("percent_change") is not None
        ]
        top_movers = [
            {
                "ticker": ticker,
                "percent_change": round(data.get("percent_change", 0), 2),
            }
            for ticker, data in sorted(
                available,
                key=lambda item: abs(item[1].get("percent_change", 0)),
                reverse=True,
            )[:5]
        ]
        score_leaders = [
            {
                "ticker": ticker,
                "total_score": data.get("total_score"),
            }
            for ticker, data in sorted(
                securities.items(),
                key=lambda item: item[1].get("total_score") or 0,
                reverse=True,
            )
            if data.get("total_score") is not None
        ][:5]

        return {
            "generated_at": snapshot.get("generated_at"),
            "universe_version": snapshot.get("universe_version"),
            "securities": len(securities),
            "available_securities": len(available),
            "snapshot_path": self._relative_archive_path(snapshot_path),
            "report_path": self._relative_archive_path(report_path),
            "html_report_path": self._relative_archive_path(html_report_path),
            "top_movers": top_movers,
            "score_leaders": score_leaders,
        }

    def _render_markdown_index(self, index_payload):
        lines = [
            "# Atlas Research Archive Index",
            "",
            f"Updated: {index_payload.get('updated_at', 'N/A')}",
            "",
            "| Generated At | Universe | Securities | Top Movers | Score Leaders | Reports |",
            "|--------------|----------|------------|------------|---------------|---------|",
        ]

        for entry in index_payload.get("entries", []):
            top_movers = ", ".join(
                f"{item['ticker']} {item['percent_change']:+.2f}%"
                for item in entry.get("top_movers", [])
            ) or "N/A"
            score_leaders = ", ".join(
                f"{item['ticker']} {item['total_score']:.1f}"
                for item in entry.get("score_leaders", [])
                if item.get("total_score") is not None
            ) or "N/A"
            reports = self._format_report_links(entry)
            lines.append(
                f"| {entry.get('generated_at', 'N/A')} | "
                f"{entry.get('universe_version', 'N/A')} | "
                f"{entry.get('available_securities', 0)}/{entry.get('securities', 0)} | "
                f"{top_movers} | {score_leaders} | {reports} |"
            )

        lines.append("")
        return "\n".join(lines)

    def _format_report_links(self, entry):
        links = []
        if entry.get("snapshot_path"):
            links.append(f"[snapshot]({entry['snapshot_path']})")
        if entry.get("report_path"):
            links.append(f"[markdown]({entry['report_path']})")
        if entry.get("html_report_path"):
            links.append(f"[html]({entry['html_report_path']})")
        return " / ".join(links) if links else "N/A"

    def _normalize_index_entry_paths(self, entry):
        normalized = dict(entry)
        for key in ("report_path", "html_report_path"):
            value = normalized.get(key)
            if isinstance(value, str) and value.startswith("reports/"):
                normalized[key] = f"../{value}"
        return normalized

    def _relative_archive_path(self, path):
        if not path:
            return None
        path = Path(path)
        try:
            return path.resolve().relative_to(self.archive_dir.resolve()).as_posix()
        except ValueError:
            return os.path.relpath(path.resolve(), self.archive_dir.resolve()).replace("\\", "/")

    def _read_json(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception:
            return None

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
