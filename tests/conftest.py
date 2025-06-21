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
async def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(message=MagicMock(content="Test AI response"))],
            usage=MagicMock(total_tokens=50)
        )
    )
    return client 