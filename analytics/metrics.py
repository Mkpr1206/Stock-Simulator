"""
analytics/metrics.py
Calculates and explains key financial metrics.
Every metric comes with a plain-English explanation — this is an educational app!
"""

from typing import Optional
from core.market import MarketData


class MetricsEngine:
    """
    Computes fundamental and technical financial metrics
    with beginner-friendly explanations attached to each one.
    """

    def __init__(self):
        self.market = MarketData()

    def get_full_analysis(self, ticker: str) -> dict:
        """Returns a complete fundamental + technical analysis for a stock."""
        info = self.market.get_info(ticker)
        price = self.market.get_price(ticker)
        historical = self.market.get_historical_dict(ticker, "1y")

        fundamental = self._fundamental_analysis(info, price)
        technical    = self._technical_analysis(historical, price)
        risk         = self._risk_assessment(info, historical)

        return {
            "ticker":      ticker,
            "name":        info.get("name", ticker),
            "price":       price,
            "fundamental": fundamental,
            "technical":   technical,
            "risk":        risk,
            "disclaimer":  "This is educational analysis only. Not financial advice.",
        }

    def _fundamental_analysis(self, info: dict, price: float) -> dict:
        pe_ratio = info.get("pe_ratio")
        eps      = info.get("eps")
        div_yield = info.get("dividend_yield")
        market_cap = info.get("market_cap")
        profit_margin = info.get("profit_margin")

        def pe_rating(pe):
            if pe is None:       return "N/A"
            elif pe < 0:         return "Negative (company losing money)"
            elif pe < 15:        return "Low — possibly undervalued or struggling"
            elif pe < 25:        return "Fair — typical for stable companies"
            elif pe < 40:        return "High — market expects strong growth"
            else:                return "Very High — significant growth expectations baked in"

        def cap_label(cap):
            if cap is None:      return "Unknown"
            elif cap > 200e9:    return "Mega Cap (>$200B)"
            elif cap > 10e9:     return "Large Cap ($10B-$200B)"
            elif cap > 2e9:      return "Mid Cap ($2B-$10B)"
            elif cap > 300e6:    return "Small Cap ($300M-$2B)"
            else:                return "Micro Cap (<$300M)"

        return {
            "pe_ratio": {
                "value":       round(pe_ratio, 2) if pe_ratio else None,
                "rating":      pe_rating(pe_ratio),
                "explanation": (
                    "Price-to-Earnings (P/E) ratio = stock price ÷ earnings per share. "
                    "It tells you how much investors pay for each dollar of profit. "
                    "A lower P/E might mean undervalued; higher means high growth expectations."
                ),
            },
            "eps": {
                "value":       round(eps, 2) if eps else None,
                "explanation": (
                    "Earnings Per Share (EPS) = company's profit ÷ total shares. "
                    "Higher EPS means the company is more profitable per share. "
                    "Consistent EPS growth is generally a positive sign."
                ),
            },
            "dividend_yield": {
                "value":       f"{round(div_yield * 100, 2)}%" if div_yield else "0% (no dividend)",
                "explanation": (
                    "Dividend yield = annual dividend payment ÷ stock price. "
                    "Some companies share profits with shareholders via dividends. "
                    "Useful for income-focused investors. Growth stocks often pay no dividends."
                ),
            },
            "market_cap": {
                "value":       f"${market_cap:,.0f}" if market_cap else "N/A",
                "label":       cap_label(market_cap),
                "explanation": (
                    "Market capitalization = share price × total shares outstanding. "
                    "It's the total value the market assigns to the company. "
                    "Large caps are generally more stable; small caps have higher growth potential but more risk."
                ),
            },
            "profit_margin": {
                "value":       f"{round(profit_margin * 100, 1)}%" if profit_margin else "N/A",
                "explanation": (
                    "Profit margin = net profit ÷ revenue. "
                    "Shows how much of every dollar in revenue becomes profit. "
                    "Higher margin = more efficient business."
                ),
            },
        }

    def _technical_analysis(self, historical: dict, current_price: float) -> dict:
        if not historical:
            return {"error": "No historical data"}

        close_dict = historical.get("Close", {})
        dates  = sorted(close_dict.keys())
        closes = [close_dict[d] for d in dates]
        # No open/high/low in our dict format — use close as proxy
        highs  = closes
        lows   = closes

        ma_50  = sum(closes[-50:])  / min(50,  len(closes))
        ma_200 = sum(closes[-200:]) / min(200, len(closes))

        high_52w = max(highs)
        low_52w  = min(lows)
        pct_from_high = round(((current_price - high_52w) / high_52w) * 100, 2)
        pct_from_low  = round(((current_price - low_52w)  / low_52w)  * 100, 2)

        # RSI (simplified 14-day)
        rsi = self._calculate_rsi(closes)

        # Trend signal
        if current_price > ma_50 > ma_200:
            trend = "🟢 Strong Uptrend"
        elif current_price > ma_200:
            trend = "🟡 Moderate Uptrend"
        elif current_price < ma_50 < ma_200:
            trend = "🔴 Strong Downtrend"
        else:
            trend = "⚪ Consolidating / Mixed"

        return {
            "current_price": current_price,
            "trend":         trend,
            "ma_50":  {
                "value":       round(ma_50, 2),
                "position":    "above" if current_price > ma_50 else "below",
                "explanation": "50-day moving average — tracks medium-term momentum.",
            },
            "ma_200": {
                "value":       round(ma_200, 2),
                "position":    "above" if current_price > ma_200 else "below",
                "explanation": "200-day moving average — the gold standard long-term trend indicator.",
            },
            "52_week": {
                "high":         high_52w,
                "low":          low_52w,
                "pct_from_high": pct_from_high,
                "pct_from_low":  pct_from_low,
                "explanation":  "52-week high/low shows the price range over the past year.",
            },
            "rsi": {
                "value":       rsi,
                "signal":      "Overbought (consider waiting)" if rsi > 70 else "Oversold (potential opportunity)" if rsi < 30 else "Neutral",
                "explanation": "RSI (Relative Strength Index) ranges 0-100. Above 70 = possibly overbought. Below 30 = possibly oversold.",
            },
        }

    def _risk_assessment(self, info: dict, historical: list) -> dict:
        beta = info.get("beta")
        close_dict = historical.get("Close", {}) if historical else {}
        closes = [close_dict[d] for d in sorted(close_dict.keys())]

        # Volatility: standard deviation of daily returns
        volatility = None
        if len(closes) > 20:
            import statistics
            daily_returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            volatility = round(statistics.stdev(daily_returns) * 100, 2)

        def beta_risk(b):
            if b is None:   return "Unknown"
            elif b < 0:     return "Inverse — moves opposite to market (e.g., gold miners)"
            elif b < 0.5:   return "Very Low — barely moves with the market"
            elif b < 1:     return "Low — less volatile than the market"
            elif b == 1:    return "Neutral — moves in line with the market"
            elif b < 1.5:   return "Moderate — slightly more volatile than the market"
            else:           return "High — significantly more volatile; higher risk and reward"

        return {
            "beta": {
                "value":       beta,
                "assessment":  beta_risk(beta),
                "explanation": (
                    "Beta measures how much a stock moves relative to the overall market. "
                    "Beta of 1 = moves with the market. Beta of 2 = twice as volatile as the market."
                ),
            },
            "volatility": {
                "value":       f"{volatility}% daily avg" if volatility else "N/A",
                "explanation": "Daily volatility measures how much the price typically swings each day.",
            },
            "risk_level": self._overall_risk(beta, volatility),
        }

    def _overall_risk(self, beta, volatility) -> str:
        score = 0
        if beta:
            score += min(4, max(0, int(beta * 2)))
        if volatility:
            score += min(4, int(volatility / 1.5))

        if score <= 2:  return "🟢 Low Risk"
        elif score <= 5: return "🟡 Medium Risk"
        elif score <= 8: return "🟠 High Risk"
        else:           return "🔴 Very High Risk"

    def _calculate_rsi(self, closes: list, period: int = 14) -> Optional[float]:
        if len(closes) < period + 1:
            return None
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        recent = deltas[-period:]
        gains  = [d for d in recent if d > 0]
        losses = [abs(d) for d in recent if d < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0.0001
        rs  = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 1)
