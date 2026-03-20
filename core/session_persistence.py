"""
core/session_persistence.py - JSONL-based Session Persistence for Zoo

每条会话存储为独立的 JSONL 文件，保证:
1. 写入即可持久化（append-only）
2. 服务重启后自动加载历史会话
3. 按 session_id 恢复会话上下文

文件结构:
  STORAGE_DIR/
    sessions/
      <session_id>.jsonl     # 每行一个 AnimalMessage JSON
      index.json             # session_id -> meta 索引
    threads/
      <thread_id>.jsonl      # 每行一个 AnimalMessage JSON
      index.json             # thread_id -> meta 索引
    invocations/
      <invocation_id>.json   # 单次调用记录
      index.json             # invocation_id -> meta
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator

from core.models import AnimalMessage, Session, Thread, AnimalSession, InvocationRecord, AnimalType


# ============================================================
# Paths
# ============================================================

STORAGE_DIR = Path.home() / ".agent-zoo" / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

SESSIONS_DIR = STORAGE_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

THREADS_DIR = STORAGE_DIR / "threads"
THREADS_DIR.mkdir(parents=True, exist_ok=True)

INVOCATIONS_DIR = STORAGE_DIR / "invocations"
INVOCATIONS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# JSONL Helpers
# ============================================================

def _jsonl_path(base_dir: Path, entity_id: str) -> Path:
    return base_dir / f"{entity_id}.jsonl"


def _index_path(base_dir: Path) -> Path:
    return base_dir / "index.json"


def _append_jsonl(file_path: Path, record: Dict) -> None:
    """Append a dict as one line to a JSONL file."""
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _read_jsonl(file_path: Path) -> Iterator[Dict]:
    """Read all records from a JSONL file."""
    if not file_path.exists():
        return
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass


def _write_jsonl(file_path: Path, records: List[Dict]) -> None:
    """Overwrite a JSONL file with records."""
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_index(base_dir: Path) -> Dict[str, Dict]:
    """Load the entity index from disk."""
    idx_file = _index_path(base_dir)
    if idx_file.exists():
        try:
            return json.loads(idx_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_index(base_dir: Path, index: Dict[str, Dict]) -> None:
    """Save the entity index to disk."""
    idx_file = _index_path(base_dir)
    idx_file.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================
# Session Persistence
# ============================================================

def persist_session_create(session: Session) -> None:
    """Persist a newly created session (metadata only, no messages yet)."""
    index = _load_index(SESSIONS_DIR)
    index[session.id] = {
        "id": session.id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "message_count": 0,
        "animal_ids": list(session.animal_sessions.keys()),
    }
    _save_index(SESSIONS_DIR, index)
    # Create empty session file
    _jsonl_path(SESSIONS_DIR, session.id).touch()


def persist_session_message(session_id: str, message: AnimalMessage) -> None:
    """
    Append a message to a session's JSONL file.
    Called immediately after add_message() for instant durability.
    """
    _append_jsonl(_jsonl_path(SESSIONS_DIR, session_id), message.model_dump(mode="json"))
    
    # Update index
    index = _load_index(SESSIONS_DIR)
    if session_id in index:
        index[session_id]["message_count"] = index[session_id].get("message_count", 0) + 1
        index[session_id]["updated_at"] = datetime.utcnow().isoformat()
        _save_index(SESSIONS_DIR, index)


def load_session_messages(session_id: str) -> List[AnimalMessage]:
    """Load all messages for a session from disk."""
    messages = []
    for record in _read_jsonl(_jsonl_path(SESSIONS_DIR, session_id)):
        try:
            # Parse datetime fields
            if "timestamp" in record and isinstance(record["timestamp"], str):
                record["timestamp"] = datetime.fromisoformat(record["timestamp"])
            if "created_at" in record and isinstance(record["created_at"], str):
                record["created_at"] = datetime.fromisoformat(record["created_at"])
            if "updated_at" in record and isinstance(record["updated_at"], str):
                record["updated_at"] = datetime.fromisoformat(record["updated_at"])
            messages.append(AnimalMessage(**record))
        except Exception:
            pass
    return messages


def load_all_session_ids() -> List[str]:
    """Load all session IDs from the index."""
    index = _load_index(SESSIONS_DIR)
    return list(index.keys())


def get_session_meta(session_id: str) -> Optional[Dict]:
    """Get session metadata without loading all messages."""
    index = _load_index(SESSIONS_DIR)
    return index.get(session_id)


def persist_session_update(session_id: str, meta_updates: Dict) -> None:
    """Update session metadata in the index."""
    index = _load_index(SESSIONS_DIR)
    if session_id in index:
        index[session_id].update(meta_updates)
        index[session_id]["updated_at"] = datetime.utcnow().isoformat()
        _save_index(SESSIONS_DIR, index)


# ============================================================
# Thread Persistence
# ============================================================

def persist_thread_message(thread_id: str, message: AnimalMessage) -> None:
    """Append a message to a thread's JSONL file."""
    _append_jsonl(_jsonl_path(THREADS_DIR, thread_id), message.model_dump(mode="json"))
    
    index = _load_index(THREADS_DIR)
    if thread_id not in index:
        index[thread_id] = {
            "id": thread_id,
            "message_count": 0,
            "updated_at": datetime.utcnow().isoformat(),
        }
    index[thread_id]["message_count"] = index[thread_id].get("message_count", 0) + 1
    index[thread_id]["updated_at"] = datetime.utcnow().isoformat()
    _save_index(THREADS_DIR, index)


def load_thread_messages(thread_id: str) -> List[AnimalMessage]:
    """Load all messages for a thread from disk."""
    messages = []
    for record in _read_jsonl(_jsonl_path(THREADS_DIR, thread_id)):
        try:
            if "timestamp" in record and isinstance(record["timestamp"], str):
                record["timestamp"] = datetime.fromisoformat(record["timestamp"])
            messages.append(AnimalMessage(**record))
        except Exception:
            pass
    return messages


# ============================================================
# Invocation Persistence
# ============================================================

def persist_invocation(record: InvocationRecord) -> None:
    """Persist an invocation record."""
    file_path = INVOCATIONS_DIR / f"{record.id}.json"
    file_path.write_text(json.dumps(record.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
    
    index = _load_index(INVOCATIONS_DIR)
    index[record.id] = {
        "id": record.id,
        "caller_animal": record.caller_animal.value if isinstance(record.caller_animal, AnimalType) else str(record.caller_animal),
        "target_animal": record.target_animal.value if isinstance(record.target_animal, AnimalType) else str(record.target_animal),
        "status": record.status,
        "requested_at": record.requested_at.isoformat() if record.requested_at else None,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
    }
    _save_index(INVOCATIONS_DIR, index)


def load_invocation(invocation_id: str) -> Optional[InvocationRecord]:
    """Load an invocation record from disk."""
    file_path = INVOCATIONS_DIR / f"{invocation_id}.json"
    if not file_path.exists():
        return None
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        # Parse datetime fields
        for dt_field in ["requested_at", "completed_at"]:
            if dt_field in data and data[dt_field]:
                data[dt_field] = datetime.fromisoformat(data[dt_field])
        # Parse enum fields
        if "caller_animal" in data:
            data["caller_animal"] = AnimalType(data["caller_animal"])
        if "target_animal" in data:
            data["target_animal"] = AnimalType(data["target_animal"])
        return InvocationRecord(**data)
    except Exception:
        return None


def update_invocation_status(invocation_id: str, status: str, response_data: Dict = None) -> None:
    """Update invocation status and optionally response data."""
    record = load_invocation(invocation_id)
    if record:
        record.status = status
        if response_data:
            record.response_data = response_data
        if status in ("completed", "failed"):
            record.completed_at = datetime.utcnow()
        persist_invocation(record)


# ============================================================
# Recovery API Support
# ============================================================

def get_recovery_info(session_id: str) -> Optional[Dict]:
    """
    Get all information needed to recover a session.
    Used by the recovery API endpoint.
    """
    meta = get_session_meta(session_id)
    if not meta:
        return None
    
    messages = load_session_messages(session_id)
    
    return {
        "session_id": session_id,
        "meta": meta,
        "messages": [m.model_dump(mode="json") for m in messages],
        "message_count": len(messages),
    }
