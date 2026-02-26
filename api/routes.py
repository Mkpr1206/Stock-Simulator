"""
StockSim - A free, educational stock market simulator.
No real money. No ads. No pro plan. Just learning.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from datetime import datetime, timedelta
from pathlib import Path
import bcrypt

from core.market import MarketData
from core.portfolio import Portfolio, InsufficientSharesError
from core.wallet import Wallet, InsufficientFundsError
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

# ── Setup ─────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent

init_db()
try:
    seed_database()
except Exception:
    pass

app = FastAPI(
    title="StockSim API",
    description="A free, educational stock market simulator.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR)),
    name="static"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
market = MarketData()
simulator = MarketSimulator()

# ── Auth Utilities ────────────────────────────────────────────────────

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
            "SELECT * FROM users WHERE id=?", (user_id,)
        ).fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return dict(user)

# ── Root ──────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def serve_home():
    return FileResponse(str(BASE_DIR / "index.html"))

# ── Auth ──────────────────────────────────────────────────────────────

@app.post("/auth/register", tags=["Auth"])
def register(username: str, email: str, password: str):
    if len(username) < 3:
        raise HTTPException(400, "Username must be at least 3 characters")
    if "@" not in email:
        raise HTTPException(400, "Invalid email address")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

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

        conn.execute(
            "INSERT INTO wallets (user_id, balance) VALUES (?,?)",
            (user_id, STARTING_BALANCE)
        )

    token = create_access_token({"user_id": user_id, "username": username})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login", tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends()):
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE LOWER(username)=LOWER(?) OR LOWER(email)=LOWER(?)",
            (form.username, form.username)
        ).fetchone()

    if not user or not bcrypt.checkpw(
        form.password.encode(),
        user["password_hash"].encode()
    ):
        raise HTTPException(401, "Incorrect username/email or password")

    token = create_access_token(
        {"user_id": user["id"], "username": user["username"]}
    )

    return {"access_token": token, "token_type": "bearer"}

# ── FIXED DELETE ACCOUNT ──────────────────────────────────────────────

@app.delete("/auth/account", tags=["Auth"])
def delete_account(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]

    try:
        with get_db() as conn:
            # Delete child tables FIRST (order matters)
            conn.execute("DELETE FROM trades WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM holdings WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM watchlist WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM lesson_progress WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM wallets WHERE user_id=?", (user_id,))

            # Then delete user
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))

        return {"message": "Account permanently deleted"}

    except Exception as e:
        raise HTTPException(500, f"Delete failed: {str(e)}")