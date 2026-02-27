"""
data/db.py
Supports PostgreSQL (Render) and SQLite (local dev).
Auto-detects via DATABASE_URL env var.
Uses a compatibility wrapper so routes.py works unchanged with both.
"""

import os
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./stocksim.db")
USE_POSTGRES = DATABASE_URL.startswith("postgres")

# ── PostgreSQL path ───────────────────────────────────────────────────
if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

    class PGCursorWrapper:
        """Makes psycopg2 cursor behave like sqlite3 — row['col'] access, ? placeholders."""
        def __init__(self, cursor):
            self._cur = cursor

        def _fix(self, sql):
            return sql.replace("?", "%s")

        def execute(self, sql, params=()):
            self._cur.execute(self._fix(sql), params)
            return self

        def fetchone(self):
            row = self._cur.fetchone()
            return dict(row) if row else None

        def fetchall(self):
            return [dict(r) for r in self._cur.fetchall()]

        @property
        def lastrowid(self):
            self._cur.execute("SELECT lastval()")
            return self._cur.fetchone()[0]

    class PGConnWrapper:
        """Wraps psycopg2 connection so conn.execute() works like sqlite3."""
        def __init__(self, conn):
            self._conn = conn
            self._cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        def execute(self, sql, params=()):
            wrapper = PGCursorWrapper(self._cur)
            return wrapper.execute(sql, params)

        def commit(self):   self._conn.commit()
        def rollback(self): self._conn.rollback()
        def close(self):    self._conn.close()

    @contextmanager
    def get_db():
        raw  = psycopg2.connect(DATABASE_URL)
        conn = PGConnWrapper(raw)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP,
                    is_active INTEGER DEFAULT 1,
                    xp_points INTEGER DEFAULT 0,
                    lessons_completed INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
                    balance REAL NOT NULL DEFAULT 100000.0,
                    total_deposited REAL DEFAULT 100000.0,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    ticker TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    avg_cost REAL NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, ticker)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    action TEXT NOT NULL CHECK(action IN ('BUY','SELL')),
                    ticker TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    order_type TEXT DEFAULT 'market',
                    executed_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    type TEXT NOT NULL CHECK(type IN ('credit','debit','reset')),
                    amount REAL NOT NULL,
                    reason TEXT,
                    balance_after REAL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    ticker TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(user_id, ticker)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS limit_orders (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    action TEXT NOT NULL CHECK(action IN ('BUY','SELL')),
                    ticker TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    limit_price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT NOW(),
                    executed_at TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_resets (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    reset_at TIMESTAMP DEFAULT NOW(),
                    portfolio_value_at_reset REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lesson_progress (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    lesson_id INTEGER NOT NULL,
                    completed INTEGER DEFAULT 0,
                    score REAL DEFAULT 0,
                    completed_at TIMESTAMP,
                    UNIQUE(user_id, lesson_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_cache (
                    ticker TEXT PRIMARY KEY,
                    price REAL NOT NULL,
                    cached_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("[DB] PostgreSQL tables ensured.")

# ── SQLite path ───────────────────────────────────────────────────────
else:
    import sqlite3

    DB_PATH = DATABASE_URL.replace("sqlite:///", "")
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)

    @contextmanager
    def get_db():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db():
        with get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1,
                    xp_points INTEGER DEFAULT 0,
                    lessons_completed INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
                    balance REAL NOT NULL DEFAULT 100000.0,
                    total_deposited REAL DEFAULT 100000.0,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    ticker TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    avg_cost REAL NOT NULL DEFAULT 0,
                    updated_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(user_id, ticker)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    action TEXT NOT NULL CHECK(action IN ('BUY','SELL')),
                    ticker TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_value REAL NOT NULL,
                    order_type TEXT DEFAULT 'market',
                    executed_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    type TEXT NOT NULL CHECK(type IN ('credit','debit','reset')),
                    amount REAL NOT NULL,
                    reason TEXT,
                    balance_after REAL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    ticker TEXT NOT NULL,
                    added_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(user_id, ticker)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS limit_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    action TEXT NOT NULL CHECK(action IN ('BUY','SELL')),
                    ticker TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    limit_price REAL NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT (datetime('now')),
                    executed_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_resets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    reset_at TEXT DEFAULT (datetime('now')),
                    portfolio_value_at_reset REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lesson_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    lesson_id INTEGER NOT NULL,
                    completed INTEGER DEFAULT 0,
                    score REAL DEFAULT 0,
                    completed_at TEXT,
                    UNIQUE(user_id, lesson_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_cache (
                    ticker TEXT PRIMARY KEY,
                    price REAL NOT NULL,
                    cached_at TEXT DEFAULT (datetime('now'))
                )
            """)
            print("[DB] SQLite tables ensured.")
