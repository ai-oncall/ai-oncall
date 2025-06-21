"""Integration tests for end-to-end message processing flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.data.models import MessageContext
from src.core.message_processor import MessageProcessor


class TestMessageFlow:
    """Test the complete message processing flow."""

    @pytest.mark.asyncio
    async def test_slack_message_to_ai_response_flow(
        self, 
        sample_message_context, 
        mock_openai_client,
        mock_slack_adapter
    ):
        """Test complete flow: Slack message → AI classification → Response."""
        # Arrange
        processor = MessageProcessor()
        
        # Mock AI classification response
        mock_openai_client.classify_message.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content='{"type": "support_request", "urgency": "medium", "category": "login_issue"}')
            )],
            usage=MagicMock(total_tokens=150)
        )
        
        # Mock workflow execution
        expected_response = "I'll help you with your login issue. Let me check your account status..."
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            with patch('src.core.message_processor.get_channel_adapter', return_value=mock_slack_adapter):
                result = await processor.process_message(sample_message_context)
        
        # Assert
        assert result is not None
        assert result.response_sent is True
        assert result.classification_type == "support_request"
        assert result.processing_time_ms >= 0
        
        # Verify AI was called for classification
        mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify response was sent through Slack adapter
        mock_slack_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_execution_flow(
        self, 
        sample_message_context,
        mock_openai_client
    ):
        """Test workflow execution based on AI classification."""
        # Arrange
        processor = MessageProcessor()
        
        # Mock AI classification for workflow trigger
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content='{"type": "incident_report", "severity": "high", "category": "system_outage"}')
            )]
        )
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            result = await processor.process_message(sample_message_context)
        
        # Assert
        assert result.classification_type == "incident_report"
        assert result.workflow_executed is True
        assert "incident" in result.workflow_name.lower()

    @pytest.mark.asyncio
    async def test_context_management_flow(
        self,
        mock_openai_client
    ):
        """Test conversation context is maintained across messages."""
        # Arrange
        processor = MessageProcessor()
        
        # First message in conversation
        first_context = MessageContext(
            user_id="U123",
            channel_id="C456", 
            channel_type="slack",
            message_text="I'm having login issues",
            thread_ts="1234567890.123"
        )
        
        # Follow-up message in same thread
        followup_context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack", 
            message_text="Yes, it's the mobile app",
            thread_ts="1234567890.123"  # Same thread
        )
        
        # Mock AI responses
        mock_openai_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"type": "support_request", "category": "login"}'))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"type": "followup", "context": "mobile_app_login"}'))])
        ]
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            first_result = await processor.process_message(first_context)
            second_result = await processor.process_message(followup_context)
        
        # Assert
        assert first_result.classification_type == "support_request"
        assert second_result.classification_type == "followup"
        assert second_result.has_context is True

    @pytest.mark.asyncio
    async def test_error_handling_flow(
        self,
        sample_message_context,
        mock_openai_client
    ):
        """Test error handling in message processing flow."""
        # Arrange
        processor = MessageProcessor()
        
        # Mock AI client to raise an exception
        mock_openai_client.chat.completions.create.side_effect = Exception("OpenAI API Error")
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            result = await processor.process_message(sample_message_context)
        
        # Assert
        assert result.error_occurred is True
        assert "OpenAI API Error" in result.error_message
        assert result.classification_type == "error"

    @pytest.mark.asyncio
    async def test_multiple_channel_support(
        self,
        mock_openai_client
    ):
        """Test that different channel types are handled correctly."""
        # Arrange  
        processor = MessageProcessor()
        
        # Different channel contexts
        slack_context = MessageContext(
            user_id="U123", channel_id="C456", channel_type="slack",
            message_text="Help with deployment"
        )
        
        teams_context = MessageContext(
            user_id="teams-user-789", channel_id="teams-channel-101", channel_type="teams",
            message_text="Help with deployment"
        )
        
        # Mock AI response
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"type": "deployment_help", "urgency": "low"}'))]
        )
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            slack_result = await processor.process_message(slack_context)
            teams_result = await processor.process_message(teams_context)
        
        # Assert
        assert slack_result.channel_type == "slack"
        assert teams_result.channel_type == "teams"
        assert slack_result.classification_type == "deployment_help"
        assert teams_result.classification_type == "deployment_help"


class TestSlackIntegration:
    """Test Slack-specific integration scenarios."""

    @pytest.mark.asyncio
    async def test_slack_mention_handling(self, mock_slack_adapter):
        """Test handling of @bot mentions in Slack."""
        # Arrange
        mention_context = MessageContext(
            user_id="U123",
            channel_id="C456", 
            channel_type="slack",
            message_text="<@UBOT123> can you help with the server?",
            is_mention=True
        )
        
        # Act
        result = await mock_slack_adapter.receive_event({
            "type": "app_mention",
            "user": "U123",
            "channel": "C456",
            "text": "<@UBOT123> can you help with the server?",
            "ts": "1234567890.123"
        })
        
        # Assert
        assert result["parsed_context"].is_mention is True
        assert "help with the server" in result["parsed_context"].message_text

    @pytest.mark.asyncio
    async def test_slack_thread_handling(self, mock_slack_adapter):
        """Test handling of threaded messages in Slack."""
        # Arrange
        thread_event = {
            "type": "message",
            "user": "U123",
            "channel": "C456", 
            "text": "Follow-up question",
            "ts": "1234567890.456",
            "thread_ts": "1234567890.123"  # This is a thread reply
        }
        
        # Act
        result = await mock_slack_adapter.receive_event(thread_event)
        
        # Assert
        assert result["parsed_context"].thread_ts == "1234567890.123"
        assert result["is_thread_reply"] is True


class TestWorkflowIntegration:
    """Test workflow execution integration."""

    @pytest.mark.asyncio
    async def test_incident_workflow_execution(self, mock_openai_client):
        """Test incident response workflow execution."""
        # Arrange
        processor = MessageProcessor()
        incident_context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack", 
            message_text="URGENT: Production database is down!"
        )
        
        # Mock AI classification for incident
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content='{"type": "incident", "severity": "critical", "category": "database"}')
            )]
        )
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            result = await processor.process_message(incident_context)
        
        # Assert
        assert result.classification_type == "incident"
        assert result.workflow_executed is True
        assert result.escalation_triggered is True

    @pytest.mark.asyncio
    async def test_knowledge_base_workflow(self, mock_openai_client):
        """Test knowledge base lookup workflow."""
        # Arrange
        processor = MessageProcessor()
        kb_context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="How do I reset my password?"
        )
        
        # Mock AI classification for knowledge base query
        mock_openai_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content='{"type": "knowledge_query", "category": "password_reset"}')
            )]
        )
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            result = await processor.process_message(kb_context)
        
        # Assert
        assert result.classification_type == "knowledge_query"
        assert result.knowledge_base_used is True 