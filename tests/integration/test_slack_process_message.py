"""Integration test for Slack message processing."""
import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from src.channels.slack_adapter import SlackAdapter
from src.core.message_processor import MessageProcessor
from src.data.models import MessageContext
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Set test environment flag
os.environ["TESTING"] = "1"

class TestSlackProcessMessage:
    """Test Slack message processing with full workflow."""
    
    @pytest.mark.asyncio
    async def test_slack_should_process_message_successfully(self):
        """Test that Slack adapter processes incident message and triggers correct workflow."""
        # Mock OpenAI client to return incident classification
        with patch('src.ai.openai_client.OpenAIClient') as mock_openai_class:
            mock_client = AsyncMock()
            mock_client.classify_message = AsyncMock(return_value={
                "type": "incident",
                "severity": "critical",
                "confidence": 0.9
            })
            mock_openai_class.return_value = mock_client
            
            # Mock the knowledge base search method
            with patch('src.knowledge.langchain_kb_manager.LangChainKnowledgeManager.search_with_chain', 
                      new_callable=AsyncMock, return_value="Knowledge base search results"):
                
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
                assert "incident acknowledged" in result.response.lower()
                assert "escalated" in result.response.lower()
                assert result.classification == "incident"
                assert result.workflow_executed is True
                assert result.escalation_triggered is True
                assert result.error_occurred is False
                
                # Verify our mocks were called correctly
                mock_client.classify_message.assert_called_once()
                
                logger.info("Slack message test passed successfully")