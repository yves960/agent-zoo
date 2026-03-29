"""FastAPI routes for Zoo Multi-Agent System API."""

import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

logger = logging.getLogger("api")

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
from agents import get_agents_config, registry
from services.cli_spawner import get_cli_spawner
from services.mcp_callback_router import get_callback_router
from services.agent_dispatcher import AgentDispatcher
from utils.a2a_mentions import ANIMAL_CONFIGS as A2A_ANIMAL_CONFIGS
from services.conversation_storage import get_conversation_storage, ConversationStorage

# Import service dependencies (will be injected)
try:
    from services.invocation_tracker import InvocationTracker, get_invocation_tracker
    from services.a2a_router import A2ARouter, get_a2a_router
    from core.websocket_manager import WebSocketManager, get_ws_manager_sync
    from core.session_manager import SessionManager, get_session_manager
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

    # SessionManager stub (fallback if core.session_manager not available)
    class SessionManager:
        pass

    async def get_session_manager() -> SessionManager:
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
        
        logger.debug("Connection confirmed, entering main loop. session_id=%s", session_id)
        
        # Main message loop
        while True:
            try:
                logger.debug("Waiting for message... (connection_id=%s)", connection_id)
                data = await websocket.receive_text()
                logger.debug("Received: %s", data[:200])
                message = WebSocketMessage.model_validate_json(data)
                logger.debug("Parsed: type=%s, content=%s, thread_id=%s", message.type, message.content, getattr(message, 'thread_id', 'N/A'))
                
                if message.type == "message":
                    thread_id = message.thread_id or session_id
                    logger.debug("Message handler: connection_id=%s, thread_id=%s, session_id=%s", connection_id, thread_id, session_id)
                    # Register this connection to the thread session
                    thread_id = message.thread_id or session_id
                    if connection_id:
                        await ws_manager.set_session_for_connection(connection_id, thread_id)
                    
                    # Get mentions from message if available (frontend sends this)
                    mentions = getattr(message, 'mentions', None)
                    logger.debug("Dispatching: content=%s, mentions=%s", message.content, mentions)
                    
                    # Send "typing" indicator immediately
                    await websocket.send_json({"type": "typing", "thread_id": thread_id})
                    
                    # Dispatch to agents in background (non-blocking)
                    # This allows responses to be sent as they arrive without waiting for all agents
                    dispatcher = AgentDispatcher(ws_manager)
                    asyncio.create_task(dispatcher.dispatch_message(
                        content=message.content,
                        thread_id=thread_id,
                        mentions=mentions,
                        exclude_connection_id=connection_id,
                    ))
                    logger.debug("Dispatch started in background")
                elif message.type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message.type == "connect":
                    thread_id = message.thread_id or session_id
                    logger.debug("Connect handler: connection_id=%s, thread_id=%s, session_id=%s", connection_id, thread_id, session_id)
                    logger.debug("Session connections before: %s", ws_manager.session_connections.keys())
                    if connection_id:
                        success = await ws_manager.set_session_for_connection(connection_id, thread_id)
                        logger.debug("set_session_for_connection result: %s", success)
                        logger.debug("Session connections after: %s", ws_manager.session_connections.keys())
                    await websocket.send_json({"type": "connected", "session_id": thread_id})
                    
                else:
                    # Unknown message type
                    await websocket.send_json({
                        "type": "system",
                        "content": f"Received type: {message.type}",
                    })
                    
            except ValidationError as ve:
                # Handle text messages directly
                logger.warning("ValidationError: %s", ve)
                await websocket.send_json({
                    "type": "system",
                    "content": f"Received: {data[:100] if data else 'empty'}",
                })
                
    except WebSocketDisconnect:
        # Clean up connection
        logger.info("WebSocketDisconnect for %s", connection_id)
        if connection_id and ws_manager:
            try:
                await ws_manager.disconnect(connection_id)
            except Exception as e:
                logger.error("Disconnect error: %s", e)
    except Exception as e:
        logger.exception("Unexpected exception: %s: %s", type(e).__name__, e)
        # Send error to client
        try:
            await websocket.send_json({
                "type": "error",
                "content": str(e),
            })
        except Exception:
            pass


# ==================== Session Recovery Routes ====================

@router.get("/sessions/{session_id}/recover")
async def recover_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
) -> Dict[str, Any]:
    """
    Recover a session's full state by session_id.
    
    After a restart or disconnect, the client can call this endpoint
    to retrieve all messages and metadata for a session.
    
    Args:
        session_id: The session ID to recover
        
    Returns:
        Session recovery data including messages and metadata
    """
    try:
        recovery_info = await session_manager.recover_session(session_id)
        if not recovery_info:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return {
            "success": True,
            "session_id": session_id,
            "messages": recovery_info.get("messages", []),
            "meta": recovery_info.get("meta", {}),
            "message_count": recovery_info.get("message_count", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "session_id": session_id,
            "error": str(e),
        }


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_sessions(
    session_manager: SessionManager = Depends(get_session_manager),
) -> List[Dict[str, Any]]:
    """
    List all sessions with their metadata.
    
    Returns all sessions (persisted and in-memory) with basic info
    suitable for session selection UI.
    """
    try:
        sessions = await session_manager.get_all_sessions()
        result = []
        for session_id, session in sessions.items():
            result.append({
                "session_id": session_id,
                "title": session.title,
                "message_count": len(session.messages),
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "animal_sessions": list(session.animal_sessions.keys()),
            })
        # Sort by updated_at desc
        result.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
        return result
    except Exception as e:
        return []


@router.post("/sessions/{session_id}/clear", response_model=MessageResponse)
async def clear_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
) -> MessageResponse:
    """
    Clear a session and its messages.
    
    Args:
        session_id: Session to clear
        
    Returns:
        Success status
    """
    try:
        cleared = await session_manager.clear_session(session_id)
        return MessageResponse(
            success=cleared,
            session_id=session_id,
            content=f"Session {'cleared' if cleared else 'not found'}",
        )
    except Exception as e:
        return MessageResponse(
            success=False,
            session_id=session_id,
            error=str(e),
        )


# ==================== Conversation Routes ====================

@router.get("/conversations", response_model=List[Dict[str, Any]])
async def list_conversations(
    storage: ConversationStorage = Depends(get_conversation_storage),
) -> List[Dict[str, Any]]:
    """
    List all conversations (summary without full messages for performance).
    """
    try:
        return storage.list_conversations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations", response_model=Dict[str, Any])
async def create_conversation(
    title: str = "New Conversation",
    participants: Optional[List[Dict[str, Any]]] = None,
    initial_messages: Optional[List[Dict[str, Any]]] = None,
    storage: ConversationStorage = Depends(get_conversation_storage),
) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        title: Conversation title (default: "New Conversation").
        participants: Optional list of participant agent objects.
        initial_messages: Optional list of initial messages.
    """
    try:
        return storage.create_conversation(
            title=title,
            participants=participants or [],
            initial_messages=initial_messages or [],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation(
    conversation_id: str,
    storage: ConversationStorage = Depends(get_conversation_storage),
) -> Dict[str, Any]:
    """
    Get a single conversation with full message history.

    Args:
        conversation_id: The conversation ID.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return conversation


@router.put("/conversations/{conversation_id}", response_model=Dict[str, Any])
async def update_conversation(
    conversation_id: str,
    title: Optional[str] = None,
    messages: Optional[List[Dict[str, Any]]] = None,
    participants: Optional[List[Dict[str, Any]]] = None,
    status: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    unread_count: Optional[int] = None,
    storage: ConversationStorage = Depends(get_conversation_storage),
) -> Dict[str, Any]:
    """
    Update a conversation.

    Args:
        conversation_id: The conversation ID.
        title: New title (optional).
        messages: New messages list (optional).
        participants: New participants list (optional).
        status: New status - active/paused/ended (optional).
        is_favorite: New favorite status (optional).
        unread_count: New unread count (optional).
    """
    result = storage.update_conversation(
        conversation_id,
        title=title,
        messages=messages,
        participants=participants,
        status=status,
        is_favorite=is_favorite,
        unread_count=unread_count,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return result


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    storage: ConversationStorage = Depends(get_conversation_storage),
) -> Dict[str, Any]:
    """
    Delete a conversation.

    Args:
        conversation_id: The conversation ID.
    """
    deleted = storage.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Conversation '{conversation_id}' not found")
    return {"success": True, "id": conversation_id}


# ==================== Utility Routes ====================

@router.get("/animals", response_model=Dict[str, Any])
async def list_animals() -> Dict[str, Any]:
    """
    List all available animals and their configurations.

    Returns all enabled agents from config/agents.yaml AND h-agent
    with their full configuration including id, name, species, color, description,
    and capabilities.
    """
    agents_config = get_agents_config()
    yaml_agent_ids = {agent.id for agent in agents_config.get_enabled_agents()}

    animals_dict = {
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
            "source": agent.source.value,
            "personality": (
                agent.personality.model_dump()
                if agent.personality
                else None
            ),
        }
        for agent in agents_config.get_enabled_agents()
    }

    for animal_id in registry.get_all_animal_ids():
        if animal_id in yaml_agent_ids:
            continue
        config = registry.get_config(animal_id)
        if config is None:
            continue
        animals_dict[animal_id] = {
            "id": config.id,
            "name": config.name,
            "species": config.species,
            "description": config.description,
            "color": config.color,
            "cli": config.capabilities.tool.value,
            "model": config.capabilities.model,
            "enabled": config.enabled,
            "mention_patterns": config.mention_patterns,
            "source": config.source.value,
            "personality": (
                config.personality.model_dump()
                if config.personality
                else None
            ),
        }

    return {"animals": animals_dict}


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


# ==================== External Agent Discovery Routes ====================

@router.get("/external/agents")
async def list_external_agents():
    """
    Aggregate all discovered agents from h-agent, directory scan, and OpenCode sessions.
    
    Returns agents from all discovery sources except local config.
    """
    from services.h_agent_client import HAgentClient
    from services.directory_scanner import DirectoryScanner
    from services.opencode_session_discovery import OpenCodeSessionDiscovery
    
    all_agents = {}
    
    # 1. h-agent agents
    h_client = HAgentClient()
    for agent in h_client.fetch_agents():
        agent_id = f"h-agent:{agent.id}"
        all_agents[agent_id] = {
            "id": agent_id,
            "name": agent.name,
            "source": "h-agent",
            "role": agent.role,
            "description": agent.description,
            "status": "available",
        }
    
    # 2. Directory scanned agents
    scanner = DirectoryScanner()
    for discovered in scanner.scan():
        agent_id = f"directory:{discovered.agent_id}"
        all_agents[agent_id] = {
            "id": agent_id,
            "name": discovered.name,
            "source": "directory",
            "status": "available",
        }
    
    # 3. OpenCode sessions
    opencode = OpenCodeSessionDiscovery()
    for session in opencode.fetch_sessions():
        agent_id = f"opencode-session:{session.session_id}"
        all_agents[agent_id] = {
            "id": agent_id,
            "name": session.name,
            "source": "opencode-session",
            "status": session.status,
            "sessionId": session.session_id,
            "directory": session.directory,
        }
    
    return {"agents": all_agents}


@router.get("/network/agents")
async def list_network_agents():
    """
    List discovered agents on the local network via mDNS.
    """
    from services.network_discovery import NetworkDiscoveryService
    
    discovery = NetworkDiscoveryService()
    agents = discovery.get_discovered_agents()
    
    return {
        "agents": {
            a.name: {
                "id": f"network:{a.name}",
                "name": a.name,
                "source": "network",
                "address": a.address,
                "port": a.port,
                "status": "available",
            }
            for a in agents
        }
    }


# ==================== Dependency Functions ====================

def get_api_router() -> APIRouter:
    """Get the API router instance."""
    return router
