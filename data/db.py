"""
data/db.py
SQLite database initialization and connection management.
"""

import sqlite3
import os
from contextlib import contextmanager
from config import DATABASE_URL

# Strip the sqlite:/// prefix for raw sqlite3 usage
DB_PATH = DATABASE_URL.replace("sqlite:///", "")


def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections — auto-commits or rolls back."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't already exist."""
    with get_db() as conn:
        cursor = conn.cursor()

        # ── Users ──────────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                email       TEXT    UNIQUE NOT NULL,
                password_hash TEXT  NOT NULL,
                created_at  TEXT    DEFAULT (datetime('now')),
                last_login  TEXT,
                is_active   INTEGER DEFAULT 1,
                xp_points   INTEGER DEFAULT 0,
                lessons_completed INTEGER DEFAULT 0
            )
        """)

        # ── Wallets ─────────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER UNIQUE NOT NULL REFERENCES users(id),
                balance     REAL    NOT NULL DEFAULT 100000.0,
                total_deposited REAL DEFAULT 100000.0,
                updated_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

        # ── Holdings ────────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                ticker      TEXT    NOT NULL,
                quantity    REAL    NOT NULL DEFAULT 0,
                avg_cost    REAL    NOT NULL DEFAULT 0,
                updated_at  TEXT    DEFAULT (datetime('now')),
                UNIQUE(user_id, ticker)
            )
        """)

        # ── Trades ──────────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                action      TEXT    NOT NULL CHECK(action IN ('BUY','SELL')),
                ticker      TEXT    NOT NULL,
                quantity    REAL    NOT NULL,
                price       REAL    NOT NULL,
                total_value REAL    NOT NULL,
                order_type  TEXT    DEFAULT 'market',
                executed_at TEXT    DEFAULT (datetime('now'))
            )
        """)

        # ── Wallet Transactions ─────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                type        TEXT    NOT NULL CHECK(type IN ('credit','debit','reset')),
                amount      REAL    NOT NULL,
                reason      TEXT,
                balance_after REAL,
                created_at  TEXT    DEFAULT (datetime('now'))
            )
        """)

        # ── Watchlist ───────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                ticker      TEXT    NOT NULL,
                added_at    TEXT    DEFAULT (datetime('now')),
                UNIQUE(user_id, ticker)
            )
        """)

        # ── Limit Orders ────────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS limit_orders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                action      TEXT    NOT NULL CHECK(action IN ('BUY','SELL')),
                ticker      TEXT    NOT NULL,
                quantity    REAL    NOT NULL,
                limit_price REAL    NOT NULL,
                status      TEXT    DEFAULT 'pending' CHECK(status IN ('pending','executed','cancelled')),
                created_at  TEXT    DEFAULT (datetime('now')),
                executed_at TEXT
            )
        """)

        # ── Portfolio Resets ────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_resets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                reset_at    TEXT    DEFAULT (datetime('now')),
                portfolio_value_at_reset REAL
            )
        """)

        # ── Lesson Progress ─────────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lesson_progress (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                lesson_id   INTEGER NOT NULL,
                completed   INTEGER DEFAULT 0,
                score       REAL    DEFAULT 0,
                completed_at TEXT,
                UNIQUE(user_id, lesson_id)
            )
        """)

        # ── Price Cache (reduce API calls) ──────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker      TEXT    PRIMARY KEY,
                price       REAL    NOT NULL,
                cached_at   TEXT    DEFAULT (datetime('now'))
            )
        """)

        print("[DB] All tables created successfully.")
