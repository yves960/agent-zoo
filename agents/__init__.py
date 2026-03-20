"""
Zoo Multi-Agent System - Animal Services Package.

Exports all animal agent services and provides factory functions.
Uses registry pattern for dynamic agent loading from config/agents.yaml.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from core.agent_config import AgentsConfig, AgentConfig
from .base import AnimalMessage, AnimalService
from .generic import GenericAgentService
from .registry import AgentRegistry, registry


def _load_agents_from_yaml() -> AgentsConfig:
    """
    Load agents configuration from config/agents.yaml.
    
    Searches for config/agents.yaml relative to this file's location.
    """
    # Try multiple paths to find config
    possible_paths = [
        Path(__file__).parent.parent / "config" / "agents.yaml",
        Path(__file__).parent.parent / "config" / "agents.yaml",
    ]
    
    # Also check AGENTS_YAML env var
    env_path = os.environ.get("AGENTS_YAML")
    if env_path:
        possible_paths.insert(0, Path(env_path))
    
    for config_path in possible_paths:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return AgentsConfig.model_validate(data)
    
    # Return empty config if no file found
    return AgentsConfig(agents=[])


def _register_agents_from_config(config: AgentsConfig) -> None:
    """
    Dynamically register all enabled agents from config.
    
    All agents use GenericAgentService with their config.
    """
    for agent_config in config.agents:
        if not agent_config.enabled:
            continue
        
        # Register config
        registry.register_config(agent_config)
        
        # Register GenericAgentService class for this agent
        registry.register_class(agent_config.id, GenericAgentService)


# Load config and register agents on module import
_agents_config = _load_agents_from_yaml()
_register_agents_from_config(_agents_config)


def get_animal_service(animal_id: str) -> AnimalService:
    """
    Get a specific animal service by ID.
    
    Args:
        animal_id: The animal identifier (e.g. xueqiu, liuliu, meiqiu)
        
    Returns:
        The configured animal service
        
    Raises:
        ValueError: If animal_id is not found
    """
    service = registry.get_service(animal_id)
    
    if service is None:
        available = registry.get_all_animal_ids()
        raise ValueError(
            f"Unknown animal_id: {animal_id}. "
            f"Available: {available}"
        )
    
    return service


def get_all_animal_services() -> Dict[str, AnimalService]:
    """
    Get all registered animal services.
    
    Returns:
        Dictionary mapping animal_id to service instance
    """
    return registry.get_all_services()


def get_agents_config() -> AgentsConfig:
    """
    Get the raw agents configuration.
    
    Returns:
        The AgentsConfig loaded from config/agents.yaml
    """
    return _agents_config


# Legacy function name for backwards compatibility
get_animal_services = get_all_animal_services


__all__ = [
    # Base classes
    "AnimalMessage",
    "AnimalService",
    # Config
    "AgentConfig",
    "AgentsConfig",
    # Registry
    "AgentRegistry",
    "registry",
    # Generic service
    "GenericAgentService",
    # Factory functions
    "get_animal_service",
    "get_animal_services",
    "get_all_animal_services",
    "get_agents_config",
]
