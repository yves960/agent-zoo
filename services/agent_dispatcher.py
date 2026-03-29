"""
Agent Dispatcher - Routes messages to agents and streams responses via WebSocket.

Handles:
- @mention parsing from message content
- All enabled agents receive messages when no @mentions present
- Invoking agent services and streaming responses
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, AsyncGenerator

from agents.base import AnimalMessage, AnimalService
from agents import get_animal_service, get_animal_services, get_agents_config
from core.websocket_manager import WebSocketManager
from utils.a2a_mentions import parse_a2a_mentions

logger = logging.getLogger("dispatcher")


@dataclass
class DispatchResult:
    """Result of dispatching a message to an agent."""
    animal_id: str
    success: bool
    error: Optional[str] = None


class AgentDispatcher:
    """
    Dispatches messages to animal agents and streams responses via WebSocket.
    
    When no @mentions are present, all enabled agents receive the message
    and each decides whether to respond.
    """
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
    
    async def dispatch_message(
        self,
        content: str,
        thread_id: str,
        mentions: Optional[List[str]] = None,
        exclude_connection_id: Optional[str] = None,
    ) -> List[DispatchResult]:
        """
        Dispatch message to target agents.

        Args:
            content: Message content
            thread_id: Conversation thread ID
            mentions: Optional list of animal_ids to route to (from @mentions)
            exclude_connection_id: WebSocket connection to exclude from broadcasts

        Returns:
            List of dispatch results
        """
        logger.debug("dispatch_message called: content=%s, thread_id=%s", content, thread_id)
        target_animals = self._resolve_targets(content, mentions)
        logger.debug("Target animals: %s", target_animals)

        if not target_animals:
            return []

        # Dispatch to each target animal in parallel with timeout
        async def dispatch_with_timeout(animal_id: str) -> DispatchResult:
            try:
                return await asyncio.wait_for(
                    self._dispatch_to_animal(
                        animal_id=animal_id,
                        content=content,
                        thread_id=thread_id,
                        mentions=mentions,
                        exclude_connection_id=exclude_connection_id,
                    ),
                    timeout=30.0  # 30 second timeout per agent
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout for %s, skipping...", animal_id)
                return DispatchResult(animal_id=animal_id, success=False, error="Timeout")
            except Exception as e:
                logger.error("Exception for %s: %s", animal_id, e)
                return DispatchResult(animal_id=animal_id, success=False, error=str(e))

        # Dispatch all agents in parallel
        results = await asyncio.gather(*[dispatch_with_timeout(aid) for aid in target_animals])
        
        for result in results:
            logger.debug("Result from %s: success=%s, error=%s", result.animal_id, result.success, result.error)

        return list(results)
    
    def _resolve_targets(
        self,
        content: str,
        mentions: Optional[List[str]],
        thread_id: Optional[str] = None,
    ) -> List[str]:
        parsed_mentions = parse_a2a_mentions(content, current_animal="user")
        logger.debug("_resolve_targets: content=%s, mentions=%s, parsed_mentions=%s", content, mentions, parsed_mentions)
        if parsed_mentions:
            logger.debug("Using parsed_mentions: %s", parsed_mentions)
            return parsed_mentions
        if mentions:
            logger.debug("Using mentions param: %s", mentions)
            return mentions
        enabled = [agent.id for agent in get_agents_config().get_enabled_agents()]
        logger.debug("Using all enabled agents: %s", enabled)
        return enabled
    
    async def _dispatch_to_animal(
        self,
        animal_id: str,
        content: str,
        thread_id: str,
        mentions: Optional[List[str]],
        exclude_connection_id: Optional[str],
    ) -> DispatchResult:
        """Dispatch to a single animal and stream response."""
        logger.debug("_dispatch_to_animal(%s): starting...", animal_id)
        try:
            try:
                service = get_animal_service(animal_id)
                logger.debug("Got service for %s", animal_id)
            except ValueError as e:
                logger.error("Failed to get service for %s: %s", animal_id, e)
                return DispatchResult(
                    animal_id=animal_id,
                    success=False,
                    error=str(e),
                )

            accumulated_content = ""
            accumulated_message_type = "text"
            message_count = 0
            BATCH_THRESHOLD = 100

            async for message in service.invoke(content, thread_id):
                message_count += 1
                accumulated_content += message.content
                accumulated_message_type = message.message_type

                should_flush = (
                    message.message_type in ("complete", "error") or
                    len(accumulated_content) >= BATCH_THRESHOLD
                )

                if should_flush and accumulated_content:
                    logger.debug("Batch broadcast from %s: %s", animal_id, accumulated_content[:100])
                    await self._broadcast_message(
                        animal_id=animal_id,
                        content=accumulated_content,
                        message_type=accumulated_message_type,
                        thread_id=thread_id,
                        mentions=mentions,
                        exclude_connection_id=exclude_connection_id,
                    )
                    accumulated_content = ""
                    accumulated_message_type = "text"

            if accumulated_content:
                logger.debug("Final broadcast from %s: %s", animal_id, accumulated_content[:100])
                await self._broadcast_message(
                    animal_id=animal_id,
                    content=accumulated_content,
                    message_type=accumulated_message_type,
                    thread_id=thread_id,
                    mentions=mentions,
                    exclude_connection_id=exclude_connection_id,
                )
                accumulated_content = ""

            logger.debug("Received %d messages from %s", message_count, animal_id)
            await self._broadcast_done(
                animal_id=animal_id,
                thread_id=thread_id,
                exclude_connection_id=exclude_connection_id,
            )
            return DispatchResult(animal_id=animal_id, success=True)

        except Exception as e:
            import traceback
            logger.exception("Exception in _dispatch_to_animal(%s): %s", animal_id, e)
            await self._broadcast_error(
                animal_id=animal_id,
                error=str(e),
                thread_id=thread_id,
                exclude_connection_id=exclude_connection_id,
            )
            return DispatchResult(
                animal_id=animal_id,
                success=False,
                error=str(e),
            )
    
    INTERNAL_MESSAGE_TYPES = {"thinking", "reasoning", "tool_call", "internal", "metadata", "start", "complete"}

    async def _broadcast_message(
        self,
        animal_id: str,
        content: str,
        message_type: str,
        thread_id: str,
        mentions: Optional[List[str]],
        exclude_connection_id: Optional[str],
    ) -> None:
        logger.debug("_broadcast_message called: animal_id=%s, content=%s, message_type=%s, thread_id=%s", 
                     animal_id, content[:30] if content else "", message_type, thread_id)
        if not content:
            logger.debug("_broadcast_message: content empty, returning")
            return
        if message_type in self.INTERNAL_MESSAGE_TYPES:
            logger.debug("_broadcast_message: message_type %s is internal, returning", message_type)
            return

        message = {
            "type": "message",
            "animal_id": animal_id,
            "content": content,
            "message_type": message_type,
            "thread_id": thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "private": mentions is not None and len(mentions) == 1,
        }

        logger.debug("_broadcast_message: calling broadcast_to_session for thread_id=%s", thread_id)
        sent = await self.ws_manager.broadcast_to_session(
            session_id=thread_id,
            message=message,
            exclude_connection_id=None,
        )
        logger.debug("broadcast_to_session(%s) sent=%s", thread_id, sent)
    
    async def _broadcast_done(
        self,
        animal_id: str,
        thread_id: str,
        exclude_connection_id: Optional[str],
    ) -> None:
        """Broadcast completion indicator."""
        message = {
            "type": "done",
            "animal_id": animal_id,
            "thread_id": thread_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        sent = await self.ws_manager.broadcast_to_session(
            session_id=thread_id,
            message=message,
            exclude_connection_id=None,
        )
    
    async def _broadcast_error(
        self,
        animal_id: str,
        error: str,
        thread_id: str,
        exclude_connection_id: Optional[str],
    ) -> None:
        """Broadcast error message."""
        message = {
            "type": "error",
            "animal_id": animal_id,
            "content": f"Agent {animal_id} error: {error}",
            "thread_id": thread_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self.ws_manager.broadcast_to_animal(
            animal_id=animal_id,
            message=message,
            exclude_connection_id=exclude_connection_id,
        )


def create_agent_dispatcher(ws_manager: WebSocketManager) -> AgentDispatcher:
    """Factory function to create an AgentDispatcher."""
    return AgentDispatcher(ws_manager=ws_manager)
