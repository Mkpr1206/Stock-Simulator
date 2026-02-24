from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta

from core.market import MarketData
from core.portfolio import Portfolio, InsufficientSharesError
from core.wallet import Wallet, InsufficientFundsError
from core.leaderboard import Leaderboard
from core.simulator import MarketSimulator
from education.lessons import get_all_lessons_summary, get_lesson, grade_quiz
from education.glossary import get_all_terms, get_term
from education.scenarios import get_all_scenarios
from data.db import get_db, init_db
from data.seed import seed_database
from config import (
    SECRET_KEY, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES,
    REAL_MONEY_PURCHASABLE, ADS_ENABLED, PRO_PLAN_EXISTS,
    FEATURED_TICKERS, APP_CURRENCY_NAME, APP_CURRENCY_SYMBOL,
    STARTING_BALANCE
)

# Auto-initialize database on startup (required for cloud deployment)
# Render doesn't have our local .db file, so we create it fresh every deploy
init_db()
seed_database()

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

# ── Serve frontend ────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="."), name="static")

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
        user = conn.execute(
            "SELECT * FROM users WHERE id=? AND is_active=1", (user_id,)
        ).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(user)


# ── Root ──────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def serve_home():
    return FileResponse("index.html")


@app.get("/info", tags=["Info"])
def info():
    return {
        "app": "StockSim",
        "tagline": "Learn to invest. Risk nothing real.",
        "currency": APP_CURRENCY_NAME,
        "starting_balance": f"{APP_CURRENCY_SYMBOL}{STARTING_BALANCE:,}",
        "real_money": REAL_MONEY_PURCHASABLE,
        "ads": ADS_ENABLED,
        "pro_plan": PRO_PLAN_EXISTS,
        "docs": "/docs"
    }


# ── Auth ──────────────────────────────────────────────────────────────
@app.post("/auth/register", tags=["Auth"])
def register(username: str, email: str, password: str):
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if "@" not in email:
        raise HTTPException(400, "Invalid email address")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    try:
        with get_db() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username=? OR email=?", (username, email)
            ).fetchone()
            if existing:
                raise HTTPException(400, "Username or email already taken")
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
                (username, email, pw_hash)
            )
            user_id = cur.lastrowid

        # Create wallet — try class method first, fall back to raw SQL
        try:
            Wallet.create_for_user(user_id)
        except Exception:
            try:
                with get_db() as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?,?)",
                        (user_id, STARTING_BALANCE)
                    )
            except Exception:
                pass  # Will be auto-created on first /wallet call

        token = create_access_token({"user_id": user_id, "username": username})
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": username,
            "message": f"Welcome {username}! You have {APP_CURRENCY_SYMBOL}{STARTING_BALANCE:,.0f} {APP_CURRENCY_NAME} to start."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Registration error: {str(e)}")


@app.post("/auth/login", tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    try:
        with get_db() as conn:
            # Accept username OR email in the username field
            user = conn.execute(
                "SELECT * FROM users WHERE username=? OR email=?",
                (form.username, form.username.lower())
            ).fetchone()
        if not user or not bcrypt.checkpw(form.password.encode(), user["password_hash"].encode()):
            raise HTTPException(401, "Incorrect username/email or password")
        token = create_access_token({"user_id": user["id"], "username": user["username"]})
        return {"access_token": token, "token_type": "bearer", "username": user["username"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login error: {str(e)}")


@app.delete("/auth/account", tags=["Auth"])
def delete_account(current_user: dict = Depends(get_current_user)):
    """Permanently delete the current user's account and all associated data."""
    user_id = current_user["id"]
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM watchlist WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM wallets WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM trades WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM holdings WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM lesson_progress WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        return {"message": "Account permanently deleted."}
    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")


@app.post("/auth/login-email", tags=["Auth"])
def login_by_email(email: str, password: str):
    """Login using email address instead of username."""
    try:
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE email=?", (email.lower(),)
            ).fetchone()
        if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            raise HTTPException(401, "Incorrect email or password")
        token = create_access_token({"user_id": user["id"], "username": user["username"]})
        return {"access_token": token, "token_type": "bearer", "username": user["username"]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Login error: {str(e)}")



def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "email": current_user["email"],
        "xp_points": current_user.get("xp_points", 0),
        "lessons_completed": current_user.get("lessons_completed", 0),
    }


# ── Market ────────────────────────────────────────────────────────────
@app.get("/market/price/{ticker}", tags=["Market"])
def get_price(ticker: str):
    try:
        price = market.get_price(ticker.upper())
        return {"ticker": ticker.upper(), "price": price}
    except Exception as e:
        raise HTTPException(404, str(e))


@app.get("/market/info/{ticker}", tags=["Market"])
def get_stock_info(ticker: str):
    try:
        info = market.get_info(ticker.upper())
        info["current_price"] = market.get_price(ticker.upper())
        return info
    except Exception as e:
        raise HTTPException(404, str(e))


@app.get("/market/history/{ticker}", tags=["Market"])
def get_history(ticker: str, period: str = "1y", interval: str = "1d"):
    try:
        return {
            "ticker": ticker.upper(),
            "period": period,
            "interval": interval,
            "data": market.get_historical_dict(ticker.upper(), period)
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/market/featured", tags=["Market"])
def get_featured():
    try:
        prices = market.get_prices_bulk(FEATURED_TICKERS)
        return [{"ticker": t, "price": prices.get(t, 0)} for t in FEATURED_TICKERS]
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/market/sentiment", tags=["Market"])
def get_sentiment():
    try:
        return simulator.get_market_sentiment()
    except Exception:
        return {"sentiment": "neutral", "score": 0}


# ── Trading ───────────────────────────────────────────────────────────
@app.post("/trade/buy", tags=["Trading"])
def buy_stock(ticker: str, quantity: float, current_user: dict = Depends(get_current_user)):
    try:
        return Portfolio(current_user["id"]).buy(ticker, quantity)
    except InsufficientFundsError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/trade/sell", tags=["Trading"])
def sell_stock(ticker: str, quantity: float, current_user: dict = Depends(get_current_user)):
    try:
        return Portfolio(current_user["id"]).sell(ticker, quantity)
    except Exception as e:
        raise HTTPException(400, str(e))


# ── Portfolio ─────────────────────────────────────────────────────────
@app.get("/portfolio", tags=["Portfolio"])
def get_portfolio(current_user: dict = Depends(get_current_user)):
    try:
        return Portfolio(current_user["id"]).get_summary()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/portfolio/trades", tags=["Portfolio"])
def get_trades(limit: int = 50, current_user: dict = Depends(get_current_user)):
    try:
        return Portfolio(current_user["id"]).get_trade_history()
    except Exception:
        return []


# ── Wallet ────────────────────────────────────────────────────────────
@app.get("/wallet", tags=["Wallet"])
def get_wallet(current_user: dict = Depends(get_current_user)):
    try:
        return Wallet(current_user["id"]).get_wallet_info()
    except Exception:
        # Auto-create wallet if missing
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO wallets (user_id, balance) VALUES (?,?)",
                    (current_user["id"], STARTING_BALANCE)
                )
            return {"balance": STARTING_BALANCE, "user_id": current_user["id"]}
        except Exception as e:
            raise HTTPException(500, str(e))


@app.post("/wallet/reset", tags=["Wallet"])
def reset_wallet(current_user: dict = Depends(get_current_user)):
    try:
        portfolio = Portfolio(current_user["id"])
        summary = portfolio.get_summary()
        return Wallet(current_user["id"]).reset(portfolio_value=summary["total_value"])
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Watchlist ─────────────────────────────────────────────────────────
@app.post("/watchlist", tags=["Watchlist"])
def add_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO watchlist (user_id, ticker) VALUES (?,?)",
                (current_user["id"], ticker.upper())
            )
        except Exception:
            raise HTTPException(400, "Already on watchlist")
    return {"message": f"{ticker.upper()} added to watchlist"}


@app.get("/watchlist", tags=["Watchlist"])
def get_watchlist(current_user: dict = Depends(get_current_user)):
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT ticker, added_at FROM watchlist WHERE user_id=?",
                (current_user["id"],)
            ).fetchall()
        if not rows:
            return []
        tickers = [r["ticker"] for r in rows]
        prices = market.get_prices_bulk(tickers)
        return [
            {"ticker": r["ticker"], "current_price": prices.get(r["ticker"], 0), "added_at": r["added_at"]}
            for r in rows
        ]
    except Exception:
        return []


@app.delete("/watchlist/{ticker}", tags=["Watchlist"])
def remove_watchlist(ticker: str, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE user_id=? AND ticker=?",
            (current_user["id"], ticker.upper())
        )
    return {"message": f"{ticker.upper()} removed from watchlist"}


# ── Education ─────────────────────────────────────────────────────────
@app.get("/education/lessons", tags=["Education"])
def list_lessons():
    try:
        return get_all_lessons_summary()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/education/lessons/{lesson_id}", tags=["Education"])
def get_lesson_detail(lesson_id: int):
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson


@app.post("/education/lessons/{lesson_id}/quiz", tags=["Education"])
def submit_quiz(lesson_id: int, payload: dict):
    """Submit quiz answers. Body: {"answers": [0, 2, 1, ...]}"""
    try:
        answers = payload.get("answers", [])
        lesson = get_lesson(lesson_id)
        if not lesson:
            raise HTTPException(404, "Lesson not found")
        result = grade_quiz(lesson_id, answers)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Quiz error: {str(e)}")


@app.get("/education/progress", tags=["Education"])
def get_progress(current_user: dict = Depends(get_current_user)):
    """Return completed lesson IDs for the current user."""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT lesson_id, completed_at FROM lesson_progress WHERE user_id=?",
                (current_user["id"],)
            ).fetchall()
        return [
            {"lesson_id": r["lesson_id"], "completed": True, "completed_at": r["completed_at"]}
            for r in rows
        ]
    except Exception:
        return []  # Table may not exist yet — return empty, frontend handles it


@app.get("/education/glossary", tags=["Education"])
def list_glossary():
    try:
        return get_all_terms()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/education/glossary/{term}", tags=["Education"])
def lookup_term(term: str):
    return get_term(term)


@app.get("/education/scenarios", tags=["Education"])
def list_scenarios():
    try:
        return get_all_scenarios()
    except Exception:
        return []


# ── Leaderboard ───────────────────────────────────────────────────────
@app.get("/leaderboard", tags=["Leaderboard"])
def get_leaderboard():
    try:
        return Leaderboard().get_top_performers()
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/leaderboard/stats", tags=["Leaderboard"])
def community_stats():
    try:
        return Leaderboard().get_community_stats()
    except Exception:
        return {"total_traders": 0, "total_trades": 0, "average_balance": 0}


@app.get("/leaderboard/me", tags=["Leaderboard"])
def my_rank(current_user: dict = Depends(get_current_user)):
    """Return the current user's rank on the leaderboard."""
    try:
        board = Leaderboard().get_top_performers()
        board_list = board if isinstance(board, list) else board.get("leaderboard", [])
        for entry in board_list:
            if entry.get("username") == current_user["username"]:
                return {"rank": entry.get("rank"), "username": current_user["username"]}
        return {"rank": None, "username": current_user["username"]}
    except Exception:
        return {"rank": None, "username": current_user["username"]}
