"""Report generation module"""

from datetime import datetime

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
            section.append("| Ticker | Price | Change | % Change |")
            section.append("|--------|-------|--------|----------|")
            
            for ticker in sorted(self.market_data.keys()):
                data = self.market_data[ticker]
                price = data.get('price')
                change = data.get('change')
                pct = data.get('percent_change')
                status = data.get('status')
                company_name = data.get('company_name', ticker)
                ticker_display = f"{ticker} ({company_name})" if company_name and company_name != ticker else ticker
                direction = "📈" if status == 'available' and change >= 0 else "📉" if status == 'available' else ""
                section.append(
                    f"| {ticker_display} | {self._format_value(price, '${:.2f}') if price is not None else 'N/A'} | "
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
        filename = self.timestamp.strftime("morning_brief_%Y%m%d_%H%M%S.md")
        filepath = os.path.join(reports_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return filepath
