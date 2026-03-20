"""Agent configuration loader service."""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import ValidationError

from core.agent_config import AgentCapabilities, AgentConfig, AgentsConfig, AgentTool


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
