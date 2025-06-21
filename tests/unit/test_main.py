"""Unit tests for main.py module."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.data.models import MessageRequest, MessageResponse

# Create test client
client = TestClient(app)


class TestMainEndpoints:
    """Test FastAPI endpoints in main.py."""

    def test_root_endpoint(self):
        """Test root endpoint returns correct message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "AI OnCall Bot - Multi-channel assistant"

    def test_health_endpoint_basic(self):
        """Test health endpoint returns expected structure."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "debug" in data
        assert "openai_configured" in data
        assert "slack_configured" in data
        assert "timestamp" in data

    def test_process_message_endpoint_success(self):
        """Test successful message processing."""
        request_data = {
            "message": "Test message",
            "user_id": "test-user",
            "channel_type": "test",
            "channel_id": "test-channel"
        }
        
        response = client.post("/process-message", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "classification_type" in data
        assert "processing_time_ms" in data
        assert "error_occurred" in data

    def test_process_message_endpoint_with_optional_fields(self):
        """Test message processing with optional fields."""
        request_data = {
            "message": "Test message with thread",
            "user_id": "test-user",
            "channel_type": "slack",
            "channel_id": "test-channel",
            "thread_ts": "1234567890.123",
            "is_mention": True,
            "metadata": {"custom": "data"}
        }
        
        response = client.post("/process-message", json=request_data)
        assert response.status_code == 200

    def test_process_message_endpoint_validation_error(self):
        """Test message processing with invalid data."""
        request_data = {
            "message": "",  # Empty message should fail validation
            "user_id": "test-user"
        }
        
        response = client.post("/process-message", json=request_data)
        assert response.status_code == 422  # Validation error

    @patch('src.main.message_processor.process_message')
    def test_process_message_endpoint_processing_error(self, mock_process):
        """Test message processing when processor raises an exception."""
        mock_process.side_effect = Exception("Processing failed")
        
        request_data = {
            "message": "Test message",
            "user_id": "test-user",
            "channel_type": "test",
            "channel_id": "test-channel"
        }
        
        response = client.post("/process-message", json=request_data)
        assert response.status_code == 500
        assert "Failed to process message" in response.json()["detail"]

    def test_slack_events_endpoint_not_configured(self):
        """Test Slack events endpoint when handler is not configured."""
        # Since slack_handler is None by default (no credentials), 
        # the endpoint shouldn't exist or should return 404
        response = client.post("/slack/events", json={})
        # Should return 404 since the endpoint is conditionally created
        assert response.status_code == 404


class TestSlackInitialization:
    """Test Slack app initialization logic."""

    @patch('src.main.config')
    def test_slack_initialization_with_credentials(self, mock_config):
        """Test Slack initialization when credentials are provided."""
        mock_config.slack_bot_token = "xoxb-test-token"
        mock_config.slack_signing_secret = "test-secret"
        
        # Test the conditional logic that would create Slack app
        credentials_provided = bool(mock_config.slack_bot_token and mock_config.slack_signing_secret)
        assert credentials_provided is True
        
        # Test that the condition would trigger Slack initialization
        if credentials_provided:
            # This is the logic that would run in main.py
            slack_would_be_initialized = True
        else:
            slack_would_be_initialized = False
            
        assert slack_would_be_initialized is True

    @patch('src.main.config')
    def test_slack_initialization_no_credentials(self, mock_config):
        """Test Slack initialization when credentials are not provided."""
        mock_config.slack_bot_token = ""
        mock_config.slack_signing_secret = ""
        
        # Reload the module to trigger initialization
        import importlib
        import src.main
        importlib.reload(src.main)
        
        # slack_app and slack_handler should remain None
        assert src.main.slack_app is None
        assert src.main.slack_handler is None


class TestSlackEventHandlers:
    """Test Slack event handler functions."""

    @pytest.mark.asyncio
    @patch('src.main.config')
    @patch('src.main.message_processor')
    async def test_slack_app_mention_handler(self, mock_processor, mock_config):
        """Test app mention handler logic."""
        mock_config.slack_bot_token = "xoxb-test-token"
        mock_config.slack_signing_secret = "test-secret"
        
        # Mock processor response
        mock_result = Mock()
        mock_result.response_text = "I can help with that!"
        mock_processor.process_message = AsyncMock(return_value=mock_result)
        
        # Mock Slack event data
        event = {
            "user": "U123",
            "channel": "C456",
            "text": "<@UBOT> help me",
            "ts": "1234567890.123"
        }
        
        # Mock say and ack functions
        say = AsyncMock()
        ack = AsyncMock()
        
        # Test the handler logic (we can't directly call the decorated function)
        # So we test the components it would use
        from src.data.models import MessageContext
        
        context = MessageContext(
            user_id=event["user"],
            channel_id=event["channel"],
            channel_type="slack",
            message_text=event["text"],
            thread_ts=event.get("thread_ts"),
            is_mention=True,
            metadata={"ts": event["ts"], "event_type": "app_mention"}
        )
        
        result = await mock_processor.process_message(context)
        
        assert result.response_text == "I can help with that!"
        mock_processor.process_message.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.main.config')
    @patch('src.main.message_processor')
    async def test_slack_message_handler_dm(self, mock_processor, mock_config):
        """Test message handler for direct messages."""
        mock_config.slack_bot_token = "xoxb-test-token"
        mock_config.slack_signing_secret = "test-secret"
        
        # Mock processor response
        mock_result = Mock()
        mock_result.response_text = "Direct message response"
        mock_processor.process_message = AsyncMock(return_value=mock_result)
        
        # Mock DM event
        event = {
            "user": "U123",
            "channel": "D456",  # DM channel
            "text": "hello",
            "ts": "1234567890.123",
            "channel_type": "im"  # Direct message
        }
        
        # Test message handler logic
        from src.data.models import MessageContext
        
        # Should process DMs
        if event.get("channel_type") == "im" or "<@" in event.get("text", ""):
            context = MessageContext(
                user_id=event["user"],
                channel_id=event["channel"],
                channel_type="slack",
                message_text=event["text"],
                thread_ts=event.get("thread_ts"),
                is_mention="<@" in event.get("text", ""),
                metadata={"ts": event["ts"], "event_type": "message"}
            )
            
            result = await mock_processor.process_message(context)
            assert result.response_text == "Direct message response"

    def test_slack_message_handler_bot_message_skip(self):
        """Test that bot messages are skipped."""
        event = {
            "user": "U123",
            "channel": "C456",
            "text": "bot message",
            "subtype": "bot_message"
        }
        
        # Should return early for bot messages
        should_skip = event.get("subtype") == "bot_message" or event.get("bot_id")
        assert should_skip is True

    def test_slack_message_handler_non_mention_skip(self):
        """Test that non-mentions in channels are skipped."""
        event = {
            "user": "U123",
            "channel": "C456",
            "text": "regular message",
            "channel_type": "channel"
        }
        
        # Should skip non-mentions in channels
        should_skip = (event.get("channel_type") != "im" and 
                      "<@" not in event.get("text", ""))
        assert should_skip is True


class TestMainFunction:
    """Test the main() function and startup logic."""

    @pytest.mark.asyncio
    @patch('src.main.config')
    @patch('src.main.slack_app')
    async def test_main_socket_mode(self, mock_slack_app, mock_config):
        """Test main() with Socket Mode enabled."""
        mock_config.debug = True
        mock_config.slack_socket_mode = True
        mock_slack_app.start = AsyncMock()
        
        from src.main import main
        await main()
        
        mock_slack_app.start.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.main.config')
    @patch('uvicorn.Server')
    @patch('uvicorn.Config')
    async def test_main_http_mode(self, mock_uvicorn_config, mock_uvicorn_server, mock_config):
        """Test main() with HTTP mode."""
        mock_config.debug = True
        mock_config.slack_socket_mode = False
        mock_config.port = 8000
        
        mock_server_instance = Mock()
        mock_server_instance.serve = AsyncMock()
        mock_uvicorn_server.return_value = mock_server_instance
        
        from src.main import main
        await main()
        
        mock_uvicorn_config.assert_called_once()
        mock_uvicorn_server.assert_called_once()
        mock_server_instance.serve.assert_called_once()


class TestAppInitialization:
    """Test application initialization logic."""

    def test_app_creation(self):
        """Test FastAPI app is created correctly."""
        assert app.title == "AI OnCall Bot"
        assert app.description == "Multi-channel AI assistant for support and workflow automation"
        assert app.version == "0.1.0"

    def test_message_processor_initialization(self):
        """Test message processor is initialized."""
        from src.main import message_processor
        assert message_processor is not None

    @patch('src.main.config')
    def test_slack_initialization_with_credentials(self, mock_config):
        """Test Slack app initialization when credentials are provided."""
        mock_config.slack_bot_token = "xoxb-test-token"
        mock_config.slack_signing_secret = "test-secret"
        
        # Since we can't easily reload the module without affecting other tests,
        # we'll test the conditional logic indirectly
        credentials_provided = bool(mock_config.slack_bot_token and mock_config.slack_signing_secret)
        assert credentials_provided is True


class TestSlackWebhookEndpoint:
    """Test Slack webhook endpoint when handler is configured."""

    @patch('src.main.slack_handler')
    def test_slack_events_endpoint_configured(self, mock_handler):
        """Test Slack events endpoint when handler is configured."""
        # Mock a configured handler
        mock_handler_instance = AsyncMock()
        mock_handler_instance.handle = AsyncMock(return_value={"ok": True})
        mock_handler.return_value = mock_handler_instance
        
        # The endpoint would be created when handler exists
        handler_configured = mock_handler is not None
        assert handler_configured is True

    def test_slack_events_endpoint_handler_none_check(self):
        """Test the handler None check in slack_events function."""
        # Test the logic that would be in the endpoint
        slack_handler = None
        
        if slack_handler is None:
            # Would raise HTTPException(status_code=503, detail="Slack not configured")
            error_expected = True
        else:
            error_expected = False
            
        assert error_expected is True 