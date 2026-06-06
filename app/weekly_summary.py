"""Weekly research summary generation for Atlas Lite."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
import html
import re
from pathlib import Path

from app.research_memory import DEFAULT_ARCHIVE_DIR


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"


class WeeklySummaryGenerator:
    """Generate a weekly rollup from the local research archive index."""

    def __init__(self, archive_dir=DEFAULT_ARCHIVE_DIR, reports_dir=DEFAULT_REPORTS_DIR):
        self.archive_dir = Path(archive_dir)
        self.reports_dir = Path(reports_dir)
        self.timestamp = datetime.now()
        self.last_html_path = None

    def load_index(self):
        index_path = self.archive_dir / "archive_index.json"
        try:
            import json

            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"entries": []}

    def recent_entries(self, days=7):
        cutoff = self.timestamp - timedelta(days=days)
        entries = []

        for entry in self.load_index().get("entries", []):
            generated_at = self._parse_datetime(entry.get("generated_at"))
            if generated_at and generated_at >= cutoff:
                entries.append(entry)

        return sorted(entries, key=lambda item: item.get("generated_at", ""))

    def generate_summary(self, days=7):
        entries = self.recent_entries(days=days)
        report = ["# Atlas Weekly Research Summary\n"]
        report.append(f"## Period\n\nLast {days} days ending {self.timestamp.strftime('%B %d, %Y')}\n")

        if not entries:
            report.append("## Summary\n\nNo archive entries are available for this period.\n")
            report.append(f"\n---\n\n*Weekly summary generated on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*\n")
            return "\n".join(report)

        report.append(self._generate_weekly_overview(entries))
        report.append(self._generate_weekly_narrative(entries))
        report.append(self._generate_key_changes(entries))
        report.append(self._generate_sector_trends(entries))
        report.append(self._generate_research_action_prompts(entries))
        report.append(self._generate_recurring_movers(entries))
        report.append(self._generate_score_leaders(entries))
        report.append(self._generate_run_log(entries))
        report.append(f"\n---\n\n*Weekly summary generated on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*\n")
        return "\n".join(report)

    def save_summary(self, days=7):
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        markdown = self.generate_summary(days=days)
        base_filename = self.timestamp.strftime("weekly_summary_%Y%m%d_%H%M%S")
        markdown_path = self.reports_dir / f"{base_filename}.md"
        html_path = self.reports_dir / f"{base_filename}.html"

        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.generate_html_summary(markdown))

        self.last_html_path = html_path
        return markdown_path

    def research_task_suggestions(self, days=7):
        """Return structured role assignments from recent weekly signals."""
        return self._research_action_items(self.recent_entries(days=days))

    def generate_html_summary(self, markdown_content=None):
        markdown_content = markdown_content or self.generate_summary()
        body = self._markdown_to_html(markdown_content)
        title = f"Atlas Weekly Research Summary - {self.timestamp.strftime('%B %d, %Y')}"
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #1d2433;
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.55;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 32px auto;
      background: #ffffff;
      border: 1px solid #d9dee8;
      border-radius: 8px;
      padding: 32px;
      box-shadow: 0 12px 30px rgba(29, 36, 51, 0.08);
    }}
    h1 {{ margin-top: 0; }}
    h2 {{ margin-top: 32px; border-bottom: 1px solid #d9dee8; padding-bottom: 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; font-size: 0.94rem; }}
    th, td {{ border: 1px solid #d9dee8; padding: 9px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #eef2f8; }}
    tr:nth-child(even) td {{ background: #fafbfc; }}
    a {{ color: #2457a6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 720px) {{
      main {{ width: 100%; margin: 0; border-radius: 0; padding: 20px; }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
  <main>
{body}
  </main>
</body>
</html>
"""

    def _generate_weekly_overview(self, entries):
        latest = entries[-1]
        available_counts = [
            entry.get("available_securities", 0)
            for entry in entries
        ]
        avg_available = sum(available_counts) / len(available_counts) if available_counts else 0
        lines = ["## Weekly Overview\n"]
        lines.append(f"- **Runs indexed**: {len(entries)}")
        lines.append(f"- **Latest run**: {latest.get('generated_at', 'N/A')}")
        lines.append(f"- **Universe version**: {latest.get('universe_version', 'N/A')}")
        lines.append(f"- **Average available securities**: {avg_available:.1f}")
        lines.append("")
        return "\n".join(lines) + "\n"

    def _generate_weekly_narrative(self, entries):
        snapshots = self._load_entry_snapshots(entries)
        latest_entry = entries[-1]
        lines = ["## What Changed This Week\n"]

        coverage = self._coverage_sentence(entries)
        if coverage:
            lines.append(f"- {coverage}")

        sector_extremes = self._sector_extreme_sentences(snapshots)
        lines.extend(f"- {sentence}" for sentence in sector_extremes)

        score_sentences = self._score_change_sentences(snapshots)
        lines.extend(f"- {sentence}" for sentence in score_sentences)

        recurring_mover = self._top_recurring_mover_sentence(entries)
        if recurring_mover:
            lines.append(f"- {recurring_mover}")

        score_leader = self._score_leader_sentence(entries)
        if score_leader:
            lines.append(f"- {score_leader}")

        if len(lines) == 1:
            lines.append("- Not enough archive data is available yet to generate a meaningful weekly narrative.")

        latest_run = latest_entry.get("generated_at")
        if latest_run:
            lines.append(f"- Latest indexed run: {latest_run}.")

        return "\n".join(lines) + "\n"

    def _generate_key_changes(self, entries):
        snapshots = self._load_entry_snapshots(entries)
        if len(snapshots) < 2:
            return "## Key Changes\n\nAt least two snapshots are needed to compare score changes.\n\n"

        first = snapshots[0]
        latest = snapshots[-1]
        first_securities = first.get("securities", {})
        latest_securities = latest.get("securities", {})
        score_changes = []

        for ticker, latest_data in latest_securities.items():
            first_data = first_securities.get(ticker)
            if not first_data:
                continue
            first_score = first_data.get("total_score")
            latest_score = latest_data.get("total_score")
            if first_score is None or latest_score is None:
                continue
            delta = latest_score - first_score
            if abs(delta) >= 0.1:
                score_changes.append((ticker, first_score, latest_score, delta))

        lines = ["## Key Changes\n"]
        if not score_changes:
            lines.append("No meaningful score changes were detected across the available snapshots.\n")
            return "\n".join(lines) + "\n"

        lines.append("| Ticker | First Score | Latest Score | Change |")
        lines.append("|--------|-------------|--------------|--------|")
        for ticker, first_score, latest_score, delta in sorted(
            score_changes,
            key=lambda item: abs(item[3]),
            reverse=True,
        )[:10]:
            lines.append(f"| {ticker} | {first_score:.1f} | {latest_score:.1f} | {delta:+.1f} |")
        return "\n".join(lines) + "\n"

    def _generate_sector_trends(self, entries):
        snapshots = self._load_entry_snapshots(entries)
        if not snapshots:
            return "## Sector Trend Shifts\n\nNo snapshot data is available for sector trend analysis.\n\n"

        sector_moves = defaultdict(list)
        for snapshot in snapshots:
            for data in snapshot.get("securities", {}).values():
                sector = data.get("sector")
                pct = data.get("percent_change")
                status = data.get("status")
                if sector and pct is not None and status == "available":
                    sector_moves[sector].append(pct)

        lines = ["## Sector Trend Shifts\n"]
        if not sector_moves:
            lines.append("No sector-level movement data is available for this period.\n")
            return "\n".join(lines) + "\n"

        rows = [
            (sector, sum(moves) / len(moves), len(moves))
            for sector, moves in sector_moves.items()
        ]
        lines.append("| Sector | Average Daily Move | Observations |")
        lines.append("|--------|--------------------|--------------|")
        for sector, avg_move, count in sorted(rows, key=lambda item: item[1], reverse=True):
            lines.append(f"| {sector} | {avg_move:+.2f}% | {count} |")
        return "\n".join(lines) + "\n"

    def _generate_research_action_prompts(self, entries):
        items = self._research_action_items(entries)
        prompts = [item["prompt"] for item in items]

        lines = ["## Research Action Prompts\n"]
        if not prompts:
            lines.append("No research action prompts are available yet; more archive history is needed.\n")
            return "\n".join(lines) + "\n"

        for prompt in prompts[:6]:
            lines.append(f"- {prompt}")
        return "\n".join(lines) + "\n"

    def _research_action_items(self, entries):
        snapshots = self._load_entry_snapshots(entries)
        items = []

        strongest_score = self._largest_positive_score_change(snapshots)
        if strongest_score:
            ticker, first_score, latest_score, delta = strongest_score
            items.append(
                {
                    "role": "CIO",
                    "subject": ticker,
                    "priority": "medium",
                    "prompt": (
                        f"Review {ticker}: score improved {delta:+.1f} points "
                        f"from {first_score:.1f} to {latest_score:.1f}; confirm whether the change reflects durable fundamentals."
                    ),
                }
            )

        weakest_score = self._largest_negative_score_change(snapshots)
        if weakest_score:
            ticker, first_score, latest_score, delta = weakest_score
            items.append(
                {
                    "role": "CRO",
                    "subject": ticker,
                    "priority": "high",
                    "prompt": (
                        f"Challenge {ticker}: score declined {delta:+.1f} points "
                        f"from {first_score:.1f} to {latest_score:.1f}; identify whether this is temporary volatility or thesis damage."
                    ),
                }
            )

        recurring_mover = self._top_recurring_mover(entries)
        if recurring_mover:
            ticker, appearances, largest_move = recurring_mover
            items.append(
                {
                    "role": "CRO" if largest_move < 0 else "CIO",
                    "subject": ticker,
                    "priority": "high" if largest_move <= -4 else "medium",
                    "prompt": (
                        f"Investigate {ticker}: appeared as a top mover {appearances} times; "
                        f"review catalysts behind the {largest_move:+.2f}% largest move."
                    ),
                }
            )

        sector_rows = self._sector_average_moves(snapshots)
        if sector_rows:
            weakest_sector = min(sector_rows, key=lambda item: item[1])
            items.append(
                {
                    "role": "CRO",
                    "subject": weakest_sector[0],
                    "priority": "medium",
                    "prompt": (
                        f"Monitor {weakest_sector[0]}: weakest sector trend at "
                        f"{weakest_sector[1]:+.2f}% average movement; check for broad pressure or isolated names."
                    ),
                }
            )

        leader = self._top_score_leader(entries)
        if leader:
            ticker, appearances, avg_score = leader
            items.append(
                {
                    "role": "CIO",
                    "subject": ticker,
                    "priority": "medium",
                    "prompt": (
                        f"Maintain thesis file for {ticker}: appeared as a recurring score leader "
                        f"{appearances} times with an average score of {avg_score:.1f}."
                    ),
                }
            )

        return items

    def _coverage_sentence(self, entries):
        latest = entries[-1]
        available = latest.get("available_securities", 0)
        total = latest.get("securities", 0)
        if not total:
            return None

        missing = total - available
        if missing == 0:
            return f"Atlas ended the week with full data coverage: {available}/{total} securities available."
        return f"Atlas ended the week with {available}/{total} securities available; {missing} lacked usable market data."

    def _sector_extreme_sentences(self, snapshots):
        rows = self._sector_average_moves(snapshots)
        if not rows:
            return []

        strongest = max(rows, key=lambda item: item[1])
        weakest = min(rows, key=lambda item: item[1])
        sentences = [
            (
                f"Strongest sector trend: {strongest[0]} averaged "
                f"{strongest[1]:+.2f}% across {strongest[2]} observations."
            )
        ]
        if weakest[0] != strongest[0]:
            sentences.append(
                f"Weakest sector trend: {weakest[0]} averaged {weakest[1]:+.2f}%."
            )
        return sentences

    def _score_change_sentences(self, snapshots):
        changes = self._score_changes(snapshots)
        if not changes:
            return ["No meaningful score changes were detected across available snapshots."]

        strongest = max(changes, key=lambda item: item[3])
        weakest = min(changes, key=lambda item: item[3])
        sentences = []

        if strongest[3] > 0:
            sentences.append(
                f"Largest score improvement: {strongest[0]} rose from "
                f"{strongest[1]:.1f} to {strongest[2]:.1f} ({strongest[3]:+.1f})."
            )
        if weakest[3] < 0:
            sentences.append(
                f"Largest score decline: {weakest[0]} fell from "
                f"{weakest[1]:.1f} to {weakest[2]:.1f} ({weakest[3]:+.1f})."
            )
        return sentences or ["Score changes were positive but modest across available snapshots."]

    def _top_recurring_mover_sentence(self, entries):
        recurring_mover = self._top_recurring_mover(entries)
        if not recurring_mover:
            return None

        ticker, appearances, largest_move = recurring_mover
        return (
            f"Most persistent top mover: {ticker} appeared {appearances} times, "
            f"with a largest move of {largest_move:+.2f}%."
        )

    def _score_leader_sentence(self, entries):
        leader = self._top_score_leader(entries)
        if not leader:
            return None

        ticker, appearances, avg_score = leader
        return (
            f"Most consistent score leader: {ticker} appeared {appearances} times "
            f"with an average score of {avg_score:.1f}."
        )

    def _top_recurring_mover(self, entries):
        mover_counts = Counter()
        largest_moves = {}

        for entry in entries:
            for mover in entry.get("top_movers", []):
                ticker = mover.get("ticker")
                pct = mover.get("percent_change")
                if not ticker or pct is None:
                    continue
                mover_counts[ticker] += 1
                current = largest_moves.get(ticker)
                if current is None or abs(pct) > abs(current):
                    largest_moves[ticker] = pct

        if not mover_counts:
            return None

        ticker, appearances = mover_counts.most_common(1)[0]
        return ticker, appearances, largest_moves[ticker]

    def _top_score_leader(self, entries):
        scores_by_ticker = defaultdict(list)

        for entry in entries:
            for leader in entry.get("score_leaders", []):
                ticker = leader.get("ticker")
                score = leader.get("total_score")
                if ticker and score is not None:
                    scores_by_ticker[ticker].append(score)

        if not scores_by_ticker:
            return None

        ticker, scores = max(
            scores_by_ticker.items(),
            key=lambda item: (len(item[1]), sum(item[1]) / len(item[1])),
        )
        avg_score = sum(scores) / len(scores)
        return ticker, len(scores), avg_score

    def _largest_positive_score_change(self, snapshots):
        gains = [change for change in self._score_changes(snapshots) if change[3] > 0]
        if not gains:
            return None
        return max(gains, key=lambda item: item[3])

    def _largest_negative_score_change(self, snapshots):
        declines = [change for change in self._score_changes(snapshots) if change[3] < 0]
        if not declines:
            return None
        return min(declines, key=lambda item: item[3])

    def _score_changes(self, snapshots):
        if len(snapshots) < 2:
            return []

        first = snapshots[0]
        latest = snapshots[-1]
        first_securities = first.get("securities", {})
        latest_securities = latest.get("securities", {})
        changes = []

        for ticker, latest_data in latest_securities.items():
            first_data = first_securities.get(ticker)
            if not first_data:
                continue
            first_score = first_data.get("total_score")
            latest_score = latest_data.get("total_score")
            if first_score is None or latest_score is None:
                continue
            delta = latest_score - first_score
            if abs(delta) >= 0.1:
                changes.append((ticker, first_score, latest_score, delta))

        return changes

    def _sector_average_moves(self, snapshots):
        sector_moves = defaultdict(list)
        for snapshot in snapshots:
            for data in snapshot.get("securities", {}).values():
                sector = data.get("sector")
                pct = data.get("percent_change")
                status = data.get("status")
                if sector and pct is not None and status == "available":
                    sector_moves[sector].append(pct)

        return [
            (sector, sum(moves) / len(moves), len(moves))
            for sector, moves in sector_moves.items()
        ]

    def _generate_recurring_movers(self, entries):
        mover_counts = Counter()
        largest_moves = {}

        for entry in entries:
            for mover in entry.get("top_movers", []):
                ticker = mover.get("ticker")
                pct = mover.get("percent_change")
                if not ticker or pct is None:
                    continue
                mover_counts[ticker] += 1
                current = largest_moves.get(ticker)
                if current is None or abs(pct) > abs(current):
                    largest_moves[ticker] = pct

        lines = ["## Recurring Top Movers\n"]
        if not mover_counts:
            lines.append("No top-mover data available for this period.\n")
            return "\n".join(lines) + "\n"

        lines.append("| Ticker | Appearances | Largest Move |")
        lines.append("|--------|-------------|--------------|")
        for ticker, count in mover_counts.most_common(10):
            lines.append(f"| {ticker} | {count} | {largest_moves[ticker]:+.2f}% |")
        return "\n".join(lines) + "\n"

    def _generate_score_leaders(self, entries):
        scores_by_ticker = defaultdict(list)

        for entry in entries:
            for leader in entry.get("score_leaders", []):
                ticker = leader.get("ticker")
                score = leader.get("total_score")
                if ticker and score is not None:
                    scores_by_ticker[ticker].append(score)

        lines = ["## Recurring Score Leaders\n"]
        if not scores_by_ticker:
            lines.append("No score-leader data available for this period.\n")
            return "\n".join(lines) + "\n"

        rows = [
            (ticker, len(scores), sum(scores) / len(scores))
            for ticker, scores in scores_by_ticker.items()
        ]
        lines.append("| Ticker | Appearances | Average Score |")
        lines.append("|--------|-------------|---------------|")
        for ticker, count, avg_score in sorted(rows, key=lambda item: (item[1], item[2]), reverse=True)[:10]:
            lines.append(f"| {ticker} | {count} | {avg_score:.1f} |")
        return "\n".join(lines) + "\n"

    def _generate_run_log(self, entries):
        lines = ["## Run Log\n"]
        lines.append("| Generated At | Securities | Top Movers | Reports |")
        lines.append("|--------------|------------|------------|---------|")

        for entry in reversed(entries):
            movers = ", ".join(
                f"{item['ticker']} {item['percent_change']:+.2f}%"
                for item in entry.get("top_movers", [])[:3]
            ) or "N/A"
            reports = self._format_report_links(entry)
            lines.append(
                f"| {entry.get('generated_at', 'N/A')} | "
                f"{entry.get('available_securities', 0)}/{entry.get('securities', 0)} | "
                f"{movers} | {reports} |"
            )

        return "\n".join(lines) + "\n"

    def _format_report_links(self, entry):
        links = []
        if entry.get("report_path"):
            links.append(f"[markdown]({self._report_relative_path(entry['report_path'])})")
        if entry.get("html_report_path"):
            links.append(f"[html]({self._report_relative_path(entry['html_report_path'])})")
        return " / ".join(links) if links else "N/A"

    def _report_relative_path(self, archive_relative_path):
        path = Path(archive_relative_path)
        if str(archive_relative_path).startswith("../reports/"):
            return path.name
        return archive_relative_path

    def _load_entry_snapshots(self, entries):
        snapshots = []
        for entry in entries:
            snapshot_path = self._resolve_archive_path(entry.get("snapshot_path"))
            if not snapshot_path:
                continue
            try:
                import json

                with open(snapshot_path, "r", encoding="utf-8") as f:
                    snapshots.append(json.load(f))
            except Exception:
                continue
        return snapshots

    def _resolve_archive_path(self, archive_relative_path):
        if not archive_relative_path:
            return None
        path = Path(archive_relative_path)
        if path.is_absolute():
            return path
        return (self.archive_dir / path).resolve()

    def _markdown_to_html(self, markdown_content):
        lines = markdown_content.splitlines()
        html_lines = []
        in_list = False
        in_table = False
        table_header_seen = False

        def close_list():
            nonlocal in_list
            if in_list:
                html_lines.append("</ul>")
                in_list = False

        def close_table():
            nonlocal in_table, table_header_seen
            if in_table:
                html_lines.append("</tbody></table>")
                in_table = False
                table_header_seen = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                close_list()
                close_table()
                continue
            if stripped == "---":
                close_list()
                close_table()
                html_lines.append("<hr>")
                continue
            if stripped.startswith("|") and stripped.endswith("|"):
                close_list()
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                if all(set(cell) <= {"-", ":"} for cell in cells):
                    continue
                if not in_table:
                    html_lines.append("<table>")
                    in_table = True
                    table_header_seen = False
                tag = "th" if not table_header_seen else "td"
                row = "".join(f"<{tag}>{self._format_inline_text(cell)}</{tag}>" for cell in cells)
                if not table_header_seen:
                    html_lines.append(f"<thead><tr>{row}</tr></thead><tbody>")
                    table_header_seen = True
                else:
                    html_lines.append(f"<tr>{row}</tr>")
                continue

            close_table()
            if stripped.startswith("# "):
                close_list()
                html_lines.append(f"<h1>{self._format_inline_text(stripped[2:])}</h1>")
            elif stripped.startswith("## "):
                close_list()
                html_lines.append(f"<h2>{self._format_inline_text(stripped[3:])}</h2>")
            elif stripped.startswith("- "):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append(f"<li>{self._format_inline_text(stripped[2:])}</li>")
            else:
                close_list()
                html_lines.append(f"<p>{self._format_inline_text(stripped)}</p>")

        close_list()
        close_table()
        return "\n".join(f"    {line}" for line in html_lines)

    def _format_inline_text(self, text):
        escaped = html.escape(text)
        escaped = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            lambda match: (
                f'<a href="{html.escape(match.group(2), quote=True)}" '
                f'target="_blank" rel="noopener noreferrer">{match.group(1)}</a>'
            ),
            escaped,
        )
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
        return escaped

    def _parse_datetime(self, value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
