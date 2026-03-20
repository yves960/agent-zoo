"""Pydantic schemas for Zoo Multi-Agent System API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    """Request to send a message to animals."""
    content: str
    thread_id: Optional[str] = None
    animal_ids: List[str] = ["xueqiu", "liuliu", "xiaohuang"]


class PostMessageCallback(BaseModel):
    """MCP callback request for posting messages."""
    invocation_id: str
    callback_token: str
    content: str


class CancelInvocationRequest(BaseModel):
    """Request to cancel an invocation/thread."""
    thread_id: str


# Response schemas
class MessageResponse(BaseModel):
    """Response for message operations."""
    success: bool
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    content: Optional[str] = None
    error: Optional[str] = None


class ThreadResponse(BaseModel):
    """Response for thread operations."""
    success: bool
    thread_id: Optional[str] = None
    title: str = ""
    participant_animals: List[str] = []
    messages: List[Dict[str, Any]] = []
    created_at: Optional[str] = None
    last_message_at: Optional[str] = None
    error: Optional[str] = None


class CancelResponse(BaseModel):
    """Response for cancel operations."""
    success: bool
    thread_id: Optional[str] = None
    cancelled_invocations: int = 0
    error: Optional[str] = None


class CallbackResponse(BaseModel):
    """Response for MCP callbacks."""
    success: bool
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    mentions: List[str] = []
    content_preview: Optional[str] = None
    error: Optional[str] = None


class ThreadContextResponse(BaseModel):
    """Response for thread context callbacks."""
    success: bool
    thread_id: Optional[str] = None
    limit: int = 50
    messages: List[Dict[str, Any]] = []
    message_count: int = 0
    error: Optional[str] = None


class PendingMentionsResponse(BaseModel):
    """Response for pending mentions callbacks."""
    success: bool
    agent_id: Optional[str] = None
    pending_count: int = 0
    mentions: List[Dict[str, Any]] = []
    error: Optional[str] = None


# WebSocket message schemas
class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # "message", "done", "error", "system", "connect", "ping"
    animal_id: Optional[str] = None
    content: Optional[str] = None
    thread_id: Optional[str] = None
    timestamp: Optional[str] = None
    mentions: Optional[List[str]] = None  # Frontend sends animal IDs to mention
    metadata: Dict[str, Any] = {}


class WebSocketConnect(BaseModel):
    """WebSocket connection request."""
    animal_id: str


class WebsocketStatusResponse(BaseModel):
    """WebSocket status response."""
    connected: bool
    animal_id: Optional[str] = None
    session_id: Optional[str] = None
