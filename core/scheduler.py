"""
Background scheduler — runs continuously, checks pending limit/stop orders,
executes them when price conditions are met, and manages other periodic tasks.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Will be injected at startup
_db = None
_market = None
_ws_manager = None


def init_scheduler(db, market, ws_manager=None):
    """Call this once at app startup with the db and market instances."""
    global _db, _market, _ws_manager
    _db = db
    _market = market
    _ws_manager = ws_manager


async def _check_limit_orders():
    """
    Scan all pending limit/stop orders and execute those whose
    price condition has been met.
    """
    if not _db or not _market:
        return

    try:
        pending = _db.query_all(
            """SELECT o.*, u.id as uid, w.balance
               FROM orders o
               JOIN users u ON o.user_id = u.id
               JOIN wallets w ON w.user_id = u.id
               WHERE o.status = 'pending'""",
        )
    except Exception as e:
        logger.error(f"[Scheduler] DB query error: {e}")
        return

    if not pending:
        return

    # Group by ticker so we only fetch each price once
    tickers_needed = list({o["ticker"] for o in pending})
    prices = {}
    for ticker in tickers_needed:
        try:
            prices[ticker] = _market.get_price(ticker)
        except Exception:
            pass

    for order in pending:
        ticker = order["ticker"]
        current_price = prices.get(ticker)
        if current_price is None:
            continue

        order_type  = order["order_type"]
        limit_price = order["limit_price"]
        qty         = order["quantity"]
        user_id     = order["user_id"]
        balance     = order["balance"]
        order_id    = order["id"]

        execute = False

        if order_type == "limit_buy" and current_price <= limit_price:
            # Price dropped to or below our buy limit — execute
            cost = current_price * qty
            if balance >= cost:
                execute = True
                action = "BUY"

        elif order_type == "limit_sell" and current_price >= limit_price:
            # Price rose to or above our sell limit — execute
            execute = True
            action = "SELL"

        elif order_type == "stop_loss" and current_price <= limit_price:
            # Price fell to stop level — sell to cut losses
            execute = True
            action = "SELL"

        if execute:
            try:
                total = current_price * qty
                if action == "BUY":
                    _db.execute(
                        "UPDATE wallets SET balance = balance - ? WHERE user_id = ?",
                        total, user_id
                    )
                    _db.execute(
                        """INSERT INTO holdings (user_id, ticker, quantity, avg_cost)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(user_id, ticker)
                           DO UPDATE SET
                             avg_cost = (avg_cost * quantity + ? * ?) / (quantity + ?),
                             quantity = quantity + ?""",
                        user_id, ticker, qty, current_price,
                        current_price, qty, qty, qty
                    )
                else:  # SELL
                    held = _db.query(
                        "SELECT quantity FROM holdings WHERE user_id=? AND ticker=?",
                        user_id, ticker
                    )
                    if not held or held < qty:
                        # Can't sell — mark expired
                        _db.execute(
                            "UPDATE orders SET status='expired' WHERE id=?", order_id
                        )
                        continue
                    _db.execute(
                        "UPDATE wallets SET balance = balance + ? WHERE user_id = ?",
                        total, user_id
                    )
                    new_qty = (held or 0) - qty
                    if new_qty <= 0:
                        _db.execute(
                            "DELETE FROM holdings WHERE user_id=? AND ticker=?",
                            user_id, ticker
                        )
                    else:
                        _db.execute(
                            "UPDATE holdings SET quantity=? WHERE user_id=? AND ticker=?",
                            new_qty, user_id, ticker
                        )

                # Record the trade
                _db.execute(
                    """INSERT INTO trades (user_id, action, ticker, quantity, price, timestamp)
                       VALUES (?, ?, ?, ?, ?, datetime('now'))""",
                    user_id, action, ticker, qty, current_price
                )

                # Mark order fulfilled
                _db.execute(
                    "UPDATE orders SET status='filled', filled_at=datetime('now'), filled_price=? WHERE id=?",
                    current_price, order_id
                )

                logger.info(f"[Scheduler] Executed {action} {qty}×{ticker} @ {current_price:.2f} for user {user_id}")

                # Notify user via WebSocket if connected
                if _ws_manager:
                    await _ws_manager.send_to_user(user_id, {
                        "type": "order_filled",
                        "action": action,
                        "ticker": ticker,
                        "quantity": qty,
                        "price": current_price,
                        "total": total,
                        "message": f"✓ Limit order filled: {action} {qty}×{ticker} @ S${current_price:.2f}"
                    })

            except Exception as e:
                logger.error(f"[Scheduler] Failed to execute order {order_id}: {e}")


async def _expire_old_orders():
    """Cancel limit orders older than 30 days."""
    if not _db:
        return
    try:
        _db.execute(
            """UPDATE orders SET status='expired'
               WHERE status='pending'
               AND created_at < datetime('now', '-30 days')"""
        )
    except Exception as e:
        logger.error(f"[Scheduler] Expire orders error: {e}")


async def _clean_expired_tokens():
    """Remove old verification/reset tokens from DB."""
    if not _db:
        return
    try:
        _db.execute(
            "DELETE FROM email_tokens WHERE expires_at < datetime('now')"
        )
    except Exception as e:
        logger.error(f"[Scheduler] Token cleanup error: {e}")


async def _update_leaderboard_cache():
    """Refresh leaderboard cache every 5 minutes."""
    if not _db or not _market:
        return
    # The leaderboard module handles its own caching — just trigger a refresh
    try:
        pass  # leaderboard.py recalculates on each /leaderboard request
    except Exception:
        pass


async def run_scheduler():
    """
    Main scheduler loop. Runs background tasks on different intervals.
    Call this with asyncio.create_task() at app startup.
    """
    logger.info("[Scheduler] Background scheduler started")

    loop_count = 0
    while True:
        try:
            loop_count += 1

            # Every 30 seconds: check limit orders
            await _check_limit_orders()

            # Every 5 minutes (10 × 30s): expire old orders + clean tokens
            if loop_count % 10 == 0:
                await _expire_old_orders()
                await _clean_expired_tokens()

            # Every 30 minutes (60 × 30s): leaderboard cache refresh
            if loop_count % 60 == 0:
                await _update_leaderboard_cache()
                loop_count = 0  # reset to avoid overflow

        except Exception as e:
            logger.error(f"[Scheduler] Unexpected error: {e}")

        await asyncio.sleep(30)
