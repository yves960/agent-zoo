"""
Xueqiu Service - 雪球 (雪纳瑞) - 主架构师 - opencode CLI
"""

import asyncio
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from services.cli_spawner import CLISpawner
from .base import AnimalMessage, AnimalService

# ANSI escape code stripper
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class XueqiuService(AnimalService):
    """
    雪球 - 雪纳瑞 - 主架构师 - opencode CLI
    
    Features:
    - Main architect agent
    - Uses opencode CLI with claude-opus-4 model
    - Outputs plain text (line by line)
    """
    
    def __init__(self, animal_id: str = "xueqiu", config: Optional[Dict[str, Any]] = None):
        super().__init__(animal_id, config or {})
        self.config.setdefault("model", "minimax/MiniMax-M2.7")
        self.config.setdefault("timeout", 300.0)
    
    def get_cli_command(self) -> tuple[str, list[str]]:
        """Get CLI command for opencode."""
        command = "opencode"
        args = ["run", "-m", self.config["model"], self.prompt]
        return (command, args)
    
    def transform_event(self, event: str | Dict[str, Any]) -> Optional[AnimalMessage]:
        """
        Transform opencode output to AnimalMessage.
        
        opencode outputs plain text line by line.
        """
        if isinstance(event, dict):
            # If event is parsed NDJSON, extract text
            text = event.get("text", event.get("content", ""))
        else:
            text = event
        
        if not text:
            return None
        
        # Strip ANSI escape codes
        text = ANSI_ESCAPE.sub('', text)
        
        if not text.strip():
            return None
        
        return self.create_message(
            content=text.strip(),
            message_type="text",
            metadata={"source": "opencode"},
            is_complete=False,
        )
    
    async def invoke(
        self,
        prompt: str,
        thread_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> AsyncGenerator[AnimalMessage, None]:
        """
        Invoke xueqiu with prompt via CLI.
        
        Args:
            prompt: The input prompt
            thread_id: Session/thread identifier
            *args: Additional arguments
            **kwargs: Additional keyword arguments
            
        Yields:
            AnimalMessage instances from opencode output
        """
        # Configure this instance
        self.configure(prompt=prompt, thread_id=thread_id)
        
        # Get CLI command
        cmd, cmd_args = self.get_cli_command()
        
        # Create spawner if not available
        if self.cli_spawner is None:
            self.cli_spawner = CLISpawner(timeout=self.config.get("timeout", 300.0))
        
        def on_line(line: str, parsed: Optional[Dict[str, Any]] = None, is_error: bool = False) -> None:
            """Callback for each line of output."""
            clean_line = ANSI_ESCAPE.sub('', line)
            
            if is_error:
                message = self.create_message(
                    content=f"Error: {clean_line}",
                    message_type="error",
                    metadata={"line": clean_line},
                    is_complete=False,
                )
                queue.put_nowait(message)
            else:
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
                except asyncio.TimeoutError:
                    if task.done():
                        break
                    continue
            
            # Check for final completion
            final_msg = self.create_message(
                content="",
                message_type="complete",
                metadata={"complete": True},
                is_complete=True,
            )
            yield final_msg
            
        except Exception as e:
            final_msg = self.create_message(
                content=f"Error: {str(e)}",
                message_type="error",
                metadata={"error": str(e)},
                is_complete=True,
            )
            yield final_msg
