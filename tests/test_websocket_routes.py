"""Tests for WebSocket routes and endpoints."""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from fastapi import WebSocket
from fastapi.testclient import TestClient

from main import app


class TestWebSocketConnection:
    """Tests for WebSocket connection handling."""
    
    @pytest.mark.asyncio
    async def test_websocket_connect_and_receive_confirmation(self, mock_websocket: MagicMock) -> None:
        """WebSocket should accept connection and send confirmation."""
        from api.routes import websocket_endpoint
        
        # Mock the initial receive for auth
        mock_websocket.receive_text.return_value = json.dumps({
            "type": "connect",
            "animal_id": "xueqiu"
        })
        
        # Mock subsequent receive to raise disconnect after confirmation
        from fastapi import WebSocketDisconnect
        
        async def raise_disconnect():
            raise WebSocketDisconnect()
        
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "connect", "animal_id": "xueqiu"}),
            raise_disconnect()
        ]
        
        with patch('api.routes.get_ws_manager_sync') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.connect = AsyncMock(return_value="test-conn-id")
            mock_manager.disconnect = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            await websocket_endpoint(mock_websocket)
        
        # Verify accept was called
        mock_websocket.accept.assert_called_once()
        
        # Verify confirmation was sent
        send_calls = mock_websocket.send_json.call_args_list
        assert len(send_calls) >= 1
        
        # Check the confirmation message
        confirmation = send_calls[0][0][0]
        assert confirmation["type"] == "connected"
        assert confirmation["animal_id"] == "xueqiu"
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self, mock_websocket: MagicMock) -> None:
        """WebSocket should respond to ping with pong."""
        from api.routes import websocket_endpoint
        from fastapi import WebSocketDisconnect
        
        async def raise_disconnect():
            raise WebSocketDisconnect()
        
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "connect", "animal_id": "xueqiu"}),
            json.dumps({"type": "ping"}),
            raise_disconnect()
        ]
        
        with patch('api.routes.get_ws_manager_sync') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.connect = AsyncMock(return_value="test-conn-id")
            mock_manager.disconnect = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            await websocket_endpoint(mock_websocket)
        
        # Find pong response
        send_calls = mock_websocket.send_json.call_args_list
        pong_found = False
        for call in send_calls:
            msg = call[0][0]
            if msg.get("type") == "pong":
                pong_found = True
                break
        
        assert pong_found, "Pong response not found"
    
    @pytest.mark.asyncio
    async def test_websocket_message_dispatched_to_agent(self, mock_websocket: MagicMock) -> None:
        """WebSocket message should be dispatched to agent via AgentDispatcher."""
        from api.routes import websocket_endpoint
        from fastapi import WebSocketDisconnect
        
        async def raise_disconnect():
            raise WebSocketDisconnect()
        
        message_content = "Hello agents!"
        thread_id = "test-thread-123"
        
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "connect", "animal_id": "user"}),
            json.dumps({
                "type": "message",
                "content": message_content,
                "thread_id": thread_id
            }),
            raise_disconnect()
        ]
        
        with patch('api.routes.get_ws_manager_sync') as mock_get_manager, \
             patch('api.routes.AgentDispatcher') as MockDispatcher:
            
            mock_manager = MagicMock()
            mock_manager.connect = AsyncMock(return_value="test-conn-id")
            mock_manager.disconnect = AsyncMock()
            mock_manager.set_session_for_connection = AsyncMock(return_value=True)
            mock_get_manager.return_value = mock_manager
            
            # Mock dispatcher
            mock_dispatcher_instance = MagicMock()
            mock_dispatcher_instance.dispatch_message = AsyncMock(return_value=[])
            MockDispatcher.return_value = mock_dispatcher_instance
            
            await websocket_endpoint(mock_websocket)
        
        # Verify dispatcher was created and dispatch_message was called
        MockDispatcher.assert_called_once_with(mock_manager)
        mock_dispatcher_instance.dispatch_message.assert_called_once()
        
        # Check dispatch arguments
        call_kwargs = mock_dispatcher_instance.dispatch_message.call_args[1]
        assert call_kwargs["content"] == message_content
        assert call_kwargs["thread_id"] == thread_id


class TestWebSocketRoutesIntegration:
    """Integration tests for WebSocket routes using TestClient."""
    
    def test_websocket_endpoint_exists(self) -> None:
        """WebSocket endpoint should be registered."""
        # Find the websocket route
        routes = [route for route in app.routes if hasattr(route, 'path')]
        ws_routes = [r for r in routes if r.path == "/api/ws"]
        
        assert len(ws_routes) > 0, "WebSocket endpoint /api/ws not found"
    
    def test_health_endpoint(self) -> None:
        """Health endpoint should return healthy status."""
        client = TestClient(app)
        
        response = client.get("/api/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_list_animals_endpoint(self) -> None:
        """List animals endpoint should return animal configurations."""
        client = TestClient(app)
        
        response = client.get("/api/animals")
        
        assert response.status_code == 200
        data = response.json()
        assert "animals" in data
        
        animals = data["animals"]
        assert "xueqiu" in animals
        assert "liuliu" in animals
        assert "xiaohuang" in animals


class TestWebSocketMessageTypes:
    """Tests for different WebSocket message types."""
    
    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self, mock_websocket: MagicMock) -> None:
        """Unknown message type should be handled gracefully."""
        from api.routes import websocket_endpoint
        from fastapi import WebSocketDisconnect
        
        async def raise_disconnect():
            raise WebSocketDisconnect()
        
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "connect", "animal_id": "xueqiu"}),
            json.dumps({"type": "unknown_type", "content": "test"}),
            raise_disconnect()
        ]
        
        with patch('api.routes.get_ws_manager_sync') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.connect = AsyncMock(return_value="test-conn-id")
            mock_manager.disconnect = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            await websocket_endpoint(mock_websocket)
        
        # Should send a system message for unknown type
        send_calls = mock_websocket.send_json.call_args_list
        system_found = False
        for call in send_calls:
            msg = call[0][0]
            if msg.get("type") == "system" and "unknown_type" in msg.get("content", ""):
                system_found = True
                break
        
        assert system_found, "System response for unknown type not found"
    
    @pytest.mark.asyncio
    async def test_websocket_disconnect_cleanup(self, mock_websocket: MagicMock) -> None:
        """WebSocket disconnect should cleanup resources."""
        from api.routes import websocket_endpoint
        from fastapi import WebSocketDisconnect
        
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "connect", "animal_id": "xueqiu"}),
            WebSocketDisconnect()
        ]
        
        with patch('api.routes.get_ws_manager_sync') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.connect = AsyncMock(return_value="test-conn-id")
            mock_manager.disconnect = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            await websocket_endpoint(mock_websocket)
        
        # Verify disconnect was called
        mock_manager.disconnect.assert_called_once_with("test-conn-id")


class TestWebSocketErrorHandling:
    """Tests for WebSocket error handling."""
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_json_handling(self, mock_websocket: MagicMock) -> None:
        """Invalid JSON should be handled gracefully."""
        from api.routes import websocket_endpoint
        from fastapi import WebSocketDisconnect
        
        async def raise_disconnect():
            raise WebSocketDisconnect()
        
        mock_websocket.receive_text.side_effect = [
            json.dumps({"type": "connect", "animal_id": "xueqiu"}),
            "not valid json {{{",
            raise_disconnect()
        ]
        
        with patch('api.routes.get_ws_manager_sync') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.connect = AsyncMock(return_value="test-conn-id")
            mock_manager.disconnect = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            # Should not raise exception
            await websocket_endpoint(mock_websocket)
        
        # Should have sent some response
        assert mock_websocket.send_json.called