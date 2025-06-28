"""Integration test for Slack message processing."""
import pytest
from unittest.mock import patch, AsyncMock
from src.channels.slack_adapter import SlackAdapter
from src.core.message_processor import MessageProcessor
from src.data.models import MessageContext

class TestSlackProcessMessage:
    """Test Slack message processing with full workflow."""
    
    @pytest.mark.asyncio
    @patch('src.core.message_processor.OpenAIClient')
    async def test_slack_should_process_message_successfully(self, mock_openai_class):
        """Test that Slack adapter processes incident message and triggers correct workflow."""
        # Mock OpenAI client to return incident classification
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock classification response for incident (different from API test)
        mock_client.classify_message = AsyncMock(return_value={
            "type": "incident",
            "severity": "critical",
            "confidence": 0.9
        })
        
        # Create message processor and Slack adapter
        processor = MessageProcessor()
        slack_adapter = SlackAdapter()
        
        # Create message context
        message_context = MessageContext(
            message_text="i think the production server is down",
            channel_type="slack",
            user_id="U123456",
            channel_id="C123456"
        )
        
        # Process message through the workflow
        result = await processor.process_message(message_context)
        
        # Verify the expected response structure
        assert result.response == "🚨 **Incident Acknowledged** \nI've escalated this to the on-call team and created a high-priority ticket. \nExpected response time: 15 minutes."
        assert result.classification == "incident"
        assert result.workflow_executed is True
        assert result.escalation_triggered is True
        assert result.error_occurred is False
        assert result.error_message == "" 