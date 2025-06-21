"""Tests for data models."""
from datetime import datetime
from src.data.models import MessageContext


def test_message_context_creation():
    """Test MessageContext can be created with required fields."""
    context = MessageContext(
        user_id="user123",
        channel_id="channel456",
        channel_type="slack",
        message_text="Test message"
    )
    
    assert context.user_id == "user123"
    assert context.channel_id == "channel456"
    assert context.channel_type == "slack"
    assert context.message_text == "Test message"
    assert context.thread_ts is None
    assert isinstance(context.timestamp, datetime)
    assert isinstance(context.metadata, dict)


def test_message_context_with_optional_fields():
    """Test MessageContext with optional fields."""
    metadata = {"source": "api", "priority": "high"}
    
    context = MessageContext(
        user_id="user123",
        channel_id="channel456",
        channel_type="teams",
        message_text="Test message",
        thread_ts="1234567890.123",
        metadata=metadata
    )
    
    assert context.thread_ts == "1234567890.123"
    assert context.metadata == metadata
    assert context.channel_type == "teams"


def test_message_context_different_channels():
    """Test MessageContext works with different channel types."""
    slack_context = MessageContext(
        user_id="slack_user",
        channel_id="slack_channel",
        channel_type="slack",
        message_text="Slack message"
    )
    
    teams_context = MessageContext(
        user_id="teams_user",
        channel_id="teams_channel",
        channel_type="teams",
        message_text="Teams message"
    )
    
    assert slack_context.channel_type == "slack"
    assert teams_context.channel_type == "teams" 