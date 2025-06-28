"""Unit tests for message processor workflows."""
import pytest
from unittest.mock import AsyncMock, patch
from src.core.message_processor import MessageProcessor
from src.data.models import MessageContext


@patch('src.core.message_processor.OpenAIClient')
class TestMessageProcessorWorkflows:
    """Test message processor workflow execution."""
    
    @pytest.mark.asyncio
    async def test_support_request_workflow(self, mock_openai_class):
        """Test support request workflow execution."""
        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock classification for support request
        mock_client.classify_message = AsyncMock(return_value={
            "type": "support_request",
            "severity": "medium", 
            "urgency": "medium",
            "confidence": 0.7
        })
        
        # Create processor and context
        processor = MessageProcessor()
        context = MessageContext(
            message_text="I need help with my login",
            channel_type="slack",
            user_id="U123",
            channel_id="C456"
        )
        
        # Process message
        result = await processor.process_message(context)
        
        # Verify support workflow executed
        assert result.classification == "support_request"
        assert result.confidence == 0.7
        assert result.workflow_executed is True
        assert "🎫 **Support ticket created:**" in result.response
        assert result.escalation_triggered is False  # Support requests don't escalate

    @pytest.mark.asyncio
    async def test_deployment_assistance_workflow(self, mock_openai_class):
        """Test deployment assistance workflow execution."""
        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock classification for deployment help
        mock_client.classify_message = AsyncMock(return_value={
            "type": "deployment_help", 
            "severity": "low",
            "confidence": 0.9
        })
        
        # Create processor and context  
        processor = MessageProcessor()
        context = MessageContext(
            message_text="how do I deploy to production?",
            channel_type="slack", 
            user_id="U789",
            channel_id="C101"
        )
        
        # Process message
        result = await processor.process_message(context)
        
        # Verify deployment workflow executed
        assert result.classification == "deployment_help"
        assert result.confidence == 0.9
        assert result.workflow_executed is True
        assert "🚀 **Deployment Information:**" in result.response
        assert result.escalation_triggered is False  # Deployment help doesn't escalate

    @pytest.mark.asyncio  
    async def test_unknown_classification_fallback(self, mock_openai_class):
        """Test behavior when classification type doesn't match any workflow."""
        # Mock OpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock unknown classification
        mock_client.classify_message = AsyncMock(return_value={
            "type": "random_unknown_type",
            "severity": "low", 
            "confidence": 0.3
        })
        
        # Create processor and context
        processor = MessageProcessor()
        context = MessageContext(
            message_text="completely random message",
            channel_type="slack",
            user_id="U999", 
            channel_id="C888"
        )
        
        # Process message
        result = await processor.process_message(context)
        
        # Verify fallback behavior
        assert result.classification == "random_unknown_type"
        assert result.workflow_executed is False  # No matching workflow
        assert result.escalation_triggered is False
        assert "I understand your request" in result.response  # Fallback response 