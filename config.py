# ── Currency ──────────────────────────────────────────────────────────────────
STARTING_BALANCE       = 100_000.0      # SimBucks every new user receives
APP_CURRENCY_NAME      = "SimBucks"
APP_CURRENCY_SYMBOL    = "S$"

# ── Hard Rules (DO NOT CHANGE) ────────────────────────────────────────────────
REAL_MONEY_PURCHASABLE = False          # SimBucks can NEVER be bought with real money
ADS_ENABLED            = False          # No advertisements, ever
PRO_PLAN_EXISTS        = False          # No premium tier — equal access for all
PAYMENT_GATEWAY        = None           # No payment integration

# ── Market Data ───────────────────────────────────────────────────────────────
DATA_SOURCE                  = "yfinance"
MARKET_REFRESH_INTERVAL_SECS = 60
DEFAULT_HISTORICAL_PERIOD    = "1y"
SUPPORTED_EXCHANGES          = ["NYSE", "NASDAQ", "AMEX"]

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
SECRET_KEY            = "stocksim-dev-secret-change-in-production"
JWT_ALGORITHM         = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL          = "sqlite:///./stocksim.db"

# ── Education ─────────────────────────────────────────────────────────────────
TOTAL_LESSONS         = 10
QUIZ_PASS_SCORE       = 0.7

# ── Watchlist ─────────────────────────────────────────────────────────────────
MAX_WATCHLIST_SIZE    = 50

# ── Popular starter tickers (shown on dashboard) ──────────────────────────────
FEATURED_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NVDA", "META", "BRK-B", "JPM", "JNJ",
    "V", "PG", "UNH", "HD", "MA"
]