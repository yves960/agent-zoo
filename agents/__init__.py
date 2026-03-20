"""
Zoo Multi-Agent System - Animal Services Package.

Exports all animal agent services and provides factory functions.
Uses registry pattern for dynamic agent loading.
"""

from typing import Dict, List, Optional

from .base import AnimalMessage, AnimalService
from .config import AgentConfig
from .registry import AgentRegistry, registry
from .xueqiu import XueqiuService
from .liuliu import LiuliuService
from .xiaohuang import XiaohuangService

# OpenAI Agent - 可选导入，如果依赖未安装则跳过
try:
    from agents_openai.zoo_adapter import OpenAIAgentService
    _has_openai = True
except ImportError:
    OpenAIAgentService = None  # type: ignore[misc,assignment]
    _has_openai = False


# Register service classes with the registry
registry.register_class("xueqiu", XueqiuService)
registry.register_class("liuliu", LiuliuService)
registry.register_class("xiaohuang", XiaohuangService)

if _has_openai and OpenAIAgentService is not None:
    registry.register_class("openai", OpenAIAgentService)  # type: ignore[arg-type]

# Register default configurations
registry.register_config(AgentConfig(
    animal_id="xueqiu",
    name="雪球",
    species="雪纳瑞",
    cli_path="opencode",
    cli_args=["run", "-m", "bailian-coding-plan/glm-5"],
    color="#4A90E2",
    mention_patterns=["@雪球", "@xueqiu"],
    enabled=True,
))

registry.register_config(AgentConfig(
    animal_id="liuliu",
    name="六六",
    species="虎皮鹦鹉(蓝)",
    cli_path="claude",
    cli_args=[],
    color="#3498DB",
    mention_patterns=["@六六", "@liuliu"],
    enabled=True,
))

registry.register_config(AgentConfig(
    animal_id="xiaohuang",
    name="小黄",
    species="虎皮鹦鹉(黄绿)",
    cli_path="crush",
    cli_args=[],
    color="#F1C40F",
    mention_patterns=["@小黄", "@xiaohuang"],
    enabled=True,
))

if _has_openai:
    registry.register_config(AgentConfig(
        animal_id="openai",
        name="OpenAI",
        species="AI Agent",
        cli_path="openai",
        cli_args=[],
        color="#10A37F",
        mention_patterns=["@openai"],
        enabled=True,
    ))


def get_animal_service(animal_id: str) -> AnimalService:
    """
    Get a specific animal service by ID.
    
    Args:
        animal_id: The animal identifier (xueqiu, liuliu, xiaohuang, openai)
        
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


# Legacy function name for backwards compatibility
get_animal_services = get_all_animal_services


__all__ = [
    # Base classes
    "AnimalMessage",
    "AnimalService",
    # Config
    "AgentConfig",
    # Registry
    "AgentRegistry",
    "registry",
    # Service classes
    "XueqiuService",
    "LiuliuService",
    "XiaohuangService",
    # Factory functions
    "get_animal_service",
    "get_animal_services",
    "get_all_animal_services",
]