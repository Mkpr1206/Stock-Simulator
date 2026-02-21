"""
api/schemas.py
Pydantic models for all API request and response validation.
"""

from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Any
from config import MIN_TRADE_QUANTITY, MAX_TRADE_QUANTITY


# ── Auth ───────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=6)

    @validator("username")
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username must be alphanumeric (underscores/dashes allowed)")
        return v.lower()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    message: str


# ── Market ─────────────────────────────────────────────────────────────────────

class PriceResponse(BaseModel):
    ticker: str
    price: float
    currency: str = "USD"
    note: str = "Real market price. Trading uses SimBucks — no real money."


class StockInfoResponse(BaseModel):
    ticker: str
    name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    price: Optional[float]
    pe_ratio: Optional[float]
    market_cap: Optional[int]
    dividend_yield: Optional[float]
    beta: Optional[float]
    description: Optional[str]


class SearchResult(BaseModel):
    ticker: str
    name: Optional[str]
    sector: Optional[str]
    exchange: Optional[str]


# ── Trading ────────────────────────────────────────────────────────────────────

class TradeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)

    @validator("ticker")
    def ticker_uppercase(cls, v):
        return v.upper().strip()

    @validator("quantity")
    def quantity_valid(cls, v):
        if v < MIN_TRADE_QUANTITY:
            raise ValueError(f"Minimum quantity is {MIN_TRADE_QUANTITY}")
        if v > MAX_TRADE_QUANTITY:
            raise ValueError(f"Maximum quantity is {MAX_TRADE_QUANTITY}")
        return v


class TradeResponse(BaseModel):
    trade_id: int
    action: str
    ticker: str
    quantity: float
    price: float
    total_cost: Optional[float] = None
    proceeds: Optional[float] = None
    gain_loss: Optional[float] = None
    gain_loss_pct: Optional[float] = None
    new_balance: float
    currency: str = "SimBucks"
    message: str


class LimitOrderRequest(BaseModel):
    ticker: str
    quantity: float = Field(..., gt=0)
    limit_price: float = Field(..., gt=0)

    @validator("ticker")
    def ticker_uppercase(cls, v):
        return v.upper().strip()


class StopLossRequest(BaseModel):
    ticker: str
    quantity: float = Field(..., gt=0)
    stop_price: float = Field(..., gt=0)

    @validator("ticker")
    def ticker_uppercase(cls, v):
        return v.upper().strip()


# ── Portfolio ──────────────────────────────────────────────────────────────────

class HoldingResponse(BaseModel):
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    current_value: float
    cost_basis: float
    gain_loss: float
    gain_loss_pct: float
    indicator: str


class PortfolioSummaryResponse(BaseModel):
    cash: float
    invested_value: float
    total_value: float
    starting_balance: float
    total_gain_loss: float
    total_gain_loss_pct: float
    overall_indicator: str
    holdings: List[HoldingResponse]
    num_positions: int


# ── Wallet ─────────────────────────────────────────────────────────────────────

class WalletInfoResponse(BaseModel):
    balance: float
    total_deposited: float
    currency: str
    symbol: str
    can_purchase: bool = False    # Always False — SimBucks cannot be bought
    updated_at: str


class ResetResponse(BaseModel):
    message: str
    new_balance: float
    resets_used_today: int
    resets_remaining_today: int


# ── Watchlist ──────────────────────────────────────────────────────────────────

class WatchlistAddRequest(BaseModel):
    ticker: str

    @validator("ticker")
    def ticker_uppercase(cls, v):
        return v.upper().strip()


class WatchlistItemResponse(BaseModel):
    ticker: str
    current_price: Optional[float]
    company_name: Optional[str]
    added_at: str


# ── Education ──────────────────────────────────────────────────────────────────

class LessonSummaryResponse(BaseModel):
    id: int
    title: str
    difficulty: str
    estimated_minutes: int
    xp_reward: int
    num_quiz_questions: int


class QuizSubmission(BaseModel):
    answers: List[int] = Field(..., description="List of selected option indices (0-based)")


class QuizResultResponse(BaseModel):
    lesson_id: int
    score: float
    score_pct: float
    correct: int
    total: int
    passed: bool
    xp_earned: int
    feedback: List[dict]
    message: str


# ── Leaderboard ────────────────────────────────────────────────────────────────

class LeaderboardEntryResponse(BaseModel):
    rank: int
    username: str
    total_value: float
    cash: float
    invested: float
    gain_loss: float
    gain_loss_pct: float
    indicator: str
    xp_points: int


# ── Analytics ─────────────────────────────────────────────────────────────────

class MarketSentimentResponse(BaseModel):
    score: int
    label: str
    color: str
    description: str
    education: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# ── User Profile ───────────────────────────────────────────────────────────────

class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str
    xp_points: int
    lessons_completed: int
    portfolio_summary: Optional[Any] = None
