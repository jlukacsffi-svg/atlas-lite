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
