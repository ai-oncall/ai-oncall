"""Tests for channel adapter interface and implementations."""
import pytest
from abc import ABC
from unittest.mock import AsyncMock, MagicMock
from src.channels.channel_interface import ChannelAdapter
from src.channels.slack_adapter import SlackAdapter
from src.channels.teams_adapter import TeamsAdapter
from src.data.models import MessageContext


class TestChannelAdapterInterface:
    """Tests for the abstract ChannelAdapter interface."""

    def test_channel_adapter_is_abstract(self):
        """Test that ChannelAdapter is an abstract base class."""
        assert issubclass(ChannelAdapter, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            ChannelAdapter()

    def test_channel_adapter_has_required_methods(self):
        """Test that ChannelAdapter has the expected abstract methods."""
        expected_methods = {
            "send_message",
            "receive_event", 
            "get_channel_type"
        }
        
        adapter_methods = {
            name for name, method in ChannelAdapter.__dict__.items()
            if hasattr(method, '__isabstractmethod__') and method.__isabstractmethod__
        }
        
        assert adapter_methods == expected_methods


class TestSlackAdapter:
    """Tests for SlackAdapter implementation."""

    def test_slack_adapter_initialization(self):
        """Test SlackAdapter can be instantiated."""
        adapter = SlackAdapter()
        assert adapter.get_channel_type() == "slack"

    @pytest.mark.asyncio
    async def test_slack_send_message(self):
        """Test Slack message sending."""
        adapter = SlackAdapter()
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Test message"
        )
        
        result = await adapter.send_message(context, "Test response")
        
        assert result["ok"] is True
        assert result["channel"] == "C456"
        assert "ts" in result

    @pytest.mark.asyncio
    async def test_slack_receive_event_message(self):
        """Test Slack event processing for regular messages."""
        adapter = SlackAdapter()
        event = {
            "type": "message",
            "user": "U123",
            "channel": "C456",
            "text": "Hello world",
            "ts": "1234567890.123"
        }
        
        result = await adapter.receive_event(event)
        
        assert result["event_type"] == "message"
        assert result["is_thread_reply"] is False
        assert result["parsed_context"].user_id == "U123"
        assert result["parsed_context"].channel_id == "C456"
        assert result["parsed_context"].message_text == "Hello world"
        assert result["parsed_context"].is_mention is False

    @pytest.mark.asyncio
    async def test_slack_receive_event_mention(self):
        """Test Slack event processing for mentions."""
        adapter = SlackAdapter()
        event = {
            "type": "app_mention",
            "user": "U123",
            "channel": "C456",
            "text": "<@UBOT123> help me please",
            "ts": "1234567890.123"
        }
        
        result = await adapter.receive_event(event)
        
        assert result["event_type"] == "app_mention"
        assert result["parsed_context"].is_mention is True
        assert "help me please" in result["parsed_context"].message_text

    @pytest.mark.asyncio
    async def test_slack_receive_event_thread(self):
        """Test Slack event processing for threaded messages."""
        adapter = SlackAdapter()
        event = {
            "type": "message",
            "user": "U123",
            "channel": "C456",
            "text": "Follow-up message",
            "ts": "1234567890.456",
            "thread_ts": "1234567890.123"
        }
        
        result = await adapter.receive_event(event)
        
        assert result["is_thread_reply"] is True
        assert result["parsed_context"].thread_ts == "1234567890.123"

    def test_slack_clean_message(self):
        """Test Slack message cleaning functionality."""
        adapter = SlackAdapter()
        
        # Test bot mention removal
        cleaned = adapter._clean_slack_message("<@UBOT123> hello world")
        assert "hello world" in cleaned
        assert "<@UBOT123>" not in cleaned
        
        # Test channel mention removal
        cleaned = adapter._clean_slack_message("Check <#C123456|general> channel")
        assert "Check channel" in cleaned
        
        # Test URL removal
        cleaned = adapter._clean_slack_message("Visit <https://example.com|Example>")
        assert "Visit" in cleaned
        assert "https://example.com" not in cleaned


class TestTeamsAdapter:
    """Tests for TeamsAdapter implementation."""

    def test_teams_adapter_initialization(self):
        """Test TeamsAdapter can be instantiated."""
        adapter = TeamsAdapter()
        assert adapter.get_channel_type() == "teams"

    @pytest.mark.asyncio
    async def test_teams_send_message(self):
        """Test Teams message sending."""
        adapter = TeamsAdapter()
        context = MessageContext(
            user_id="teams-user-123",
            channel_id="teams-channel-456",
            channel_type="teams",
            message_text="Test message"
        )
        
        result = await adapter.send_message(context, "Test response")
        
        assert result["success"] is True
        assert result["conversationId"] == "teams-channel-456"
        assert "id" in result

    @pytest.mark.asyncio
    async def test_teams_receive_event(self):
        """Test Teams event processing."""
        adapter = TeamsAdapter()
        event = {
            "type": "message",
            "from": {"id": "teams-user-123"},
            "conversation": {"id": "teams-channel-456"},
            "text": "Hello from Teams",
            "id": "teams-msg-123",
            "timestamp": "2023-01-01T10:00:00Z"
        }
        
        result = await adapter.receive_event(event)
        
        assert result["event_type"] == "message"
        assert result["is_thread_reply"] is False
        assert result["parsed_context"].user_id == "teams-user-123"
        assert result["parsed_context"].channel_id == "teams-channel-456"
        assert result["parsed_context"].message_text == "Hello from Teams"

    @pytest.mark.asyncio
    async def test_teams_receive_event_thread_reply(self):
        """Test Teams event processing for thread replies."""
        adapter = TeamsAdapter()
        event = {
            "type": "message",
            "from": {"id": "teams-user-123"},
            "conversation": {"id": "teams-channel-456"},
            "text": "Reply in thread",
            "replyToId": "teams-original-msg-123"
        }
        
        result = await adapter.receive_event(event)
        
        assert result["is_thread_reply"] is True
        assert result["parsed_context"].thread_ts == "teams-original-msg-123"

    @pytest.mark.asyncio
    async def test_teams_receive_event_mention(self):
        """Test Teams mention detection."""
        adapter = TeamsAdapter()
        event = {
            "type": "message",
            "from": {"id": "teams-user-123"},
            "conversation": {"id": "teams-channel-456"},
            "text": "@bot help me with this issue"
        }
        
        result = await adapter.receive_event(event)
        
        assert result["parsed_context"].is_mention is True


class MockAdapter(ChannelAdapter):
    """Mock implementation for testing the interface."""
    
    async def send_message(self, context, message):
        return f"Sent: {message}"
    
    async def receive_event(self, request):
        return {"type": "test", "data": request}
    
    def get_channel_type(self):
        return "mock"


class TestMockAdapter:
    """Tests for mock adapter to validate interface."""

    @pytest.mark.asyncio
    async def test_mock_adapter_implementation(self):
        """Test that a concrete implementation works."""
        adapter = MockAdapter()
        
        # Test send_message
        result = await adapter.send_message({"channel": "test"}, "Hello")
        assert result == "Sent: Hello"
        
        # Test receive_event
        event = await adapter.receive_event("test_request")
        assert event["type"] == "test"
        assert event["data"] == "test_request"
        
        # Test get_channel_type
        assert adapter.get_channel_type() == "mock" 