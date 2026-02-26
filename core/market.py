"""
market.py — FIXED
Bug fixes:
  1. Removed sys.path Windows hardcode (crashed on Render/Linux)
  2. _fetch_live_price now uses multi-strategy fallback:
       fast_info → 5d daily history → info dict currentPrice
     The original history(period="1d", interval="1m") returns empty
     outside market hours and for Indian .NS/.BO tickers on Render.
  3. get_price_with_change() added (needed by /market/featured)
  4. get_historical_dict() handles timezone-aware DatetimeIndex safely
"""

from datetime import datetime
from typing import Optional
import pandas as pd

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False

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

    def get_price_with_change(self, ticker: str) -> dict:
        """Returns {price, change_pct, change_abs} — used by /market/featured."""
        if not YF_AVAILABLE:
            price = self._mock_price(ticker)
            return {"price": price, "change_pct": 0.0, "change_abs": 0.0}
        try:
            stock = yf.Ticker(ticker)
            fi    = stock.fast_info
            price = float(getattr(fi, "last_price", None) or 0)
            prev  = float(getattr(fi, "previous_close", None) or price)

            if price <= 0:
                hist = stock.history(period="5d", interval="1d")
                if not hist.empty:
                    closes = hist["Close"].dropna()
                    if len(closes) >= 2:
                        price = float(closes.iloc[-1])
                        prev  = float(closes.iloc[-2])
                    elif len(closes) == 1:
                        price = float(closes.iloc[-1])
                        prev  = price

            change_abs = price - prev
            change_pct = (change_abs / prev * 100) if prev else 0.0
            self._cache_price(ticker, price)
            return {
                "price":      round(price, 2),
                "change_pct": round(change_pct, 2),
                "change_abs": round(change_abs, 2),
            }
        except Exception:
            price = self.get_price(ticker)
            return {"price": price, "change_pct": 0.0, "change_abs": 0.0}

    def get_prices_bulk(self, tickers: list) -> dict:
        result   = {}
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
        """
        Multi-strategy fetch — works for US, Indian (.NS/.BO), UK (.L), JP (.T)
        and outside market hours (when 1m intraday returns empty).

        Strategy 1: fast_info.last_price  — fastest
        Strategy 2: history(5d, 1d)       — reliable, works after hours & globally
        Strategy 3: info dict prices      — slowest, most comprehensive
        """
        if not YF_AVAILABLE:
            return self._mock_price(ticker)

        stock = yf.Ticker(ticker)

        # Strategy 1 — fast_info
        try:
            fi    = stock.fast_info
            price = getattr(fi, "last_price", None)
            if price and float(price) > 0:
                return round(float(price), 2)
        except Exception:
            pass

        # Strategy 2 — recent daily history (best for Indian & global tickers)
        try:
            hist = stock.history(period="5d", interval="1d")
            if not hist.empty:
                closes = hist["Close"].dropna()
                if len(closes) > 0:
                    return round(float(closes.iloc[-1]), 2)
        except Exception:
            pass

        # Strategy 3 — info dict
        try:
            info = stock.info
            for key in ("currentPrice", "regularMarketPrice", "previousClose", "ask", "bid"):
                val = info.get(key)
                if val and float(val) > 0:
                    return round(float(val), 2)
        except Exception:
            pass

        raise TickerNotFoundError(
            f"Could not load \"{ticker}\" — check spelling or server"
        )

    def _mock_price(self, ticker: str) -> float:
        import random
        mock = {
            "AAPL": 189.50, "MSFT": 415.20, "GOOGL": 178.30, "AMZN": 198.75,
            "TSLA": 245.60, "NVDA": 875.00, "META": 525.40, "JPM": 210.80,
            "V": 285.00, "MA": 490.30, "BRK-B": 380.00, "JNJ": 152.30,
            "TCS.NS": 3950.0, "INFY.NS": 1780.0, "RELIANCE.NS": 2850.0,
            "HDFCBANK.NS": 1650.0, "WIPRO.NS": 520.0, "ICICIBANK.NS": 1240.0,
            "ITC.NS": 445.0, "SBIN.NS": 780.0, "HINDUNILVR.NS": 2400.0,
            "BAJFINANCE.NS": 7200.0, "GSK.L": 1720.0, "7203.T": 3200.0,
        }
        base = mock.get(ticker, 100.0)
        return round(base * (1 + random.uniform(-0.02, 0.02)), 2)

    def get_info(self, ticker: str) -> dict:
        if not YF_AVAILABLE:
            return {"ticker": ticker, "name": f"{ticker} Corp",
                    "sector": "Technology", "description": "Install yfinance for real data."}
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            if not info or not info.get("symbol"):
                fi = stock.fast_info
                return {
                    "ticker":      ticker.upper(),
                    "name":        ticker.upper(),
                    "sector":      "Unknown",
                    "industry":    "Unknown",
                    "description": "Company details not available.",
                    "market_cap":  getattr(fi, "market_cap", None),
                    "52w_high":    getattr(fi, "year_high", None),
                    "52w_low":     getattr(fi, "year_low", None),
                }
            return {
                "ticker":         ticker.upper(),
                "name":           info.get("longName") or info.get("shortName", ticker),
                "sector":         info.get("sector", "Unknown"),
                "industry":       info.get("industry", "Unknown"),
                "pe_ratio":       info.get("trailingPE"),
                "market_cap":     info.get("marketCap"),
                "dividend_yield": info.get("dividendYield"),
                "beta":           info.get("beta"),
                "52w_high":       info.get("fiftyTwoWeekHigh"),
                "52w_low":        info.get("fiftyTwoWeekLow"),
                "description":    info.get("longBusinessSummary", "No description available."),
                "website":        info.get("website"),
                "employees":      info.get("fullTimeEmployees"),
            }
        except Exception as e:
            return {"error": str(e), "ticker": ticker, "name": ticker,
                    "description": "Could not load company info."}

    def get_historical(self, ticker: str, period: str = DEFAULT_HISTORICAL_PERIOD) -> pd.DataFrame:
        if not YF_AVAILABLE:
            return self._mock_historical()
        try:
            stock = yf.Ticker(ticker)
            df    = stock.history(period=period)
            if df.empty:
                df = stock.history(period=period, interval="1d")
            if df.empty:
                raise TickerNotFoundError(f"No historical data for {ticker}")
            return df
        except TickerNotFoundError:
            raise
        except Exception as e:
            raise MarketClosedError(str(e))

    def get_historical_dict(self, ticker: str, period: str = "1y") -> dict:
        """Returns {Close: {date: price}, Volume: {date: vol}} — matches frontend expectation."""
        df = self.get_historical(ticker, period)
        df = df.reset_index()
        close_dict  = {}
        volume_dict = {}
        for _, row in df.iterrows():
            try:
                d = row["Date"]
                date_str = str(d.date()) if hasattr(d, "date") else str(d)[:10]
                close_dict[date_str]  = round(float(row["Close"]), 2)
                volume_dict[date_str] = int(row.get("Volume", 0))
            except Exception:
                continue
        return {"Close": close_dict, "Volume": volume_dict}

    def _mock_historical(self) -> pd.DataFrame:
        dates  = pd.date_range(end=datetime.today(), periods=252, freq="B")
        prices = 100 + (pd.Series(range(252)) * 0.5)
        return pd.DataFrame({
            "Open":   prices * 0.99, "High": prices * 1.01,
            "Low":    prices * 0.98, "Close": prices,
            "Volume": [1_000_000] * 252,
        }, index=dates)

    def search_ticker(self, query: str) -> list:
        if not query:
            return []
        if not YF_AVAILABLE:
            return [{"ticker": query.upper(), "name": f"{query.upper()} Corp"}]
        try:
            stock = yf.Ticker(query.upper())
            info  = stock.info
            if info and info.get("longName"):
                return [{"ticker": query.upper(), "name": info["longName"],
                         "sector": info.get("sector", "")}]
            fi = stock.fast_info
            if getattr(fi, "last_price", None):
                return [{"ticker": query.upper(), "name": query.upper()}]
            return []
        except Exception:
            return []

    def _get_cached_price(self, ticker: str) -> Optional[float]:
        try:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT price, cached_at FROM price_cache WHERE ticker=?", (ticker,)
                ).fetchone()
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
                    INSERT INTO price_cache (ticker, price, cached_at)
                    VALUES (?, ?, datetime('now'))
                    ON CONFLICT(ticker) DO UPDATE
                    SET price=excluded.price, cached_at=excluded.cached_at
                """, (ticker, price))
        except Exception:
            pass
