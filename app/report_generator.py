"""Report generation module"""

from datetime import datetime
import html
import re

from app.news_data import NewsFetcher


class ReportGenerator:
    """Generate markdown reports from market data"""
    
    def __init__(self, market_data, market_summary):
        """
        Initialize the report generator
        
        Args:
            market_data (dict): Market data from MarketDataFetcher
            market_summary (dict): Market summary with indices
        """
        self.market_data = market_data or {}
        self.market_summary = market_summary or {}
        self.timestamp = datetime.now()
        self.news_fetcher = NewsFetcher()
        self.last_html_path = None
    
    def generate_report(self):
        """
        Generate a complete Morning Executive Brief
        
        Returns:
            str: Markdown formatted report
        """
        report = []
        
        # Title
        report.append("# Morning Executive Brief\n")
        
        # Date
        date_str = self.timestamp.strftime("%B %d, %Y")
        report.append(f"## Date\n\n{date_str}\n")

        # Data Quality
        report.append(self._generate_data_quality())

        if not self._has_valid_market_data():
            report.append("### ⚠️ Market data unavailable for this run.\n")
        
        # Executive Summary
        report.append(self._generate_executive_summary())

        # Market Summary
        report.append(self._generate_market_summary())
        
        # Watchlist Summary
        report.append(self._generate_watchlist_summary())
        
        # Top Movers
        report.append(self._generate_top_movers())

        # News Highlights
        report.append(self._generate_news_highlights())
        
        # Potential Opportunities
        report.append(self._generate_opportunities())
        
        # Risks To Watch
        report.append(self._generate_risks())
        
        # Footer
        report.append(f"\n---\n\n*Report generated on {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}*\n")
        
        return "\n".join(report)

    def generate_html_report(self, markdown_content=None):
        """
        Generate an HTML version of the Morning Executive Brief.

        Args:
            markdown_content (str): Optional markdown content to render.

        Returns:
            str: Complete HTML document
        """
        markdown_content = markdown_content or self.generate_report()
        body = self._markdown_to_html(markdown_content)
        title = f"Morning Executive Brief - {self.timestamp.strftime('%B %d, %Y')}"

        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1d2433;
      --muted: #667085;
      --line: #d9dee8;
      --accent: #2457a6;
      --positive: #0f7a4f;
      --negative: #a33b35;
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.55;
    }}

    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 32px auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 32px;
      box-shadow: 0 12px 30px rgba(29, 36, 51, 0.08);
    }}

    h1 {{
      margin: 0 0 20px;
      color: #101828;
      font-size: 2rem;
      line-height: 1.2;
    }}

    h2 {{
      margin: 32px 0 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--line);
      color: #172033;
      font-size: 1.35rem;
    }}

    h3 {{
      margin: 20px 0 8px;
      color: #243b63;
      font-size: 1.05rem;
    }}

    p, ul {{
      margin-top: 0;
    }}

    a {{
      color: var(--accent);
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0 24px;
      font-size: 0.94rem;
    }}

    th, td {{
      border: 1px solid var(--line);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
    }}

    th {{
      background: #eef2f8;
      color: #1d2939;
      font-weight: 650;
    }}

    tr:nth-child(even) td {{
      background: #fafbfc;
    }}

    li {{
      margin-bottom: 7px;
    }}

    hr {{
      border: 0;
      border-top: 1px solid var(--line);
      margin: 32px 0 12px;
    }}

    em {{
      color: var(--muted);
    }}

    @media (max-width: 720px) {{
      main {{
        width: 100%;
        margin: 0;
        border-radius: 0;
        border-left: 0;
        border-right: 0;
        padding: 20px;
      }}

      table {{
        display: block;
        overflow-x: auto;
        white-space: nowrap;
      }}
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

                cell_html = "".join(
                    f"<{'th' if not table_header_seen else 'td'}>{self._format_inline_text(cell)}</{'th' if not table_header_seen else 'td'}>"
                    for cell in cells
                )
                if not table_header_seen:
                    html_lines.append(f"<thead><tr>{cell_html}</tr></thead><tbody>")
                    table_header_seen = True
                else:
                    html_lines.append(f"<tr>{cell_html}</tr>")
                continue

            close_table()

            if stripped.startswith("# "):
                close_list()
                html_lines.append(f"<h1>{self._format_inline_text(stripped[2:])}</h1>")
            elif stripped.startswith("## "):
                close_list()
                html_lines.append(f"<h2>{self._format_inline_text(stripped[3:])}</h2>")
            elif stripped.startswith("### "):
                close_list()
                html_lines.append(f"<h3>{self._format_inline_text(stripped[4:])}</h3>")
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
    
    def _has_valid_market_data(self):
        return any(
            item.get('status') == 'available'
            for item in self.market_data.values()
        ) or any(
            item.get('status') == 'available'
            for item in self.market_summary.values()
        )

    def _available_market_data(self):
        return {
            ticker: data for ticker, data in self.market_data.items()
            if data.get('status') == 'available'
        }

    def _generate_executive_summary(self):
        """Generate a concise, rule-based executive summary"""
        section = ["## Executive Summary\n"]
        available_data = self._available_market_data()

        if not available_data:
            section.append("- Market data was unavailable, so Atlas cannot produce a reliable executive summary.")
            section.append("- Review data connectivity and fallback diagnostics before using today's report.")
            return "\n".join(section) + "\n"

        spy_pct = self.market_summary.get('SPY', {}).get('percent_change')
        qqq_pct = self.market_summary.get('QQQ', {}).get('percent_change')
        index_changes = [
            pct for pct in (spy_pct, qqq_pct)
            if pct is not None
        ]
        avg_index_change = sum(index_changes) / len(index_changes) if index_changes else 0

        if avg_index_change >= 1:
            market_tone = "risk-on"
        elif avg_index_change <= -1:
            market_tone = "risk-off"
        else:
            market_tone = "mixed to stable"

        sorted_by_change = sorted(
            available_data.items(),
            key=lambda x: x[1].get('percent_change', 0),
            reverse=True,
        )
        top_gainer, top_gainer_data = sorted_by_change[0]
        top_loser, top_loser_data = sorted_by_change[-1]

        significant_movers = [
            (ticker, data) for ticker, data in available_data.items()
            if abs(data.get('percent_change', 0)) > 2
        ]
        gainers = [
            (ticker, data) for ticker, data in significant_movers
            if data.get('percent_change', 0) > 0
        ]
        losers = [
            (ticker, data) for ticker, data in significant_movers
            if data.get('percent_change', 0) < 0
        ]

        section.append(
            f"- **Market tone**: {market_tone}; SPY {self._format_value(spy_pct, '{:+.2f}%')} "
            f"and QQQ {self._format_value(qqq_pct, '{:+.2f}%')}."
        )
        section.append(
            f"- **Leadership**: {top_gainer} led the watchlist at "
            f"{top_gainer_data.get('percent_change', 0):+.2f}%."
        )
        section.append(
            f"- **Pressure point**: {top_loser} was the weakest name at "
            f"{top_loser_data.get('percent_change', 0):+.2f}%."
        )

        if significant_movers:
            section.append(
                f"- **Volatility**: {len(significant_movers)} watchlist names moved more than 2%; "
                f"{len(gainers)} higher and {len(losers)} lower."
            )
        else:
            section.append("- **Volatility**: no watchlist names moved more than 2%.")

        if losers:
            downside_focus = ", ".join(
                ticker for ticker, _ in sorted(
                    losers,
                    key=lambda x: x[1].get('percent_change', 0)
                )[:3]
            )
            section.append(f"- **Risk focus**: monitor downside follow-through in {downside_focus}.")
        elif gainers:
            upside_focus = ", ".join(
                ticker for ticker, _ in sorted(
                    gainers,
                    key=lambda x: abs(x[1].get('percent_change', 0)),
                    reverse=True
                )[:3]
            )
            section.append(
                f"- **Opportunity focus**: review whether strength in {upside_focus} "
                "is supported by company-specific news."
            )
        else:
            section.append("- **Action focus**: no urgent watchlist dislocation detected.")

        return "\n".join(section) + "\n"

    def _generate_data_quality(self):
        """Generate data quality/source section"""
        section = ["## Data Quality\n"]
        
        total = len(self.market_data)
        available = sum(1 for data in self.market_data.values() if data.get('status') == 'available')
        unavailable = total - available
        yfinance_count = sum(1 for data in self.market_data.values() if data.get('source') == 'yfinance')
        yahoo_count = sum(1 for data in self.market_data.values() if data.get('source') == 'yahoo_fallback')
        placeholder_count = sum(1 for data in self.market_data.values() if data.get('source') == 'placeholder')
        
        section.append(f"- **Tickers Requested**: {total}")
        section.append(f"- **Real Data**: {available} ({yfinance_count} from yfinance, {yahoo_count} from Yahoo fallback)")
        section.append(f"- **Placeholder Data**: {unavailable}\n")
        
        return "\n".join(section) + "\n"
    
    def _format_value(self, value, fmt="{:+.2f}"):
        if value is None:
            return "N/A"
        return fmt.format(value)
    
    def _generate_market_summary(self):
        """Generate market summary section"""
        section = ["## Market Summary\n"]
        
        if self.market_summary:
            section.append("| Index | Price | Change | % Change |")
            section.append("|-------|-------|--------|----------|")
            
            for idx, data in self.market_summary.items():
                price = data['price']
                change = data['change']
                pct = data['percent_change']
                status = data.get('status')
                direction = "📈" if status == 'available' and change >= 0 else "📉" if status == 'available' else ""
                section.append(
                    f"| {idx} | {self._format_value(price, '${:.2f}') if price is not None else 'N/A'} | "
                    f"{self._format_value(change)} | {self._format_value(pct, '{:+.2f}%')} {direction} |"
                )
        else:
            section.append("Unable to fetch market summary data at this time.\n")
        
        return "\n".join(section) + "\n"
    
    def _generate_watchlist_summary(self):
        """Generate watchlist summary section"""
        section = ["## Watchlist Summary\n"]
        
        if self.market_data:
            section.append("| Ticker | Sector | Category | Price | Change | % Change |")
            section.append("|--------|--------|----------|-------|--------|----------|")
            
            for ticker in sorted(self.market_data.keys()):
                data = self.market_data[ticker]
                price = data.get('price')
                change = data.get('change')
                pct = data.get('percent_change')
                status = data.get('status')
                company_name = data.get('company_name', ticker)
                sector = data.get('sector', 'Unclassified')
                category = data.get('category', 'Watchlist')
                ticker_display = f"{ticker} ({company_name})" if company_name and company_name != ticker else ticker
                direction = "📈" if status == 'available' and change >= 0 else "📉" if status == 'available' else ""
                section.append(
                    f"| {ticker_display} | {sector} | {category} | "
                    f"{self._format_value(price, '${:.2f}') if price is not None else 'N/A'} | "
                    f"{self._format_value(change)} | {self._format_value(pct, '{:+.2f}%')} {direction} |"
                )
        else:
            section.append("Unable to fetch watchlist data at this time.\n")
        
        return "\n".join(section) + "\n"
    
    def _generate_top_movers(self):
        """Generate top movers section"""
        section = ["## Top Movers\n"]
        available_data = {
            ticker: data for ticker, data in self.market_data.items()
            if data.get('status') == 'available'
        }
        
        if not available_data:
            section.append("Unable to determine top movers at this time.\n")
            return "\n".join(section) + "\n"
        
        sorted_data = sorted(
            available_data.items(),
            key=lambda x: x[1]['percent_change'],
            reverse=True
        )
        
        section.append("### 🔝 Top Gainers\n")
        for ticker, data in sorted_data[:3]:
            section.append(f"- **{ticker}**: {data['percent_change']:+.2f}% (${data['price']})")
        
        section.append("")
        
        section.append("### 🔻 Top Losers\n")
        for ticker, data in sorted_data[-3:]:
            section.append(f"- **{ticker}**: {data['percent_change']:+.2f}% (${data['price']})")
        
        return "\n".join(section) + "\n"

    def _get_significant_movers(self, threshold=2, limit=6):
        available_data = {
            ticker: data for ticker, data in self.market_data.items()
            if data.get('status') == 'available'
        }

        movers = [
            (ticker, data) for ticker, data in available_data.items()
            if abs(data.get('percent_change', 0)) > threshold
        ]

        return sorted(
            movers,
            key=lambda x: abs(x[1].get('percent_change', 0)),
            reverse=True
        )[:limit]

    def _generate_news_highlights(self):
        """Generate recent headline section for major movers"""
        section = ["## News Highlights\n"]
        movers = self._get_significant_movers()

        if not movers:
            section.append("No major watchlist moves required headline review today.\n")
            return "\n".join(section) + "\n"

        section.append("Recent headlines for watchlist moves greater than 2%:\n")

        for ticker, data in movers:
            company_name = data.get('company_name') or ticker
            pct = data.get('percent_change', 0)
            section.append(f"### {ticker}: {pct:+.2f}%")

            headlines = self.news_fetcher.fetch_headlines(ticker, company_name)
            if not headlines:
                section.append("- No recent headlines found from the configured news source.")
                section.append("")
                continue

            for headline in headlines:
                title = headline['title']
                publisher = headline['publisher']
                url = headline['url']
                relevance = headline.get('relevance', 'broad')
                relevance_label = {
                    'company': 'company headline',
                    'sector': 'sector headline',
                    'broad': 'broad market headline',
                }.get(relevance, 'headline')
                if url:
                    section.append(f"- [{title}]({url}) - {publisher} ({relevance_label})")
                else:
                    section.append(f"- {title} - {publisher} ({relevance_label})")

            section.append("")

        return "\n".join(section) + "\n"
    
    def _generate_opportunities(self):
        """Generate potential opportunities section"""
        section = ["## Potential Opportunities\n"]
        available_data = {
            ticker: data for ticker, data in self.market_data.items()
            if data.get('status') == 'available'
        }
        
        if not available_data:
            section.append("Unable to identify opportunities at this time.\n")
            return "\n".join(section) + "\n"
        
        opportunities = [
            (ticker, data) for ticker, data in available_data.items()
            if abs(data['percent_change']) > 2
        ]
        
        if opportunities:
            section.append("Stocks showing significant price movements (>2%):\n")
            for ticker, data in sorted(opportunities, key=lambda x: abs(x[1]['percent_change']), reverse=True):
                direction = "strong buying" if data['change'] >= 0 else "selling"
                section.append(
                    f"- **{ticker}**: {abs(data['percent_change']):.2f}% move with {direction} pressure"
                )
        else:
            section.append("Market showing stability with no significant outliers detected.\n")
        
        return "\n".join(section) + "\n"
    
    def _generate_risks(self):
        """Generate risks to watch section"""
        section = ["## Risks To Watch\n"]
        
        available_data = {
            ticker: data for ticker, data in self.market_data.items()
            if data.get('status') == 'available'
        }
        risks = []
        
        if available_data:
            losers = [
                (ticker, data) for ticker, data in available_data.items()
                if data['percent_change'] < -2
            ]
            if losers:
                risks.append(
                    f"**Sector Weakness**: {len(losers)} stocks down >2% - monitor for broader "
                    "market implications"
                )
            
            all_changes = [abs(data['percent_change']) for data in available_data.values()]
            if all_changes and max(all_changes) > 5:
                risks.append("**High Volatility**: Significant price swings detected - exercise caution")

        if risks:
            for risk in risks:
                section.append(f"- {risk}")
        else:
            section.append("- Market conditions appear stable at this time")
            section.append("- Continue monitoring watchlist for unexpected developments")

        return "\n".join(section) + "\n"

    def save_report(self, reports_dir="reports"):
        """
        Save the generated report to a file
        
        Args:
            reports_dir (str): Directory to save the report
            
        Returns:
            str: Path to the saved file
        """
        import os
        
        os.makedirs(reports_dir, exist_ok=True)
        
        report_content = self.generate_report()
        base_filename = self.timestamp.strftime("morning_brief_%Y%m%d_%H%M%S")
        filepath = os.path.join(reports_dir, f"{base_filename}.md")
        html_filepath = os.path.join(reports_dir, f"{base_filename}.html")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)

        with open(html_filepath, 'w', encoding='utf-8') as f:
            f.write(self.generate_html_report(report_content))

        self.last_html_path = html_filepath
        
        return filepath
