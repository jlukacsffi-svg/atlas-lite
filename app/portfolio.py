"""Local portfolio intelligence for Atlas Lite."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORTFOLIO_PATH = PROJECT_ROOT / "data" / "portfolio.json"


class Portfolio:
    """Load optional local portfolio holdings and calculate exposure."""

    def __init__(self, portfolio_path=DEFAULT_PORTFOLIO_PATH):
        self.portfolio_path = Path(portfolio_path)

    def load(self):
        if not self.portfolio_path.exists():
            return {"configured": False, "positions": []}

        with open(self.portfolio_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        positions = payload.get("positions", [])
        if not isinstance(positions, list):
            raise ValueError("portfolio positions must be a list")

        return {
            "configured": True,
            "name": payload.get("name", "Local Portfolio"),
            "positions": [self._normalize_position(position) for position in positions],
        }

    def analyze(self, market_data):
        portfolio = self.load()
        if not portfolio.get("configured"):
            return {"configured": False, "positions": []}

        positions = []
        unavailable = []

        for position in portfolio["positions"]:
            ticker = position["ticker"]
            shares = position["shares"]
            cost_basis = position.get("cost_basis")
            data = market_data.get(ticker, {})
            price = data.get("price")

            if price is None or data.get("status") != "available":
                unavailable.append(ticker)
                market_value = None
                gain_loss = None
                gain_loss_pct = None
            else:
                market_value = shares * price
                gain_loss = market_value - (shares * cost_basis) if cost_basis is not None else None
                gain_loss_pct = (
                    gain_loss / (shares * cost_basis) * 100
                    if gain_loss is not None and shares * cost_basis
                    else None
                )

            positions.append(
                {
                    "ticker": ticker,
                    "shares": shares,
                    "cost_basis": cost_basis,
                    "price": price,
                    "market_value": market_value,
                    "gain_loss": gain_loss,
                    "gain_loss_pct": gain_loss_pct,
                    "sector": data.get("sector", "Unclassified"),
                    "day_change_pct": data.get("percent_change"),
                    "status": data.get("status", "unavailable"),
                }
            )

        total_value = sum(
            position["market_value"] or 0
            for position in positions
        )
        for position in positions:
            position["allocation_pct"] = (
                position["market_value"] / total_value * 100
                if total_value and position["market_value"] is not None
                else None
            )

        day_change_value = sum(
            self._position_day_change_value(position)
            for position in positions
        )
        previous_value = total_value - day_change_value
        day_change_pct = (
            day_change_value / previous_value * 100
            if previous_value
            else None
        )

        return {
            "configured": True,
            "name": portfolio.get("name", "Local Portfolio"),
            "total_value": total_value,
            "day_change_value": day_change_value,
            "day_change_pct": day_change_pct,
            "positions": positions,
            "sector_allocations": self._sector_allocations(positions, total_value),
            "unavailable_tickers": unavailable,
            "risk_alerts": self._risk_alerts(positions, total_value, unavailable),
        }

    def _normalize_position(self, position):
        ticker = str(position.get("ticker", "")).upper().strip()
        shares = float(position.get("shares", 0))
        cost_basis = position.get("cost_basis")

        if not ticker:
            raise ValueError("portfolio position is missing ticker")
        if shares <= 0:
            raise ValueError(f"portfolio position {ticker} must have positive shares")

        return {
            "ticker": ticker,
            "shares": shares,
            "cost_basis": float(cost_basis) if cost_basis is not None else None,
        }

    def _sector_allocations(self, positions, total_value):
        sector_values = {}
        for position in positions:
            market_value = position.get("market_value")
            if market_value is None:
                continue
            sector = position.get("sector", "Unclassified")
            sector_values[sector] = sector_values.get(sector, 0) + market_value

        return [
            {
                "sector": sector,
                "market_value": value,
                "allocation_pct": value / total_value * 100 if total_value else 0,
            }
            for sector, value in sorted(
                sector_values.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    def _position_day_change_value(self, position):
        market_value = position.get("market_value")
        day_change_pct = position.get("day_change_pct")
        if market_value is None or day_change_pct is None or day_change_pct <= -100:
            return 0

        previous_value = market_value / (1 + day_change_pct / 100)
        return market_value - previous_value

    def _risk_alerts(self, positions, total_value, unavailable):
        alerts = []

        for position in positions:
            allocation = position.get("allocation_pct")
            if allocation is not None and allocation >= 25:
                alerts.append(
                    {
                        "type": "position_concentration",
                        "severity": "high" if allocation >= 35 else "medium",
                        "message": f"{position['ticker']} is {allocation:.1f}% of tracked portfolio value.",
                    }
                )

            day_change_pct = position.get("day_change_pct")
            if day_change_pct is not None and day_change_pct <= -5:
                alerts.append(
                    {
                        "type": "holding_drawdown",
                        "severity": "medium",
                        "message": f"{position['ticker']} is down {day_change_pct:.2f}% today.",
                    }
                )

        sector_allocations = self._sector_allocations(positions, total_value)
        for sector in sector_allocations:
            allocation = sector.get("allocation_pct")
            if allocation is not None and allocation >= 40:
                alerts.append(
                    {
                        "type": "sector_concentration",
                        "severity": "high" if allocation >= 55 else "medium",
                        "message": f"{sector['sector']} is {allocation:.1f}% of tracked portfolio value.",
                    }
                )

        if unavailable:
            alerts.append(
                {
                    "type": "missing_data",
                    "severity": "medium",
                    "message": f"Missing market data for holdings: {', '.join(unavailable)}.",
                }
            )

        return alerts
