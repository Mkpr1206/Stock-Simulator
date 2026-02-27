from typing import List
from data.db import get_db
from core.market import MarketData
from core.wallet import Wallet
from config import APP_CURRENCY_SYMBOL


class OrderNotFoundError(Exception):
    pass

class OrderAlreadyClosedError(Exception):
    pass


class OrderManager:

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.market = MarketData()

    def place_limit_buy(self, ticker: str, quantity: float, limit_price: float) -> dict:
        ticker = ticker.upper()
        total_required = round(limit_price * quantity, 2)
        wallet = Wallet(self.user_id)
        wallet.debit(total_required, f"Reserved for LIMIT BUY {quantity}x {ticker}")
        order_id = self._insert_order("BUY", ticker, quantity, limit_price, "limit")
        return {
            "order_id": order_id, "type": "LIMIT BUY", "ticker": ticker,
            "quantity": quantity, "limit_price": limit_price,
            "funds_reserved": total_required, "status": "pending",
            "message": f"Limit buy placed: {quantity}x {ticker} when price drops to {APP_CURRENCY_SYMBOL}{limit_price:.2f}",
        }

    def place_limit_sell(self, ticker: str, quantity: float, limit_price: float) -> dict:
        ticker = ticker.upper()
        order_id = self._insert_order("SELL", ticker, quantity, limit_price, "limit")
        return {
            "order_id": order_id, "type": "LIMIT SELL", "ticker": ticker,
            "quantity": quantity, "limit_price": limit_price, "status": "pending",
            "message": f"Limit sell placed: {quantity}x {ticker} when price rises to {APP_CURRENCY_SYMBOL}{limit_price:.2f}",
        }

    def place_stop_loss(self, ticker: str, quantity: float, stop_price: float) -> dict:
        ticker = ticker.upper()
        current_price = self.market.get_price(ticker)
        if stop_price >= current_price:
            raise ValueError(f"Stop price must be below current price ({APP_CURRENCY_SYMBOL}{current_price:.2f})")
        order_id = self._insert_order("SELL", ticker, quantity, stop_price, "stop_loss")
        return {
            "order_id": order_id, "type": "STOP LOSS", "ticker": ticker,
            "quantity": quantity, "stop_price": stop_price,
            "current_price": current_price, "status": "pending",
            "message": f"Stop-loss set: sell {quantity}x {ticker} if price falls to {APP_CURRENCY_SYMBOL}{stop_price:.2f}",
        }

    def cancel_order(self, order_id: int) -> dict:
        with get_db() as conn:
            order = conn.execute(
                "SELECT * FROM limit_orders WHERE id=? AND user_id=?", (order_id, self.user_id)
            ).fetchone()
            if not order:
                raise OrderNotFoundError(f"Order #{order_id} not found")
            if order["status"] != "pending":
                raise OrderAlreadyClosedError(f"Order #{order_id} is already {order['status']}")
            conn.execute("UPDATE limit_orders SET status='cancelled' WHERE id=?", (order_id,))
            if order["action"] == "BUY" and order["order_type"] == "limit":
                reserved = round(order["limit_price"] * order["quantity"], 2)
                Wallet(self.user_id).credit(reserved, f"Refund for cancelled order #{order_id}")
        return {"order_id": order_id, "status": "cancelled", "message": f"Order #{order_id} cancelled."}

    def get_pending_orders(self) -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM limit_orders WHERE user_id=? AND status='pending' ORDER BY created_at DESC",
                (self.user_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_order_history(self, limit: int = 50) -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM limit_orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (self.user_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def check_and_execute_pending_orders(self) -> List[dict]:
        with get_db() as conn:
            pending = conn.execute(
                "SELECT * FROM limit_orders WHERE user_id=? AND status='pending'", (self.user_id,)
            ).fetchall()
        executed = []
        for order in pending:
            try:
                current_price = self.market.get_price(order["ticker"])
                should_execute = False
                if order["action"] == "BUY":
                    should_execute = current_price <= order["limit_price"]
                elif order["action"] == "SELL":
                    if order["order_type"] == "limit":
                        should_execute = current_price >= order["limit_price"]
                    elif order["order_type"] == "stop_loss":
                        should_execute = current_price <= order["limit_price"]
                if should_execute:
                    with get_db() as conn:
                        conn.execute(
                            "UPDATE limit_orders SET status='executed', executed_at=datetime('now') WHERE id=?",
                            (order["id"],)
                        )
                    executed.append({"order_id": order["id"], "ticker": order["ticker"],
                                     "execution_price": current_price, "action": order["action"]})
            except Exception:
                pass
        return executed

    def _insert_order(self, action, ticker, qty, limit_price, order_type) -> int:
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO limit_orders (user_id, action, ticker, quantity, limit_price, status) VALUES (?,?,?,?,?,?)",
                (self.user_id, action, ticker, qty, limit_price, "pending")
            )
            return cursor.lastrowid
