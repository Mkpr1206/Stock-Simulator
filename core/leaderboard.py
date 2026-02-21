"""
core/leaderboard.py
Global leaderboard — shows top-performing portfolios.
Purely educational and motivational. No prizes, no real money.
"""

from data.db import get_db
from core.market import MarketData
from config import LEADERBOARD_TOP_N, STARTING_BALANCE, APP_CURRENCY_SYMBOL


class Leaderboard:
    """
    Ranks all users by their total portfolio value (cash + holdings).
    Refreshed on demand — not real-time to avoid excessive API calls.
    """

    def __init__(self):
        self.market = MarketData()

    def get_top_performers(self, n: int = LEADERBOARD_TOP_N) -> list:
        """
        Returns top N users ranked by total portfolio value.
        Computing this properly requires fetching prices for all tickers.
        """
        with get_db() as conn:
            # Get all users with their cash balances
            users = conn.execute(
                "SELECT u.id, u.username, u.xp_points, w.balance as cash "
                "FROM users u JOIN wallets w ON u.id = w.user_id "
                "WHERE u.is_active=1 ORDER BY w.balance DESC"
            ).fetchall()

            # Get all holdings for all users
            all_holdings = conn.execute(
                "SELECT user_id, ticker, quantity FROM holdings WHERE quantity > 0"
            ).fetchall()

        # Build ticker set for bulk price fetch
        tickers = list(set(h["ticker"] for h in all_holdings))
        prices = self.market.get_prices_bulk(tickers) if tickers else {}

        # Calculate total portfolio value per user
        user_holdings_map = {}
        for h in all_holdings:
            uid = h["user_id"]
            if uid not in user_holdings_map:
                user_holdings_map[uid] = 0.0
            user_holdings_map[uid] += prices.get(h["ticker"], 0.0) * h["quantity"]

        leaderboard = []
        for rank, user in enumerate(users, 1):
            uid = user["id"]
            cash = user["cash"]
            invested = user_holdings_map.get(uid, 0.0)
            total = round(cash + invested, 2)
            gain_loss = round(total - STARTING_BALANCE, 2)
            gain_loss_pct = round((gain_loss / STARTING_BALANCE) * 100, 2)

            leaderboard.append({
                "rank":           rank,
                "username":       user["username"],
                "total_value":    total,
                "cash":           round(cash, 2),
                "invested":       round(invested, 2),
                "gain_loss":      gain_loss,
                "gain_loss_pct":  gain_loss_pct,
                "indicator":      "📈" if gain_loss >= 0 else "📉",
                "xp_points":      user["xp_points"],
            })

        leaderboard.sort(key=lambda x: x["total_value"], reverse=True)
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        return leaderboard[:n]

    def get_user_rank(self, user_id: int) -> dict:
        """Get a specific user's rank among all players."""
        board = self.get_top_performers(n=9999)
        for entry in board:
            # We need username lookup
            pass

        with get_db() as conn:
            user = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
            if not user:
                return {"error": "User not found"}

        username = user["username"]
        for entry in board:
            if entry["username"] == username:
                total = len(board)
                percentile = round((1 - (entry["rank"] / total)) * 100, 1)
                return {
                    **entry,
                    "total_players": total,
                    "percentile":    percentile,
                    "message":       f"You're in the top {100-percentile:.0f}% of traders!",
                }

        return {"rank": "Unranked", "message": "Make your first trade to appear on the leaderboard!"}

    def get_most_traded_stocks(self, limit: int = 10) -> list:
        """What stocks are most popular among all SimTrader users?"""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT ticker,
                       COUNT(*) as trade_count,
                       SUM(CASE WHEN action='BUY' THEN 1 ELSE 0 END) as buys,
                       SUM(CASE WHEN action='SELL' THEN 1 ELSE 0 END) as sells
                FROM trades
                GROUP BY ticker
                ORDER BY trade_count DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_community_stats(self) -> dict:
        """High-level stats about the StockSim community."""
        with get_db() as conn:
            total_users = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_active=1").fetchone()["c"]
            total_trades = conn.execute("SELECT COUNT(*) as c FROM trades").fetchone()["c"]
            total_volume = conn.execute("SELECT SUM(total_value) as s FROM trades").fetchone()["s"] or 0
            avg_balance = conn.execute("SELECT AVG(balance) as a FROM wallets").fetchone()["a"] or 0

        return {
            "total_traders":       total_users,
            "total_trades":        total_trades,
            "total_sim_volume":    round(total_volume, 2),
            "average_balance":     round(avg_balance, 2),
            "currency":            "SimBucks",
            "disclaimer":          "All figures are in SimBucks — no real money involved.",
        }
