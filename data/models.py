"""
data/models.py
Dataclass models representing database entities.
Used throughout the app for type safety and clarity.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str
    created_at: str
    last_login: Optional[str] = None
    is_active: int = 1
    xp_points: int = 0
    lessons_completed: int = 0


@dataclass
class Wallet:
    id: int
    user_id: int
    balance: float
    total_deposited: float
    updated_at: str


@dataclass
class Holding:
    id: int
    user_id: int
    ticker: str
    quantity: float
    avg_cost: float
    updated_at: str
    # Computed fields (not from DB)
    current_price: float = 0.0
    current_value: float = 0.0
    gain_loss: float = 0.0
    gain_loss_pct: float = 0.0


@dataclass
class Trade:
    id: int
    user_id: int
    action: str          # 'BUY' or 'SELL'
    ticker: str
    quantity: float
    price: float
    total_value: float
    order_type: str
    executed_at: str


@dataclass
class Transaction:
    id: int
    user_id: int
    type: str            # 'credit', 'debit', 'reset'
    amount: float
    reason: str
    balance_after: float
    created_at: str


@dataclass
class LimitOrder:
    id: int
    user_id: int
    action: str
    ticker: str
    quantity: float
    limit_price: float
    status: str          # 'pending', 'executed', 'cancelled'
    created_at: str
    executed_at: Optional[str] = None


@dataclass
class WatchlistItem:
    id: int
    user_id: int
    ticker: str
    added_at: str
    # Enriched fields
    current_price: float = 0.0
    company_name: str = ""


@dataclass
class LessonProgress:
    id: int
    user_id: int
    lesson_id: int
    completed: bool
    score: float
    completed_at: Optional[str] = None


@dataclass
class PortfolioSummary:
    cash: float
    invested_value: float
    total_value: float
    total_gain_loss: float
    total_gain_loss_pct: float
    holdings: List[Holding] = field(default_factory=list)
    starting_balance: float = 100_000.0


@dataclass
class LeaderboardEntry:
    rank: int
    username: str
    total_value: float
    gain_loss: float
    gain_loss_pct: float
    total_trades: int
