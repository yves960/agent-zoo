"""WebSocket management for Zoo Multi-Agent System."""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Set
from uuid import uuid4

import websockets
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from core.config import get_config
from core.models import AnimalType

logger = logging.getLogger("ws_manager")


class WSConnection:
    """WebSocket connection info."""
    def __init__(self, ws: WebSocket, animal_id: Optional[AnimalType] = None, session_id: Optional[str] = None, connected_at: float = 0.0):
        self.ws = ws
        self.animal_id = animal_id
        self.session_id = session_id
        self.connected_at = connected_at


class WebSocketManager:
    """Manages WebSocket connections for real-time animal communication."""

    def __init__(self):
        self.config = get_config()
        self.active_connections: Dict[str, WSConnection] = {}
        self.animal_connections: Dict[AnimalType, Set[str]] = {}
        self.session_connections: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, animal_id: Optional[AnimalType] = None, already_accepted: bool = False) -> str:
        """Accept a new WebSocket connection."""
        if not already_accepted:
            await websocket.accept()
        connection_id = str(uuid4())
        async with self._lock:
            self.active_connections[connection_id] = WSConnection(
                ws=websocket,
                animal_id=animal_id,
                connected_at=0.0  # Simplified, no raw_scope access
            )
            if animal_id:
                if animal_id not in self.animal_connections:
                    self.animal_connections[animal_id] = set()
                self.animal_connections[animal_id].add(connection_id)
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if connection_id in self.active_connections:
                conn = self.active_connections.pop(connection_id)
                if conn.animal_id and conn.animal_id in self.animal_connections:
                    self.animal_connections[conn.animal_id].discard(connection_id)
                if conn.session_id and conn.session_id in self.session_connections:
                    self.session_connections[conn.session_id].discard(connection_id)

    async def broadcast_to_animal(
        self,
        animal_id: AnimalType,
        message: dict,
        exclude_connection_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all connections for an animal."""
        sent = 0
        if animal_id in self.animal_connections:
            connection_ids = self.animal_connections[animal_id].copy()
            for conn_id in connection_ids:
                if conn_id == exclude_connection_id:
                    continue
                if conn_id in self.active_connections:
                    try:
                        await self.active_connections[conn_id].ws.send_json(message)
                        sent += 1
                    except Exception:
                        await self.disconnect(conn_id)
        return sent

    async def broadcast_to_agents(
        self,
        agent_ids: List[str],
        message: dict,
        exclude_connection_id: Optional[str] = None,
    ) -> int:
        sent = 0
        for animal_id in agent_ids:
            if animal_id in self.animal_connections:
                connection_ids = self.animal_connections[animal_id].copy()
                for conn_id in connection_ids:
                    if conn_id == exclude_connection_id:
                        continue
                    if conn_id in self.active_connections:
                        try:
                            await self.active_connections[conn_id].ws.send_json(message)
                            sent += 1
                        except Exception:
                            await self.disconnect(conn_id)
        return sent

    async def broadcast_to_session(
        self,
        session_id: str,
        message: dict,
        exclude_connection_id: Optional[str] = None
    ) -> int:
        """Broadcast message to all connections in a session."""
        logger.debug("broadcast_to_session: session_id=%s, message_type=%s", session_id, message.get('type'))
        logger.debug("session_connections keys: %s", list(self.session_connections.keys()))
        sent = 0
        if session_id in self.session_connections:
            connection_ids = self.session_connections[session_id].copy()
            logger.debug("Found %d connections for session", len(connection_ids))
            for conn_id in connection_ids:
                if conn_id == exclude_connection_id:
                    logger.debug("Skipping excluded connection %s", conn_id)
                    continue
                if conn_id in self.active_connections:
                    try:
                        await self.active_connections[conn_id].ws.send_json(message)
                        sent += 1
                    except Exception as e:
                        logger.warning("Failed to send to %s: %s", conn_id, e)
                        await self.disconnect(conn_id)
        else:
            logger.warning("session_id NOT FOUND in session_connections!")
        return sent

    async def send_to_animal(self, animal_id: AnimalType, message: dict) -> bool:
        """Send message to a specific animal (first available connection)."""
        if animal_id in self.animal_connections:
            for conn_id in self.animal_connections[animal_id]:
                if conn_id in self.active_connections:
                    try:
                        await self.active_connections[conn_id].ws.send_json(message)
                        return True
                    except Exception:
                        await self.disconnect(conn_id)
        return False

    async def set_session_for_connection(
        self,
        connection_id: str,
        session_id: str
    ) -> bool:
        """Associate a connection with a session."""
        async with self._lock:
            logger.debug("set_session_for_connection: connection_id=%s, session_id=%s", connection_id, session_id)
            logger.debug("active_connections keys: %s", list(self.active_connections.keys()))
            if connection_id in self.active_connections:
                self.active_connections[connection_id].session_id = session_id
                if session_id not in self.session_connections:
                    self.session_connections[session_id] = set()
                self.session_connections[session_id].add(connection_id)
                logger.debug("Registered. session_connections now: %s", {k: len(v) for k, v in self.session_connections.items()})
                return True
            logger.warning("connection_id not found in active_connections!")
            return False

    async def get_connections_for_animal(
        self,
        animal_id: AnimalType
    ) -> List[WSConnection]:
        """Get all connections for an animal."""
        async with self._lock:
            connections = []
            if animal_id in self.animal_connections:
                for conn_id in self.animal_connections[animal_id]:
                    if conn_id in self.active_connections:
                        connections.append(self.active_connections[conn_id])
            return connections

    async def get_animal_count(self) -> Dict[AnimalType, int]:
        """Get connection counts per animal."""
        async with self._lock:
            return {
                animal_id: len(conns)
                for animal_id, conns in self.animal_connections.items()
            }

    async def send_to_connection(self, connection_id: str, message: dict) -> bool:
        """Send message to a specific connection by ID."""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].ws.send_json(message)
                return True
            except Exception:
                await self.disconnect(connection_id)
        return False

    async def broadcast_to_all(self, message: dict, exclude_connection_id: Optional[str] = None) -> int:
        """Broadcast message to all active connections."""
        sent = 0
        for conn_id in list(self.active_connections.keys()):
            if conn_id == exclude_connection_id:
                continue
            if conn_id in self.active_connections:
                try:
                    await self.active_connections[conn_id].ws.send_json(message)
                    sent += 1
                except Exception:
                    await self.disconnect(conn_id)
        return sent

    async def close_all(self) -> None:
        """Close all WebSocket connections."""
        async with self._lock:
            for connection_id in list(self.active_connections.keys()):
                try:
                    await self.active_connections[connection_id].ws.close()
                except Exception:
                    pass
            self.active_connections.clear()
            self.animal_connections.clear()
            self.session_connections.clear()


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketManager] = None


def get_ws_manager_sync() -> WebSocketManager:
    """Get WebSocket manager synchronously."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager


async def get_ws_manager() -> WebSocketManager:
    """Get or create the global WebSocket manager instance."""
    return get_ws_manager_sync()


async def reset_ws_manager() -> None:
    """Reset the global WebSocket manager (for testing)."""
    global _ws_manager
    _ws_manager = None


# WebSocket endpoint handler
async def websocket_endpoint(
    websocket: WebSocket,
    animal_id: Optional[str] = None
):
    """WebSocket endpoint handler."""
    manager = await get_ws_manager()
    connection_id = await manager.connect(
        websocket,
        AnimalType(animal_id) if animal_id else None
    )

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data) if data else {}

            # Handle different message types
            msg_type = message.get("type", "unknown")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "join_session":
                session_id = message.get("session_id")
                if session_id:
                    await manager.set_session_for_connection(connection_id, session_id)

            elif msg_type == "message":
                # Forward message to target
                target_animal = message.get("target_animal")
                if target_animal:
                    await manager.send_to_animal(
                        AnimalType(target_animal),
                        {
                            "type": "message",
                            "source_animal": animal_id,
                            "content": message.get("content", {})
                        }
                    )

    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception:
        await manager.disconnect(connection_id)
