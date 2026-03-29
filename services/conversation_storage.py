"""
Conversation Storage Service using SQLite.

Provides persistent storage for conversations and messages using Python's
built-in sqlite3 module (no external dependencies).
"""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "conversations.db")


def get_db_path() -> str:
    """Get the absolute database path."""
    return os.path.abspath(DB_PATH)


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Conversation',
                participants TEXT NOT NULL DEFAULT '[]',
                messages TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                unread_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()


class ConversationStorage:
    """Service for storing and retrieving conversations."""

    def __init__(self):
        """Initialize the storage service."""
        init_db()

    def _row_to_conversation(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a conversation dict."""
        return {
            "id": row["id"],
            "title": row["title"],
            "participants": json.loads(row["participants"]),
            "messages": json.loads(row["messages"]),
            "status": row["status"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "isFavorite": bool(row["is_favorite"]),
            "unreadCount": row["unread_count"],
        }

    def _conversation_to_row(self, conv: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a conversation dict to database row format."""
        return {
            "id": conv.get("id", str(uuid.uuid4())),
            "title": conv.get("title", "New Conversation"),
            "participants": json.dumps(conv.get("participants", [])),
            "messages": json.dumps(conv.get("messages", [])),
            "status": conv.get("status", "active"),
            "created_at": conv.get("createdAt", datetime.utcnow().isoformat()),
            "updated_at": conv.get("updatedAt", datetime.utcnow().isoformat()),
            "is_favorite": 1 if conv.get("isFavorite", False) else 0,
            "unread_count": conv.get("unreadCount", 0),
        }

    def list_conversations(self) -> List[Dict[str, Any]]:
        """
        List all conversations (summary without full messages).

        Returns:
            List of conversation summaries sorted by updated_at desc.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, participants, status, created_at, updated_at,
                       is_favorite, unread_count
                FROM conversations
                ORDER BY updated_at DESC
            """)
            rows = cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "participants": json.loads(row["participants"]),
                    "status": row["status"],
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"],
                    "isFavorite": bool(row["is_favorite"]),
                    "unreadCount": row["unread_count"],
                    "messageCount": len(json.loads(cursor.execute(
                        "SELECT messages FROM conversations WHERE id = ?",
                        (row["id"],)
                    ).fetchone()["messages"])),
                }
                for row in rows
            ]

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single conversation with full messages.

        Args:
            conversation_id: The conversation ID.

        Returns:
            Conversation dict with full message history, or None if not found.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_conversation(row)

    def create_conversation(
        self,
        title: str = "New Conversation",
        participants: Optional[List[Dict[str, Any]]] = None,
        initial_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new conversation.

        Args:
            title: Conversation title.
            participants: List of participant agent objects.
            initial_messages: Optional list of initial messages.

        Returns:
            The created conversation dict.
        """
        now = datetime.utcnow().isoformat()
        conversation_id = str(uuid.uuid4())

        conversation = {
            "id": conversation_id,
            "title": title,
            "participants": participants or [],
            "messages": initial_messages or [],
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
            "isFavorite": False,
            "unreadCount": 0,
        }

        with get_db_connection() as conn:
            cursor = conn.cursor()
            row = self._conversation_to_row(conversation)
            cursor.execute("""
                INSERT INTO conversations (
                    id, title, participants, messages, status,
                    created_at, updated_at, is_favorite, unread_count
                ) VALUES (
                    :id, :title, :participants, :messages, :status,
                    :created_at, :updated_at, :is_favorite, :unread_count
                )
            """, row)

        return conversation

    def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        participants: Optional[List[Dict[str, Any]]] = None,
        status: Optional[str] = None,
        is_favorite: Optional[bool] = None,
        unread_count: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update a conversation.

        Args:
            conversation_id: The conversation ID.
            title: New title (if provided).
            messages: New messages list (if provided).
            participants: New participants list (if provided).
            status: New status (if provided).
            is_favorite: New favorite status (if provided).
            unread_count: New unread count (if provided).

        Returns:
            Updated conversation dict, or None if not found.
        """
        existing = self.get_conversation(conversation_id)
        if existing is None:
            return None

        now = datetime.utcnow().isoformat()
        updates = {"updated_at": now}

        if title is not None:
            updates["title"] = title
        if messages is not None:
            updates["messages"] = json.dumps(messages)
        if participants is not None:
            updates["participants"] = json.dumps(participants)
        if status is not None:
            updates["status"] = status
        if is_favorite is not None:
            updates["is_favorite"] = str(1 if is_favorite else 0)
        if unread_count is not None:
            updates["unread_count"] = str(unread_count)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
            cursor.execute(
                f"UPDATE conversations SET {set_clause} WHERE id = :id",
                {"id": conversation_id, **updates}
            )

        return self.get_conversation(conversation_id)

    def add_message(
        self,
        conversation_id: str,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Add a message to a conversation.

        Args:
            conversation_id: The conversation ID.
            message: The message to add.

        Returns:
            Updated conversation dict, or None if conversation not found.
        """
        existing = self.get_conversation(conversation_id)
        if existing is None:
            return None

        # Ensure message has an ID
        if "id" not in message:
            message["id"] = str(uuid.uuid4())

        messages = existing["messages"] + [message]
        return self.update_conversation(conversation_id, messages=messages)

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: The conversation ID.

        Returns:
            True if deleted, False if not found.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM conversations WHERE id = ?",
                (conversation_id,)
            )
            return cursor.rowcount > 0


# Singleton instance
_storage_instance: Optional[ConversationStorage] = None


def get_conversation_storage() -> ConversationStorage:
    """Get the singleton ConversationStorage instance."""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = ConversationStorage()
    return _storage_instance
