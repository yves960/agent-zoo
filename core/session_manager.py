"""Session management for Zoo Multi-Agent System."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from core.config import get_config
from core.models import (
    AnimalMessage,
    AnimalSession,
    AnimalType,
    InvocationRecord,
    Session,
    Thread,
)
from core import session_persistence as persistence


class SessionManager:
    """
    Manages multi-animal sessions, threads, and invocations.

    All state is immediately persisted to JSONL files for crash recovery.
    On startup, existing sessions are loaded from disk.
    """

    def __init__(self):
        self.config = get_config()
        self.sessions: Dict[str, Session] = {}
        self.threads: Dict[str, Thread] = {}
        self.invocations: Dict[str, InvocationRecord] = {}
        self._lock = asyncio.Lock()
        # Load persisted sessions on startup
        self._load_persisted()

    def _load_persisted(self) -> None:
        """Load sessions and invocations from disk on startup."""
        # Load sessions metadata
        for session_id in persistence.load_all_session_ids():
            meta = persistence.get_session_meta(session_id)
            if not meta:
                continue
            try:
                messages = persistence.load_session_messages(session_id)
                session = Session(
                    id=session_id,
                    title=meta.get("title", ""),
                    created_at=datetime.fromisoformat(meta["created_at"]) if meta.get("created_at") else datetime.utcnow(),
                    updated_at=datetime.fromisoformat(meta["updated_at"]) if meta.get("updated_at") else datetime.utcnow(),
                )
                session.messages = messages
                # Restore animal sessions
                for animal_id_str in meta.get("animal_ids", []):
                    try:
                        animal_id = AnimalType(animal_id_str)
                        session.animal_sessions[animal_id] = AnimalSession(
                            animal_id=animal_id,
                            session_id=session_id,
                        )
                        # Filter messages for this animal
                        animal_msgs = [m for m in messages if m.animal_id == animal_id]
                        session.animal_sessions[animal_id].messages = animal_msgs
                        if animal_msgs:
                            session.animal_sessions[animal_id].last_activity = max(
                                m.timestamp for m in animal_msgs
                            )
                    except (ValueError, KeyError):
                        pass
                self.sessions[session_id] = session
            except Exception:
                pass

        # Load invocations
        inv_index = persistence._load_index(persistence.INVOCATIONS_DIR)
        for inv_id in inv_index:
            rec = persistence.load_invocation(inv_id)
            if rec:
                self.invocations[inv_id] = rec

    async def create_session(self, title: str = "") -> Session:
        """Create a new multi-animal session."""
        async with self._lock:
            session = Session(title=title)
            self.sessions[session.id] = session
            # Initialize animal sessions
            for animal_id in AnimalType:
                session.animal_sessions[animal_id] = AnimalSession(
                    animal_id=animal_id,
                    session_id=session.id
                )
            # Persist immediately
            persistence.persist_session_create(session)
            return session

    async def add_message(self, message: AnimalMessage) -> None:
        """Add a message to the appropriate session and thread. Immediately persisted."""
        async with self._lock:
            if message.thread_id not in self.threads:
                # Create thread if it doesn't exist
                self.threads[message.thread_id] = Thread(
                    id=message.thread_id,
                    participant_animals=[message.animal_id]
                )

            thread = self.threads[message.thread_id]
            thread.last_message_at = datetime.utcnow()
            thread.messages.append(message)

            # Update session
            session_id = message.thread_id
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session.messages.append(message)
                session.updated_at = datetime.utcnow()

                # Update animal session
                if message.animal_id in session.animal_sessions:
                    animal_session = session.animal_sessions[message.animal_id]
                    animal_session.messages.append(message)
                    animal_session.last_activity = datetime.utcnow()

            # Immediately persist message to disk for durability
            persistence.persist_thread_message(message.thread_id, message)
            persistence.persist_session_message(session_id, message)

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return self.sessions.get(session_id)

    async def get_thread(self, thread_id: str) -> Optional[Thread]:
        """Get a thread by ID."""
        return self.threads.get(thread_id)

    async def create_invocation(
        self,
        caller: AnimalType,
        target: AnimalType,
        request_data: Optional[Dict] = None
    ) -> InvocationRecord:
        """Create an invocation record."""
        async with self._lock:
            callback_token = str(uuid4())
            record = InvocationRecord(
                caller_animal=caller,
                target_animal=target,
                callback_token=callback_token,
                request_data=request_data or {}
            )
            self.invocations[record.id] = record
            # Persist immediately
            persistence.persist_invocation(record)
            return record

    async def complete_invocation(
        self,
        invocation_id: str,
        response_data: Dict,
        status: str = "completed"
    ) -> Optional[InvocationRecord]:
        """Mark an invocation as completed."""
        async with self._lock:
            if invocation_id in self.invocations:
                record = self.invocations[invocation_id]
                record.status = status
                record.completed_at = datetime.utcnow()
                record.response_data = response_data
                # Persist immediately
                persistence.persist_invocation(record)
                return record
            return None

    async def get_active_invocations(self, animal_id: AnimalType) -> List[InvocationRecord]:
        """Get all pending invocations for an animal."""
        async with self._lock:
            return [
                record for record in self.invocations.values()
                if record.target_animal == animal_id and record.status == "pending"
            ]

    async def recover_session(self, session_id: str) -> Optional[Dict]:
        """
        Recover a session's full state including messages.
        Can be called after a restart to resume a conversation.
        """
        recovery_info = persistence.get_recovery_info(session_id)
        if recovery_info and session_id in self.sessions:
            # Merge with in-memory session if it exists
            recovery_info["in_memory"] = True
        return recovery_info

    async def clear_session(self, session_id: str) -> bool:
        """Clear a session and its related data."""
        async with self._lock:
            if session_id in self.sessions:
                session = self.sessions.pop(session_id)
                # Also clear thread
                if session_id in self.threads:
                    del self.threads[session_id]
                # Remove persisted file
                session_file = persistence._jsonl_path(persistence.SESSIONS_DIR, session_id)
                if session_file.exists():
                    session_file.unlink()
                # Update index
                persistence.persist_session_update(session_id, {"status": "cleared"})
                return True
            return False

    async def get_all_sessions(self) -> Dict[str, Session]:
        """Get all active sessions."""
        return self.sessions.copy()

    async def get_all_threads(self) -> Dict[str, Thread]:
        """Get all active threads."""
        return self.threads.copy()


# Global session manager instance
_session_manager: Optional[SessionManager] = None


async def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def reset_session_manager() -> None:
    """Reset the global session manager (for testing)."""
    global _session_manager
    _session_manager = None
