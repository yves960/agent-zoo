"""FastAPI dependencies for Zoo Multi-Agent System API.

Provides dependency injection functions for service components.
"""

from typing import Optional

from services.invocation_tracker import InvocationTracker, get_invocation_tracker
from utils.a2a_mentions import ANIMAL_CONFIGS
from services.mcp_callback_router import get_callback_router

# Try to import optional service dependencies
try:
    from services.session_manager import SessionManager, get_session_manager
    from utils.a2a_router import A2ARouter, get_a2a_router
    from core.websocket_manager import WebSocketManager, get_ws_manager
    SERVICE_IMPORTS_AVAILABLE = True
except ImportError:
    SERVICE_IMPORTS_AVAILABLE = False
    # Create stub classes for development
    class SessionManager:
        """Stub SessionManager when services not available."""
        pass
    
    class A2ARouter:
        """Stub A2ARouter when utils not available."""
        pass
    
    class WebSocketManager:
        """Stub WebSocketManager when core not available."""
        async def connect(self, websocket, animal_id=None, already_accepted=False) -> str:
            return "stub-connection-id"
        async def close_all(self) -> None:
            pass
    
    def get_session_manager() -> SessionManager:
        return SessionManager()
    
    def get_a2a_router() -> A2ARouter:
        return A2ARouter()
    
    def get_ws_manager() -> WebSocketManager:
        return WebSocketManager()


def get_session_manager() -> SessionManager:
    """
    Get the SessionManager instance.
    
    Returns:
        SessionManager for managing animal sessions
    """
    if SERVICE_IMPORTS_AVAILABLE:
        return get_session_manager()
    return SessionManager()


def get_invocation_tracker() -> InvocationTracker:
    """
    Get the InvocationTracker instance.
    
    Returns:
        InvocationTracker for tracking multi-animal invocations
    """
    return get_invocation_tracker()


def get_a2a_router() -> Optional[A2ARouter]:
    """
    Get the A2ARouter instance for routing @mentions between animals.
    
    Returns:
        A2ARouter or None if not available
    """
    if SERVICE_IMPORTS_AVAILABLE:
        try:
            from agents.base import AgentService
            from agents.opencode_agent import OpenCodeAgent
            from agents.claude_agent import ClaudeAgent
            from agents.crush_agent import CrushAgent
            
            agent_services = {
                "xueqiu": OpenCodeAgent(),
                "liuliu": ClaudeAgent(),
                "xiaohuang": CrushAgent(),
            }
            return get_a2a_router(agent_services=agent_services)
        except ImportError:
            return A2ARouter()
    return A2ARouter()


def get_callback_router():
    """
    Get the MCP callback router.
    
    Returns:
        MCPHTTPCallbackRouter for handling animal callbacks
    """
    return get_callback_router()


def get_websocket_manager() -> WebSocketManager:
    """
    Get the WebSocketManager instance.
    
    Returns:
        WebSocketManager for managing WebSocket connections
    """
    if SERVICE_IMPORTS_AVAILABLE:
        from core.websocket_manager import get_ws_manager_sync
        return get_ws_manager_sync()
    return WebSocketManager()


def get_animal_config(animal_id: str) -> dict:
    """
    Get configuration for a specific animal.
    
    Args:
        animal_id: Animal identifier (xueqiu, liuliu, xiaohuang)
        
    Returns:
        Animal configuration dict with name, species, cli, color
    """
    return ANIMAL_CONFIGS.get(animal_id, {})


def get_all_animals() -> dict:
    """
    Get configuration for all animals.
    
    Returns:
        Dict mapping animal IDs to configurations
    """
    return ANIMAL_CONFIGS.copy()
