"""Integration test for Teams message processing."""
import os
import pytest
from unittest.mock import patch, AsyncMock
from src.channels.teams_adapter import TeamsAdapter
from src.core.message_processor import MessageProcessor
from src.data.models import MessageContext
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Set test environment flag
os.environ["TESTING"] = "1"

class TestTeamsProcessMessage:
    """Test Teams message processing with full workflow."""
    
    @pytest.mark.asyncio
    async def test_teams_should_process_message_successfully(self):
        """Test that Teams adapter processes a knowledge query and triggers the correct workflow."""
        # Mock the AI client to return a knowledge_query classification
        with patch('src.core.message_processor.get_ai_client') as mock_get_ai_client:
            mock_ai_client = AsyncMock()
            mock_ai_client.classify_message.return_value = {"type": "knowledge_query"}
            mock_get_ai_client.return_value = mock_ai_client

            # Mock the knowledge manager
            with patch('src.core.message_processor.LangChainKnowledgeManager') as mock_kb_manager_class:
                mock_kb_manager = AsyncMock()
                mock_kb_manager.search.return_value = "Relevant knowledge"
                mock_kb_manager_class.return_value = mock_kb_manager

                # Initialize MessageProcessor
                message_processor = MessageProcessor()

                # Mock the Teams adapter and its send_message method
                with patch('src.core.message_processor.get_channel_adapter') as mock_get_channel_adapter:
                    mock_teams_adapter = AsyncMock(spec=TeamsAdapter)
                    mock_teams_adapter.send_message = AsyncMock()
                    mock_get_channel_adapter.return_value = mock_teams_adapter

                    # Create a sample message context for Teams
                    context = MessageContext(
                        user_id="test_user",
                        channel_id="test_channel",
                        channel_type="teams",
                        message_text="How do I deploy the application?",
                    )

                    # Process the message
                    await message_processor.process_message(context)

                    # Assert that the AI client was called to classify the message
                    mock_ai_client.classify_message.assert_called_once()

                    # Assert that the knowledge base was searched
                    mock_kb_manager.search.assert_called_once_with(query="How do I deploy the application?")

                    # Assert that a response message was sent
                    mock_teams_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_teams_should_handle_support_request(self):
        """Test that Teams adapter processes a support request and triggers the correct workflow."""
        # Mock the AI client to return a support_request classification
        with patch('src.core.message_processor.get_ai_client') as mock_get_ai_client:
            mock_ai_client = AsyncMock()
            mock_ai_client.classify_message.return_value = {"type": "support_request"}
            mock_ai_client.generate_response.return_value = "A support ticket has been created for you."
            mock_get_ai_client.return_value = mock_ai_client

            # Mock the knowledge manager
            with patch('src.core.message_processor.LangChainKnowledgeManager') as mock_kb_manager_class:
                mock_kb_manager = AsyncMock()
                mock_kb_manager_class.return_value = mock_kb_manager

                # Initialize MessageProcessor
                message_processor = MessageProcessor()

                # Mock the Teams adapter and its send_message method
                with patch('src.core.message_processor.get_channel_adapter') as mock_get_channel_adapter:
                    mock_teams_adapter = AsyncMock(spec=TeamsAdapter)
                    mock_teams_adapter.send_message = AsyncMock()
                    mock_get_channel_adapter.return_value = mock_teams_adapter

                    # Create a sample message context for Teams
                    context = MessageContext(
                        user_id="test_user",
                        channel_id="test_channel",
                        channel_type="teams",
                        message_text="I am having trouble with my login.",
                    )

                    # Process the message
                    await message_processor.process_message(context)

                    # Assert that the AI client was called to classify the message
                    mock_ai_client.classify_message.assert_called_once()

                    # Assert that the knowledge base was NOT searched for a support request
                    mock_kb_manager.search.assert_not_called()

                    # Assert that the AI client was called to generate a response
                    mock_ai_client.generate_response.assert_called_once()

                    # Assert that a response message was sent
                    mock_teams_adapter.send_message.assert_called_once()
