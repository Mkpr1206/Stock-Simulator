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
            # US
            "AAPL": 189.50, "MSFT": 415.20, "GOOGL": 178.30, "AMZN": 198.75,
            "TSLA": 245.60, "NVDA": 875.00, "META": 525.40, "JPM": 210.80,
            "V": 285.00, "MA": 490.30, "BRK-B": 380.00, "JNJ": 152.30,
            "WMT": 68.50, "KO": 61.20, "MCD": 295.00, "NKE": 92.40,
            "PG": 165.00, "SBUX": 78.30, "XOM": 112.50, "CVX": 158.00,
            "SPY": 520.00, "QQQ": 445.00, "DIA": 390.00, "VTI": 258.00,
            "AMD": 165.00, "NFLX": 625.00, "ADBE": 480.00, "BAC": 38.50,
            "GS": 495.00, "ABBV": 172.00, "PFE": 28.50, "UNH": 540.00,
            # India (NSE) — prices in INR
            "TCS.NS": 3950.0, "INFY.NS": 1780.0, "RELIANCE.NS": 2850.0,
            "HDFCBANK.NS": 1650.0, "WIPRO.NS": 520.0, "ICICIBANK.NS": 1240.0,
            "ITC.NS": 445.0, "SBIN.NS": 780.0, "HINDUNILVR.NS": 2400.0,
            "BAJFINANCE.NS": 7200.0, "KOTAKBANK.NS": 1850.0, "AXISBANK.NS": 1120.0,
            "HCLTECH.NS": 1680.0, "TECHM.NS": 1520.0, "NESTLEIND.NS": 2250.0,
            "BRITANNIA.NS": 5100.0, "ONGC.NS": 265.0, "NTPC.NS": 355.0,
            "POWERGRID.NS": 295.0, "BPCL.NS": 310.0, "NIFTYBEES.NS": 245.0,
            "BANKBEES.NS": 490.0, "ADANIENT.NS": 2450.0, "TATAMOTORS.NS": 940.0,
            "TATASTEEL.NS": 145.0,
            # UK (LSE) — prices in GBp (pence)
            "GSK.L": 1720.0, "AZN.L": 11200.0, "HSBA.L": 720.0,
            "BP.L": 485.0, "SHEL.L": 2680.0, "ULVR.L": 3850.0,
            "DGE.L": 2450.0, "MKS.L": 395.0, "VOD.L": 68.0,
            "BT-A.L": 145.0, "LLOY.L": 58.0, "BARC.L": 255.0,
            "NWG.L": 395.0, "RIO.L": 5200.0,
            # Japan (TSE) — prices in JPY
            "7203.T": 3200.0, "9984.T": 8900.0, "6758.T": 12500.0,
            "8306.T": 1580.0, "9432.T": 4200.0, "7974.T": 7800.0,
            "6861.T": 65000.0, "4519.T": 4800.0, "8058.T": 3100.0,
            "9433.T": 4050.0, "9983.T": 41000.0,
            # Europe — prices in EUR
            "ASML.AS": 720.0, "SAP.DE": 195.0, "TTE.PA": 62.0,
            "MC.PA": 680.0, "AIR.PA": 165.0, "SIE.DE": 185.0,
            "NESN.SW": 95.0, "ROG.SW": 265.0, "NOVN.SW": 92.0,
            "LVMH.PA": 680.0, "BNP.PA": 65.0, "AXA.PA": 35.0,
            "DB": 16.50, "SAP": 195.0, "ASML": 720.0,
            "VWAGY": 7.80, "BMWYY": 35.0, "TTFCF": 62.0,
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
        except Exception:
            return self._mock_info(ticker)

    def _mock_info(self, ticker: str) -> dict:
        mock = {
            "TCS.NS":       {"name": "Tata Consultancy Services", "sector": "Technology",  "pe_ratio": 28.5, "market_cap": 11500000000000, "beta": 0.6,  "dividend_yield": 0.012},
            "INFY.NS":      {"name": "Infosys Limited",           "sector": "Technology",  "pe_ratio": 24.2, "market_cap": 7400000000000,  "beta": 0.7,  "dividend_yield": 0.021},
            "RELIANCE.NS":  {"name": "Reliance Industries",       "sector": "Energy",      "pe_ratio": 22.1, "market_cap": 19000000000000, "beta": 0.9,  "dividend_yield": 0.004},
            "HDFCBANK.NS":  {"name": "HDFC Bank",                 "sector": "Finance",     "pe_ratio": 18.4, "market_cap": 12500000000000, "beta": 0.8,  "dividend_yield": 0.011},
            "WIPRO.NS":     {"name": "Wipro Limited",             "sector": "Technology",  "pe_ratio": 21.3, "market_cap": 2800000000000,  "beta": 0.75, "dividend_yield": 0.005},
            "TATASTEEL.NS": {"name": "Tata Steel",                "sector": "Materials",   "pe_ratio": 8.2,  "market_cap": 1900000000000,  "beta": 1.4,  "dividend_yield": 0.008},
            "SBIN.NS":      {"name": "State Bank of India",       "sector": "Finance",     "pe_ratio": 10.1, "market_cap": 7100000000000,  "beta": 1.1,  "dividend_yield": 0.018},
            "AAPL":         {"name": "Apple Inc.",                "sector": "Technology",  "pe_ratio": 29.8, "market_cap": 2900000000000,  "beta": 1.2,  "dividend_yield": 0.005},
            "MSFT":         {"name": "Microsoft Corporation",     "sector": "Technology",  "pe_ratio": 35.2, "market_cap": 3100000000000,  "beta": 0.9,  "dividend_yield": 0.007},
            "GOOGL":        {"name": "Alphabet Inc.",             "sector": "Technology",  "pe_ratio": 24.1, "market_cap": 2100000000000,  "beta": 1.1,  "dividend_yield": 0.0},
            "TSLA":         {"name": "Tesla Inc.",                "sector": "Automotive",  "pe_ratio": 55.0, "market_cap": 780000000000,   "beta": 2.0,  "dividend_yield": 0.0},
            "NVDA":         {"name": "NVIDIA Corporation",        "sector": "Technology",  "pe_ratio": 65.0, "market_cap": 2200000000000,  "beta": 1.7,  "dividend_yield": 0.001},
            "AMZN":         {"name": "Amazon.com Inc.",           "sector": "Consumer",    "pe_ratio": 42.0, "market_cap": 1900000000000,  "beta": 1.3,  "dividend_yield": 0.0},
            "META":         {"name": "Meta Platforms",            "sector": "Technology",  "pe_ratio": 22.0, "market_cap": 1300000000000,  "beta": 1.2,  "dividend_yield": 0.004},
            "GSK.L":        {"name": "GSK plc",                   "sector": "Healthcare",  "pe_ratio": 14.2, "market_cap": 72000000000,    "beta": 0.5,  "dividend_yield": 0.038},
            "AZN.L":        {"name": "AstraZeneca",               "sector": "Healthcare",  "pe_ratio": 22.5, "market_cap": 215000000000,   "beta": 0.4,  "dividend_yield": 0.021},
            "HSBA.L":       {"name": "HSBC Holdings",             "sector": "Finance",     "pe_ratio": 8.1,  "market_cap": 145000000000,   "beta": 0.7,  "dividend_yield": 0.052},
            "BP.L":         {"name": "BP plc",                    "sector": "Energy",      "pe_ratio": 9.5,  "market_cap": 92000000000,    "beta": 0.8,  "dividend_yield": 0.045},
            "7203.T":       {"name": "Toyota Motor",              "sector": "Automotive",  "pe_ratio": 9.8,  "market_cap": 38000000000000, "beta": 0.7,  "dividend_yield": 0.028},
            "9984.T":       {"name": "SoftBank Group",            "sector": "Technology",  "pe_ratio": 15.0, "market_cap": 10000000000000, "beta": 1.3,  "dividend_yield": 0.005},
            "ASML.AS":      {"name": "ASML Holding",              "sector": "Technology",  "pe_ratio": 38.0, "market_cap": 290000000000,   "beta": 1.1,  "dividend_yield": 0.008},
            "SAP.DE":       {"name": "SAP SE",                    "sector": "Technology",  "pe_ratio": 32.0, "market_cap": 230000000000,   "beta": 0.9,  "dividend_yield": 0.012},
        }
        d = mock.get(ticker.upper(), {})
        return {
            "ticker":         ticker.upper(),
            "name":           d.get("name", ticker.upper()),
            "sector":         d.get("sector", "Unknown"),
            "industry":       d.get("sector", "Unknown"),
            "pe_ratio":       d.get("pe_ratio"),
            "market_cap":     d.get("market_cap"),
            "dividend_yield": d.get("dividend_yield"),
            "beta":           d.get("beta"),
            "52w_high":       None,
            "52w_low":        None,
            "description":    d.get("name", ticker.upper()) + " — live company details unavailable.",
        }

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




