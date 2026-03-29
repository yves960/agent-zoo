"""
Animal Service Abstract Base Class for Zoo Multi-Agent System.

Defines the interface for all animal agent services.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from services.cli_spawner import CLISpawner


class AnimalMessage:
    """Represents a message from an animal agent."""
    
    def __init__(
        self,
        animal_id: str,
        content: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        is_complete: bool = False,
    ):
        self.animal_id = animal_id
        self.content = content
        self.message_type = message_type
        self.metadata = metadata or {}
        self.is_complete = is_complete
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "animal_id": self.animal_id,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
            "is_complete": self.is_complete,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnimalMessage":
        """Create message from dictionary."""
        return cls(
            animal_id=data["animal_id"],
            content=data["content"],
            message_type=data.get("message_type", "text"),
            metadata=data.get("metadata", {}),
            is_complete=data.get("is_complete", False),
        )
    
    def __repr__(self) -> str:
        return f"AnimalMessage(animal_id={self.animal_id!r}, content={self.content!r}, type={self.message_type!r})"


class AnimalService(ABC):
    """Abstract base class for all animal agent services."""
    
    def __init__(self, animal_id: str, config: Dict[str, Any]):
        self.animal_id = animal_id
        self.config = config
        self.cli_spawner = None
        self.prompt: str = ""
        self.thread_id: str = ""
    
    def configure(
        self, prompt: str, thread_id: str, cli_spawner: Optional["CLISpawner"] = None
    ) -> None:
        """Configure the service with prompt and session info."""
        self.prompt = prompt
        self.thread_id = thread_id
        self.cli_spawner = cli_spawner
    
    @abstractmethod
    async def invoke(
        self,
        prompt: str,
        thread_id: str,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Invoke the animal agent with a prompt.
        
        Args:
            prompt: The input prompt
            thread_id: Session/thread identifier
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Yields:
            AnimalMessage instances from the agent's output
        """
        pass
    
    @abstractmethod
    def get_cli_command(self) -> Tuple[str, List[str]]:
        """
        Get the CLI command and arguments for this animal.
        
        Returns:
            Tuple of (command, args list)
        """
        pass
    
    @abstractmethod
    def transform_event(
        self, event: Union[str, Dict[str, Any]]
    ) -> Optional[AnimalMessage]:
        """
        Transform raw event/output to AnimalMessage.
        
        Args:
            event: Raw event from CLI (string or parsed NDJSON dict)
            
        Returns:
            AnimalMessage or None if event should be skipped
        """
        pass
    
    def create_message(
        self,
        content: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        is_complete: bool = False,
    ) -> AnimalMessage:
        """Helper to create an AnimalMessage."""
        return AnimalMessage(
            animal_id=self.animal_id,
            content=content,
            message_type=message_type,
            metadata=metadata or {},
            is_complete=is_complete,
        )
    
    def get_animal_type(self) -> str:
        """Get the animal type name."""
        return self.animal_id
    
    async def __aenter__(self) -> "AnimalService":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        pass
