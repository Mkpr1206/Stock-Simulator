from data.db import get_db
from config import STARTING_BALANCE, APP_CURRENCY_NAME, APP_CURRENCY_SYMBOL, ALLOW_PORTFOLIO_RESET, MAX_RESETS_PER_DAY


class InsufficientFundsError(Exception):
    pass

class PurchaseBlockedError(Exception):
    pass

class ResetLimitError(Exception):
    pass


class Wallet:

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_balance(self) -> float:
        with get_db() as conn:
            row = conn.execute("SELECT balance FROM wallets WHERE user_id=?", (self.user_id,)).fetchone()
            if not row:
                raise ValueError(f"No wallet found for user {self.user_id}")
            return round(row["balance"], 2)

    def get_wallet_info(self) -> dict:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM wallets WHERE user_id=?", (self.user_id,)).fetchone()
            if not row:
                raise ValueError(f"No wallet found for user {self.user_id}")
            return {
                "balance": round(row["balance"], 2),
                "total_deposited": round(row["total_deposited"], 2),
                "currency": APP_CURRENCY_NAME,
                "symbol": APP_CURRENCY_SYMBOL,
                "can_purchase": False,
                "updated_at": row["updated_at"],
            }

    def credit(self, amount: float, reason: str) -> float:
        if amount <= 0:
            raise ValueError("Credit amount must be positive")
        with get_db() as conn:
            conn.execute(
                "UPDATE wallets SET balance = balance + ?, updated_at = datetime('now') WHERE user_id=?",
                (amount, self.user_id)
            )
            new_balance = self.get_balance()
            self._log(conn, "credit", amount, reason, new_balance)
        return new_balance

    def debit(self, amount: float, reason: str) -> float:
        if amount <= 0:
            raise ValueError("Debit amount must be positive")
        current = self.get_balance()
        if current < amount:
            raise InsufficientFundsError(
                f"Insufficient {APP_CURRENCY_NAME}. "
                f"Required: {APP_CURRENCY_SYMBOL}{amount:,.2f}, "
                f"Available: {APP_CURRENCY_SYMBOL}{current:,.2f}"
            )
        with get_db() as conn:
            conn.execute(
                "UPDATE wallets SET balance = balance - ?, updated_at = datetime('now') WHERE user_id=?",
                (amount, self.user_id)
            )
            new_balance = self.get_balance()
            self._log(conn, "debit", amount, reason, new_balance)
        return new_balance

    def can_afford(self, amount: float) -> bool:
        return self.get_balance() >= amount

    def reset(self, portfolio_value: float = 0.0) -> dict:
        if not ALLOW_PORTFOLIO_RESET:
            raise ResetLimitError("Portfolio reset is disabled.")
        resets_today = self._count_resets_today()
        if resets_today >= MAX_RESETS_PER_DAY:
            raise ResetLimitError(f"Maximum {MAX_RESETS_PER_DAY} resets per day reached.")
        with get_db() as conn:
            conn.execute(
                "UPDATE wallets SET balance=?, updated_at=datetime('now') WHERE user_id=?",
                (STARTING_BALANCE, self.user_id)
            )
            conn.execute("DELETE FROM holdings WHERE user_id=?", (self.user_id,))
            conn.execute(
                "UPDATE limit_orders SET status='cancelled' WHERE user_id=? AND status='pending'",
                (self.user_id,)
            )
            conn.execute(
                "INSERT INTO portfolio_resets (user_id, portfolio_value_at_reset) VALUES (?,?)",
                (self.user_id, portfolio_value)
            )
            self._log(conn, "reset", STARTING_BALANCE, "Portfolio reset", STARTING_BALANCE)
        return {
            "message": f"Portfolio reset! You now have {APP_CURRENCY_SYMBOL}{STARTING_BALANCE:,.0f} {APP_CURRENCY_NAME}.",
            "new_balance": STARTING_BALANCE,
            "resets_used_today": resets_today + 1,
            "resets_remaining_today": MAX_RESETS_PER_DAY - (resets_today + 1),
        }

    def _count_resets_today(self) -> int:
        with get_db() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM portfolio_resets WHERE user_id=? AND date(reset_at) = date('now')",
                (self.user_id,)
            ).fetchone()
            return row["cnt"] if row else 0

    def get_transaction_history(self, limit: int = 50) -> list:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (self.user_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def _log(self, conn, tx_type, amount, reason, balance_after):
        conn.execute(
            "INSERT INTO transactions (user_id, type, amount, reason, balance_after) VALUES (?,?,?,?,?)",
            (self.user_id, tx_type, amount, reason, balance_after)
        )

    @classmethod
    def create_for_user(cls, user_id: int) -> "Wallet":
        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO wallets (user_id, balance, total_deposited) VALUES (?,?,?)",
                (user_id, STARTING_BALANCE, STARTING_BALANCE)
            )
            conn.execute(
                "INSERT INTO transactions (user_id, type, amount, reason, balance_after) VALUES (?,?,?,?,?)",
                (user_id, "credit", STARTING_BALANCE, "Welcome! Initial SimBucks grant.", STARTING_BALANCE)
            )
        return cls(user_id)
