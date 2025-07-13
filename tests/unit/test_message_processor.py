"""Unit tests for message processor workflows."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.message_processor import MessageProcessor
from src.data.models import MessageContext
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Set test environment flag
os.environ["TESTING"] = "1"


class TestMessageProcessorWorkflows:
    """Test message processor workflow execution."""

    def setup_method(self):
        """Set up test environment before each test."""
        os.environ["TESTING"] = "1"

    @pytest.mark.asyncio
    async def test_support_request_workflow(self):
        """Test support request workflow execution."""
        with patch("src.ai.langchain_client.LangChainAIClient") as mock_langchain_class:
            # Mock LangChain client
            mock_client = AsyncMock()
            mock_langchain_class.return_value = mock_client

            # Mock classification for support request
            mock_client.classify_message = AsyncMock(
                return_value={
                    "type": "support_request",
                    "severity": "medium",
                    "urgency": "medium",
                    "confidence": 0.7,
                }
            )

            # Mock the knowledge base search method
            with patch(
                "src.knowledge.langchain_kb_manager.LangChainKnowledgeManager.search_with_chain",
                new_callable=AsyncMock,
                return_value="Knowledge base search results",
            ):
                # Create processor and context after mocks are in place
                processor = MessageProcessor()
                context = MessageContext(
                    message_id="MSG_001",  # Add required field
                    message_text="I need help with my login",
                    channel_type="slack",
                    user_id="U123",
                    channel_id="C456",
                )

                # Process message
                result = await processor.process_message(context)

                # Verify LangChain client was called correctly
                mock_langchain_class.assert_called_once()
                mock_client.classify_message.assert_called_once()

                # Verify support workflow executed
                assert result.classification == "support_request"
                assert result.workflow_executed is True
                assert "support ticket" in result.response.lower()
                assert result.error_occurred is False

    @pytest.mark.asyncio
    async def test_knowledge_query_workflow(self):
        """Test knowledge query workflow execution."""
        with patch("src.ai.langchain_client.LangChainAIClient") as mock_langchain_class:
            # Mock LangChain client
            mock_client = AsyncMock()
            mock_langchain_class.return_value = mock_client

            # Mock classification for knowledge query
            mock_client.classify_message = AsyncMock(
                return_value={
                    "type": "knowledge_query",
                    "severity": "low",
                    "confidence": 0.8,
                }
            )

            # Set up a proper knowledge base search response
            kb_response = "Here's how to reset your password: Go to settings and click 'Reset Password'"

            # Mock the knowledge base search method
            with patch(
                "src.knowledge.langchain_kb_manager.LangChainKnowledgeManager.search_with_chain",
                new_callable=AsyncMock,
                return_value=kb_response,
            ):
                # Create processor and context after mocks are in place
                processor = MessageProcessor()
                context = MessageContext(
                    message_id="MSG_002",  # Add required field
                    message_text="How do I reset my password?",
                    channel_type="slack",
                    user_id="U123",
                    channel_id="C456",
                )

                # Process message
                result = await processor.process_message(context)

                # Verify knowledge workflow executed
                assert result.classification == "knowledge_query"
                assert "reset your password" in result.response
                assert result.error_occurred is False

                logger.info("Knowledge query workflow test passed")

    @pytest.mark.asyncio
    async def test_unknown_classification_fallback(self):
        """Test fallback for unknown classification."""
        with patch("src.ai.langchain_client.LangChainAIClient") as mock_langchain_class:
            # Mock LangChain client with unknown classification
            mock_client = AsyncMock()
            mock_langchain_class.return_value = mock_client
            mock_client.classify_message = AsyncMock(
                return_value={"type": "unknown", "confidence": 0.3}
            )

            # Mock the knowledge base search method
            with patch(
                "src.knowledge.langchain_kb_manager.LangChainKnowledgeManager.search_with_chain",
                new_callable=AsyncMock,
                return_value="Knowledge base search results",
            ):
                # Create processor and context
                processor = MessageProcessor()
                context = MessageContext(
                    message_id="MSG_003",  # Add required field
                    message_text="Random message that doesn't match any category",
                    channel_type="slack",
                    user_id="U123",
                    channel_id="C456",
                )

                # Process message
                result = await processor.process_message(context)

                # Verify we got a generic fallback response
                assert result.classification == "unknown"
                assert result.workflow_executed is False
                assert "I understand your request" in result.response
                assert result.error_occurred is False

                logger.info("Unknown classification fallback test passed")
