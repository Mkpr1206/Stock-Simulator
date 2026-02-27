from typing import List
from data.db import get_db
from core.market import MarketData
from core.wallet import Wallet, InsufficientFundsError
from config import STARTING_BALANCE, MAX_TRADE_QUANTITY, FRACTIONAL_SHARES, APP_CURRENCY_SYMBOL


class InsufficientSharesError(Exception):
    pass

class InvalidTradeError(Exception):
    pass


class Portfolio:

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.wallet = Wallet(user_id)
        self.market = MarketData()

    def buy(self, ticker: str, quantity: float, order_type: str = "market") -> dict:
        ticker = ticker.upper().strip()
        self._validate_quantity(quantity)
        price = self.market.get_price(ticker)
        total_cost = round(price * quantity, 2)

        if not self.wallet.can_afford(total_cost):
            balance = self.wallet.get_balance()
            max_shares = int(balance / price)
            raise InsufficientFundsError(
                f"Need {APP_CURRENCY_SYMBOL}{total_cost:,.2f} but have {APP_CURRENCY_SYMBOL}{balance:,.2f}. "
                f"You can afford up to {max_shares} shares."
            )

        self.wallet.debit(total_cost, f"BUY {quantity}x {ticker} @ {APP_CURRENCY_SYMBOL}{price:.2f}")
        self._upsert_holding(ticker, quantity, price)
        trade_id = self._record_trade("BUY", ticker, quantity, price, total_cost, order_type)

        return {
            "trade_id": trade_id, "action": "BUY", "ticker": ticker,
            "quantity": quantity, "price": price, "total_cost": total_cost,
            "currency": "SimBucks", "new_balance": self.wallet.get_balance(),
            "message": f"Bought {quantity} share(s) of {ticker} for {APP_CURRENCY_SYMBOL}{total_cost:,.2f}",
        }

    def sell(self, ticker: str, quantity: float, order_type: str = "market") -> dict:
        ticker = ticker.upper().strip()
        self._validate_quantity(quantity)
        held = self.get_holding_quantity(ticker)
        if held < quantity:
            raise InsufficientSharesError(f"You only hold {held:.4f} shares of {ticker}.")

        price = self.market.get_price(ticker)
        proceeds = round(price * quantity, 2)
        avg_cost = self._get_avg_cost(ticker)
        gain_loss = round((price - avg_cost) * quantity, 2)

        self.wallet.credit(proceeds, f"SELL {quantity}x {ticker} @ {APP_CURRENCY_SYMBOL}{price:.2f}")
        self._reduce_holding(ticker, quantity)
        trade_id = self._record_trade("SELL", ticker, quantity, price, proceeds, order_type)

        return {
            "trade_id": trade_id, "action": "SELL", "ticker": ticker,
            "quantity": quantity, "price": price, "proceeds": proceeds,
            "gain_loss": gain_loss,
            "gain_loss_pct": round((gain_loss / (avg_cost * quantity)) * 100, 2) if avg_cost else 0,
            "currency": "SimBucks", "new_balance": self.wallet.get_balance(),
            "message": f"Sold {quantity} share(s) of {ticker} for {APP_CURRENCY_SYMBOL}{proceeds:,.2f} ({APP_CURRENCY_SYMBOL}{gain_loss:+,.2f})",
        }

    def get_holding_quantity(self, ticker: str) -> float:
        with get_db() as conn:
            row = conn.execute(
                "SELECT quantity FROM holdings WHERE user_id=? AND ticker=?",
                (self.user_id, ticker.upper())
            ).fetchone()
            return row["quantity"] if row else 0.0

    def _get_avg_cost(self, ticker: str) -> float:
        with get_db() as conn:
            row = conn.execute(
                "SELECT avg_cost FROM holdings WHERE user_id=? AND ticker=?",
                (self.user_id, ticker.upper())
            ).fetchone()
            return row["avg_cost"] if row else 0.0

    def get_all_holdings(self) -> List[dict]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT ticker, quantity, avg_cost FROM holdings WHERE user_id=? AND quantity > 0",
                (self.user_id,)
            ).fetchall()

        if not rows:
            return []

        tickers = [r["ticker"] for r in rows]
        prices = self.market.get_prices_bulk(tickers)
        holdings = []

        for row in rows:
            ticker = row["ticker"]
            qty = row["quantity"]
            avg_cost = row["avg_cost"]
            current_price = prices.get(ticker, 0.0)
            current_value = round(current_price * qty, 2)
            cost_basis = round(avg_cost * qty, 2)
            gain_loss = round(current_value - cost_basis, 2)
            gain_loss_pct = round(((current_price - avg_cost) / avg_cost) * 100, 2) if avg_cost else 0.0

            holdings.append({
                "ticker": ticker, "quantity": qty, "avg_cost": round(avg_cost, 2),
                "current_price": current_price, "current_value": current_value,
                "cost_basis": cost_basis, "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct,
                "indicator": "UP" if gain_loss >= 0 else "DOWN",
            })

        return sorted(holdings, key=lambda x: x["current_value"], reverse=True)

    def get_summary(self) -> dict:
        holdings = self.get_all_holdings()
        cash = self.wallet.get_balance()
        invested = sum(h["current_value"] for h in holdings)
        total = round(cash + invested, 2)
        total_gain_loss = round(total - STARTING_BALANCE, 2)
        total_gain_loss_pct = round((total_gain_loss / STARTING_BALANCE) * 100, 2)

        return {
            "cash": cash, "invested_value": round(invested, 2),
            "total_value": total, "starting_balance": STARTING_BALANCE,
            "total_gain_loss": total_gain_loss,
            "total_gain_loss_pct": total_gain_loss_pct,
            "holdings": holdings, "num_positions": len(holdings),
        }

    def get_trade_history(self, limit: int = 50, ticker: str = None) -> list:
        with get_db() as conn:
            if ticker:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE user_id=? AND ticker=? ORDER BY executed_at DESC LIMIT ?",
                    (self.user_id, ticker.upper(), limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trades WHERE user_id=? ORDER BY executed_at DESC LIMIT ?",
                    (self.user_id, limit)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_trade_stats(self) -> dict:
        with get_db() as conn:
            trades = conn.execute("SELECT * FROM trades WHERE user_id=?", (self.user_id,)).fetchall()
        if not trades:
            return {"message": "No trades yet. Start trading to see your stats!"}
        return {
            "total_trades": len(trades),
            "total_buys": sum(1 for t in trades if t["action"] == "BUY"),
            "total_sells": sum(1 for t in trades if t["action"] == "SELL"),
            "tickers_traded": len(set(t["ticker"] for t in trades)),
        }

    def _validate_quantity(self, quantity: float):
        if quantity <= 0:
            raise InvalidTradeError("Quantity must be greater than 0")
        if not FRACTIONAL_SHARES and quantity != int(quantity):
            raise InvalidTradeError("Fractional shares are not enabled")
        if quantity > MAX_TRADE_QUANTITY:
            raise InvalidTradeError(f"Maximum trade size is {MAX_TRADE_QUANTITY} shares")

    def _upsert_holding(self, ticker: str, qty: float, price: float):
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id, quantity, avg_cost FROM holdings WHERE user_id=? AND ticker=?",
                (self.user_id, ticker)
            ).fetchone()
            if existing:
                old_qty = existing["quantity"]
                old_cost = existing["avg_cost"]
                new_qty = old_qty + qty
                new_avg = ((old_qty * old_cost) + (qty * price)) / new_qty
                conn.execute(
                    "UPDATE holdings SET quantity=?, avg_cost=?, updated_at=datetime('now') WHERE id=?",
                    (new_qty, new_avg, existing["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO holdings (user_id, ticker, quantity, avg_cost) VALUES (?,?,?,?)",
                    (self.user_id, ticker, qty, price)
                )

    def _reduce_holding(self, ticker: str, qty: float):
        with get_db() as conn:
            conn.execute(
                "UPDATE holdings SET quantity = quantity - ?, updated_at=datetime('now') WHERE user_id=? AND ticker=?",
                (qty, self.user_id, ticker)
            )
            conn.execute(
                "DELETE FROM holdings WHERE user_id=? AND ticker=? AND quantity <= 0",
                (self.user_id, ticker)
            )

    def _record_trade(self, action, ticker, qty, price, total, order_type) -> int:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO trades (user_id, action, ticker, quantity, price, total_value, order_type) VALUES (?,?,?,?,?,?,?)",
                (self.user_id, action, ticker, qty, price, total, order_type)
            )
            return cursor.lastrowid
