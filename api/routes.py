import sys, os
sys.path.insert(0, r'C:\Users\PRANAV\Desktop\stocksim')

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta

from core.market import MarketData, TickerNotFoundError, MarketClosedError
from core.portfolio import Portfolio, InsufficientSharesError, InvalidTradeError
from core.wallet import Wallet, InsufficientFundsError
from core.orders import OrderManager, OrderNotFoundError, OrderAlreadyClosedError
from core.leaderboard import Leaderboard
from core.simulator import MarketSimulator
from analytics.charts import ChartData
from analytics.metrics import MetricsEngine
from analytics.history import PerformanceTracker
from education.lessons import get_all_lessons_summary, get_lesson, grade_quiz
from education.glossary import get_term, search_glossary, get_all_terms
from education.scenarios import get_all_scenarios, get_scenario, check_scenario_completion
from data.db import get_db
from config import (
    SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    REAL_MONEY_PURCHASABLE, ADS_ENABLED, PRO_PLAN_EXISTS,
    FEATURED_TICKERS, APP_CURRENCY_NAME, APP_CURRENCY_SYMBOL,
    STARTING_BALANCE
)

app = FastAPI(
    title="StockSim API",
    description="A free, educational stock market simulator. Real market data. SimBucks only. No real money. No ads.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
market = MarketData()
simulator = MarketSimulator()


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id=? AND is_active=1", (user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


@app.get("/", tags=["Info"])
def root():
    return {
        "app": "StockSim",
        "tagline": "Learn to invest. Risk nothing real.",
        "currency": APP_CURRENCY_NAME,
        "starting_balance": f"{APP_CURRENCY_SYMBOL}{STARTING_BALANCE:,.0f}",
        "real_money": False,
        "ads": False,
        "pro_plan": False,
        "docs": "/docs",
    }


@app.post("/auth/register", tags=["Auth"])
def register(username: str, email: str, password: str):
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM users WHERE username=? OR email=?", (username, email)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Username or email already taken")
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cursor = conn.execute("INSERT INTO users (username, email, password_hash) VALUES (?,?,?)", (username, email, password_hash))
        user_id = cursor.lastrowid
    Wallet.create_for_user(user_id)
    token = create_access_token({"user_id": user_id, "username": username})
    return {"access_token": token, "token_type": "bearer", "username": username,
            "message": f"Welcome! You have {APP_CURRENCY_SYMBOL}{STARTING_BALANCE:,.0f} {APP_CURRENCY_NAME} to start."}


@app.post("/auth/login", tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (form.username,)).fetchone()
    if not user or not bcrypt.checkpw(form.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"user_id": user["id"], "username": user["username"]})
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}


@app.get("/auth/me", tags=["Auth"])
def get_me(current_user: dict = Depends(get_current_user)):
    return {"id": current_user["id"], "username": current_user["username"],
            "email": current_user["email"], "xp_points": current_user["xp_points"]}


@app.get("/market/price/{ticker}", tags=["Market"])
def get_price(ticker: str):
    try:
        price = market.get_price(ticker.upper())
        return {"ticker": ticker.upper(), "price": price, "note": "Real price. Trading uses SimBucks only."}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/market/info/{ticker}", tags=["Market"])
def get_stock_info(ticker: str):
    try:
        info = market.get_info(ticker.upper())
        info["current_price"] = market.get_price(ticker.upper())
        return info
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/market/history/{ticker}", tags=["Market"])
def get_history(ticker: str, period: str = "1y"):
    try:
        return {"ticker": ticker.upper(), "period": period, "data": market.get_historical_dict(ticker.upper(), period)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/market/featured", tags=["Market"])
def get_featured():
    prices = market.get_prices_bulk(FEATURED_TICKERS)
    return [{"ticker": t, "price": prices.get(t, 0)} for t in FEATURED_TICKERS]


@app.get("/market/sentiment", tags=["Market"])
def get_sentiment():
    return simulator.get_market_sentiment()


@app.post("/trade/buy", tags=["Trading"])
def buy_stock(ticker: str, quantity: float, current_user: dict = Depends(get_current_user)):
    try:
        portfolio = Portfolio(current_user["id"])
        return portfolio.buy(ticker, quantity)
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/trade/sell", tags=["Trading"])
def sell_stock(ticker: str, quantity: float, current_user: dict = Depends(get_current_user)):
    try:
        portfolio = Portfolio(current_user["id"])
        return portfolio.sell(ticker, quantity)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/portfolio", tags=["Portfolio"])
def get_portfolio(current_user: dict = Depends(get_current_user)):
    return Portfolio(current_user["id"]).get_summary()


@app.get("/portfolio/trades", tags=["Portfolio"])
def get_trades(current_user: dict = Depends(get_current_user)):
    return Portfolio(current_user["id"]).get_trade_history()


@app.get("/wallet", tags=["Wallet"])
def get_wallet(current_user: dict = Depends(get_current_user)):
    return Wallet(current_user["id"]).get_wallet_info()


@app.post("/wallet/reset", tags=["Wallet"])
def reset_wallet(current_user: dict = Depends(get_current_user)):
    portfolio = Portfolio(current_user["id"])
    summary = portfolio.get_summary()
    return Wallet(current_user["id"]).reset(portfolio_value=summary["total_value"])


@app.post("/watchlist", tags=["Watchlist"])
def add_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        try:
            conn.execute("INSERT INTO watchlist (user_id, ticker) VALUES (?,?)", (current_user["id"], ticker.upper()))
        except Exception:
            raise HTTPException(status_code=400, detail="Already on watchlist")
    return {"message": f"{ticker.upper()} added to watchlist"}


@app.get("/watchlist", tags=["Watchlist"])
def get_watchlist(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute("SELECT ticker, added_at FROM watchlist WHERE user_id=?", (current_user["id"],)).fetchall()
    if not rows:
        return []
    tickers = [r["ticker"] for r in rows]
    prices = market.get_prices_bulk(tickers)
    return [{"ticker": r["ticker"], "price": prices.get(r["ticker"], 0), "added_at": r["added_at"]} for r in rows]


@app.get("/education/lessons", tags=["Education"])
def list_lessons():
    return get_all_lessons_summary()


@app.get("/education/lessons/{lesson_id}", tags=["Education"])
def get_lesson_detail(lesson_id: int):
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@app.get("/education/glossary", tags=["Education"])
def list_glossary():
    return get_all_terms()


@app.get("/education/glossary/{term}", tags=["Education"])
def lookup_term(term: str):
    return get_term(term)


@app.get("/education/scenarios", tags=["Education"])
def list_scenarios():
    return get_all_scenarios()


@app.get("/leaderboard", tags=["Leaderboard"])
def get_leaderboard():
    return Leaderboard().get_top_performers()


@app.get("/leaderboard/stats", tags=["Leaderboard"])
def community_stats():
    return Leaderboard().get_community_stats()
