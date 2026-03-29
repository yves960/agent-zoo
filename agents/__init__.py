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
    possible_paths = [
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

# Lazy-loaded agents (deferred to avoid blocking import on slow CLI calls)
# Use _lazy_* flags to ensure we only load once
_lazy_session_agents_loaded = False
_lazy_h_agent_agents_loaded = False
_lazy_session_agents = []
_lazy_h_agent_agents = []


def _ensure_lazy_agents_loaded():
    """Load OpenCode sessions and h-agent agents lazily (only when first accessed)."""
    global _lazy_session_agents_loaded, _lazy_h_agent_agents_loaded
    global _lazy_session_agents, _lazy_h_agent_agents

    if _lazy_session_agents_loaded and _lazy_h_agent_agents_loaded:
        return

    # Import inside function to avoid circular import at module load time
    from services.agent_loader import load_h_agent_agents, load_opencode_sessions
    from agents.opencode_service import OpenCodeService
    from agents.h_agent_service import HAgentService

    # Load OpenCode sessions (can be slow - subprocess call)
    if not _lazy_session_agents_loaded:
        try:
            _lazy_session_agents = load_opencode_sessions()
        except Exception as e:
            print(f"Warning: Failed to load OpenCode sessions: {e}")
            _lazy_session_agents = []
        _lazy_session_agents_loaded = True

    # Register opencode-session agents with OpenCodeService
    for agent_config in _lazy_session_agents:
        _agents_config.agents.append(agent_config)
        registry.register_config(agent_config)
        registry.register_class(agent_config.id, OpenCodeService)

    # Load h-agent agents
    if not _lazy_h_agent_agents_loaded:
        try:
            _lazy_h_agent_agents = load_h_agent_agents()
        except Exception as e:
            print(f"Warning: Failed to load h-agent agents: {e}")
            _lazy_h_agent_agents = []
        _lazy_h_agent_agents_loaded = True

    # h-agent agents are registered inside load_h_agent_agents()
    _agents_config.agents.extend(_lazy_h_agent_agents)

    # Register h-agent agents with HAgentService via the h-agent HTTP API on port 8080
    from agents.h_agent_service import HAgentService
    for agent_config in _lazy_h_agent_agents:
        registry.register_config(agent_config)
        registry.register_class(agent_config.id, HAgentService)


# Directory-scanned agents - loaded lazily
_lazy_dir_agents_loaded = False


def _load_directory_agents():
    """Scan directories for agent configs and add them as READ-ONLY virtual agents."""
    global _lazy_dir_agents_loaded
    if _lazy_dir_agents_loaded:
        return
    _lazy_dir_agents_loaded = True

    try:
        from services.directory_scanner import DirectoryScanner
        from core.agent_config import AgentSource, AgentCapabilities, PersonalityConfig

        scanner = DirectoryScanner()
        discovered_agents = scanner.scan()
        for discovered in discovered_agents:
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
    except Exception as e:
        print(f"Warning: Failed to load directory agents: {e}")


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
    _ensure_lazy_agents_loaded()
    _load_directory_agents()
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
