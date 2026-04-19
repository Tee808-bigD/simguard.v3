"""WebSocket manager."""
import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.add(conn)
        for conn in dead:
            self.disconnect(conn)

manager = ConnectionManager()
ws_manager = manager  # alias for main.py

async def broadcast_alert(alert_data: dict):
    await manager.broadcast({"type": "fraud_alert", "data": alert_data})
    await manager.broadcast({"type": "dashboard_refresh"})