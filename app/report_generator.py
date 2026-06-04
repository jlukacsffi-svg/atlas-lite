"""Report generation module"""

from datetime import datetime
import html
import re

from app.news_data import NewsFetcher
from app.scoring import ScoringEngine


class ReportGenerator:
    """Generate markdown reports from market data"""
    
    def __init__(
        self,
        market_data,
        market_summary,
        previous_snapshot=None,
        earnings_events=None,
        analyst_actions=None,
    ):
        """
        Initialize the report generator
        
        Args:
            market_data (dict): Market data from MarketDataFetcher
            market_summary (dict): Market summary with indices
            previous_snapshot (dict): Optional prior structured research snapshot
            earnings_events (list): Optional upcoming earnings events
            analyst_actions (list): Optional analyst-action headlines
        """
        self.market_data = market_data or {}
        self.market_summary = market_summary or {}
        self.previous_snapshot = previous_snapshot
        self.earnings_events = earnings_events or []
        self.analyst_actions = analyst_actions or []
        self.timestamp = datetime.now()
        self.news_fetcher = NewsFetcher()
        self.scoring_engine = ScoringEngine()
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

        # Upcoming Earnings
        report.append(self._generate_upcoming_earnings())
        
        # Watchlist Summary
        report.append(self._generate_watchlist_summary())

        # Scoring Summary
        report.append(self._generate_scoring_summary())

        # Company Profiles
        report.append(self._generate_company_profile_highlights())

        # Automated Growth
        report.append(self._generate_growth_summary())

        # Automated Quality
        report.append(self._generate_quality_summary())

        # Automated Momentum
        report.append(self._generate_momentum_summary())

        # Research Memory
        report.append(self._generate_research_memory())
        
        # Top Movers
        report.append(self._generate_top_movers())

        # News Highlights
        report.append(self._generate_news_highlights())

        # Analyst Actions
        report.append(self._generate_analyst_actions())
        
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

    def _generate_upcoming_earnings(self):
        """Generate upcoming earnings section"""
        section = ["## Upcoming Earnings\n"]

        if not self.earnings_events:
            section.append("No Atlas universe earnings events found in the next 7 days.\n")
            return "\n".join(section) + "\n"

        section.append("Upcoming Atlas universe earnings events in the next 7 days:\n")
        section.append("| Date | Ticker | Company | Time | Fiscal Quarter | EPS Forecast | Last Year EPS |")
        section.append("|------|--------|---------|------|----------------|--------------|---------------|")

        for event in sorted(self.earnings_events, key=lambda item: (item.get("date", ""), item.get("ticker", ""))):
            section.append(
                f"| {event.get('date', 'N/A')} | {event.get('ticker', 'N/A')} | "
                f"{event.get('company_name', 'N/A')} | {event.get('time', 'N/A')} | "
                f"{event.get('fiscal_quarter_ending', 'N/A')} | {event.get('eps_forecast', 'N/A')} | "
                f"{event.get('last_year_eps', 'N/A')} |"
            )

        return "\n".join(section) + "\n"
    
    def _generate_watchlist_summary(self):
        """Generate watchlist summary section"""
        section = ["## Watchlist Summary\n"]
        
        if self.market_data:
            section.append("| Ticker | Sector | Category | Score | Price | Change | % Change |")
            section.append("|--------|--------|----------|-------|-------|--------|----------|")
            
            for ticker in sorted(self.market_data.keys()):
                data = self.market_data[ticker]
                price = data.get('price')
                change = data.get('change')
                pct = data.get('percent_change')
                status = data.get('status')
                company_name = data.get('company_name', ticker)
                sector = data.get('sector', 'Unclassified')
                category = data.get('category', 'Watchlist')
                total_score = self._score_data(data)
                ticker_display = f"{ticker} ({company_name})" if company_name and company_name != ticker else ticker
                direction = "📈" if status == 'available' and change >= 0 else "📉" if status == 'available' else ""
                section.append(
                    f"| {ticker_display} | {sector} | {category} | {total_score} | "
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

    def _score_data(self, data):
        scores = data.get('scores')
        if not scores:
            return "N/A"
        return f"{self.scoring_engine.score(scores):.1f}"

    def _generate_scoring_summary(self):
        """Generate transparent weighted score rankings"""
        section = ["## Atlas Scoring Summary\n"]
        scored = []

        for ticker, data in self.market_data.items():
            scores = data.get('scores')
            if not scores or data.get('sector') == 'Benchmark ETF':
                continue
            scored.append((ticker, data, self.scoring_engine.score(scores)))

        if not scored:
            section.append("No company scores are available for this run.\n")
            return "\n".join(section) + "\n"

        section.append(
            "Hybrid v3 scores: Growth and Quality are calculated from SEC filing data, and "
            "Momentum is calculated from recent market returns when data is available. "
            "Moat and Risk remain manual seed inputs. "
            "Higher Risk Score means a stronger risk profile. "
            "Weights: Growth 40%, Quality 20%, Moat 15%, Momentum 15%, Risk 10%.\n"
        )
        section.append("| Rank | Ticker | Total | Growth | Quality | Moat | Momentum | Risk |")
        section.append("|------|--------|-------|--------|---------|------|----------|------|")

        for rank, (ticker, data, total_score) in enumerate(
            sorted(scored, key=lambda x: x[2], reverse=True),
            start=1,
        ):
            scores = data['scores']
            section.append(
                f"| {rank} | {ticker} | {total_score:.1f} | "
                f"{scores['growth']:.0f} | {scores['quality']:.0f} | {scores['moat']:.0f} | "
                f"{scores['momentum']:.0f} | {scores['risk']:.0f} |"
            )

        return "\n".join(section) + "\n"

    def _generate_company_profile_highlights(self):
        """Generate concise profiles for the highest-ranked companies"""
        section = ["## Company Profile Highlights\n"]
        ranked = []

        for ticker, data in self.market_data.items():
            if data.get('sector') == 'Benchmark ETF' or not data.get('scores'):
                continue
            ranked.append((ticker, data, self.scoring_engine.score(data['scores'])))

        if not ranked:
            section.append("No company profiles are available for this run.\n")
            return "\n".join(section) + "\n"

        for ticker, data, total_score in sorted(
            ranked,
            key=lambda item: item[2],
            reverse=True,
        )[:5]:
            profile = data.get('profile') or {}
            section.append(f"### {ticker}: {data.get('company_name', ticker)}")
            section.append(
                f"- **Sector**: {data.get('sector', 'Unclassified')} | "
                f"**Category**: {data.get('category', 'Watchlist')} | "
                f"**Atlas Score**: {total_score:.1f}"
            )
            section.append(
                f"- **Thesis**: {profile.get('thesis', data.get('notes', 'No profile notes available.'))}"
            )
            section.append(
                f"- **Key Driver**: {profile.get('key_driver', 'Not yet documented.')} | "
                f"**Key Risk**: {profile.get('key_risk', 'Not yet documented.')}"
            )
            section.append("")

        return "\n".join(section) + "\n"

    def _generate_growth_summary(self):
        """Generate auditable automated fundamental growth metrics"""
        section = ["## Automated Growth\n"]
        growth_rows = []

        for ticker, data in self.market_data.items():
            metrics = data.get('growth_metrics')
            if not metrics or data.get('sector') == 'Benchmark ETF':
                continue
            growth_rows.append((ticker, metrics))

        if not growth_rows:
            section.append("Automated Growth data was unavailable for this run.\n")
            return "\n".join(section) + "\n"

        section.append(
            "Growth Score is calculated from annual revenue growth and annual net-income "
            "growth reported in SEC filings. Revenue growth is the primary input with a "
            "70% weight; net-income growth has a 30% weight when available. "
            "Manual seed Growth scores remain in use when a meaningful filing comparison "
            "is unavailable.\n"
        )
        section.append("| Ticker | Growth Score | Revenue Growth | Net Income Growth | Latest Fiscal Year |")
        section.append("|--------|--------------|----------------|-------------------|--------------------|")

        for ticker, metrics in sorted(
            growth_rows,
            key=lambda item: item[1].get('growth_score', 0),
            reverse=True,
        ):
            section.append(
                f"| {ticker} | {metrics['growth_score']:.1f} | "
                f"{self._format_optional_percent(metrics.get('revenue_growth'))} | "
                f"{self._format_optional_percent(metrics.get('net_income_growth'))} | "
                f"{metrics.get('latest_fiscal_year') or 'N/A'} |"
            )

        return "\n".join(section) + "\n"

    def _generate_quality_summary(self):
        """Generate auditable automated fundamental quality metrics"""
        section = ["## Automated Quality\n"]
        quality_rows = []

        for ticker, data in self.market_data.items():
            metrics = data.get('quality_metrics')
            if not metrics or data.get('sector') == 'Benchmark ETF':
                continue
            quality_rows.append((ticker, metrics))

        if not quality_rows:
            section.append("Automated Quality data was unavailable for this run.\n")
            return "\n".join(section) + "\n"

        section.append(
            "Quality Score is calculated from net margin, operating cash-flow margin, and "
            "free-cash-flow margin reported in the same annual SEC filing period. Manual "
            "seed Quality scores remain in use when meaningful filing metrics are unavailable.\n"
        )
        section.append(
            "| Ticker | Quality Score | Net Margin | Operating Cash Flow Margin | "
            "Free Cash Flow Margin | Latest Fiscal Year |"
        )
        section.append(
            "|--------|---------------|------------|----------------------------|"
            "-----------------------|--------------------|"
        )

        for ticker, metrics in sorted(
            quality_rows,
            key=lambda item: item[1].get('quality_score', 0),
            reverse=True,
        ):
            section.append(
                f"| {ticker} | {metrics['quality_score']:.1f} | "
                f"{self._format_optional_percent(metrics.get('net_margin'))} | "
                f"{self._format_optional_percent(metrics.get('operating_cash_flow_margin'))} | "
                f"{self._format_optional_percent(metrics.get('free_cash_flow_margin'))} | "
                f"{metrics.get('latest_fiscal_year') or 'N/A'} |"
            )

        return "\n".join(section) + "\n"

    def _generate_momentum_summary(self):
        """Generate auditable automated momentum metrics"""
        section = ["## Automated Momentum\n"]
        momentum_rows = []

        for ticker, data in self.market_data.items():
            metrics = data.get('momentum_metrics')
            if not metrics or data.get('sector') == 'Benchmark ETF':
                continue
            momentum_rows.append((ticker, metrics))

        if not momentum_rows:
            section.append("Automated momentum data was unavailable for this run.\n")
            return "\n".join(section) + "\n"

        section.append(
            "Momentum Score is calculated from 1-month and 3-month returns and bounded from 0-100.\n"
        )
        section.append("| Ticker | Momentum Score | 1M Return | 3M Return | 6M Return |")
        section.append("|--------|----------------|-----------|-----------|-----------|")

        for ticker, metrics in sorted(
            momentum_rows,
            key=lambda item: item[1].get('momentum_score', 0),
            reverse=True,
        ):
            section.append(
                f"| {ticker} | {metrics['momentum_score']:.1f} | "
                f"{self._format_optional_percent(metrics.get('return_1m'))} | "
                f"{self._format_optional_percent(metrics.get('return_3m'))} | "
                f"{self._format_optional_percent(metrics.get('return_6m'))} |"
            )

        return "\n".join(section) + "\n"

    def _format_optional_percent(self, value):
        return f"{value:+.2f}%" if value is not None else "N/A"

    def _generate_research_memory(self):
        """Generate comparison with the most recent prior research snapshot"""
        section = ["## Research Memory\n"]

        if not self.previous_snapshot:
            section.append(
                "No prior structured snapshot is available. This run establishes the research-memory baseline.\n"
            )
            return "\n".join(section) + "\n"

        prior_generated_at = self.previous_snapshot.get("generated_at", "unknown time")
        prior_securities = self.previous_snapshot.get("securities", {})
        comparisons = []
        score_changes = []

        for ticker, data in self.market_data.items():
            prior = prior_securities.get(ticker)
            if not prior:
                continue

            current_price = data.get("price")
            prior_price = prior.get("price")
            price_change_pct = None
            if current_price is not None and prior_price not in (None, 0):
                price_change_pct = ((current_price - prior_price) / prior_price) * 100

            current_score = None
            if data.get("scores"):
                current_score = self.scoring_engine.score(data["scores"])
            prior_score = prior.get("total_score")
            score_change = None
            if current_score is not None and prior_score is not None:
                score_change = current_score - prior_score

            comparisons.append((ticker, price_change_pct))
            if score_change is not None and abs(score_change) >= 0.05:
                score_changes.append((ticker, score_change, current_score))

        valid_price_changes = [
            (ticker, change)
            for ticker, change in comparisons
            if change is not None and abs(change) >= 0.01
        ]

        section.append(f"Compared with the prior snapshot from `{prior_generated_at}`.\n")

        if valid_price_changes:
            largest_moves = sorted(
                valid_price_changes,
                key=lambda item: abs(item[1]),
                reverse=True,
            )[:5]
            section.append("Largest price changes since the prior snapshot:\n")
            for ticker, change in largest_moves:
                section.append(f"- **{ticker}**: {change:+.2f}%")
        else:
            section.append("No meaningful price changes since the prior snapshot.\n")

        section.append("")
        if score_changes:
            section.append("Score changes since the prior snapshot:\n")
            for ticker, change, current_score in sorted(
                score_changes,
                key=lambda item: abs(item[1]),
                reverse=True,
            ):
                section.append(
                    f"- **{ticker}**: {change:+.1f} points to {current_score:.1f}"
                )
        else:
            section.append("No Atlas score changes since the prior snapshot.\n")

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

    def _generate_analyst_actions(self):
        """Generate analyst-action headline section"""
        section = ["## Analyst Actions\n"]

        if not self.analyst_actions:
            section.append("No recent analyst-action headlines found for the Atlas universe.\n")
            return "\n".join(section) + "\n"

        section.append(
            "Recent analyst-action headlines found for Atlas universe companies. "
            "This is headline-based tracking, not a full structured ratings database.\n"
        )
        section.append("| Ticker | Action Signal | Headline | Publisher |")
        section.append("|--------|---------------|----------|-----------|")

        for action in self.analyst_actions:
            title = self._format_table_text(action.get("title", "N/A"))
            url = action.get("url", "")
            headline = f"[{title}]({url})" if url else title
            section.append(
                f"| {self._format_table_text(action.get('ticker', 'N/A'))} | "
                f"{self._format_table_text(action.get('action_type', 'N/A'))} | "
                f"{headline} | {self._format_table_text(action.get('publisher', 'Unknown publisher'))} |"
            )

        return "\n".join(section) + "\n"

    def _format_table_text(self, value):
        return str(value).replace("|", "/").replace("\n", " ").strip()
    
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
