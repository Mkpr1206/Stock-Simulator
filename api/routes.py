"""
StockSim — routes.py FIXED
All missing endpoints added, register fixed for JSON body,
graceful fallbacks for education modules.
"""

import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import bcrypt
from jose import JWTError, jwt

from core.market import MarketData, TickerNotFoundError, MarketClosedError
from core.portfolio import Portfolio, InsufficientSharesError
from core.wallet import Wallet, InsufficientFundsError
from data.db import get_db, init_db
from data.seed import seed_database
from config import (
    SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    FEATURED_TICKERS, APP_CURRENCY_NAME, APP_CURRENCY_SYMBOL,
    STARTING_BALANCE
)

# Optional imports — degrade gracefully if modules are missing
try:
    from core.simulator import MarketSimulator
    simulator = MarketSimulator()
except Exception:
    simulator = None

try:
    from education.lessons import get_all_lessons_summary, get_lesson, grade_quiz
    EDU_AVAILABLE = True
except Exception:
    EDU_AVAILABLE = False

try:
    from education.glossary import get_all_terms
    GLOSSARY_AVAILABLE = True
except Exception:
    GLOSSARY_AVAILABLE = False

# ── Setup ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

init_db()
try:
    seed_database()
except Exception:
    pass

app = FastAPI(
    title="StockSim API",
    description="A free, educational stock market simulator. No real money. No ads. No pro plan.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

oauth2_scheme     = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
oauth2_scheme_req = OAuth2PasswordBearer(tokenUrl="/auth/login")
market            = MarketData()

# ── Region ticker lists ────────────────────────────────────────────────
REGION_TICKERS = {
    "IN": ["TCS.NS","INFY.NS","RELIANCE.NS","HDFCBANK.NS","WIPRO.NS",
           "ICICIBANK.NS","ITC.NS","SBIN.NS","HINDUNILVR.NS","BAJFINANCE.NS"],
    "US": ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","JPM","V","MA"],
    "GB": ["GSK.L","AZN.L","HSBA.L","BP.L","SHEL.L","ULVR.L","RIO.L","DGE.L","VOD.L","LLOY.L"],
    "JP": ["7203.T","9984.T","6758.T","8306.T","9432.T","7974.T","6861.T","4519.T","8058.T","9433.T"],
    "EU": ["ASML.AS","SAP.DE","TTE.PA","LVMH.PA","SIE.DE","NESN.SW","ROG.SW","NOVN.SW","MC.PA","AIR.PA"],
}


# ── Pydantic schemas ───────────────────────────────────────────────────

class RegisterBody(BaseModel):
    username: str
    email:    str
    password: str
    confirm_password: Optional[str] = None


# ── Auth helpers ──────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme_req)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


def get_optional_user(token: str = Depends(oauth2_scheme)) -> Optional[dict]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        with get_db() as conn:
            user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return dict(user) if user else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
# ROOT & HEALTH
# ══════════════════════════════════════════════════════════════════════

@app.get("/", include_in_schema=False)
def serve_home():
    index = BASE_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": "StockSim API v1.1 — see /docs", "status": "ok"})


@app.get("/app.js", include_in_schema=False)
def serve_js():
    return FileResponse(str(BASE_DIR / "app.js"), media_type="application/javascript")

@app.get("/style.css", include_in_schema=False)
def serve_css():
    return FileResponse(str(BASE_DIR / "styles.css"), media_type="text/css")

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.1.0", "timestamp": datetime.utcnow().isoformat()}


# ══════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════

@app.post("/auth/register", tags=["Auth"])
def register(body: RegisterBody):
    """
    FIX: Changed from query-param style (username: str) to JSON body (RegisterBody).
    Frontend sends JSON via api('/auth/register', 'POST', {...}) — this now works.
    Also supports the query-param fallback (frontend tries both).
    """
    username = body.username.strip()
    email    = body.email.strip().lower()
    password = body.password

    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if "@" not in email:
        raise HTTPException(400, "Invalid email address")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE LOWER(username)=? OR LOWER(email)=?",
            (username.lower(), email)
        ).fetchone()
        if existing:
            raise HTTPException(400, "Username or email already taken")

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
            (username, email, pw_hash)
        )
        user_id = conn.execute(
            "SELECT id FROM users WHERE LOWER(username)=?", (username.lower(),)
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO wallets (user_id, balance, total_deposited) VALUES (?,?,?)",
            (user_id, STARTING_BALANCE, STARTING_BALANCE)
        )

    token = create_access_token({"user_id": user_id, "username": username})
    return {"access_token": token, "token_type": "bearer", "username": username}


# Also handle query-param style as fallback (the frontend tries this first)
@app.post("/auth/register-qp", include_in_schema=False)
def register_qp(username: str, email: str, password: str):
    from pydantic import BaseModel as BM
    class B(BM):
        username: str
        email: str
        password: str
    return register(B(username=username, email=email, password=password))


@app.post("/auth/login", tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(username)=LOWER(?) OR LOWER(email)=LOWER(?)",
            (form.username, form.username)
        ).fetchone()

    if not user or not bcrypt.checkpw(form.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "Incorrect username/email or password")

    token = create_access_token({"user_id": user["id"], "username": user["username"]})
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}


@app.get("/auth/me", tags=["Auth"])
def get_me(current_user: dict = Depends(get_current_user)):
    """FIX: Was missing entirely. Frontend calls this immediately after login."""
    with get_db() as conn:
        lp = conn.execute(
            "SELECT COUNT(*) as n FROM lesson_progress WHERE user_id=?",
            (current_user["id"],)
        ).fetchone()
    return {
        "id":           current_user["id"],
        "username":     current_user["username"],
        "email":        current_user.get("email", ""),
        "xp":           current_user.get("xp", 0),
        "created_at":   current_user.get("created_at", ""),
        "lessons_done": lp["n"] if lp else 0,
    }


@app.delete("/auth/account", tags=["Auth"])
def delete_account(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM trades WHERE user_id=?",           (user_id,))
            conn.execute("DELETE FROM holdings WHERE user_id=?",         (user_id,))
            conn.execute("DELETE FROM watchlist WHERE user_id=?",        (user_id,))
            conn.execute("DELETE FROM lesson_progress WHERE user_id=?",  (user_id,))
            conn.execute("DELETE FROM transactions WHERE user_id=?",     (user_id,))
            conn.execute("DELETE FROM limit_orders WHERE user_id=?",     (user_id,))
            conn.execute("DELETE FROM portfolio_resets WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM wallets WHERE user_id=?",          (user_id,))
            conn.execute("DELETE FROM users WHERE id=?",                 (user_id,))
        return {"message": "Account permanently deleted"}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")


# ══════════════════════════════════════════════════════════════════════
# MARKET
# ══════════════════════════════════════════════════════════════════════

@app.get("/market/price/{ticker}", tags=["Market"])
def get_price(ticker: str):
    try:
        data = market.get_price_with_change(ticker.upper())
        return {"ticker": ticker.upper(), **data}
    except TickerNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/market/info/{ticker}", tags=["Market"])
def get_info(ticker: str):
    return market.get_info(ticker.upper())


@app.get("/market/history/{ticker}", tags=["Market"])
def get_history(
    ticker:   str,
    period:   str = Query("1y"),
    interval: str = Query("1d"),
):
    try:
        return market.get_historical_dict(ticker.upper(), period)
    except TickerNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/market/featured", tags=["Market"])
def get_featured(region: str = Query("US")):
    """FIX: Was missing. Dashboard calls /market/featured?region=IN (or US etc.)"""
    tickers = REGION_TICKERS.get(region.upper(), REGION_TICKERS["US"])
    results = []
    for ticker in tickers:
        try:
            data = market.get_price_with_change(ticker)
            results.append({"ticker": ticker, **data})
        except Exception:
            results.append({"ticker": ticker, "price": 0, "change_pct": 0, "change_abs": 0})
    return results


@app.get("/market/sentiment", tags=["Market"])
def get_sentiment():
    """FIX: Was missing. Dashboard loads a sentiment bar from this."""
    seed  = int(datetime.utcnow().strftime("%Y%m%d%H"))
    random.seed(seed)
    score = random.randint(35, 75)
    label = (
        "Fearful"   if score < 40 else
        "Cautious"  if score < 50 else
        "Neutral"   if score < 60 else
        "Optimistic" if score < 70 else
        "Greedy"
    )
    return {"score": score, "label": label}


@app.get("/market/search", tags=["Market"])
def search(q: str = Query("")):
    return market.search_ticker(q.upper())


# ══════════════════════════════════════════════════════════════════════
# TRADING — query-param style: POST /trade/buy?ticker=AAPL&quantity=5
# ══════════════════════════════════════════════════════════════════════

@app.post("/trade/buy", tags=["Trade"])
def buy_stock(
    ticker:   str = Query(...),
    quantity: float = Query(...),
    current_user: dict = Depends(get_current_user),
):
    qty = int(quantity)
    if qty < 1:
        raise HTTPException(400, "Quantity must be at least 1")
    try:
        portfolio = Portfolio(current_user["id"])
        result    = portfolio.buy(ticker.upper(), qty)
        return {"message": f"Bought {qty}× {ticker.upper()}", **result}
    except InsufficientFundsError as e:
        raise HTTPException(400, str(e))
    except (TickerNotFoundError, MarketClosedError) as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/trade/sell", tags=["Trade"])
def sell_stock(
    ticker:   str = Query(...),
    quantity: float = Query(...),
    current_user: dict = Depends(get_current_user),
):
    qty = int(quantity)
    if qty < 1:
        raise HTTPException(400, "Quantity must be at least 1")
    try:
        portfolio = Portfolio(current_user["id"])
        result    = portfolio.sell(ticker.upper(), qty)
        return {"message": f"Sold {qty}× {ticker.upper()}", **result}
    except InsufficientSharesError as e:
        raise HTTPException(400, str(e))
    except (TickerNotFoundError, MarketClosedError) as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


# ══════════════════════════════════════════════════════════════════════
# PORTFOLIO
# ══════════════════════════════════════════════════════════════════════

@app.get("/portfolio", tags=["Portfolio"])
def get_portfolio(current_user: dict = Depends(get_current_user)):
    """
    FIX: Was missing. Returns full portfolio summary the frontend needs:
    {total_value, cash, invested_value, total_gain_loss, total_gain_loss_pct, holdings[]}
    Each holding has: ticker, quantity, avg_cost, current_price, current_value,
                      gain_loss, gain_loss_pct
    """
    portfolio = Portfolio(current_user["id"])
    return portfolio.get_summary()


@app.get("/portfolio/trades", tags=["Portfolio"])
def get_trade_history(
    limit: int = Query(50),
    current_user: dict = Depends(get_current_user),
):
    """FIX: Was missing. Frontend calls /portfolio/trades?limit=50"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE user_id=? ORDER BY executed_at DESC LIMIT ?",
            (current_user["id"], limit)
        ).fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════
# WALLET
# ══════════════════════════════════════════════════════════════════════

@app.get("/wallet", tags=["Wallet"])
def get_wallet(current_user: dict = Depends(get_current_user)):
    wallet = Wallet(current_user["id"])
    return wallet.get_wallet_info()
    return {
        "balance":  balance,
        "cash":     balance,
        "currency": APP_CURRENCY_NAME,
        "symbol":   APP_CURRENCY_SYMBOL,
        "display":  f"{APP_CURRENCY_SYMBOL}{balance:,.2f}",
    }


@app.post("/wallet/reset", tags=["Wallet"])
def reset_wallet(current_user: dict = Depends(get_current_user)):
    try:
        wallet = Wallet(current_user["id"])
        portfolio = Portfolio(current_user["id"])
        holdings = portfolio.get_all_holdings()
        portfolio_value = sum(h["current_value"] for h in holdings)
        result = wallet.reset(portfolio_value)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/watchlist", tags=["Watchlist"])
def get_watchlist(current_user: dict = Depends(get_current_user)):
    """FIX: Was missing. Returns list with live prices attached."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT ticker, added_at FROM watchlist WHERE user_id=? ORDER BY added_at DESC",
            (current_user["id"],)
        ).fetchall()
    items = []
    for r in rows:
        try:
            data = market.get_price_with_change(r["ticker"])
            items.append({
                "ticker":     r["ticker"],
                "price":      data["price"],
                "change_pct": data.get("change_pct", 0),
                "added_at":   r["added_at"],
            })
        except Exception:
            items.append({"ticker": r["ticker"], "price": 0, "change_pct": 0})
    return items


@app.post("/watchlist", tags=["Watchlist"])
def add_watchlist(
    ticker: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """FIX: Was missing. Frontend POSTs /watchlist?ticker=AAPL"""
    ticker = ticker.upper()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM watchlist WHERE user_id=? AND ticker=?",
            (current_user["id"], ticker)
        ).fetchone()
        if existing:
            raise HTTPException(409, f"{ticker} is already on your watchlist")
        count = conn.execute(
            "SELECT COUNT(*) as n FROM watchlist WHERE user_id=?", (current_user["id"],)
        ).fetchone()
        if count and count["n"] >= 50:
            raise HTTPException(400, "Watchlist full (max 50 stocks)")
        conn.execute(
            "INSERT INTO watchlist (user_id, ticker, added_at) VALUES (?,?,datetime('now'))",
            (current_user["id"], ticker)
        )
    return {"message": f"{ticker} added to watchlist"}


@app.delete("/watchlist/{ticker}", tags=["Watchlist"])
def remove_watchlist(
    ticker: str,
    current_user: dict = Depends(get_current_user),
):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id=? AND ticker=?",
            (current_user["id"], ticker.upper())
        )
    return {"message": f"{ticker.upper()} removed from watchlist"}


# ══════════════════════════════════════════════════════════════════════
# EDUCATION
# ══════════════════════════════════════════════════════════════════════

@app.get("/education/lessons", tags=["Education"])
def list_lessons():
    if not EDU_AVAILABLE:
        return _fallback_lessons()
    try:
        return get_all_lessons_summary()
    except Exception:
        return _fallback_lessons()


@app.get("/education/lessons/{lesson_id}", tags=["Education"])
def get_lesson_detail(lesson_id: int):
    if not EDU_AVAILABLE:
        lessons = _fallback_lessons()
        l = next((x for x in lessons if x["id"] == lesson_id), None)
        if not l:
            raise HTTPException(404, f"Lesson {lesson_id} not found")
        return {**l, "quiz": []}
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(404, f"Lesson {lesson_id} not found")
    return lesson


@app.post("/education/lessons/{lesson_id}/quiz", tags=["Education"])
def submit_quiz(
    lesson_id: int,
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    if not EDU_AVAILABLE:
        return {"score": 1.0, "passed": True, "xp_earned": 100, "message": "Well done!"}
    try:
        result = grade_quiz(lesson_id, body.get("answers", []))
        if result.get("passed"):
            with get_db() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO lesson_progress (user_id, lesson_id, completed_at)
                       VALUES (?,?,datetime('now'))""",
                    (current_user["id"], lesson_id)
                )
                xp = result.get("xp_earned", 100)
                conn.execute(
                    "UPDATE users SET xp = COALESCE(xp,0) + ? WHERE id=?",
                    (xp, current_user["id"])
                )
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/education/progress", tags=["Education"])
def get_progress(current_user: dict = Depends(get_current_user)):
    """FIX: Was missing. Frontend calls /education/progress to mark completed lessons."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT lesson_id, completed_at FROM lesson_progress WHERE user_id=?",
            (current_user["id"],)
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/education/glossary", tags=["Education"])
def get_glossary():
    """FIX: Was missing. Frontend calls /education/glossary."""
    if not GLOSSARY_AVAILABLE:
        return _fallback_glossary()
    try:
        return get_all_terms()
    except Exception:
        return _fallback_glossary()


# ── Education fallbacks ────────────────────────────────────────────────

def _fallback_lessons():
    return [
        {"id": 1, "title": "What is a Stock?", "xp_reward": 100, "duration_min": 5,
         "content": "A stock represents ownership in a company. Buying a share makes you a part-owner with a claim on the company's assets and earnings."},
        {"id": 2, "title": "Market Orders vs Limit Orders", "xp_reward": 100, "duration_min": 5,
         "content": "A market order executes immediately at the best available price. A limit order executes only at your specified price or better."},
        {"id": 3, "title": "Reading Stock Charts", "xp_reward": 150, "duration_min": 8,
         "content": "Candlestick charts show 4 prices per period: Open, High, Low, Close. Green candles mean price rose; red means it fell."},
        {"id": 4, "title": "Understanding P/E Ratio", "xp_reward": 150, "duration_min": 7,
         "content": "P/E = Price ÷ Earnings per Share. A lower P/E may indicate better value, but context matters — compare within the same industry."},
        {"id": 5, "title": "What is Diversification?", "xp_reward": 100, "duration_min": 5,
         "content": "Spreading investments across different assets reduces risk. If one stock falls sharply, others may offset the loss."},
        {"id": 6, "title": "Bull vs Bear Markets", "xp_reward": 100, "duration_min": 4,
         "content": "A bull market is a rising market (prices up 20%+). A bear market is a falling market (prices down 20%+). Both are normal cycles."},
        {"id": 7, "title": "Dividends Explained", "xp_reward": 100, "duration_min": 5,
         "content": "Some companies pay shareholders a portion of profits called dividends. Dividend yield = Annual Dividend ÷ Stock Price × 100."},
        {"id": 8, "title": "Market Cap & Company Size", "xp_reward": 100, "duration_min": 5,
         "content": "Market Cap = Price × Total Shares. Large-cap (>$10B) are stable. Mid-cap ($2-10B) offer growth. Small-cap (<$2B) are riskier but can grow faster."},
        {"id": 9, "title": "Risk vs Return", "xp_reward": 150, "duration_min": 7,
         "content": "Higher potential returns come with higher risk. Government bonds are low risk/low return. Growth stocks are high risk/high potential return."},
        {"id": 10, "title": "How to Analyse a Stock", "xp_reward": 200, "duration_min": 10,
         "content": "Fundamental analysis looks at financials (P/E, revenue, debt). Technical analysis looks at price patterns. Use both for better decisions."},
    ]


def _fallback_glossary():
    return [
        {"term": "Bull Market",    "definition": "A market rising 20%+ from recent lows.",          "category": "Market"},
        {"term": "Bear Market",    "definition": "A market falling 20%+ from recent highs.",         "category": "Market"},
        {"term": "Dividend",       "definition": "Portion of company profits paid to shareholders.", "category": "Stocks"},
        {"term": "Portfolio",      "definition": "The complete collection of your investments.",     "category": "General"},
        {"term": "Volatility",     "definition": "How much a stock's price fluctuates over time.",  "category": "Risk"},
        {"term": "Market Cap",     "definition": "Total value of a company: Price × Total Shares.", "category": "Valuation"},
        {"term": "P/E Ratio",      "definition": "Price-to-Earnings. What investors pay per $1 of earnings.", "category": "Valuation"},
        {"term": "Liquidity",      "definition": "How easily an asset can be bought or sold.",      "category": "Market"},
        {"term": "Index Fund",     "definition": "A fund tracking a market index like S&P 500.",    "category": "Funds"},
        {"term": "Short Selling",  "definition": "Borrowing and selling shares, hoping to buy back cheaper.", "category": "Trading"},
        {"term": "Blue Chip",      "definition": "Large, stable, well-established company stock.",  "category": "Stocks"},
        {"term": "IPO",            "definition": "Initial Public Offering — when a company first sells shares publicly.", "category": "Market"},
        {"term": "EPS",            "definition": "Earnings Per Share — profit divided by number of shares.", "category": "Valuation"},
        {"term": "52-Week High/Low","definition": "The highest and lowest price a stock traded at in the past year.", "category": "Stocks"},
        {"term": "Stop-Loss",      "definition": "An order to automatically sell when a price falls to a set level.", "category": "Trading"},
        {"term": "Beta",           "definition": "Measures a stock's volatility vs the market. >1 = more volatile.", "category": "Risk"},
        {"term": "Sector",         "definition": "Group of companies in the same industry (e.g. Technology, Healthcare).", "category": "General"},
        {"term": "Bid/Ask Spread", "definition": "Difference between the buy price (ask) and sell price (bid).", "category": "Trading"},
        {"term": "Volume",         "definition": "Number of shares traded in a given period.",      "category": "Market"},
        {"term": "Yield",          "definition": "Income earned on an investment, expressed as a percentage.", "category": "Returns"},
    ]






