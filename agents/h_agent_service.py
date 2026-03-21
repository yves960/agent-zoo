"""
HAgent Service - Invokes h-agent team agents via HTTP API.

Uses h-agent's HTTP API (port 8080) to send messages to team agents
and streams the SSE response.

API reference: POST /api/agents/{agent_id}/message
Streaming format: SSE (text/event-stream)
"""

import asyncio
import json
import re
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from core.agent_config import AgentConfig
from .base import AnimalMessage, AnimalService


class HAgentService(AnimalService):
    """
    Invokes h-agent team agents via HTTP API.

    Uses h-agent's SSE streaming endpoint to yield incremental responses.
    """

    DEFAULT_BASE_URL = "http://localhost:8080"

    def __init__(
        self,
        agent_config: AgentConfig,
        config: Optional[Dict[str, Any]] = None,
        base_url: Optional[str] = None,
    ):
        animal_id = agent_config.id
        merged = {
            **agent_config.capabilities.model_dump(),
            **(config or {}),
        }

        super().__init__(animal_id, merged)
        self.agent_config = agent_config
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self._timeout = agent_config.capabilities.timeout

    def get_cli_command(self) -> tuple[str, list[str]]:
        return ("", [])

    def _get_agent_id(self) -> str:
        """Extract the h-agent agent ID from the full animal ID (e.g., 'h-agent:planner' -> 'planner')."""
        agent_id = self.agent_config.id
        if agent_id.startswith("h-agent:"):
            return agent_id[len("h-agent:"):]
        return agent_id

    def transform_event(self, event):
        return None

    async def invoke(
        self,
        prompt: str,
        thread_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[AnimalMessage, None]:
        """
        Invoke an h-agent team agent via SSE streaming.

        Sends POST to /api/agents/{agent_id}/message and parses SSE stream.

        Args:
            prompt: The input prompt/message
            thread_id: The thread/session identifier

        Yields:
            AnimalMessage instances from the SSE streaming response
        """
        agent_id = self._get_agent_id()
        url = f"{self.base_url}/api/agents/{agent_id}/message"

        payload = {
            "message": prompt,
            "session_id": thread_id,
        }

        timeout = max(1, self._timeout or 300)

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status_code != 200:
                        text = await response.aread()
                        yield self.create_message(
                            content=f"h-agent API error: HTTP {response.status_code}",
                            message_type="error",
                            metadata={"source": "h-agent", "status_code": response.status_code},
                            is_complete=True,
                        )
                        return

                    accumulated = ""
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue

                        if line.startswith("event:"):
                            continue

                        if line.startswith("data:"):
                            data_str = line[len("data:"):].strip()
                            if not data_str:
                                continue

                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue

                            if "token" in data:
                                token = data["token"]
                                accumulated += token
                                yield self.create_message(
                                    content=token,
                                    message_type="text",
                                    metadata={"source": "h-agent", "event": "token"},
                                    is_complete=False,
                                )
                            elif "error" in data:
                                yield self.create_message(
                                    content=f"h-agent error: {data['error']}",
                                    message_type="error",
                                    metadata={"source": "h-agent", "error": data["error"]},
                                    is_complete=True,
                                )
                                return
                            elif data.get("done"):
                                yield self.create_message(
                                    content="",
                                    message_type="complete",
                                    metadata={"source": "h-agent", "event": "end"},
                                    is_complete=True,
                                )
                                return

        except httpx.ConnectError:
            yield self.create_message(
                content=f"Cannot connect to h-agent at {self.base_url}. "
                        f"Please ensure h-agent is running on port 8080.",
                message_type="error",
                metadata={"source": "h-agent", "error": "connection_error"},
                is_complete=True,
            )
        except httpx.TimeoutException:
            yield self.create_message(
                content=f"h-agent request timed out after {timeout}s.",
                message_type="error",
                metadata={"source": "h-agent", "error": "timeout"},
                is_complete=True,
            )
        except Exception as e:
            yield self.create_message(
                content=f"h-agent error: {str(e)}",
                message_type="error",
                metadata={"source": "h-agent", "error": str(e)},
                is_complete=True,
            )


HAgentAgentService = HAgentService
