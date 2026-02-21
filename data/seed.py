"""
data/seed.py
Seeds the database with sample users and demo data for testing and onboarding.
"""

import bcrypt
from data.db import get_db
from config import STARTING_BALANCE


DEMO_USERS = [
    {"username": "demo_alice",  "email": "alice@stocksim.app",  "password": "demo1234"},
    {"username": "demo_bob",    "email": "bob@stocksim.app",    "password": "demo1234"},
    {"username": "demo_carol",  "email": "carol@stocksim.app",  "password": "demo1234"},
]

# Fake trade history for demo users to populate leaderboard
DEMO_TRADES = [
    {"username": "demo_alice",  "ticker": "AAPL", "action": "BUY",  "qty": 50,  "price": 170.0},
    {"username": "demo_alice",  "ticker": "TSLA", "action": "BUY",  "qty": 10,  "price": 220.0},
    {"username": "demo_bob",    "ticker": "MSFT", "action": "BUY",  "qty": 30,  "price": 380.0},
    {"username": "demo_bob",    "ticker": "NVDA", "action": "BUY",  "qty": 5,   "price": 800.0},
    {"username": "demo_carol",  "ticker": "GOOGL", "action": "BUY", "qty": 20,  "price": 175.0},
]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed_database():
    """Insert demo users if they don't already exist."""
    with get_db() as conn:
        cursor = conn.cursor()

        for user in DEMO_USERS:
            existing = cursor.execute(
                "SELECT id FROM users WHERE username=?", (user["username"],)
            ).fetchone()

            if existing:
                continue

            # Insert user
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, xp_points)
                VALUES (?, ?, ?, ?)
            """, (user["username"], user["email"], _hash_password(user["password"]), 100))

            user_id = cursor.lastrowid

            # Create wallet
            cursor.execute("""
                INSERT INTO wallets (user_id, balance, total_deposited)
                VALUES (?, ?, ?)
            """, (user_id, STARTING_BALANCE, STARTING_BALANCE))

        # Seed some demo holdings for demo users
        for trade in DEMO_TRADES:
            row = cursor.execute(
                "SELECT id FROM users WHERE username=?", (trade["username"],)
            ).fetchone()
            if not row:
                continue

            user_id = row["id"]
            total = trade["qty"] * trade["price"]

            # Deduct from wallet
            cursor.execute(
                "UPDATE wallets SET balance = balance - ? WHERE user_id=?",
                (total, user_id)
            )

            # Upsert holdings
            existing_holding = cursor.execute(
                "SELECT id, quantity, avg_cost FROM holdings WHERE user_id=? AND ticker=?",
                (user_id, trade["ticker"])
            ).fetchone()

            if existing_holding:
                old_qty = existing_holding["quantity"]
                old_cost = existing_holding["avg_cost"]
                new_qty = old_qty + trade["qty"]
                new_avg = ((old_qty * old_cost) + total) / new_qty
                cursor.execute(
                    "UPDATE holdings SET quantity=?, avg_cost=? WHERE id=?",
                    (new_qty, new_avg, existing_holding["id"])
                )
            else:
                cursor.execute(
                    "INSERT INTO holdings (user_id, ticker, quantity, avg_cost) VALUES (?,?,?,?)",
                    (user_id, trade["ticker"], trade["qty"], trade["price"])
                )

            # Record trade
            cursor.execute("""
                INSERT INTO trades (user_id, action, ticker, quantity, price, total_value, order_type)
                VALUES (?,?,?,?,?,?,?)
            """, (user_id, trade["action"], trade["ticker"], trade["qty"], trade["price"], total, "market"))

        print("[Seed] Demo users and trades seeded successfully.")


def clear_database():
    """Wipe all data — use only for development/testing."""
    with get_db() as conn:
        tables = ["trades", "holdings", "transactions", "wallets",
                  "watchlist", "limit_orders", "lesson_progress",
                  "portfolio_resets", "price_cache", "users"]
        for table in tables:
            conn.execute(f"DELETE FROM {table}")
        print("[Seed] Database cleared.")
