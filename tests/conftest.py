import pytest
from unittest.mock import AsyncMock, MagicMock
from src.utils.config import AppConfig
from src.data.models import MessageContext


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return AppConfig(
        debug=True,
        log_level="DEBUG",
        port=8001,
    )


@pytest.fixture
def sample_message_context():
    """Sample message context for testing."""
    return MessageContext(
        user_id="U12345678",
        channel_id="C87654321",
        channel_type="slack",
        message_text="I need help with my application",
    )


@pytest.fixture
def sample_teams_message_context():
    """Sample Teams message context for testing."""
    return MessageContext(
        user_id="teams-user-123",
        channel_id="teams-channel-456",
        channel_type="teams",
        message_text="Help with login issues",
    )


@pytest.fixture
async def mock_channel_adapter():
    """Mock channel adapter for testing."""
    adapter = AsyncMock()
    adapter.send_message = AsyncMock(return_value=None)
    adapter.receive_event = AsyncMock(return_value={})
    adapter.get_channel_type = MagicMock(return_value="test")
    return adapter


@pytest.fixture
async def mock_slack_adapter():
    """Mock Slack adapter for testing."""
    adapter = AsyncMock()
    adapter.send_message = AsyncMock(return_value={"ok": True, "ts": "123456789.123"})
    
    # Configure receive_event to return properly parsed context based on input
    def mock_receive_event(event):
        return {
            "parsed_context": MessageContext(
                user_id=event.get("user", "U123"),
                channel_id=event.get("channel", "C456"), 
                channel_type="slack",
                message_text=event.get("text", "test message").replace("<@UBOT123>", "").strip(),
                thread_ts=event.get("thread_ts"),
                is_mention=event.get("type") == "app_mention" or "<@" in event.get("text", ""),
                metadata={"ts": event.get("ts"), "event_type": event.get("type")}
            ),
            "is_thread_reply": bool(event.get("thread_ts")),
            "event_type": event.get("type")
        }
    
    adapter.receive_event = AsyncMock(side_effect=mock_receive_event)
    adapter.get_channel_type = MagicMock(return_value="slack")
    return adapter


@pytest.fixture
async def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    
    # Configure classify_message to return proper mock response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = '{"type": "support_request", "urgency": "medium", "category": "general", "confidence": 0.8}'
    mock_response.usage = MagicMock()
    mock_response.usage.total_tokens = 120
    
    client.classify_message = AsyncMock(return_value=mock_response)
    
    # Also configure the old style for backward compatibility
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return client


@pytest.fixture
def mock_processing_result():
    """Mock processing result for testing."""
    return MagicMock(
        response_sent=True,
        classification_type="support_request",
        processing_time_ms=150,
        workflow_executed=False,
        workflow_name="",
        has_context=False,
        error_occurred=False,
        error_message="",
        channel_type="slack",
        escalation_triggered=False,
        knowledge_base_used=False
    ) 