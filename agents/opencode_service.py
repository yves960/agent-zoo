"""
OpenCode Service - Invokes OpenCode sessions via HTTP API.

Uses the opencode serve HTTP API (port 4096) to send messages to existing
sessions and streams the response via NDJSON.

API reference: POST /session/:sessionID/message
Streaming format: NDJSON (newline-delimited JSON)
"""

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import requests

from core.agent_config import AgentConfig
from .base import AnimalMessage, AnimalService


class OpenCodeService(AnimalService):
    """
    Invokes OpenCode sessions via HTTP API.

    Uses the opencode serve REST API (port 4096) with streaming NDJSON
    responses to yield incremental message updates.
    """

    # Default opencode serve URL - should match what opencode serve starts on
    DEFAULT_BASE_URL = "http://localhost:4096"

    def __init__(
        self,
        agent_config: AgentConfig,
        config: Optional[Dict[str, Any]] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize OpenCodeService.

        Args:
            agent_config: AgentConfig instance with id in format "opencode-session:{session_id}".
            config: Override config dict.
            base_url: Base URL for opencode serve API. Defaults to localhost:4096.
        """
        animal_id = agent_config.id
        merged = {
            **agent_config.capabilities.model_dump(),
            **(config or {}),
        }

        super().__init__(animal_id, merged)
        self.agent_config = agent_config
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self._timeout = agent_config.capabilities.timeout

    def get_cli_command(self) -> Tuple[str, List[str]]:
        """Not used for HTTP-based service."""
        return ("", [])

    def transform_event(self, event: Union[str, Dict[str, Any]]) -> Optional[AnimalMessage]:
        """
        Transform opencode NDJSON event to AnimalMessage.

        Handles:
        - message.part.updated (with delta for streaming text)
        - message.updated (complete message)
        - step_finish (end of response)
        """
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except json.JSONDecodeError:
                if event.strip():
                    return self.create_message(
                        content=event.strip(),
                        message_type="text",
                        metadata={"source": "opencode", "format": "plain"},
                        is_complete=False,
                    )
                return None

        if not isinstance(event, dict):
            return None

        event_type = event.get("type", "")

        # Skip step_start events
        if event_type == "step_start":
            return None

        # Streaming text update
        if event_type == "message.part.updated":
            part = event.get("part", {})
            part_type = part.get("type", "")
            if part_type == "text":
                # delta contains incremental text update
                delta = event.get("delta", "")
                if delta:
                    return self.create_message(
                        content=delta,
                        message_type="text",
                        metadata={"source": "opencode", "event": "part_updated"},
                        is_complete=False,
                    )
                # Full text in "text" field
                text = part.get("text", "")
                if text:
                    return self.create_message(
                        content=text,
                        message_type="text",
                        metadata={"source": "opencode", "event": "part_updated"},
                        is_complete=False,
                    )

        # Complete message
        elif event_type == "message.updated":
            info = event.get("info", {})
            role = info.get("type", "")
            # Only handle assistant messages
            if role != "assistant":
                return None

            # Collect text parts
            parts = info.get("parts", [])
            text_parts = []
            for part in parts:
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))

            content = "".join(text_parts)
            if content:
                return self.create_message(
                    content=content,
                    message_type="assistant",
                    metadata={"source": "opencode", "event": "message_updated"},
                    is_complete=True,
                )

        # Step complete
        elif event_type == "step_finish":
            return self.create_message(
                content="",
                message_type="complete",
                metadata={"source": "opencode", "event": "step_finish"},
                is_complete=True,
            )

        # Plain text event (opencode's direct text output)
        elif event_type == "text":
            text = event.get("text", "")
            if text:
                return self.create_message(
                    content=text,
                    message_type="text",
                    metadata={"source": "opencode", "event": "text"},
                    is_complete=False,
                )

        return None

    async def invoke(
        self,
        prompt: str,
        thread_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[AnimalMessage, None]:
        """
        Invoke the opencode session via HTTP API.

        Sends a POST to /session/{sessionID}/message with streaming enabled,
        then parses the NDJSON response and yields AnimalMessage instances.

        Args:
            prompt: The input prompt/message
            thread_id: The thread/session identifier

        Yields:
            AnimalMessage instances from the opencode streaming response
        """
        # Parse session_id from agent_config.id (format: "opencode-session:{session_id}")
        session_id = self.agent_config.id
        if session_id.startswith("opencode-session:"):
            session_id = session_id[len("opencode-session:"):]

        url = f"{self.base_url}/session/{session_id}/message"

        payload = {
            "parts": [{"type": "text", "text": prompt}],
        }

        try:
            # Ensure timeout is at least 1 second (requests rejects 0)
            timeout = max(1, self._timeout or 15)
            response = requests.post(
                url,
                json=payload,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            # Opencode serve returns a single complete JSON object with embedded parts
            # Parse it as a whole and yield messages for each part
            full_response = response.json()

            # Handle the parts array embedded in the response
            parts = full_response.get("parts", [])
            for part in parts:
                part_type = part.get("type", "")
                if part_type == "text":
                    text = part.get("text", "")
                    if text:
                        yield self.create_message(
                            content=text,
                            message_type="text",
                            metadata={"source": "opencode"},
                            is_complete=False,
                        )
                elif part_type == "step-finish":
                    yield self.create_message(
                        content="",
                        message_type="complete",
                        metadata={"source": "opencode", "event": "step_finish"},
                        is_complete=True,
                    )
                    return

        except requests.exceptions.ConnectionError:
            yield self.create_message(
                content=f"Cannot connect to opencode serve at {self.base_url}. "
                        f"Please ensure 'opencode serve' is running on port 4096.",
                message_type="error",
                metadata={"source": "opencode", "error": "connection_error"},
                is_complete=True,
            )
        except requests.exceptions.Timeout:
            yield self.create_message(
                content=f"OpenCode request timed out after {self._timeout}s.",
                message_type="error",
                metadata={"source": "opencode", "error": "timeout"},
                is_complete=True,
            )
        except requests.exceptions.HTTPError as e:
            yield self.create_message(
                content=f"OpenCode API error: HTTP {e.response.status_code}: {e}",
                message_type="error",
                metadata={"source": "opencode", "error": "http_error", "status_code": e.response.status_code},
                is_complete=True,
            )
        except Exception as e:
            yield self.create_message(
                content=f"OpenCode error: {str(e)}",
                message_type="error",
                metadata={"source": "opencode", "error": str(e)},
                is_complete=True,
            )

    async def _stream_lines(self, response: requests.Response) -> AsyncGenerator[str, None]:
        """
        Stream response lines as async generator.

        Args:
            response: requests Response object with streaming enabled

        Yields:
            Lines from the NDJSON response
        """
        loop = asyncio.get_event_loop()

        def read_line() -> Optional[bytes]:
            try:
                return response.raw.readline()
            except Exception:
                return None

        while True:
            line = await loop.run_in_executor(None, read_line)
            if line is None or line == b"":
                break
            if isinstance(line, bytes):
                yield line.decode("utf-8")
            else:
                yield line


# Backwards compatibility alias
OpenCodeAgentService = OpenCodeService
