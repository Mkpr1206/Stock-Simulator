"""
analytics/history.py
Trade history analysis and performance tracking.
Helps users learn from their past trades with detailed breakdowns.
"""

from data.db import get_db
from config import STARTING_BALANCE, APP_CURRENCY_SYMBOL


class PerformanceTracker:
    """Analyzes a user's complete trading history for educational insight."""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def get_full_history(self, limit: int = 100) -> dict:
        """Returns annotated trade history with educational context."""
        with get_db() as conn:
            trades = conn.execute(
                "SELECT * FROM trades WHERE user_id=? ORDER BY executed_at DESC LIMIT ?",
                (self.user_id, limit)
            ).fetchall()
            wallet_txns = conn.execute(
                "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
                (self.user_id,)
            ).fetchall()

        return {
            "trades": [dict(t) for t in trades],
            "transactions": [dict(t) for t in wallet_txns],
            "count": len(trades),
        }

    def get_performance_report(self) -> dict:
        """
        Comprehensive trading performance report.
        Identifies strengths, weaknesses, and learning opportunities.
        """
        with get_db() as conn:
            trades = conn.execute(
                "SELECT * FROM trades WHERE user_id=? ORDER BY executed_at",
                (self.user_id,)
            ).fetchall()
            wallet = conn.execute(
                "SELECT balance FROM wallets WHERE user_id=?", (self.user_id,)
            ).fetchone()
            resets = conn.execute(
                "SELECT COUNT(*) as c FROM portfolio_resets WHERE user_id=?", (self.user_id,)
            ).fetchone()

        if not trades:
            return {
                "message":  "No trades yet! Start trading to see your performance report.",
                "tip":      "Try buying a stock you know — a company whose products you use every day.",
            }

        total_trades    = len(trades)
        buys            = [t for t in trades if t["action"] == "BUY"]
        sells           = [t for t in trades if t["action"] == "SELL"]
        unique_tickers  = set(t["ticker"] for t in trades)
        current_balance = wallet["balance"] if wallet else STARTING_BALANCE

        # Most traded ticker
        ticker_counts = {}
        for t in trades:
            ticker_counts[t["ticker"]] = ticker_counts.get(t["ticker"], 0) + 1
        most_traded = max(ticker_counts, key=ticker_counts.get) if ticker_counts else None

        # Largest single trade
        largest_trade = max(trades, key=lambda t: t["total_value"]) if trades else None

        report = {
            "summary": {
                "total_trades":      total_trades,
                "total_buys":        len(buys),
                "total_sells":       len(sells),
                "unique_tickers":    len(unique_tickers),
                "tickers_traded":    list(unique_tickers),
                "portfolio_resets":  resets["c"] if resets else 0,
            },
            "highlights": {
                "most_traded_stock": most_traded,
                "largest_trade": {
                    "ticker":      largest_trade["ticker"] if largest_trade else None,
                    "value":       round(largest_trade["total_value"], 2) if largest_trade else None,
                    "action":      largest_trade["action"] if largest_trade else None,
                } if largest_trade else None,
            },
            "balance": {
                "starting":    STARTING_BALANCE,
                "current_cash": round(current_balance, 2),
            },
            "insights": self._generate_insights(trades, current_balance),
        }

        return report

    def get_ticker_history(self, ticker: str) -> dict:
        """Full trade history + P&L analysis for a single stock."""
        with get_db() as conn:
            trades = conn.execute(
                "SELECT * FROM trades WHERE user_id=? AND ticker=? ORDER BY executed_at",
                (self.user_id, ticker.upper())
            ).fetchall()

        if not trades:
            return {"message": f"No trade history for {ticker}"}

        total_bought   = sum(t["total_value"] for t in trades if t["action"] == "BUY")
        total_sold     = sum(t["total_value"] for t in trades if t["action"] == "SELL")
        shares_bought  = sum(t["quantity"]    for t in trades if t["action"] == "BUY")
        shares_sold    = sum(t["quantity"]    for t in trades if t["action"] == "SELL")
        shares_held    = shares_bought - shares_sold
        realized_pnl   = total_sold - total_bought if total_sold > 0 else None

        return {
            "ticker":       ticker,
            "trades":       [dict(t) for t in trades],
            "totals": {
                "shares_bought":  shares_bought,
                "shares_sold":    shares_sold,
                "shares_held":    round(shares_held, 4),
                "total_spent":    round(total_bought, 2),
                "total_received": round(total_sold, 2),
                "realized_pnl":   round(realized_pnl, 2) if realized_pnl is not None else None,
            },
            "education": (
                f"You've made {len(trades)} trades on {ticker}. "
                "Reviewing your entry and exit points helps you learn whether your timing decisions were correct."
            ),
        }

    def _generate_insights(self, trades: list, current_balance: float) -> list:
        """Generate personalized educational insights based on behavior."""
        insights = []
        tickers = set(t["ticker"] for t in trades)

        # Diversification insight
        if len(tickers) == 1:
            insights.append({
                "type":    "warning",
                "title":   "Concentration Risk",
                "message": f"All your trades are in one stock ({list(tickers)[0]}). "
                           "Consider diversifying across multiple companies or sectors to reduce risk.",
            })
        elif len(tickers) >= 5:
            insights.append({
                "type":    "positive",
                "title":   "Good Diversification",
                "message": f"You've traded {len(tickers)} different stocks — great for spreading risk!",
            })

        # Trading frequency
        if len(trades) > 30:
            insights.append({
                "type":    "info",
                "title":   "Active Trader",
                "message": "You trade frequently. Research shows that most frequent traders underperform patient, long-term investors. "
                           "Consider a buy-and-hold strategy for comparison.",
            })

        # Balance insight
        if current_balance > STARTING_BALANCE:
            gain = round(current_balance - STARTING_BALANCE, 2)
            insights.append({
                "type":    "positive",
                "title":   "Profitable Balance",
                "message": f"Your cash balance is {APP_CURRENCY_SYMBOL}{gain:,.2f} above your starting balance — keep it up!",
            })
        else:
            loss = round(STARTING_BALANCE - current_balance, 2)
            insights.append({
                "type":    "info",
                "title":   "Learning from Losses",
                "message": f"Your cash balance is {APP_CURRENCY_SYMBOL}{loss:,.2f} below start. "
                           "Losses are a normal part of investing — the key is to analyze why and adjust your strategy.",
            })

        return insights
