"""Tests for channel adapter interface."""
import pytest
from abc import ABC
from src.channels.channel_interface import ChannelAdapter


def test_channel_adapter_is_abstract():
    """Test that ChannelAdapter is an abstract base class."""
    assert issubclass(ChannelAdapter, ABC)
    
    # Should not be able to instantiate directly
    with pytest.raises(TypeError):
        ChannelAdapter()


def test_channel_adapter_has_required_methods():
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


class MockAdapter(ChannelAdapter):
    """Mock implementation for testing."""
    
    async def send_message(self, context, message):
        return f"Sent: {message}"
    
    async def receive_event(self, request):
        return {"type": "test", "data": request}
    
    def get_channel_type(self):
        return "mock"


@pytest.mark.asyncio
async def test_mock_adapter_implementation():
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