"""
WebSocket manager — broadcasts live price updates to all connected clients.
The background task fetches prices every WS_PRICE_BROADCAST_INTERVAL seconds
and pushes them to every open WebSocket connection.
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from config import WS_PRICE_BROADCAST_INTERVAL, FEATURED_TICKERS

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages all active WebSocket connections."""

    def __init__(self):
        # user_id → set of WebSocket connections (same user, multiple tabs)
        self.active: Dict[int, Set[WebSocket]] = {}
        # anonymous connections (not yet authenticated)
        self.anonymous: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket, user_id: int = None):
        await ws.accept()
        if user_id:
            self.active.setdefault(user_id, set()).add(ws)
        else:
            self.anonymous.add(ws)
        logger.info(f"WS connected. Total: {self.total_connections}")

    def disconnect(self, ws: WebSocket, user_id: int = None):
        if user_id and user_id in self.active:
            self.active[user_id].discard(ws)
            if not self.active[user_id]:
                del self.active[user_id]
        self.anonymous.discard(ws)
        logger.info(f"WS disconnected. Total: {self.total_connections}")

    @property
    def total_connections(self) -> int:
        return sum(len(v) for v in self.active.values()) + len(self.anonymous)

    async def broadcast(self, message: dict):
        """Send to every connected client."""
        data = json.dumps(message)
        dead = []
        all_ws = list(self.anonymous)
        for connections in self.active.values():
            all_ws.extend(connections)
        for ws in all_ws:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self.anonymous.discard(ws)
            for uid, conns in list(self.active.items()):
                conns.discard(ws)
                if not conns:
                    del self.active[uid]

    async def send_to_user(self, user_id: int, message: dict):
        """Send a targeted message to a specific user's connections."""
        if user_id not in self.active:
            return
        data = json.dumps(message)
        dead = []
        for ws in list(self.active[user_id]):
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active[user_id].discard(ws)


# Singleton
manager = ConnectionManager()


async def price_broadcaster(market_data_fn):
    """
    Background task — runs forever, fetches prices, broadcasts to all clients.
    market_data_fn: async callable that returns dict of {ticker: price}
    """
    logger.info("[WS] Price broadcaster started")
    while True:
        try:
            if manager.total_connections > 0:
                prices = await market_data_fn(FEATURED_TICKERS)
                if prices:
                    await manager.broadcast({
                        "type": "price_update",
                        "data": prices
                    })
        except Exception as e:
            logger.error(f"[WS] Broadcaster error: {e}")
        await asyncio.sleep(WS_PRICE_BROADCAST_INTERVAL)


async def ws_endpoint(ws: WebSocket, user_id: int = None):
    """
    FastAPI WebSocket endpoint handler.
    Usage in routes.py:
        @app.websocket("/ws")
        async def websocket(ws: WebSocket, token: str = None):
            uid = get_user_id_from_token(token)
            await ws_endpoint(ws, uid)
    """
    await manager.connect(ws, user_id)
    try:
        # Send welcome + current prices immediately on connect
        await ws.send_text(json.dumps({
            "type": "connected",
            "message": "Real-time price feed active",
            "user_id": user_id
        }))
        # Keep connection alive, handle incoming messages
        while True:
            try:
                data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                msg = json.loads(data)
                # Client can subscribe to specific tickers
                if msg.get("type") == "subscribe":
                    tickers = msg.get("tickers", [])
                    await ws.send_text(json.dumps({
                        "type": "subscribed",
                        "tickers": tickers
                    }))
                elif msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send keepalive ping
                await ws.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
    finally:
        manager.disconnect(ws, user_id)
