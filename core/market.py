import sys, os
sys.path.insert(0, r'C:\Users\PRANAV\Desktop\stocksim')

from datetime import datetime
from typing import Optional
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

from data.db import get_db
from config import MARKET_REFRESH_INTERVAL_SECS, DEFAULT_HISTORICAL_PERIOD


class MarketClosedError(Exception):
    pass

class TickerNotFoundError(Exception):
    pass


class MarketData:

    CACHE_TTL_SECONDS = MARKET_REFRESH_INTERVAL_SECS

    def get_price(self, ticker: str) -> float:
        cached = self._get_cached_price(ticker)
        if cached is not None:
            return cached
        price = self._fetch_live_price(ticker)
        self._cache_price(ticker, price)
        return price

    def get_prices_bulk(self, tickers: list) -> dict:
        result = {}
        to_fetch = []
        for ticker in tickers:
            cached = self._get_cached_price(ticker)
            if cached is not None:
                result[ticker] = cached
            else:
                to_fetch.append(ticker)
        for ticker in to_fetch:
            try:
                result[ticker] = self._fetch_live_price(ticker)
            except Exception:
                result[ticker] = 0.0
        return result

    def _fetch_live_price(self, ticker: str) -> float:
        if yf is None:
            return self._mock_price(ticker)
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d", interval="1m")
            if hist.empty:
                info = stock.fast_info
                price = getattr(info, "last_price", None)
                if price:
                    return float(price)
                raise TickerNotFoundError(f"No price data for: {ticker}")
            return float(hist["Close"].dropna().iloc[-1])
        except TickerNotFoundError:
            raise
        except Exception as e:
            raise MarketClosedError(f"Could not fetch price for {ticker}: {e}")

    def _mock_price(self, ticker: str) -> float:
        import random
        mock_prices = {
            "AAPL": 189.50, "MSFT": 415.20, "GOOGL": 178.30,
            "AMZN": 198.75, "TSLA": 245.60, "NVDA": 875.00,
            "META": 525.40, "JPM": 210.80, "V": 285.00, "MA": 490.30,
        }
        base = mock_prices.get(ticker, 100.0)
        return round(base * (1 + random.uniform(-0.02, 0.02)), 2)

    def get_info(self, ticker: str) -> dict:
        if yf is None:
            return {"ticker": ticker, "name": f"{ticker} Corp", "sector": "Technology",
                    "description": "Install yfinance for real data."}
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "ticker":        ticker.upper(),
                "name":          info.get("longName", ticker),
                "sector":        info.get("sector", "Unknown"),
                "industry":      info.get("industry", "Unknown"),
                "pe_ratio":      info.get("trailingPE"),
                "market_cap":    info.get("marketCap"),
                "dividend_yield": info.get("dividendYield"),
                "beta":          info.get("beta"),
                "52w_high":      info.get("fiftyTwoWeekHigh"),
                "52w_low":       info.get("fiftyTwoWeekLow"),
                "description":   info.get("longBusinessSummary", "No description available."),
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker}

    def get_historical(self, ticker: str, period: str = DEFAULT_HISTORICAL_PERIOD) -> pd.DataFrame:
        if yf is None:
            return self._mock_historical()
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period)
            if df.empty:
                raise TickerNotFoundError(f"No history for {ticker}")
            return df
        except Exception as e:
            raise MarketClosedError(str(e))

    def get_historical_dict(self, ticker: str, period: str = "1y") -> list:
        df = self.get_historical(ticker, period)
        df = df.reset_index()
        records = []
        for _, row in df.iterrows():
            records.append({
                "date":   str(row["Date"].date()),
                "open":   round(float(row["Open"]), 2),
                "high":   round(float(row["High"]), 2),
                "low":    round(float(row["Low"]), 2),
                "close":  round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        return records

    def _mock_historical(self) -> pd.DataFrame:
        import numpy as np
        dates = pd.date_range(end=datetime.today(), periods=252, freq="B")
        prices = 100 + np.cumsum(np.random.randn(252) * 2)
        return pd.DataFrame({
            "Open": prices * 0.99, "High": prices * 1.01,
            "Low": prices * 0.98, "Close": prices,
            "Volume": np.random.randint(1_000_000, 10_000_000, 252),
        }, index=dates)

    def search_ticker(self, query: str) -> list:
        if not query:
            return []
        if yf is None:
            return [{"ticker": query, "name": f"{query} Corp (mock)"}]
        try:
            stock = yf.Ticker(query)
            info = stock.info
            if info.get("longName"):
                return [{"ticker": query, "name": info.get("longName"), "sector": info.get("sector", "")}]
            return []
        except Exception:
            return []

    def _get_cached_price(self, ticker: str) -> Optional[float]:
        try:
            with get_db() as conn:
                row = conn.execute("SELECT price, cached_at FROM price_cache WHERE ticker=?", (ticker,)).fetchone()
                if not row:
                    return None
                cached_at = datetime.fromisoformat(row["cached_at"])
                age = (datetime.utcnow() - cached_at).total_seconds()
                if age > self.CACHE_TTL_SECONDS:
                    return None
                return row["price"]
        except Exception:
            return None

    def _cache_price(self, ticker: str, price: float):
        try:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO price_cache (ticker, price, cached_at) VALUES (?, ?, datetime('now'))
                    ON CONFLICT(ticker) DO UPDATE SET price=excluded.price, cached_at=excluded.cached_at
                """, (ticker, price))
        except Exception:
            pass
