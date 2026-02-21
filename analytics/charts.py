"""
analytics/charts.py
Generates chart data for frontend visualization.
Returns structured data (not images) so the frontend can render them.
Optional: can generate matplotlib charts and save as PNG if needed.
"""

from typing import List, Optional
from core.market import MarketData


class ChartData:
    """Prepares chart-ready data for stock prices and portfolio performance."""

    def __init__(self):
        self.market = MarketData()

    def get_price_chart(self, ticker: str, period: str = "1y") -> dict:
        """
        Returns candlestick + line chart data for a stock.
        Frontend can use this with Chart.js, Recharts, etc.
        """
        try:
            records = self.market.get_historical_dict(ticker, period)
        except Exception as e:
            return {"error": str(e)}

        # Compute moving averages
        closes = [r["close"] for r in records]
        ma_50  = self._moving_average(closes, 50)
        ma_200 = self._moving_average(closes, 200)

        for i, record in enumerate(records):
            record["ma_50"]  = ma_50[i]
            record["ma_200"] = ma_200[i]

        # Calculate support/resistance levels
        all_highs = [r["high"] for r in records]
        all_lows  = [r["low"]  for r in records]

        return {
            "ticker":     ticker,
            "period":     period,
            "candles":    records,
            "summary": {
                "current_price":  records[-1]["close"] if records else None,
                "period_high":    max(all_highs) if all_highs else None,
                "period_low":     min(all_lows)  if all_lows  else None,
                "period_change":  round(records[-1]["close"] - records[0]["open"], 2) if len(records) > 1 else 0,
                "period_change_pct": round(
                    ((records[-1]["close"] - records[0]["open"]) / records[0]["open"]) * 100, 2
                ) if len(records) > 1 and records[0]["open"] else 0,
            },
            "education": {
                "ma_50_explanation":  "The 50-day moving average smooths out short-term price noise. Price above MA50 is generally bullish.",
                "ma_200_explanation": "The 200-day moving average is the most-watched long-term trend indicator. Above it = bull market, below = bear.",
                "candlestick_tip":    "Each candle shows open/high/low/close. Green = price rose, Red = price fell that day.",
            }
        }

    def get_volume_chart(self, ticker: str, period: str = "3mo") -> dict:
        """Returns volume bar chart data."""
        try:
            records = self.market.get_historical_dict(ticker, period)
        except Exception as e:
            return {"error": str(e)}

        avg_volume = sum(r["volume"] for r in records) / len(records) if records else 0

        return {
            "ticker": ticker,
            "data":   [{"date": r["date"], "volume": r["volume"], "above_avg": r["volume"] > avg_volume} for r in records],
            "avg_volume": int(avg_volume),
            "education": "High volume on a price move confirms strength. Low volume moves may not last.",
        }

    def get_portfolio_performance_chart(self, user_id: int) -> dict:
        """
        Approximates portfolio value over time using trade history.
        Shows how the user's decisions played out.
        """
        from data.db import get_db
        from config import STARTING_BALANCE

        with get_db() as conn:
            trades = conn.execute(
                "SELECT * FROM trades WHERE user_id=? ORDER BY executed_at",
                (user_id,)
            ).fetchall()

        if not trades:
            return {"message": "No trades yet. Buy your first stock to see performance!"}

        # Build a timeline of portfolio value changes
        timeline = [{"date": trades[0]["executed_at"][:10], "value": STARTING_BALANCE}]
        running_cash = STARTING_BALANCE

        for trade in trades:
            if trade["action"] == "BUY":
                running_cash -= trade["total_value"]
            else:
                running_cash += trade["total_value"]

            timeline.append({
                "date":   trade["executed_at"][:10],
                "value":  round(running_cash, 2),
                "action": trade["action"],
                "ticker": trade["ticker"],
            })

        return {
            "timeline":        timeline,
            "starting_value":  STARTING_BALANCE,
            "education":       "This chart tracks your portfolio value over time based on your trades.",
        }

    def get_allocation_pie(self, user_id: int) -> dict:
        """Returns portfolio allocation data for a pie chart."""
        from core.portfolio import Portfolio
        portfolio = Portfolio(user_id)
        summary = portfolio.get_summary()

        slices = [{"label": "Cash", "value": summary["cash"], "pct": 0}]
        for h in summary["holdings"]:
            slices.append({
                "label": h["ticker"],
                "value": h["current_value"],
                "pct":   0
            })

        total = summary["total_value"]
        for s in slices:
            s["pct"] = round((s["value"] / total) * 100, 1) if total else 0

        return {
            "total_value": total,
            "slices": slices,
            "education": "A well-diversified portfolio typically spreads risk across many sectors. No single position should dominate.",
        }

    def _moving_average(self, values: List[float], window: int) -> List[Optional[float]]:
        result = []
        for i in range(len(values)):
            if i < window - 1:
                result.append(None)
            else:
                avg = sum(values[i - window + 1: i + 1]) / window
                result.append(round(avg, 2))
        return result
