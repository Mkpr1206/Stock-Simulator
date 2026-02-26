import os

# ── Currency ──────────────────────────────────────────────────────────────────
STARTING_BALANCE       = 100_000.0
APP_CURRENCY_NAME      = "SimBucks"
APP_CURRENCY_SYMBOL    = "S$"

# ── Hard Rules (DO NOT CHANGE) ────────────────────────────────────────────────
REAL_MONEY_PURCHASABLE = False
ADS_ENABLED            = False
PRO_PLAN_EXISTS        = False
PAYMENT_GATEWAY        = None

# ── Market Data ───────────────────────────────────────────────────────────────
DATA_SOURCE                  = "yfinance"
MARKET_REFRESH_INTERVAL_SECS = 60
DEFAULT_HISTORICAL_PERIOD    = "1y"
SUPPORTED_EXCHANGES          = ["NYSE", "NASDAQ", "AMEX", "NSE", "BSE", "LSE", "TSE"]

# ── Trading Rules ─────────────────────────────────────────────────────────────
MIN_TRADE_QUANTITY    = 1
MAX_TRADE_QUANTITY    = 10_000
COMMISSION_FEE        = 0.0
SHORT_SELLING_ENABLED = False
OPTIONS_ENABLED       = False
FRACTIONAL_SHARES     = True

# ── Portfolio Reset ───────────────────────────────────────────────────────────
ALLOW_PORTFOLIO_RESET = True
MAX_RESETS_PER_DAY    = 3

# ── Leaderboard ───────────────────────────────────────────────────────────────
LEADERBOARD_ENABLED   = True
LEADERBOARD_TOP_N     = 50

# ── Authentication ────────────────────────────────────────────────────────────
# FIX: Read SECRET_KEY from environment variable on Render.
# Set this in Render dashboard → Environment → SECRET_KEY
# Fallback to dev key when running locally.
SECRET_KEY                  = os.getenv("SECRET_KEY", "stocksim-dev-secret-change-in-production")
JWT_ALGORITHM               = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7   # 7 days

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stocksim.db")

# ── Education ─────────────────────────────────────────────────────────────────
TOTAL_LESSONS  = 10
QUIZ_PASS_SCORE = 0.7

# ── Watchlist ─────────────────────────────────────────────────────────────────
MAX_WATCHLIST_SIZE = 50

# ── Featured tickers shown on dashboard ───────────────────────────────────────
FEATURED_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "BRK-B", "JPM", "JNJ",
    "V", "PG", "UNH", "HD", "MA"
]
