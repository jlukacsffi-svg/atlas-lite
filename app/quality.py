"""Automated fundamental quality measurement using SEC Company Facts."""

from app.growth import GrowthEngine, NET_INCOME_TAGS, REVENUE_TAGS


OPERATING_CASH_FLOW_TAGS = (
    ("us-gaap", "NetCashProvidedByUsedInOperatingActivities"),
    ("ifrs-full", "CashFlowsFromUsedInOperatingActivities"),
)
CAPEX_TAGS = (
    ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
    ("ifrs-full", "PurchaseOfPropertyPlantAndEquipment"),
)


class QualityEngine(GrowthEngine):
    """Convert filing profitability and cash generation into a Quality score."""

    def fetch_metrics(self, ticker):
        payload = self.fetch_company_facts(ticker)
        if not payload:
            return None
        return self.metrics_from_payload(payload)

    def metrics_from_payload(self, payload):
        """Build Quality metrics from an already retrieved SEC Company Facts payload."""
        revenue_pair = self._latest_annual_pair(payload, REVENUE_TAGS)
        if not revenue_pair:
            return None

        revenue = revenue_pair[0]
        period_end = revenue["end"]
        net_income = self._latest_annual_value(payload, NET_INCOME_TAGS, period_end)
        operating_cash_flow = self._latest_annual_value(
            payload,
            OPERATING_CASH_FLOW_TAGS,
            period_end,
        )
        capex = self._latest_annual_value(payload, CAPEX_TAGS, period_end)

        net_margin = self._margin(net_income, revenue)
        operating_cash_flow_margin = self._margin(operating_cash_flow, revenue)
        free_cash_flow_margin = self._free_cash_flow_margin(
            operating_cash_flow,
            capex,
            revenue,
        )
        quality_score = self.calculate_score(
            net_margin,
            operating_cash_flow_margin,
            free_cash_flow_margin,
        )
        if quality_score is None:
            return None

        return {
            "quality_score": quality_score,
            "net_margin": self._round_optional(net_margin),
            "operating_cash_flow_margin": self._round_optional(operating_cash_flow_margin),
            "free_cash_flow_margin": self._round_optional(free_cash_flow_margin),
            "latest_fiscal_year": revenue.get("fy"),
            "period_end": period_end,
            "revenue_tag": revenue.get("tag"),
            "net_income_tag": net_income.get("tag") if net_income else None,
            "operating_cash_flow_tag": (
                operating_cash_flow.get("tag")
                if operating_cash_flow
                else None
            ),
            "capex_tag": capex.get("tag") if capex else None,
            "source": "sec_companyfacts",
        }

    def calculate_score(
        self,
        net_margin,
        operating_cash_flow_margin,
        free_cash_flow_margin,
    ):
        """Calculate a bounded score from available profitability metrics."""
        components = []
        if net_margin is not None:
            components.append((self._metric_score(net_margin, multiplier=2.0), 0.4))
        if operating_cash_flow_margin is not None:
            components.append(
                (self._metric_score(operating_cash_flow_margin, multiplier=1.5), 0.35)
            )
        if free_cash_flow_margin is not None:
            components.append(
                (self._metric_score(free_cash_flow_margin, multiplier=2.0), 0.25)
            )

        if not components:
            return None

        total_weight = sum(weight for _, weight in components)
        weighted_score = sum(score * weight for score, weight in components) / total_weight
        return round(weighted_score, 1)

    def _margin(self, numerator, revenue):
        if not numerator or not revenue or revenue["value"] == 0:
            return None
        return (numerator["value"] / revenue["value"]) * 100

    def _free_cash_flow_margin(self, operating_cash_flow, capex, revenue):
        if not operating_cash_flow or not capex or not revenue or revenue["value"] == 0:
            return None
        free_cash_flow = operating_cash_flow["value"] - abs(capex["value"])
        return (free_cash_flow / revenue["value"]) * 100
