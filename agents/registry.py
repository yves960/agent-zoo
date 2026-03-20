"""
Agent Registry for Zoo Multi-Agent System.

Provides a registry pattern for dynamic agent registration and retrieval.
"""

from typing import Dict, List, Optional, Type

from .base import AnimalService
from .config import AgentConfig


class AgentRegistry:
    """
    Registry for managing animal agent services.
    
    Implements the registry pattern for dynamic agent loading with:
    - Service class registration
    - Configuration management
    - Instance caching
    """
    
    def __init__(self) -> None:
        self._service_classes: Dict[str, Type[AnimalService]] = {}
        self._configs: Dict[str, AgentConfig] = {}
        self._instances: Dict[str, AnimalService] = {}
    
    def register_class(self, animal_id: str, service_class: Type[AnimalService]) -> None:
        """
        Register a service class for an animal.
        
        Args:
            animal_id: Unique identifier for the animal
            service_class: The AnimalService subclass to register
        """
        self._service_classes[animal_id] = service_class
        # Clear cached instance if class is re-registered
        if animal_id in self._instances:
            del self._instances[animal_id]
    
    def register_config(self, config: AgentConfig) -> None:
        """
        Register a configuration for an animal.
        
        Supports both:
        - agents.config.AgentConfig (animal_id field)
        - core.agent_config.AgentConfig (id field)
        """
        # Handle both config types - use id if available, otherwise animal_id
        config_id = getattr(config, "id", None) or getattr(config, "animal_id", None)
        if config_id is None:
            raise ValueError(f"Config has no 'id' or 'animal_id' field: {config}")
        self._configs[config_id] = config
    
    def get_service(self, animal_id: str) -> Optional[AnimalService]:
        """
        Get a service instance for an animal (factory with caching).
        
        Args:
            animal_id: Unique identifier for the animal
            
        Returns:
            AnimalService instance or None if not registered
        """
        # Return cached instance if available
        if animal_id in self._instances:
            return self._instances[animal_id]
        
        # Get service class
        service_class = self._service_classes.get(animal_id)
        if service_class is None:
            return None
        
        # Get config for this agent
        config = self._configs.get(animal_id)
        
        # Create new instance:
        # - If GenericAgentService: pass agent_config= (the Pydantic model)
        # - Otherwise (legacy services): pass animal_id= and config={}
        import inspect
        sig = inspect.signature(service_class.__init__)
        if "agent_config" in sig.parameters:
            instance = service_class(agent_config=config)
        else:
            instance = service_class(animal_id=animal_id, config={})
        
        self._instances[animal_id] = instance
        return instance
    
    def get_config(self, animal_id: str) -> Optional[AgentConfig]:
        """
        Get configuration for an animal.
        
        Args:
            animal_id: Unique identifier for the animal
            
        Returns:
            AgentConfig or None if not registered
        """
        return self._configs.get(animal_id)
    
    def get_all_animal_ids(self) -> List[str]:
        """
        Get all registered animal IDs.
        
        Returns:
            List of animal_id strings
        """
        return list(self._service_classes.keys())
    
    def get_all_services(self) -> Dict[str, AnimalService]:
        """
        Get all registered service instances.
        
        Returns:
            Dictionary mapping animal_id to service instance
        """
        return {
            animal_id: service
            for animal_id in self.get_all_animal_ids()
            if (service := self.get_service(animal_id)) is not None
        }
    
    def clear_cache(self) -> None:
        """Clear all cached instances."""
        self._instances.clear()
    
    def unregister(self, animal_id: str) -> bool:
        """
        Unregister an animal completely.
        
        Args:
            animal_id: Unique identifier for the animal
            
        Returns:
            True if animal was registered, False otherwise
        """
        removed = False
        if animal_id in self._service_classes:
            del self._service_classes[animal_id]
            removed = True
        if animal_id in self._configs:
            del self._configs[animal_id]
        if animal_id in self._instances:
            del self._instances[animal_id]
        return removed


# Global registry instance
registry = AgentRegistry()