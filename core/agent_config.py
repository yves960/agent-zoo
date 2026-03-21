"""Agent configuration Pydantic models for Zoo Multi-Agent System."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class AgentTool(str, Enum):
    """Available agent tools."""
    OPENCODE = "opencode"
    CLAUDE = "claude"
    CRUSH = "crush"
    OPENAI = "openai"


class PersonalityConfig(BaseModel):
    """Agent personality and background configuration."""
    traits: List[str] = Field(default_factory=list, description="Personality traits list")
    background: str = Field(default="", description="Agent background story")
    style: str = Field(default="", description="Response style description")
    greetings: List[str] = Field(default_factory=list, description="Greeting messages")


class AgentCapabilities(BaseModel):
    """Agent capabilities configuration."""
    tool: AgentTool = AgentTool.OPENCODE
    model: str = "minimax/MiniMax-M2.7"
    timeout: int = 300
    args: List[str] = Field(default_factory=list)

    @field_validator("args", mode="before")
    @classmethod
    def resolve_args(cls, v: List[str]) -> List[str]:
        """Resolve template variables in args."""
        resolved = []
        for arg in v:
            # 支持 {{model}} 模板变量
            if "{{model}}" in arg:
                # 默认不替换，等待运行时注入
                resolved.append(arg)
            else:
                resolved.append(arg)
        return resolved


class AgentSource(str, Enum):
    """Agent source type."""
    LOCAL = "local"
    H_AGENT = "h-agent"
    DIRECTORY = "directory"
    OPENCODE_SESSION = "opencode-session"
    NETWORK = "network"


class AgentConfig(BaseModel):
    """Single agent configuration."""
    id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Display name")
    species: str = Field(..., description="Agent species/type")
    description: str = Field(default="", description="Agent description")
    color: str = Field(default="#666666", description="Agent color (hex)")
    mention_patterns: List[str] = Field(default_factory=list, description="Patterns to trigger this agent")
    enabled: bool = Field(default=True, description="Whether agent is enabled")
    personality: Optional[PersonalityConfig] = Field(
        default=None, description="Agent personality and background"
    )
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    source: AgentSource = Field(default=AgentSource.LOCAL, description="Agent discovery source")

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate hex color format."""
        if not v.startswith("#") or len(v) not in (4, 7, 9):
            return "#666666"
        return v

    def match_mention(self, text: str) -> bool:
        """Check if text contains any mention pattern."""
        for pattern in self.mention_patterns:
            if pattern.lower() in text.lower():
                return True
        return False

    def resolve_args(self, **kwargs) -> List[str]:
        """Resolve args with provided variables."""
        resolved = []
        for arg in self.capabilities.args:
            for key, value in kwargs.items():
                arg = arg.replace(f"{{{{{key}}}}}", str(value))
            resolved.append(arg)
        return resolved


class AgentsConfig(BaseModel):
    """Root agents configuration container."""
    agents: List[AgentConfig] = Field(default_factory=list)

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent by ID."""
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def get_enabled_agents(self) -> List[AgentConfig]:
        """Get all enabled agents."""
        return [a for a in self.agents if a.enabled]

    def match_agent(self, text: str) -> Optional[AgentConfig]:
        """Match an agent by mention pattern in text."""
        for agent in self.agents:
            if agent.enabled and agent.match_mention(text):
                return agent
        return None
