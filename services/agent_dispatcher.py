"""
Agent Dispatcher - Routes messages to agents and streams responses via WebSocket.

Handles:
- @mention parsing from message content
- Random agent selection when no @mentions present
- Invoking agent services and streaming responses
"""

import asyncio
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, AsyncGenerator

from agents.base import AnimalMessage, AnimalService
from agents import get_animal_service, get_animal_services
from core.websocket_manager import WebSocketManager
from utils.a2a_mentions import parse_a2a_mentions


@dataclass
class DispatchResult:
    """Result of dispatching a message to an agent."""
    animal_id: str
    success: bool
    error: Optional[str] = None


class AgentDispatcher:
    """
    Dispatches messages to animal agents and streams responses via WebSocket.
    
    Decision: When no @mentions are present, randomly select one agent to respond.
    """
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self._available_animals = ["xueqiu", "liuliu", "xiaohuang"]
    
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
        print(f"[Dispatcher] dispatch_message called: content={content}, thread_id={thread_id}")
        # Determine target animals
        target_animals = self._resolve_targets(content, mentions)
        print(f"[Dispatcher] Target animals: {target_animals}")

        if not target_animals:
            return []

        # Dispatch to each target animal
        results = []
        for animal_id in target_animals:
            print(f"[Dispatcher] Dispatching to {animal_id}...")
            result = await self._dispatch_to_animal(
                animal_id=animal_id,
                content=content,
                thread_id=thread_id,
                exclude_connection_id=exclude_connection_id,
            )
            print(f"[Dispatcher] Result from {animal_id}: success={result.success}, error={result.error}")
            results.append(result)

        return results
    
    def _resolve_targets(
        self,
        content: str,
        mentions: Optional[List[str]]
    ) -> List[str]:
        """
        Resolve target animals from mentions or random selection.
        
        Decision: Random agent when no @mentions.
        """
        # Try parsing @mentions from content
        parsed_mentions = parse_a2a_mentions(content, current_animal="user")
        
        if parsed_mentions:
            return parsed_mentions
        
        # Fall back to provided mentions
        if mentions:
            return mentions
        
        # Random selection (one agent)
        return [random.choice(self._available_animals)]
    
    async def _dispatch_to_animal(
        self,
        animal_id: str,
        content: str,
        thread_id: str,
        exclude_connection_id: Optional[str],
    ) -> DispatchResult:
        """Dispatch to a single animal and stream response."""
        print(f"[Dispatcher] _dispatch_to_animal({animal_id}): starting...")
        try:
            # Get animal service
            try:
                service = get_animal_service(animal_id)
                print(f"[Dispatcher] Got service for {animal_id}")
            except ValueError as e:
                print(f"[Dispatcher] Failed to get service for {animal_id}: {e}")
                return DispatchResult(
                    animal_id=animal_id,
                    success=False,
                    error=str(e),
                )

            # Stream messages from agent
            message_count = 0
            async for message in service.invoke(content, thread_id):
                message_count += 1
                print(f"[Dispatcher] Message #{message_count} from {animal_id}: {message.content[:100]}")
                await self._broadcast_message(
                    animal_id=animal_id,
                    content=message.content,
                    message_type=message.message_type,
                    thread_id=thread_id,
                    exclude_connection_id=exclude_connection_id,
                )

            print(f"[Dispatcher] Received {message_count} messages from {animal_id}")

            # Send completion indicator
            await self._broadcast_done(
                animal_id=animal_id,
                thread_id=thread_id,
                exclude_connection_id=exclude_connection_id,
            )

            return DispatchResult(animal_id=animal_id, success=True)

        except Exception as e:
            import traceback
            print(f"[Dispatcher] Exception in _dispatch_to_animal({animal_id}): {e}")
            traceback.print_exc()
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
    
    async def _broadcast_message(
        self,
        animal_id: str,
        content: str,
        message_type: str,
        thread_id: str,
        exclude_connection_id: Optional[str],
    ) -> None:
        """Broadcast agent message via WebSocket."""
        if not content:
            return
            
        message = {
            "type": "message",
            "animal_id": animal_id,
            "content": content,
            "message_type": message_type,
            "thread_id": thread_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Broadcast to all active connections (users need to see animal responses)
        sent = await self.ws_manager.broadcast_to_all(
            message=message,
            exclude_connection_id=None,  # Don't exclude anyone
        )
        print(f"[Dispatcher] broadcast_to_all sent={sent}")
    
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
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self.ws_manager.broadcast_to_animal(
            animal_id=animal_id,
            message=message,
            exclude_connection_id=exclude_connection_id,
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
