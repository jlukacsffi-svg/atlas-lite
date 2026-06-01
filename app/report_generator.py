"""Report generation module"""

from datetime import datetime


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
        
        # Market Summary
        report.append(self._generate_market_summary())
        
        # Watchlist Summary
        report.append(self._generate_watchlist_summary())
        
        # Top Movers
        report.append(self._generate_top_movers())
        
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
