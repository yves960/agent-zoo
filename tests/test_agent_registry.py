"""Tests for AgentRegistry class."""

import pytest
from unittest.mock import MagicMock

from agents.registry import AgentRegistry
from agents.base import AnimalService
from core.agent_config import AgentConfig


class MockAnimalService(AnimalService):
    """Mock implementation of AnimalService for testing."""
    
    async def invoke(self, prompt: str, thread_id: str):
        """Mock invoke method."""
        from agents.base import AnimalMessage
        yield AnimalMessage(
            animal_id=self.animal_id,
            content=f"Mock response to: {prompt}",
            message_type="text"
        )
    
    def get_cli_command(self):
        """Mock CLI command."""
        return ("mock-cli", [])
    
    def transform_event(self, event):
        """Mock event transformer."""
        return None


class TestAgentRegistryRegister:
    """Tests for registration methods."""
    
    def test_register_class(self) -> None:
        """Register a service class for an animal."""
        registry = AgentRegistry()
        
        registry.register_class("test_animal", MockAnimalService)
        
        assert "test_animal" in registry._service_classes
        assert registry._service_classes["test_animal"] == MockAnimalService
    
    def test_register_class_clears_cached_instance(self) -> None:
        """Re-registering a class should clear the cached instance."""
        registry = AgentRegistry()
        
        # Register and create instance
        registry.register_class("test_animal", MockAnimalService)
        instance1 = registry.get_service("test_animal")
        
        # Re-register
        registry.register_class("test_animal", MockAnimalService)
        
        # Cached instance should be cleared
        assert "test_animal" not in registry._instances
    
    def test_register_config(self) -> None:
        """Register a configuration for an animal."""
        registry = AgentRegistry()
        
        config = AgentConfig(
            id="test_animal",
            name="Test Animal",
            species="Test Species",
            description="test-cli",
        )
        
        registry.register_config(config)
        
        assert "test_animal" in registry._configs
        assert registry._configs["test_animal"] == config


class TestAgentRegistryGetService:
    """Tests for get_service method."""
    
    def test_get_service_creates_instance(self) -> None:
        """Getting a service should create an instance."""
        registry = AgentRegistry()
        registry.register_class("test_animal", MockAnimalService)
        
        service = registry.get_service("test_animal")
        
        assert service is not None
        assert isinstance(service, MockAnimalService)
        assert service.animal_id == "test_animal"
    
    def test_get_service_caches_instance(self) -> None:
        """Getting a service twice should return the same instance (singleton)."""
        registry = AgentRegistry()
        registry.register_class("test_animal", MockAnimalService)
        
        service1 = registry.get_service("test_animal")
        service2 = registry.get_service("test_animal")
        
        assert service1 is service2
    
    def test_get_unknown_service_returns_none(self) -> None:
        """Getting an unregistered service should return None."""
        registry = AgentRegistry()
        
        service = registry.get_service("unknown_animal")
        
        assert service is None
    
    def test_get_service_with_config(self) -> None:
        """Service instance should be created with correct animal_id."""
        registry = AgentRegistry()
        registry.register_class("test_animal", MockAnimalService)
        
        service = registry.get_service("test_animal")
        
        assert service.animal_id == "test_animal"


class TestAgentRegistryGetConfig:
    """Tests for get_config method."""
    
    def test_get_config_returns_registered_config(self) -> None:
        """Getting a config should return the registered config."""
        registry = AgentRegistry()
        
        config = AgentConfig(
            id="test_animal",
            name="Test Animal",
            species="Test Species",
            description="test-cli",
        )
        
        registry.register_config(config)
        
        result = registry.get_config("test_animal")
        
        assert result == config
    
    def test_get_config_unknown_returns_none(self) -> None:
        """Getting an unregistered config should return None."""
        registry = AgentRegistry()
        
        result = registry.get_config("unknown_animal")
        
        assert result is None


class TestAgentRegistryGetAll:
    """Tests for get_all_* methods."""
    
    def test_get_all_animal_ids(self) -> None:
        """Get all registered animal IDs."""
        registry = AgentRegistry()
        registry.register_class("xueqiu", MockAnimalService)
        registry.register_class("liuliu", MockAnimalService)
        
        ids = registry.get_all_animal_ids()
        
        assert set(ids) == {"xueqiu", "liuliu"}
    
    def test_get_all_services(self) -> None:
        """Get all registered service instances."""
        registry = AgentRegistry()
        registry.register_class("xueqiu", MockAnimalService)
        registry.register_class("liuliu", MockAnimalService)
        
        services = registry.get_all_services()
        
        assert "xueqiu" in services
        assert "liuliu" in services
        assert isinstance(services["xueqiu"], MockAnimalService)
        assert isinstance(services["liuliu"], MockAnimalService)


class TestAgentRegistryCacheManagement:
    """Tests for cache management methods."""
    
    def test_clear_cache(self) -> None:
        """Clear cache should remove all cached instances."""
        registry = AgentRegistry()
        registry.register_class("test_animal", MockAnimalService)
        
        # Create instance (cached)
        registry.get_service("test_animal")
        assert "test_animal" in registry._instances
        
        # Clear cache
        registry.clear_cache()
        
        assert len(registry._instances) == 0
    
    def test_clear_cache_preserves_classes_and_configs(self) -> None:
        """Clear cache should not remove registered classes and configs."""
        registry = AgentRegistry()
        registry.register_class("test_animal", MockAnimalService)
        
        config = AgentConfig(
            id="test_animal",
            name="Test Animal",
            species="Test Species",
            description="test-cli",
        )
        registry.register_config(config)
        
        # Create instance
        registry.get_service("test_animal")
        
        # Clear cache
        registry.clear_cache()
        
        # Classes and configs should still exist
        assert "test_animal" in registry._service_classes
        assert "test_animal" in registry._configs


class TestAgentRegistryUnregister:
    """Tests for unregister method."""
    
    def test_unregister_removes_all(self) -> None:
        """Unregister should remove class, config, and instance."""
        registry = AgentRegistry()
        registry.register_class("test_animal", MockAnimalService)
        
        config = AgentConfig(
            id="test_animal",
            name="Test Animal",
            species="Test Species",
            description="test-cli",
        )
        registry.register_config(config)
        
        # Create instance
        registry.get_service("test_animal")
        
        # Unregister
        result = registry.unregister("test_animal")
        
        assert result is True
        assert "test_animal" not in registry._service_classes
        assert "test_animal" not in registry._configs
        assert "test_animal" not in registry._instances
    
    def test_unregister_unknown_returns_false(self) -> None:
        """Unregistering unknown animal should return False."""
        registry = AgentRegistry()
        
        result = registry.unregister("unknown_animal")
        
        assert result is False