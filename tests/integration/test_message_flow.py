"""Integration tests for end-to-end message processing flow."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.data.models import MessageContext
from src.core.message_processor import MessageProcessor
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


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
        mock_openai_client.classify_message.assert_called_once()
        
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
        mock_openai_client.classify_message.return_value = MagicMock(
            choices=[MagicMock(
                message=MagicMock(content='{"type": "incident_report", "severity": "high", "category": "system_outage"}')
            )],
            usage=MagicMock(total_tokens=130)
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
        mock_openai_client.classify_message.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"type": "support_request", "category": "login"}'))], usage=MagicMock(total_tokens=100)),
            MagicMock(choices=[MagicMock(message=MagicMock(content='{"type": "followup", "context": "mobile_app_login"}'))], usage=MagicMock(total_tokens=95))
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
        mock_openai_client.classify_message.side_effect = Exception("OpenAI API Error")
        
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
        mock_openai_client.classify_message.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"type": "deployment_help", "urgency": "low"}'))],
            usage=MagicMock(total_tokens=110)
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

    def test_health_endpoint(self):
        """Test health endpoint is accessible."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_server_startup(self):
        """Test that the server starts up correctly without event loop conflicts."""
        import asyncio
        from unittest.mock import patch, AsyncMock
        
        # Mock uvicorn.Server to avoid actually starting the server
        with patch('uvicorn.Server') as mock_server_class:
            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server
            
            # Import and run the main function
            from src.main import main
            
            # This should not raise an asyncio event loop error
            asyncio.run(main())
            
            # Verify the server was configured and started
            mock_server_class.assert_called_once()
            mock_server.serve.assert_called_once()


class TestSlackIntegration:
    """Test Slack-specific integration scenarios."""

    @pytest.mark.asyncio
    async def test_slack_mention_handling(self, mock_slack_adapter):
        """Test handling of Slack mentions."""
        # Arrange
        processor = MessageProcessor()
        mention_context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="<@UBOT123> help me with deployment",
            is_mention=True
        )
        
        # Act
        with patch('src.core.message_processor.get_channel_adapter', return_value=mock_slack_adapter):
            result = await processor.process_message(mention_context)
        
        # Assert
        assert mention_context.is_mention is True
        assert result.response_sent is True
        mock_slack_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_slack_thread_handling(self, mock_slack_adapter):
        """Test handling of Slack thread messages."""
        # Arrange
        processor = MessageProcessor()
        thread_context = MessageContext(
            user_id="U123",
            channel_id="C456", 
            channel_type="slack",
            message_text="Follow up question",
            thread_ts="1234567890.123"
        )
        
        # Act
        with patch('src.core.message_processor.get_channel_adapter', return_value=mock_slack_adapter):
            result = await processor.process_message(thread_context)
        
        # Assert
        assert thread_context.thread_ts == "1234567890.123"
        assert result.response_sent is True


class TestWorkflowIntegration:
    """Test workflow execution integration."""

    @pytest.mark.asyncio
    async def test_incident_workflow_execution(self, mock_openai_client):
        """Test incident workflow is triggered for high-severity issues."""
        # Arrange
        processor = MessageProcessor()
        incident_context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="URGENT: Production database is down!"
        )
        
        # Mock high-severity incident classification
        mock_openai_client.classify_message.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"type": "incident", "severity": "critical", "category": "database"}'))],
            usage=MagicMock(total_tokens=140)
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
        """Test knowledge base lookup workflow for questions."""
        # Arrange
        processor = MessageProcessor()
        question_context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack", 
            message_text="How do I configure SSL certificates?"
        )
        
        # Mock question classification
        mock_openai_client.classify_message.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"type": "question", "category": "configuration", "topic": "ssl"}'))],
            usage=MagicMock(total_tokens=120)
        )
        
        # Act
        with patch('src.core.message_processor.get_openai_client', return_value=mock_openai_client):
            result = await processor.process_message(question_context)
        
        # Assert
        assert result.classification_type == "question"
        # For now, just verify the message was processed successfully
        assert result.response_sent is True
        assert result.error_occurred is False 