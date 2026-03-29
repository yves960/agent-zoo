"""Tests for AgentDispatcher class."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from services.agent_dispatcher import AgentDispatcher, DispatchResult
from agents.base import AnimalMessage


class TestAgentDispatcherResolveTargets:
    """Tests for _resolve_targets method."""
    
    def test_resolve_targets_with_mentions(self, mock_websocket_manager: MagicMock) -> None:
        """When @mentions are present in content, use those targets."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        # Content contains @雪球 mention
        content = "Hello @雪球, how are you?"
        
        targets = dispatcher._resolve_targets(content, mentions=None)
        
        # Should resolve to xueqiu (from @雪球)
        assert targets == ["xueqiu"]
    
    def test_resolve_targets_multiple_mentions(self, mock_websocket_manager: MagicMock) -> None:
        """When multiple @mentions are present, return both (max 2)."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        # Content contains @雪球 and @六六 mentions
        content = "Hello @雪球 and @六六"
        
        targets = dispatcher._resolve_targets(content, mentions=None)
        
        # Should resolve to both
        assert set(targets) == {"xueqiu", "liuliu"}
    
    def test_resolve_targets_random_without_mentions(self, mock_websocket_manager: MagicMock) -> None:
        """When no @mentions are present, return all enabled agents."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        content = "Hello everyone!"
        targets = dispatcher._resolve_targets(content, mentions=None)
        
        # Should return all enabled agents when no mentions
        assert len(targets) > 1
        assert all(isinstance(t, str) for t in targets)
    
    def test_resolve_targets_uses_provided_mentions(self, mock_websocket_manager: MagicMock) -> None:
        """When no @mentions in content but mentions provided, use provided mentions."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        # Content without mentions, but provided mentions
        content = "Hello!"
        provided_mentions = ["liuliu", "xiaohuang"]
        
        targets = dispatcher._resolve_targets(content, mentions=provided_mentions)
        
        # Should use provided mentions
        assert targets == provided_mentions
    
    def test_resolve_mentions_in_content_overrides_provided(self, mock_websocket_manager: MagicMock) -> None:
        """@mentions in content take priority over provided mentions."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        # Content has @雪球, but provided mentions are different
        content = "Hello @雪球!"
        provided_mentions = ["liuliu"]
        
        targets = dispatcher._resolve_targets(content, mentions=provided_mentions)
        
        # Content @mentions should win
        assert targets == ["xueqiu"]
    
    def test_resolve_targets_ignores_self_mention(self, mock_websocket_manager: MagicMock) -> None:
        """Self mentions should be ignored (current_animal filtering)."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        # The parse_a2a_mentions filters out current_animal
        # Since we're parsing from "user" perspective, all valid mentions should work
        content = "Hello @雪球 @雪球 @雪球!"  # Duplicate mentions
        
        targets = dispatcher._resolve_targets(content, mentions=None)
        
        # Should only return one xueqiu (duplicates removed)
        assert targets == ["xueqiu"]


class TestAgentDispatcherDispatch:
    """Tests for dispatch_message method."""
    
    @pytest.mark.asyncio
    async def test_dispatch_to_unknown_animal_returns_error(self, mock_websocket_manager: MagicMock) -> None:
        """Dispatching to an unknown animal should return an error result."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        # Mock get_animal_service to raise ValueError for unknown animal
        with patch('services.agent_dispatcher.get_animal_service') as mock_get_service:
            mock_get_service.side_effect = ValueError("Unknown animal_id: unknown_animal. Available: ['xueqiu', 'liuliu', 'xiaohuang']")
            
            # Force unknown animal by patching _resolve_targets
            with patch.object(dispatcher, '_resolve_targets', return_value=['unknown_animal']):
                results = await dispatcher.dispatch_message(
                    content="Hello!",
                    thread_id="test-thread",
                )
        
        # Should have one error result
        assert len(results) == 1
        assert results[0].animal_id == "unknown_animal"
        assert results[0].success is False
        assert "Unknown animal_id" in results[0].error
    
    @pytest.mark.asyncio
    async def test_dispatch_to_multiple_animals(self, mock_websocket_manager: MagicMock) -> None:
        """Dispatching to multiple animals should return multiple results."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        # Create mock service that yields messages
        mock_service = MagicMock()
        
        async def mock_invoke(prompt: str, thread_id: str):
            yield AnimalMessage(
                animal_id="xueqiu",
                content="Response",
                message_type="text"
            )
        
        mock_service.invoke = mock_invoke
        
        with patch('services.agent_dispatcher.get_animal_service', return_value=mock_service):
            results = await dispatcher.dispatch_message(
                content="@雪球 @六六 hello",
                thread_id="test-thread",
            )
        
        # Should have results for both animals
        assert len(results) == 2
        assert all(r.success for r in results)
    
    @pytest.mark.asyncio
    async def test_dispatch_empty_targets_returns_empty_list(self, mock_websocket_manager: MagicMock) -> None:
        """When no targets resolved, return empty results list."""
        dispatcher = AgentDispatcher(ws_manager=mock_websocket_manager)
        
        with patch.object(dispatcher, '_resolve_targets', return_value=[]):
            results = await dispatcher.dispatch_message(
                content="Hello!",
                thread_id="test-thread",
            )
        
        assert results == []


class TestDispatchResult:
    """Tests for DispatchResult dataclass."""
    
    def test_dispatch_result_success(self) -> None:
        """Create a successful dispatch result."""
        result = DispatchResult(
            animal_id="xueqiu",
            success=True,
        )
        
        assert result.animal_id == "xueqiu"
        assert result.success is True
        assert result.error is None
    
    def test_dispatch_result_error(self) -> None:
        """Create an error dispatch result."""
        result = DispatchResult(
            animal_id="unknown",
            success=False,
            error="Animal not found",
        )
        
        assert result.animal_id == "unknown"
        assert result.success is False
        assert result.error == "Animal not found"