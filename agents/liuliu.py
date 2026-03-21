"""
Liuliu Service - 六六 (虎皮蓝鹦鹉) - Code Review - claude CLI
"""

import asyncio
import json
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from services.cli_spawner import CLISpawner
from .base import AnimalMessage, AnimalService

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class LiuliuService(AnimalService):
    """
    六六 - 虎皮鹦鹉(蓝) - Code Review - claude CLI
    
    Features:
    - Code review specialist
    - Uses claude CLI with NDJSON output
    - Handles {"type":"assistant",...} format
    """
    
    def __init__(self, animal_id: str = "liuliu", config: Optional[Dict[str, Any]] = None):
        super().__init__(animal_id, config or {})
        self.config.setdefault("model", "claude-3-5-sonnet")
        self.config.setdefault("timeout", 300.0)
    
    def get_cli_command(self) -> tuple[str, list[str]]:
        """Get CLI command for claude."""
        command = "claude"
        args = [
            "-p", self.prompt,
            "--output-format", "stream-json"
        ]
        return (command, args)
    
    def transform_event(self, event: str | Dict[str, Any]) -> Optional[AnimalMessage]:
        """
        Transform claude NDJSON output to AnimalMessage.
        
        Handles format: {"type":"assistant","message":{...}}
        """
        if isinstance(event, str):
            # Try to parse as NDJSON
            try:
                event = json.loads(event)
            except json.JSONDecodeError:
                # Plain text fallback
                if event.strip():
                    return self.create_message(
                        content=event.strip(),
                        message_type="text",
                        metadata={"source": "claude", "format": "plain"},
                        is_complete=False,
                    )
                return None
        
        if not isinstance(event, dict):
            return None
        
        # Handle different event types
        event_type = event.get("type", "")
        
        if event_type == "assistant":
            message_data = event.get("message", {})
            content = ""
            
            if isinstance(message_data, dict):
                if "content" in message_data:
                    content_parts = message_data["content"]
                    if isinstance(content_parts, list):
                        text_parts = []
                        for p in content_parts:
                            if isinstance(p, dict):
                                if p.get("type") == "text":
                                    text_parts.append(str(p.get("text", "")))
                                elif p.get("type") == "thinking":
                                    pass
                                elif p.get("type") == "tool_use":
                                    pass
                            elif isinstance(p, str):
                                text_parts.append(p)
                        content = "\n".join(text_parts)
                    else:
                        content = str(content_parts)
                elif "text" in message_data:
                    content = message_data["text"]
            
            if content.strip():
                return self.create_message(
                    content=content.strip(),
                    message_type="assistant",
                    metadata={
                        "source": "claude",
                        "event_type": event_type,
                    },
                    is_complete=False,
                )
        
        elif event_type in ("thinking", "tool_call", "tool_use"):
            return None
        
        elif event_type == "message_start":
            return self.create_message(
                content="",
                message_type="start",
                metadata={
                    "source": "claude",
                    "event_type": event_type,
                },
                is_complete=False,
            )
        
        elif event_type == "message_end":
            return self.create_message(
                content="",
                message_type="complete",
                metadata={
                    "source": "claude",
                    "event_type": event_type,
                },
                is_complete=True,
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
        Invoke liuliu with prompt via CLI.
        
        Args:
            prompt: The input prompt
            thread_id: Session/thread identifier
            *args: Additional arguments
            **kwargs: Additional keyword arguments
            
        Yields:
            AnimalMessage instances from claude NDJSON output
        """
        # Configure this instance
        self.configure(prompt=prompt, thread_id=thread_id)
        
        # Get CLI command
        cmd, cmd_args = self.get_cli_command()
        
        # Create spawner if not available
        if self.cli_spawner is None:
            self.cli_spawner = CLISpawner(timeout=self.config.get("timeout", 300.0))
        
        def on_line(line: str, parsed: Optional[Dict[str, Any]] = None, is_error: bool = False) -> None:
            """Callback for each line of NDJSON output."""
            if is_error:
                clean_line = ANSI_ESCAPE.sub('', line)
                message = self.create_message(
                    content=f"Error: {clean_line}" if clean_line else "An error occurred",
                    message_type="error",
                    metadata={"line": clean_line},
                    is_complete=False,
                )
                queue.put_nowait(message)
            else:
                # Use parsed NDJSON or raw line
                transformed = self.transform_event(parsed if parsed is not None else line)
                if transformed:
                    queue.put_nowait(transformed)
        
        # Create queue for streaming messages
        queue: asyncio.Queue = asyncio.Queue()
        
        # Spawn process
        task = await self.cli_spawner.spawn_cli_process(
            command=cmd,
            args=cmd_args,
            animal_id=self.animal_id,
            on_line=on_line,
            on_error=on_line,
        )
        
        try:
            # Stream messages from queue
            while not task.done() or not queue.empty():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield message
                    
                    # Stop if we got a complete message
                    if message.is_complete:
                        break
                except asyncio.TimeoutError:
                    if task.done():
                        break
                    continue
            
        except Exception as e:
            error_msg = self.create_message(
                content=f"Error: {str(e)}",
                message_type="error",
                metadata={"error": str(e)},
                is_complete=True,
            )
            yield error_msg
