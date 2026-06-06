"""Strictly simulated paper-trading account for Atlas Stage 5."""

from datetime import datetime
import json
from pathlib import Path
import uuid


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PAPER_DIR = PROJECT_ROOT / "paper_trading"
DEFAULT_ACCOUNT_FILE = DEFAULT_PAPER_DIR / "account.json"
DEFAULT_LEDGER_FILE = DEFAULT_PAPER_DIR / "ledger.jsonl"

DEFAULT_POLICY = {
    "minimum_cash_reserve_pct": 10.0,
    "maximum_position_pct": 20.0,
    "maximum_daily_trades": 5,
}


class PaperTradingAccount:
    """Manage a local simulated account with conservative risk rules."""

    def __init__(
        self,
        account_file=DEFAULT_ACCOUNT_FILE,
        ledger_file=DEFAULT_LEDGER_FILE,
        policy=None,
        clock=None,
    ):
        self.account_file = Path(account_file)
        self.ledger_file = Path(ledger_file)
        self.policy = dict(DEFAULT_POLICY)
        if policy:
            self.policy.update(policy)
        self.clock = clock or datetime.now

    def initialize(self, starting_cash, name="Atlas Paper Portfolio"):
        starting_cash = float(starting_cash)
        if starting_cash <= 0:
            raise ValueError("starting cash must be positive")
        if self.account_file.exists():
            raise ValueError("paper account already exists")

        now = self.clock().isoformat(timespec="seconds")
        account = {
            "account_version": "1.0",
            "name": str(name).strip() or "Atlas Paper Portfolio",
            "created_at": now,
            "updated_at": now,
            "starting_cash": starting_cash,
            "cash": starting_cash,
            "realized_gain_loss": 0.0,
            "positions": {},
            "policy": dict(self.policy),
        }
        self._save_account(account)
        self._append_event(
            {
                "event": "account_initialized",
                "timestamp": now,
                "starting_cash": starting_cash,
                "policy": dict(self.policy),
            }
        )
        return account

    def load(self):
        if not self.account_file.exists():
            raise ValueError("paper account is not initialized")
        with open(self.account_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def preview_order(self, side, ticker, shares, price, thesis):
        account = self.load()
        order = self._normalize_order(side, ticker, shares, price, thesis)
        return self._validate_order(account, order)

    def execute_order(self, side, ticker, shares, price, thesis, source="manual"):
        """Apply a simulated fill and append it to the local audit ledger."""
        account = self.load()
        order = self._normalize_order(side, ticker, shares, price, thesis)
        validation = self._validate_order(account, order)
        if validation["errors"]:
            raise ValueError("; ".join(validation["errors"]))

        now = self.clock().isoformat(timespec="seconds")
        ticker = order["ticker"]
        notional = order["notional"]
        position = account["positions"].get(
            ticker,
            {"shares": 0.0, "average_cost": 0.0},
        )
        realized = 0.0

        if order["side"] == "buy":
            prior_cost = position["shares"] * position["average_cost"]
            new_shares = position["shares"] + order["shares"]
            position = {
                "shares": new_shares,
                "average_cost": (prior_cost + notional) / new_shares,
            }
            account["cash"] -= notional
            account["positions"][ticker] = position
        else:
            realized = (order["price"] - position["average_cost"]) * order["shares"]
            remaining_shares = position["shares"] - order["shares"]
            account["cash"] += notional
            account["realized_gain_loss"] += realized
            if remaining_shares <= 0.0000001:
                account["positions"].pop(ticker, None)
            else:
                position["shares"] = remaining_shares
                account["positions"][ticker] = position

        account["updated_at"] = now
        self._save_account(account)
        event = {
            "event": "paper_trade",
            "trade_id": f"paper_{uuid.uuid4().hex[:12]}",
            "timestamp": now,
            "source": source,
            **order,
            "realized_gain_loss": round(realized, 2),
            "cash_after": round(account["cash"], 2),
            "policy": dict(account.get("policy", self.policy)),
        }
        self._append_event(event)
        return event

    def status(self, prices=None):
        account = self.load()
        prices = prices or {}
        positions = []
        market_value = 0.0
        unrealized = 0.0

        for ticker, position in sorted(account["positions"].items()):
            price = prices.get(ticker)
            value = position["shares"] * price if price is not None else None
            gain_loss = (
                (price - position["average_cost"]) * position["shares"]
                if price is not None
                else None
            )
            if value is not None:
                market_value += value
                unrealized += gain_loss
            positions.append(
                {
                    "ticker": ticker,
                    **position,
                    "price": price,
                    "market_value": value,
                    "unrealized_gain_loss": gain_loss,
                }
            )

        equity = account["cash"] + market_value
        return {
            "name": account["name"],
            "starting_cash": account["starting_cash"],
            "cash": account["cash"],
            "market_value": market_value,
            "equity": equity,
            "realized_gain_loss": account["realized_gain_loss"],
            "unrealized_gain_loss": unrealized,
            "positions": positions,
            "policy": account.get("policy", dict(self.policy)),
        }

    def ledger(self):
        if not self.ledger_file.exists():
            return []
        events = []
        with open(self.ledger_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def _normalize_order(self, side, ticker, shares, price, thesis):
        side = str(side).strip().lower()
        ticker = str(ticker).strip().upper()
        shares = float(shares)
        price = float(price)
        thesis = str(thesis).strip()
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if not ticker:
            raise ValueError("ticker is required")
        if shares <= 0:
            raise ValueError("shares must be positive")
        if price <= 0:
            raise ValueError("price must be positive")
        if not thesis:
            raise ValueError("a paper-trade thesis is required")
        return {
            "side": side,
            "ticker": ticker,
            "shares": shares,
            "price": price,
            "notional": round(shares * price, 2),
            "thesis": thesis,
        }

    def _validate_order(self, account, order):
        errors = []
        warnings = []
        policy = account.get("policy", self.policy)
        trades_today = self._trades_on_date(self.clock().date().isoformat())
        if trades_today >= int(policy["maximum_daily_trades"]):
            errors.append("maximum daily paper-trade count reached")

        positions = account.get("positions", {})
        position = positions.get(order["ticker"], {"shares": 0.0, "average_cost": 0.0})

        if order["side"] == "sell":
            if order["shares"] > position["shares"]:
                errors.append("paper sell exceeds simulated holdings; short selling is disabled")
        else:
            cash_after = account["cash"] - order["notional"]
            if cash_after < 0:
                errors.append("paper buy exceeds available simulated cash; margin is disabled")

            estimated_equity = account["cash"] + sum(
                item["shares"] * item["average_cost"]
                for item in positions.values()
            )
            reserve = estimated_equity * float(policy["minimum_cash_reserve_pct"]) / 100
            if cash_after < reserve:
                errors.append(
                    f"paper buy would breach {policy['minimum_cash_reserve_pct']:.1f}% cash reserve"
                )

            existing_value = position["shares"] * order["price"]
            resulting_value = existing_value + order["notional"]
            resulting_pct = resulting_value / estimated_equity * 100 if estimated_equity else 100
            if resulting_pct > float(policy["maximum_position_pct"]):
                errors.append(
                    f"paper buy would exceed {policy['maximum_position_pct']:.1f}% position limit"
                )

        return {
            "valid": not errors,
            "errors": errors,
            "warnings": warnings,
            "order": order,
        }

    def _trades_on_date(self, date_text):
        return sum(
            1
            for event in self.ledger()
            if event.get("event") == "paper_trade"
            and str(event.get("timestamp", "")).startswith(date_text)
        )

    def _save_account(self, account):
        self.account_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.account_file, "w", encoding="utf-8") as f:
            json.dump(account, f, indent=2, sort_keys=True)

    def _append_event(self, event):
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
