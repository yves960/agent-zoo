"""FastAPI routes for Zoo Multi-Agent System API."""

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from api.schemas import (
    CancelInvocationRequest,
    CallbackResponse,
    MessageResponse,
    PendingMentionsResponse,
    PostMessageCallback,
    SendMessageRequest,
    ThreadContextResponse,
    ThreadResponse,
    WebSocketMessage,
)
from core.config import get_config
from agents import get_agents_config
from services.cli_spawner import get_cli_spawner
from services.mcp_callback_router import get_callback_router
from services.agent_dispatcher import AgentDispatcher
from utils.a2a_mentions import ANIMAL_CONFIGS as A2A_ANIMAL_CONFIGS

# Import service dependencies (will be injected)
try:
    from services.invocation_tracker import InvocationTracker, get_invocation_tracker
    from services.a2a_router import A2ARouter, get_a2a_router
    from core.websocket_manager import WebSocketManager, get_ws_manager_sync
except ImportError as e:
    print(f"Import error: {e}")
    # Stub implementations for development
    class InvocationTracker:
        pass
    class A2ARouter:
        pass
    class WebSocketManager:
        async def connect(self, websocket, animal_id=None, already_accepted=False) -> str:
            return "stub-connection-id"
        async def close_all(self) -> None:
            pass
    def get_invocation_tracker() -> InvocationTracker:
        return InvocationTracker()
    def get_a2a_router() -> A2ARouter:
        return A2ARouter()
    def get_ws_manager_sync() -> WebSocketManager:
        return WebSocketManager()

# SessionManager stub (not implemented yet)
class SessionManager:
    pass

def get_session_manager() -> SessionManager:
    return SessionManager()

router = APIRouter(
    prefix="/api",
    tags=["zoo", "multi-agent"],
    responses={404: {"description": "Not found"}},
)


@router.post("/messages", response_model=MessageResponse)
async def send_message(
    request: SendMessageRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> MessageResponse:
    """
    Send a message to multiple animals.
    
    Args:
        request: Message content and target animals
        
    Returns:
        MessageResponse with success status and thread_id
    """
    try:
        # Validate animal IDs against dynamic config
        agents_config = get_agents_config()
        valid_animals = {agent.id for agent in agents_config.get_enabled_agents()}
        invalid_animals = set(request.animal_ids) - valid_animals
        if invalid_animals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid animal IDs: {invalid_animals}. Valid: {valid_animals}",
            )
        
        # Create or get thread
        thread_id = request.thread_id or str(uuid.uuid4())
        
        # Route message to animals
        # In production, this would use A2ARouter.route_execution()
        # For now, return success response
        
        return MessageResponse(
            success=True,
            message_id=str(uuid.uuid4()),
            thread_id=thread_id,
            content=f"Message sent to {', '.join(request.animal_ids)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        return MessageResponse(
            success=False,
            error=str(e),
        )


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
) -> ThreadResponse:
    """
    Get thread details and messages.
    
    Args:
        thread_id: Thread identifier
        
    Returns:
        ThreadResponse with thread info and messages
    """
    try:
        # TODO: Implement actual thread retrieval from storage
        agents_config = get_agents_config()
        return ThreadResponse(
            success=True,
            thread_id=thread_id,
            title=f"Thread {thread_id[:8]}",
            participant_animals=[a.id for a in agents_config.get_enabled_agents()],
            messages=[],
            created_at="2026-03-18T00:00:00",
        )
    except Exception as e:
        return ThreadResponse(
            success=False,
            error=str(e),
        )


@router.post("/threads/{thread_id}/cancel", response_model=MessageResponse)
async def cancel_thread(
    thread_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    invocation_tracker: InvocationTracker = Depends(get_invocation_tracker),
) -> MessageResponse:
    """
    Cancel all invocations in a thread.
    
    Args:
        thread_id: Thread identifier to cancel
        
    Returns:
        MessageResponse with cancellation status
    """
    try:
        # Cancel thread in invocation tracker
        cancelled_count = 0
        try:
            cancelled_count = invocation_tracker.cancel_thread(thread_id)
        except AttributeError:
            # Fallback for mock
            cancelled_count = 1
        
        return MessageResponse(
            success=True,
            thread_id=thread_id,
            content=f"Thread {thread_id} cancelled. Cancelled {cancelled_count} invocations.",
        )
    except Exception as e:
        return MessageResponse(
            success=False,
            thread_id=thread_id,
            error=str(e),
        )


# ==================== MCP Callback Endpoints ====================

@router.post("/callbacks/post-message", response_model=CallbackResponse)
async def callback_post_message(
    request: PostMessageCallback,
) -> CallbackResponse:
    """
    MCP callback endpoint for animals to post messages.
    
    Args:
        request: Callback request with invocation_id, token, and content
        
    Returns:
        CallbackResponse with message details
    """
    try:
        router = get_callback_router()
        
        result = router.post_message(
            invocation_id=request.invocation_id,
            token=request.callback_token,
            content=request.content,
        )
        
        if not result.success:
            raise HTTPException(status_code=401, detail=result.message)
        
        # Extract mentions from content
        mentions = []
        text = request.content
        for pattern, animal_key in A2A_ANIMAL_CONFIGS.items():
            if pattern in text:
                mentions.append(animal_key)
        
        return CallbackResponse(
            success=True,
            message_id=result.data.get("message_id") if result.data else None,
            thread_id=result.data.get("thread_id") if result.data else None,
            mentions=mentions,
            content_preview=request.content[:100],
        )
    except HTTPException:
        raise
    except Exception as e:
        return CallbackResponse(
            success=False,
            error=str(e),
        )


@router.get("/callbacks/thread-context", response_model=ThreadContextResponse)
async def callback_thread_context(
    invocation_id: str,
    callback_token: str,
) -> ThreadContextResponse:
    """
    MCP callback endpoint for animals to get thread context.
    
    Args:
        invocation_id: Current invocation identifier
        callback_token: Authentication token
        
    Returns:
        ThreadContextResponse with recent messages
    """
    try:
        router = get_callback_router()
        
        result = router.get_thread_context(
            invocation_id=invocation_id,
            token=callback_token,
            limit=50,
        )
        
        if not result.success:
            raise HTTPException(status_code=401, detail=result.message)
        
        return ThreadContextResponse(
            success=True,
            thread_id=result.data.get("thread_id"),
            limit=50,
            messages=result.data.get("messages", []),
            message_count=result.data.get("message_count", 0),
        )
    except HTTPException:
        raise
    except Exception as e:
        return ThreadContextResponse(
            success=False,
            error=str(e),
        )


@router.get("/callbacks/pending-mentions", response_model=PendingMentionsResponse)
async def callback_pending_mentions(
    invocation_id: str,
    callback_token: str,
) -> PendingMentionsResponse:
    """
    MCP callback endpoint for animals to check pending @mentions.
    
    Args:
        invocation_id: Current invocation identifier
        callback_token: Authentication token
        
    Returns:
        PendingMentionsResponse with pending mentions
    """
    try:
        router = get_callback_router()
        
        result = router.get_pending_mentions(
            invocation_id=invocation_id,
            token=callback_token,
        )
        
        if not result.success:
            raise HTTPException(status_code=401, detail=result.message)
        
        return PendingMentionsResponse(
            success=True,
            pending_count=result.data.get("mention_count", 0),
            mentions=result.data.get("mentions", []),
        )
    except HTTPException:
        raise
    except Exception as e:
        return PendingMentionsResponse(
            success=False,
            error=str(e),
        )


# ==================== WebSocket ====================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time multi-animal communication.
    
    Supports:
    - Animal connection/auth
    - Message broadcasting
    - Thread membership
    - Status updates
    """
    await websocket.accept()
    
    animal_id = None
    session_id = str(uuid.uuid4())
    ws_manager = None
    connection_id = None
    
    try:
        # Initial authentication message
        data = await websocket.receive_text()
        try:
            connect_req = WebSocketMessage.model_validate_json(data)
            animal_id = connect_req.animal_id or "unknown"
        except Exception as e:
            # Handle plain text connection request
            print(f"Parse error: {e}")
            if isinstance(data, str):
                # Try to extract animal_id from JSON manually
                try:
                    parsed = json.loads(data)
                    animal_id = parsed.get("animal_id", "unknown")
                except:
                    animal_id = "unknown"
        
        # Get WebSocket manager for broadcasting
        ws_manager = get_ws_manager_sync()
        
        # Connect animal to WS manager (already accepted above)
        try:
            connection_id = await ws_manager.connect(websocket, animal_id, already_accepted=True)
        except Exception as e:
            connection_id = None
            print(f"WebSocket connect error: {e}")
        
        # Send connection confirmation with connection_id
        await websocket.send_json({
            "type": "connected",
            "animal_id": animal_id,
            "session_id": session_id,
            "connection_id": connection_id,
            "message": f"Connected as {animal_id}",
        })
        
        print(f"[WS] Connection confirmed, entering main loop. session_id={session_id}", flush=True)
        
        # Main message loop
        while True:
            try:
                print(f"[WS] Waiting for message... (connection_id={connection_id})", flush=True)
                data = await websocket.receive_text()
                print(f"[WS] Received: {data[:200]}", flush=True)
                message = WebSocketMessage.parse_raw(data)
                print(f"[WS] Parsed: type={message.type}, content={message.content}")
                
                if message.type == "message":
                    # Register this connection to the thread session
                    thread_id = message.thread_id or session_id
                    if connection_id:
                        await ws_manager.set_session_for_connection(connection_id, thread_id)
                    
                    # Dispatch to agents
                    dispatcher = AgentDispatcher(ws_manager)
                    # Get mentions from message if available (frontend sends this)
                    mentions = getattr(message, 'mentions', None)
                    print(f"[WS] Dispatching: content={message.content}, mentions={mentions}", flush=True)
                    await dispatcher.dispatch_message(
                        content=message.content,
                        thread_id=thread_id,
                        mentions=mentions,
                        exclude_connection_id=connection_id,
                    )
                    print(f"[WS] Dispatch complete", flush=True)
                    
                elif message.type == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "system",
                        "content": f"Received type: {message.type}",
                    })
                    
            except ValidationError as ve:
                # Handle text messages directly
                print(f"[WS] ValidationError: {ve}")
                await websocket.send_json({
                    "type": "system",
                    "content": f"Received: {data[:100] if data else 'empty'}",
                })
                
    except WebSocketDisconnect:
        # Clean up connection
        print(f"[WS] WebSocketDisconnect for {connection_id}")
        if connection_id and ws_manager:
            try:
                await ws_manager.disconnect(connection_id)
            except Exception as e:
                print(f"[WS] Disconnect error: {e}")
    except Exception as e:
        print(f"[WS] Unexpected exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Send error to client
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e),
            })
        except Exception:
            pass


# ==================== Utility Routes ====================

@router.get("/animals", response_model=Dict[str, Any])
async def list_animals() -> Dict[str, Any]:
    """
    List all available animals and their configurations.
    
    Returns all enabled agents from config/agents.yaml with their
    full configuration including id, name, species, color, description,
    and capabilities.
    """
    agents_config = get_agents_config()
    
    return {
        "animals": {
            agent.id: {
                "id": agent.id,
                "name": agent.name,
                "species": agent.species,
                "description": agent.description,
                "color": agent.color,
                "cli": agent.capabilities.tool.value,
                "model": agent.capabilities.model,
                "enabled": agent.enabled,
                "mention_patterns": agent.mention_patterns,
                "personality": (
                    agent.personality.model_dump()
                    if agent.personality
                    else None
                ),
            }
            for agent in agents_config.get_enabled_agents()
        }
    }


@router.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Status dict with service health info
    """
    return {
        "status": "healthy",
        "service": "zoo-api",
        "version": "1.0.0",
    }


# ==================== Dependency Functions ====================

def get_api_router() -> APIRouter:
    """Get the API router instance."""
    return router
