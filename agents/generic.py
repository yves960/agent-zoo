"""
Generic Agent Service - Dynamically handles any Agent from config.

Supports opencode, claude, crush tools based on AgentConfig.
"""

import asyncio
import json
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from services.cli_spawner import CLISpawner
from core.agent_config import AgentConfig, AgentTool
from .base import AnimalMessage, AnimalService

# ANSI escape code stripper
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class GenericAgentService(AnimalService):
    """
    Generic Agent Service - dynamically handles any agent from config.
    
    Reads tool, model, args from AgentConfig and routes to the appropriate
    CLI handler at runtime.
    """

    def __init__(self, agent_config: AgentConfig, config: Optional[Dict[str, Any]] = None):
        """
        Initialize GenericAgentService with an AgentConfig.
        
        Args:
            agent_config: AgentConfig instance from core/agent_config.py
            config: Optional override config dict (merged with agent_config)
        """
        animal_id = agent_config.id
        merged = {**agent_config.capabilities.model_dump(), **(config or {})}
        super().__init__(animal_id, merged)
        self.agent_config = agent_config
        self._tool = AgentTool(agent_config.capabilities.tool.value)
        self._model = agent_config.capabilities.model
        self._timeout = agent_config.capabilities.timeout
        self._raw_args: List[str] = list(agent_config.capabilities.args)

    def get_cli_command(self) -> Tuple[str, List[str]]:
        """
        Build CLI command from agent config.
        
        Resolves {{model}} in args with the configured model.
        """
        tool_map = {
            AgentTool.OPENCODE: "opencode",
            AgentTool.CLAUDE: "claude",
            AgentTool.CRUSH: "crush",
            AgentTool.OPENAI: "openai",
        }
        command = tool_map.get(self._tool, "opencode")
        
        # Resolve {{model}} in args
        resolved_args = [arg.replace("{{model}}", self._model) for arg in self._raw_args]
        
        return (command, resolved_args)

    def transform_event(self, event: Union[str, Dict[str, Any]]) -> Optional[AnimalMessage]:
        """
        Transform raw CLI output to AnimalMessage.
        
        Handles different formats based on tool type:
        - opencode/crush: plain text line by line
        - claude: NDJSON with {"type": ...} structure
        """
        tool = self._tool

        if tool == AgentTool.CLAUDE:
            return self._transform_claude_event(event)
        else:
            # opencode, crush: plain text
            return self._transform_plain_event(event)

    def _transform_plain_event(self, event: Union[str, Dict[str, Any]]) -> Optional[AnimalMessage]:
        """Transform plain text output (opencode, crush)."""
        if isinstance(event, dict):
            text = event.get("text", event.get("content", ""))
        else:
            text = event

        if not text:
            return None

        text = ANSI_ESCAPE.sub('', str(text))
        if not text.strip():
            return None

        return self.create_message(
            content=text.strip(),
            message_type="text",
            metadata={"source": self._tool.value},
            is_complete=False,
        )

    def _transform_claude_event(self, event: Union[str, Dict[str, Any]]) -> Optional[AnimalMessage]:
        """Transform claude NDJSON output."""
        if isinstance(event, str):
            try:
                event = json.loads(event)
            except json.JSONDecodeError:
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

        event_type = event.get("type", "")

        if event_type == "assistant":
            message_data = event.get("message", {})
            content = ""
            if isinstance(message_data, dict):
                if "content" in message_data:
                    content_parts = message_data["content"]
                    if isinstance(content_parts, list):
                        content = "\n".join(str(p) for p in content_parts)
                    else:
                        content = str(content_parts)
                elif "text" in message_data:
                    content = message_data["text"]

            if content.strip():
                return self.create_message(
                    content=content.strip(),
                    message_type="assistant",
                    metadata={"source": "claude", "event_type": event_type},
                    is_complete=False,
                )

        elif event_type == "message_end":
            return self.create_message(
                content="",
                message_type="complete",
                metadata={"source": "claude", "event_type": event_type},
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
        Invoke the agent via CLI based on configured tool.
        
        Args:
            prompt: The input prompt
            thread_id: Session/thread identifier
            *args: Additional arguments
            **kwargs: Additional keyword arguments
            
        Yields:
            AnimalMessage instances from CLI output
        """
        self.configure(prompt=prompt, thread_id=thread_id)
        cmd, cmd_args = self.get_cli_command()

        # For claude, inject prompt into args
        if self._tool == AgentTool.CLAUDE:
            cmd_args = ["-p", prompt] + cmd_args

        if self.cli_spawner is None:
            self.cli_spawner = CLISpawner(timeout=float(self._timeout))

        queue: asyncio.Queue = asyncio.Queue()

        def on_line(line: str, parsed: Optional[Dict[str, Any]] = None, is_error: bool = False) -> None:
            if is_error:
                queue.put_nowait(self.create_message(
                    content=f"Error: {line}",
                    message_type="error",
                    metadata={"line": line},
                    is_complete=False,
                ))
            else:
                # For claude use parsed NDJSON; for others use raw line
                data = parsed if self._tool == AgentTool.CLAUDE and parsed else line
                transformed = self.transform_event(data)
                if transformed:
                    queue.put_nowait(transformed)

        task = await self.cli_spawner.spawn_cli_process(
            command=cmd,
            args=cmd_args,
            animal_id=self.animal_id,
            on_line=on_line,
            on_error=on_line,
        )

        try:
            while not task.done() or not queue.empty():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield message
                    if message.is_complete:
                        break
                except asyncio.TimeoutError:
                    if task.done():
                        break
                    continue

            # Final completion message if not already sent
            yield self.create_message(
                content="",
                message_type="complete",
                metadata={"complete": True},
                is_complete=True,
            )
        except Exception as e:
            yield self.create_message(
                content=f"Error: {str(e)}",
                message_type="error",
                metadata={"error": str(e)},
                is_complete=True,
            )
