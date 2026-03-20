"""Configuration management for Zoo Multi-Agent System."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AnimalCLIConfig(BaseModel):
    """Configuration for an animal's CLI tool."""
    cli_path: str
    cli_args: List[str] = []


class ZooConfig(BaseSettings):
    """Zoo system configuration loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_prefix="ZOO_",
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # App config
    app_name: str = "Zoo Multi-Agent System"
    debug: bool = False
    log_level: str = "INFO"

    # CLI paths
    opencode_cli_path: str = "opencode"
    opencode_cli_args: List[str] = ["run"]

    claude_cli_path: str = "claude"
    claude_cli_args: List[str] = ["-p", "--output-format", "stream-json"]

    crush_cli_path: str = "crush"
    crush_cli_args: List[str] = ["run"]

    # Animal-specific CLI configs
    animal_clis: Dict[str, AnimalCLIConfig] = {}

    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Database configuration
    database_url: str = "sqlite+aiosqlite:///./zoo.db"

    # WebSocket configuration
    ws_host: str = "0.0.0.0"
    ws_port: int = 8002

    @field_validator("animal_clis", mode="before")
    @classmethod
    def set_default_animal_clis(cls, v: Dict) -> Dict:
        """Set default CLI configurations for animals."""
        if not v:
            v = {
                "xueqiu": AnimalCLIConfig(
                    cli_path="opencode",
                    cli_args=["run"]
                ),
                "liuliu": AnimalCLIConfig(
                    cli_path="claude",
                    cli_args=["-p", "--output-format", "stream-json"]
                ),
                "xiaohuang": AnimalCLIConfig(
                    cli_path="crush",
                    cli_args=["run"]
                ),
            }
        return v

    @property
    def animal_cli_paths(self) -> Dict[str, str]:
        """Get CLI paths for each animal."""
        return {
            "xueqiu": self.opencode_cli_path,
            "liuliu": self.claude_cli_path,
            "xiaohuang": self.crush_cli_path,
        }

    @property
    def animal_cli_args(self) -> Dict[str, List[str]]:
        """Get CLI arguments for each animal."""
        return {
            "xueqiu": self.opencode_cli_args,
            "liuliu": self.claude_cli_args,
            "xiaohuang": self.crush_cli_args,
        }


# Global config instance
_config: Optional[ZooConfig] = None


def get_config() -> ZooConfig:
    """Get or create the global config instance."""
    global _config
    if _config is None:
        _config = ZooConfig()
    return _config


def reload_config() -> ZooConfig:
    """Reload configuration from environment."""
    global _config
    _config = ZooConfig()
    return _config
