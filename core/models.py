"""Core Pydantic models for Zoo Multi-Agent System."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AnimalType(str, Enum):
    """Available animal types in the Zoo system."""
    XUEQIU = "xueqiu"
    LIULIU = "liuliu"
    XIAOHUANG = "xiaohuang"


class MessageRole(str, Enum):
    """Message role types."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class AnimalMessage(BaseModel):
    """Message exchanged between animals in the Zoo system."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = "message"
    animal_id: AnimalType
    content: str
    thread_id: str
    mentions: List[AnimalType] = Field(default_factory=list)
    role: MessageRole = MessageRole.USER
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnimalSession(BaseModel):
    """Session state for a specific animal."""
    animal_id: AnimalType
    session_id: str
    active: bool = True
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(default_factory=dict)
    messages: List[AnimalMessage] = Field(default_factory=list)


class Session(BaseModel):
    """Multi-animal session representation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    messages: List[AnimalMessage] = Field(default_factory=list)
    animal_sessions: Dict[AnimalType, AnimalSession] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvocationRecord(BaseModel):
    """Records an invocation between animals."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    caller_animal: AnimalType
    target_animal: AnimalType
    callback_token: str
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, completed, failed
    request_data: Dict[str, Any] = Field(default_factory=dict)
    response_data: Optional[Dict[str, Any]] = None


class Thread(BaseModel):
    """Thread for multi-animal conversation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    participant_animals: List[AnimalType] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None
    messages: List[AnimalMessage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Animal configuration mapping
ANIMAL_CONFIGS = {
    "xueqiu": {"name": "雪球", "species": "雪纳瑞", "cli": "opencode", "color": "#4A90E2"},
    "liuliu": {"name": "六六", "species": "虎皮鹦鹉(蓝)", "cli": "claude", "color": "#50C8E6"},
    "xiaohuang": {"name": "小黄", "species": "虎皮鹦鹉(黄绿)", "cli": "crush", "color": "#7ED321"},
}
