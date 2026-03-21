"""
Xiaohuang Service - 小黄 (虎皮黄绿鹦鹉) - 视觉设计 - crush CLI
"""

import asyncio
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from services.cli_spawner import CLISpawner
from .base import AnimalMessage, AnimalService

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class XiaohuangService(AnimalService):
    """
    小黄 - 虎皮鹦鹉(黄绿) - 视觉设计 - crush CLI
    
    Features:
    - Visual design specialist
    - Uses crush CLI with zhipu/glm-4.5 model
    - Outputs plain text line by line
    """
    
    def __init__(self, animal_id: str = "xiaohuang", config: Optional[Dict[str, Any]] = None):
        super().__init__(animal_id, config or {})
        self.config.setdefault("model", "zhipu/glm-4.5")
        self.config.setdefault("timeout", 300.0)
    
    def get_cli_command(self) -> tuple[str, list[str]]:
        """Get CLI command for crush."""
        command = "crush"
        args = ["run", "-m", self.config["model"], self.prompt]
        return (command, args)
    
    def transform_event(self, event: str | Dict[str, Any]) -> Optional[AnimalMessage]:
        """
        Transform crush output to AnimalMessage.
        
        crush outputs plain text.
        Wrap plain text in message format.
        """
        if isinstance(event, dict):
            # If event is a dict, try to extract text
            text = event.get("text", event.get("content", event.get("message", "")))
        else:
            text = event
        
        if not text or str(text).strip() == "":
            return None
        
        return self.create_message(
            content=str(text).strip(),
            message_type="text",
            metadata={
                "source": "crush",
                "model": self.config.get("model", "zhipu/glm-4.5"),
            },
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
        Invoke xiaohuang with prompt via CLI.
        
        Args:
            prompt: The input prompt
            thread_id: Session/thread identifier
            *args: Additional arguments
            **kwargs: Additional keyword arguments
            
        Yields:
            AnimalMessage instances from crush output
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
            error_msg = self.create_message(
                content=f"Error: {str(e)}",
                message_type="error",
                metadata={"error": str(e)},
                is_complete=True,
            )
            yield error_msg
