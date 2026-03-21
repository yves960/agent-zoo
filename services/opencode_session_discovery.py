"""OpenCode Session Discovery Service.

Discovers running OpenCode sessions via CLI or SQLite database.
"""

import json
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class SessionAgent:
    """Represents a discovered OpenCode session."""

    source: str = "opencode-session"
    session_id: str = ""
    name: str = ""
    directory: str = ""
    updated_at: str = ""
    message_count: int = 0
    status: str = "idle"


class OpenCodeSessionDiscovery:
    """Discovers OpenCode sessions via CLI or SQLite database."""

    DB_PATH = Path.home() / ".local" / "share" / "opencode" / "opencode.db"

    def __init__(self):
        """Initialize the session discovery service."""
        self._sessions: Optional[List[SessionAgent]] = None

    def fetch_sessions(self) -> List[SessionAgent]:
        """
        Fetch all OpenCode sessions.

        Tries CLI method first, falls back to SQLite database.

        Returns:
            List of SessionAgent instances (empty if no sessions or OpenCode not installed).
        """
        # Try CLI method first
        sessions = self._fetch_via_cli()
        if sessions is not None:
            return sessions

        # Fall back to SQLite
        return self._fetch_via_sqlite()

    def _fetch_via_cli(self) -> Optional[List[SessionAgent]]:
        """
        Fetch sessions via opencode CLI.

        Returns:
            List of sessions if CLI succeeded, None if CLI failed/not installed.
        """
        try:
            result = subprocess.run(
                ["opencode", "session", "list", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return None

            data = json.loads(result.stdout)

            # Handle both {"sessions": [...]} and [...] formats
            session_list = data if isinstance(data, list) else data.get("sessions", [])

            sessions = []
            for item in session_list:
                sessions.append(
                    SessionAgent(
                        session_id=item.get("session_id", item.get("id", "")),
                        name=item.get("name", item.get("title", "")),
                        directory=item.get("directory", item.get("dir", "")),
                        updated_at=item.get("updated", item.get("updated_at", "")),
                        message_count=item.get("message_count", item.get("messages", 0)),
                        status=item.get("status", "idle"),
                    )
                )
            return sessions
        except (subprocess.SubprocessError, FileNotFoundError, json.JSONDecodeError, ValueError):
            return None

    def _fetch_via_sqlite(self) -> List[SessionAgent]:
        """
        Fetch sessions directly from SQLite database.

        Returns:
            List of sessions from database, empty list if db not accessible.
        """
        if not self.DB_PATH.exists():
            return []

        try:
            conn = sqlite3.connect(self.DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, directory, updated, message_count, status
                FROM sessions
                ORDER BY updated DESC
                """
            )
            rows = cursor.fetchall()
            conn.close()

            sessions = []
            for row in rows:
                session_id, name, directory, updated, message_count, status = row
                sessions.append(
                    SessionAgent(
                        session_id=str(session_id),
                        name=name or "",
                        directory=directory or "",
                        updated_at=str(updated) if updated else "",
                        message_count=message_count or 0,
                        status=status or "idle",
                    )
                )
            return sessions
        except (sqlite3.Error, OSError):
            return []

    def get_session(self, session_id: str) -> Optional[SessionAgent]:
        """
        Get a specific session by ID.

        Args:
            session_id: The session ID to look up.

        Returns:
            SessionAgent if found, None otherwise.
        """
        sessions = self.fetch_sessions()
        for session in sessions:
            if session.session_id == session_id:
                return session
        return None

    def clear_cache(self) -> None:
        """Clear cached session list to force fresh fetch on next call."""
        self._sessions = None
