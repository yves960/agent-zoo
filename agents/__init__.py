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

# Load OpenCode sessions and h-agent agents
from services.agent_loader import load_h_agent_agents, load_opencode_sessions
from agents.opencode_service import OpenCodeService
from agents.h_agent_service import HAgentService

session_agents = load_opencode_sessions()
h_agent_agents = load_h_agent_agents()

# Register opencode-session agents with OpenCodeService so they can be invoked
# via the opencode serve HTTP API on port 4096
for agent_config in session_agents:
    _agents_config.agents.append(agent_config)
    registry.register_config(agent_config)
    registry.register_class(agent_config.id, OpenCodeService)

# h-agent agents are registered inside load_h_agent_agents()
_agents_config.agents.extend(h_agent_agents)

# Register h-agent agents with HAgentService via the h-agent HTTP API on port 8080
for agent_config in h_agent_agents:
    registry.register_config(agent_config)
    registry.register_class(agent_config.id, HAgentService)

# Scan directories for agent configs and add them as READ-ONLY virtual agents
from services.directory_scanner import DirectoryScanner
from core.agent_config import AgentSource, AgentCapabilities, PersonalityConfig

scanner = DirectoryScanner()
discovered_agents = scanner.scan()
for discovered in discovered_agents:
    # Use config dict to build AgentConfig, with defaults for missing fields
    config_data = discovered.config or {}
    agent_config = AgentConfig(
        id=discovered.agent_id,
        name=discovered.name,
        species=config_data.get("species", "directory"),
        description=config_data.get("description", f"Agent from {discovered.config_path}"),
        color=config_data.get("color", "#4A90A4"),
        mention_patterns=config_data.get("mention_patterns", [f"@{discovered.name}"]),
        enabled=True,
        personality=PersonalityConfig(**config_data["personality"]) if config_data.get("personality") else None,
        capabilities=AgentCapabilities(**config_data["capabilities"]) if config_data.get("capabilities") else AgentCapabilities(),
        source=AgentSource.DIRECTORY,
    )
    _agents_config.agents.append(agent_config)


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
