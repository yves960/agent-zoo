"""H-Agent HTTP Client - Discovers agents from a running h-agent instance."""

from dataclasses import dataclass
from typing import List, Optional

import requests


@dataclass
class HAgentInfo:
    """Information about a single agent from h-agent."""
    id: str
    name: str
    role: str
    description: str
    team: Optional[str]


class HAgentClient:
    """HTTP client for discovering agents from h-agent."""

    DEFAULT_BASE_URL = "http://localhost:8080"
    API_AGENTS_ENDPOINT = "/api/agents"
    TIMEOUT_SECONDS = 5

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the h-agent client.

        Args:
            base_url: Base URL for h-agent. Defaults to http://localhost:8080.
        """
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self._agents_cache: Optional[List[HAgentInfo]] = None

    def is_running(self) -> bool:
        """
        Check if h-agent is running and responsive.

        Returns:
            True if h-agent is reachable, False otherwise.
        """
        try:
            response = requests.get(
                self.base_url + self.API_AGENTS_ENDPOINT,
                timeout=self.TIMEOUT_SECONDS,
            )
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def fetch_agents(self, force_refresh: bool = False) -> List[HAgentInfo]:
        """
        Fetch agent list from h-agent.

        Args:
            force_refresh: Force fetch even if cached. Defaults to False.

        Returns:
            List of HAgentInfo. Returns empty list if h-agent is not running
            or request fails.
        """
        if self._agents_cache is not None and not force_refresh:
            return self._agents_cache

        try:
            response = requests.get(
                self.base_url + self.API_AGENTS_ENDPOINT,
                timeout=self.TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("success"):
                self._agents_cache = []
                return []

            agents = []
            for agent_data in data.get("agents", []):
                agents.append(
                    HAgentInfo(
                        id=agent_data.get("id", ""),
                        name=agent_data.get("name", ""),
                        role=agent_data.get("role", ""),
                        description=agent_data.get("description", ""),
                        team=agent_data.get("team"),
                    )
                )
            self._agents_cache = agents
            return agents

        except (requests.ConnectionError, requests.Timeout, requests.RequestException):
            self._agents_cache = []
            return []

    def get_agent(self, agent_id: str) -> Optional[HAgentInfo]:
        """
        Get a specific agent by ID.

        Args:
            agent_id: The agent ID to look up.

        Returns:
            HAgentInfo if found, None otherwise.
        """
        agents = self.fetch_agents()
        for agent in agents:
            if agent.id == agent_id:
                return agent
        return None

    def clear_cache(self) -> None:
        """Clear the cached agent list."""
        self._agents_cache = None
