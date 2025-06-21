"""Tests for channel adapter components."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.channels.channel_interface import ChannelAdapter
from src.channels.slack_adapter import SlackAdapter
from src.channels.teams_adapter import TeamsAdapter
from src.data.models import MessageContext


class TestSlackAdapter:
    """Tests for SlackAdapter implementation."""

    def test_slack_adapter_initialization_no_credentials(self):
        """Test SlackAdapter initialization without credentials."""
        with patch('src.channels.slack_adapter.config') as mock_config:
            mock_config.slack_bot_token = ""  
            mock_config.slack_signing_secret = ""
            
            adapter = SlackAdapter()
            assert adapter._client is None

    @patch('src.channels.slack_adapter.config')
    @patch('src.channels.slack_adapter.AsyncApp')
    def test_slack_adapter_initialization_with_credentials(self, mock_app, mock_config):
        """Test SlackAdapter initialization with credentials."""
        mock_config.slack_bot_token = "xoxb-test-token"
        mock_config.slack_signing_secret = "test-secret"
        
        adapter = SlackAdapter()
        
        mock_app.assert_called_once_with(
            token="xoxb-test-token",
            signing_secret="test-secret"
        )

    @pytest.mark.asyncio
    async def test_send_message_no_client(self):
        """Test send_message when client is not configured."""
        with patch('src.channels.slack_adapter.config') as mock_config:
            mock_config.slack_bot_token = ""
            mock_config.slack_signing_secret = ""
            
            adapter = SlackAdapter()
            
            context = MessageContext(
                user_id="U123",
                channel_id="C456", 
                channel_type="slack",
                message_text="Test message"
            )
            
            result = await adapter.send_message(context, "Test response")
            
            assert result["ok"] is True
            assert "ts" in result
            assert result["channel"] == "C456"

    @pytest.mark.asyncio
    async def test_send_message_with_client(self):
        """Test send_message with configured client."""
        with patch('src.channels.slack_adapter.config') as mock_config:
            mock_config.slack_bot_token = "xoxb-test-token"
            mock_config.slack_signing_secret = "test-secret"
            
            with patch('src.channels.slack_adapter.AsyncApp') as mock_app:
                mock_client = AsyncMock()
                mock_client.client.chat_postMessage = AsyncMock(return_value={
                    "ok": True,
                    "ts": "1234567890.123",
                    "channel": "C456"
                })
                mock_app.return_value = mock_client
                
                adapter = SlackAdapter()
                
                context = MessageContext(
                    user_id="U123",
                    channel_id="C456",
                    channel_type="slack", 
                    message_text="Test message"
                )
                
                result = await adapter.send_message(context, "Test response")
                
                assert result["ok"] is True
                assert result["ts"] == "1234567890.123"
                assert result["channel"] == "C456"
                mock_client.client.chat_postMessage.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_with_thread(self):
        """Test send_message with thread timestamp."""
        with patch('src.channels.slack_adapter.config') as mock_config:
            mock_config.slack_bot_token = "xoxb-test-token"
            mock_config.slack_signing_secret = "test-secret"
            
            with patch('src.channels.slack_adapter.AsyncApp') as mock_app:
                mock_client = AsyncMock()
                mock_client.client.chat_postMessage = AsyncMock(return_value={
                    "ok": True,
                    "ts": "1234567890.123",
                    "channel": "C456"
                })
                mock_app.return_value = mock_client
                
                adapter = SlackAdapter()
                
                context = MessageContext(
                    user_id="U123",
                    channel_id="C456",
                    channel_type="slack",
                    message_text="Test message",
                    thread_ts="1234567890.000"
                )
                
                await adapter.send_message(context, "Test response")
                
                # Check that thread_ts was passed correctly
                mock_client.client.chat_postMessage.assert_called_once()
                call_args = mock_client.client.chat_postMessage.call_args
                if call_args:
                    assert call_args[1]["thread_ts"] == "1234567890.000"

    @pytest.mark.asyncio
    async def test_send_message_exception(self):
        """Test send_message when exception occurs."""
        with patch('src.channels.slack_adapter.config') as mock_config:
            mock_config.slack_bot_token = "xoxb-test-token"
            mock_config.slack_signing_secret = "test-secret"
            
            with patch('src.channels.slack_adapter.AsyncApp') as mock_app:
                mock_client = AsyncMock()
                mock_client.client.chat_postMessage = AsyncMock(side_effect=Exception("API Error"))
                mock_app.return_value = mock_client
                
                adapter = SlackAdapter()
                
                context = MessageContext(
                    user_id="U123",
                    channel_id="C456",
                    channel_type="slack",
                    message_text="Test message"
                )
                
                with pytest.raises(Exception, match="API Error"):
                    await adapter.send_message(context, "Test response")

    @pytest.mark.asyncio
    async def test_receive_event(self):
        """Test receive_event processing."""
        adapter = SlackAdapter()
        
        event = {
            "type": "message",
            "user": "U123",
            "channel": "C456",
            "text": "Hello bot",
            "ts": "1234567890.123"
        }
        
        result = await adapter.receive_event(event)
        
        assert "parsed_context" in result
        assert result["is_thread_reply"] is False
        assert result["event_type"] == "message"

    @pytest.mark.asyncio 
    async def test_receive_event_with_thread(self):
        """Test receive_event with thread reply."""
        adapter = SlackAdapter()
        
        event = {
            "type": "message",
            "user": "U123",
            "channel": "C456",
            "text": "Reply in thread",
            "ts": "1234567890.456",
            "thread_ts": "1234567890.123"
        }
        
        result = await adapter.receive_event(event)
        
        assert result["is_thread_reply"] is True
        assert result["parsed_context"].thread_ts == "1234567890.123"

    def test_get_channel_type(self):
        """Test get_channel_type method."""
        adapter = SlackAdapter()
        assert adapter.get_channel_type() == "slack"

    def test_parse_slack_event_basic(self):
        """Test parsing basic Slack event."""
        adapter = SlackAdapter()
        
        event = {
            "type": "message",
            "user": "U123",
            "channel": "C456",
            "text": "Hello world",
            "ts": "1234567890.123"
        }
        
        context = adapter._parse_slack_event(event)
        
        assert context.user_id == "U123"
        assert context.channel_id == "C456"
        assert context.channel_type == "slack"
        assert context.message_text == "Hello world"
        assert context.is_mention is False

    def test_parse_slack_event_mention(self):
        """Test parsing Slack event with mention."""
        adapter = SlackAdapter()
        
        event = {
            "type": "app_mention",
            "user": "U123",
            "channel": "C456",
            "text": "<@U789> hello",
            "ts": "1234567890.123"
        }
        
        context = adapter._parse_slack_event(event)
        
        assert context.is_mention is True
        assert context.metadata["event_type"] == "app_mention"

    def test_clean_slack_message_mentions(self):
        """Test cleaning Slack message with mentions."""
        adapter = SlackAdapter()
        
        text = "<@U123456> hello <#C789|general> world"
        cleaned = adapter._clean_slack_message(text)
        
        assert "<@U123456>" not in cleaned
        assert "<#C789|general>" not in cleaned
        assert "hello" in cleaned
        assert "world" in cleaned

    def test_clean_slack_message_urls(self):
        """Test cleaning Slack message with URLs."""
        adapter = SlackAdapter()
        
        text = "Check this out <https://example.com|example>"
        cleaned = adapter._clean_slack_message(text)
        
        assert "<https://example.com|example>" not in cleaned
        assert "Check this out" in cleaned

    def test_clean_slack_message_whitespace(self):
        """Test cleaning Slack message whitespace."""
        adapter = SlackAdapter()
        
        text = "  hello   world  "
        cleaned = adapter._clean_slack_message(text)
        
        assert cleaned == "hello world"


class TestTeamsAdapter:
    """Tests for TeamsAdapter implementation."""

    def test_teams_adapter_initialization(self):
        """Test TeamsAdapter can be instantiated."""
        adapter = TeamsAdapter()
        assert adapter is not None

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test that send_message returns success response."""
        adapter = TeamsAdapter()
        
        context = MessageContext(
            user_id="user123",
            channel_id="channel456",
            channel_type="teams",
            message_text="Test message"
        )
        
        result = await adapter.send_message(context, "Test response")
        
        assert result["success"] is True
        assert result["id"] == "teams-msg-123"
        assert result["conversationId"] == "channel456"

    @pytest.mark.asyncio
    async def test_receive_event_success(self):
        """Test that receive_event processes events correctly."""
        adapter = TeamsAdapter()
        
        event = {
            "type": "message",
            "from": {"id": "user123"},
            "conversation": {"id": "channel456"},
            "text": "Hello Teams bot",
            "id": "msg-id-123",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        result = await adapter.receive_event(event)
        
        assert "parsed_context" in result
        assert result["is_thread_reply"] is False
        assert result["event_type"] == "message"

    def test_parse_teams_event_basic(self):
        """Test parsing basic Teams event."""
        adapter = TeamsAdapter()
        
        event = {
            "type": "message",
            "from": {"id": "user123"},
            "conversation": {"id": "channel456"},
            "text": "Hello Teams",
            "id": "msg-id-123",
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        context = adapter._parse_teams_event(event)
        
        assert context.user_id == "user123"
        assert context.channel_id == "channel456"
        assert context.channel_type == "teams"
        assert context.message_text == "Hello Teams"
        assert context.is_mention is False

    def test_parse_teams_event_with_mention(self):
        """Test parsing Teams event with mention."""
        adapter = TeamsAdapter()
        
        event = {
            "type": "message",
            "from": {"id": "user123"},
            "conversation": {"id": "channel456"},
            "text": "@bot hello there",
            "id": "msg-id-123"
        }
        
        context = adapter._parse_teams_event(event)
        
        assert context.is_mention is True
        assert context.metadata["id"] == "msg-id-123"

    def test_get_channel_type(self):
        """Test get_channel_type method."""
        adapter = TeamsAdapter()
        assert adapter.get_channel_type() == "teams" 