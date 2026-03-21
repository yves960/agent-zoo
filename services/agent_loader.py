"""Agent configuration loader service."""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import ValidationError

from core.agent_config import AgentCapabilities, AgentConfig, AgentsConfig, AgentSource, AgentTool


class AgentLoader:
    """Loads and manages agent configurations from YAML files."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the agent loader.

        Args:
            config_path: Path to agents.yaml. Defaults to config/agents.yaml in project root.
        """
        if config_path is None:
            # Default to project root config/agents.yaml
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "agents.yaml"
        self.config_path = Path(config_path)
        self._config: Optional[AgentsConfig] = None

    def load(self, force_reload: bool = False) -> AgentsConfig:
        """
        Load agent configuration from YAML file.

        Args:
            force_reload: Force reload even if already loaded.

        Returns:
            Loaded AgentsConfig instance.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValueError: If config file is invalid.
        """
        if self._config is not None and not force_reload:
            return self._config

        if not self.config_path.exists():
            raise FileNotFoundError(f"Agent config not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)

        if raw_config is None:
            raw_config = {"agents": []}

        try:
            self._config = AgentsConfig(**raw_config)
        except ValidationError as e:
            raise ValueError(f"Invalid agent config: {e}")

        return self._config

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent by ID."""
        config = self.load()
        return config.get_agent(agent_id)

    def get_enabled_agents(self) -> List[AgentConfig]:
        """Get all enabled agents."""
        config = self.load()
        return config.get_enabled_agents()

    def match_agent(self, text: str) -> Optional[AgentConfig]:
        """Match an agent by mention pattern in text."""
        config = self.load()
        return config.match_agent(text)

    def reload(self) -> AgentsConfig:
        """Force reload configuration."""
        return self.load(force_reload=True)

    @property
    def config(self) -> AgentsConfig:
        """Get current configuration (loads if not loaded)."""
        return self.load()


# Global loader instance
_loader: Optional[AgentLoader] = None


def get_agent_loader() -> AgentLoader:
    """Get or create the global agent loader instance."""
    global _loader
    if _loader is None:
        _loader = AgentLoader()
    return _loader


def load_agents() -> AgentsConfig:
    """Convenience function to load agents."""
    return get_agent_loader().load()


def get_agent(agent_id: str) -> Optional[AgentConfig]:
    """Convenience function to get a single agent."""
    return get_agent_loader().get_agent(agent_id)


def match_agent(text: str) -> Optional[AgentConfig]:
    """Convenience function to match an agent by mention text."""
    return get_agent_loader().match_agent(text)


def load_opencode_sessions(
    max_age_days: Optional[int] = 30,
    prefix: str = "opencode-session:",
) -> List[AgentConfig]:
    """
    Load OpenCode sessions as virtual agent configurations.

    These session agents are READ-ONLY (display-only) - they will appear in
    the agents list but cannot be invoked since no service class is registered
    for them.

    Args:
        max_age_days: Only load sessions from the last N days. None to load all.
        prefix: Agent ID prefix for session agents.

    Returns:
        List of AgentConfig objects for OpenCode sessions.
    """
    from datetime import datetime, timedelta, timezone
    from core.agent_config import AgentSource
    from services.opencode_session_discovery import OpenCodeSessionDiscovery

    print("Loading OpenCode sessions...")

    discovery = OpenCodeSessionDiscovery()
    sessions = discovery.fetch_sessions()

    if not sessions:
        print("  No OpenCode sessions found")
        return []

    cutoff_time = None
    if max_age_days is not None:
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    session_agents = []
    for session in sessions:
        # Skip sessions with empty IDs
        if not session.session_id:
            continue

        # Filter by age if specified
        if cutoff_time and session.updated_at:
            try:
                if isinstance(session.updated_at, int):
                    updated = datetime.fromtimestamp(session.updated_at, tz=timezone.utc)
                else:
                    updated = datetime.fromisoformat(session.updated_at.replace("Z", "+00:00"))
                if updated < cutoff_time:
                    continue
            except (ValueError, TypeError, OSError):
                pass

        # Create virtual agent config for this session
        # These are READ-ONLY - no service class will be registered
        agent_config = AgentConfig(
            id=f"{prefix}{session.session_id}",
            name=session.name or f"OpenCode Session {session.session_id[:8]}",
            species="OpenCode会话",
            description=session.directory or f"Session {session.session_id}",
            color="#6B5B95",  # Purple-ish to differentiate from regular agents
            enabled=True,
            capabilities=AgentCapabilities(
                tool=AgentTool.OPENCODE,
                model="virtual",
                timeout=300,
            ),
            personality=None,
            source=AgentSource.OPENCODE_SESSION,
        )
        session_agents.append(agent_config)

    print(f"  Loaded {len(session_agents)} OpenCode session agents")
    return session_agents


def load_h_agent_agents() -> List[AgentConfig]:
    """
    Load agents from a running h-agent instance and register them.

    Creates AgentConfig for each h-agent agent and registers them with the
    global registry. Only loads if h-agent is running (checked via is_running()).
    Does not override agents already registered (local configured agents take precedence).

    Returns:
        List of AgentConfig for successfully registered h-agent agents.
    """
    # Lazy import to avoid circular dependency
    from agents.generic import GenericAgentService
    from agents.registry import registry
    from services.h_agent_client import HAgentClient, HAgentInfo

    print("Loading h-agent agents...")

    client = HAgentClient()

    # Check if h-agent is running
    if not client.is_running():
        print("  h-agent not running, skipping")
        return []

    # Fetch agents from h-agent
    h_agents = client.fetch_agents()
    if not h_agents:
        print("  no h-agent agents found")
        return []

    registered = []
    for h_agent in h_agents:
        # Skip if agent already registered (local takes precedence)
        if registry.get_config(f"h-agent:{h_agent.id}") is not None:
            print(f"  Skipping {h_agent.id} (already registered)")
            continue

        # Create AgentConfig from h-agent agent
        agent_config = _create_agent_config_from_h_agent(h_agent)
        if agent_config is None:
            continue

        # Register config and class
        registry.register_config(agent_config)
        registry.register_class(agent_config.id, GenericAgentService)

        print(f"  Registered h-agent agent: {agent_config.name} ({agent_config.id})")
        registered.append(agent_config)

    print(f"  Loaded {len(registered)} h-agent agents")
    return registered


def _create_agent_config_from_h_agent(h_agent) -> Optional[AgentConfig]:
    """
    Create an AgentConfig from an HAgentInfo.

    Args:
        h_agent: HAgentInfo from h-agent client

    Returns:
        AgentConfig or None if creation fails
    """
    try:
        return AgentConfig(
            id=f"h-agent:{h_agent.id}",
            name=h_agent.name,
            species=h_agent.role or "h-agent",
            description=h_agent.description,
            color="#888888",
            mention_patterns=[f"@{h_agent.name}"],
            enabled=True,
            personality=None,
            source=AgentSource.H_AGENT,
            capabilities=AgentCapabilities(
                tool=AgentTool.OPENCODE,
                model="minimax/MiniMax-M2.7",
                timeout=300,
            ),
        )
    except ValidationError:
        return None
