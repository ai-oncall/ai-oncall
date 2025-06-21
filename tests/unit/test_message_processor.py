"""Tests for MessageProcessor."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.message_processor import MessageProcessor, get_openai_client, get_channel_adapter
from src.data.models import MessageContext, ProcessingResult


class TestMessageProcessor:
    """Tests for MessageProcessor class."""

    def test_message_processor_initialization(self):
        """Test MessageProcessor can be instantiated."""
        processor = MessageProcessor()
        assert processor.conversation_context == {}

    @pytest.mark.asyncio
    async def test_process_message_success(self):
        """Test successful message processing."""
        processor = MessageProcessor()
        
        # Create test context
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="I need help with login"
        )
        
        # Mock AI client
        mock_ai_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = '{"type": "support_request", "urgency": "medium"}'
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        mock_ai_client.classify_message = AsyncMock(return_value=mock_response)
        
        # Mock channel adapter
        mock_adapter = AsyncMock()
        mock_adapter.send_message = AsyncMock(return_value={"ok": True})
        
        with patch('src.core.message_processor.get_openai_client', return_value=mock_ai_client):
            with patch('src.core.message_processor.get_channel_adapter', return_value=mock_adapter):
                result = await processor.process_message(context)
        
        assert isinstance(result, ProcessingResult)
        assert result.classification_type == "support_request"
        assert result.response_sent is True
        assert result.processing_time_ms >= 0
        mock_ai_client.classify_message.assert_called_once()
        mock_adapter.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_ai_error(self):
        """Test message processing with AI error."""
        processor = MessageProcessor()
        
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Test message"
        )
        
        # Mock AI client to raise exception
        mock_ai_client = AsyncMock()
        mock_ai_client.classify_message = AsyncMock(side_effect=Exception("AI API Error"))
        
        with patch('src.core.message_processor.get_openai_client', return_value=mock_ai_client):
            result = await processor.process_message(context)
        
        assert result.error_occurred is True
        assert "AI API Error" in result.error_message
        assert result.classification_type == "error"

    def test_get_conversation_context_no_thread(self):
        """Test conversation context retrieval without thread."""
        processor = MessageProcessor()
        
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Test message"
        )
        
        # Initially empty
        history = processor._get_conversation_context(context)
        assert history == []
        
        # Add some context
        key = "C456:U123"
        processor.conversation_context[key] = [{"user_message": "previous", "classification": {}}]
        
        history = processor._get_conversation_context(context)
        assert len(history) == 1

    def test_get_conversation_context_with_thread(self):
        """Test conversation context retrieval with thread."""
        processor = MessageProcessor()
        
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Test message",
            thread_ts="1234567890.123"
        )
        
        # Add thread context
        key = "C456:1234567890.123"
        processor.conversation_context[key] = [{"user_message": "thread msg", "classification": {}}]
        
        history = processor._get_conversation_context(context)
        assert len(history) == 1

    def test_build_classification_prompt(self):
        """Test AI classification prompt building."""
        processor = MessageProcessor()
        
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Help with deployment"
        )
        
        history = [{"user_message": "previous message"}]
        prompt = processor._build_classification_prompt(context, history)
        
        assert "Help with deployment" in prompt
        assert "slack" in prompt
        assert "previous message" in prompt

    @pytest.mark.asyncio
    async def test_execute_workflow_incident(self):
        """Test workflow execution for incident."""
        processor = MessageProcessor()
        
        classification = {"type": "incident", "severity": "critical"}
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="URGENT: System down"
        )
        
        result = await processor._execute_workflow(classification, context)
        
        assert result["executed"] is True
        assert result["name"] == "incident_response"
        assert result["escalation_triggered"] is True

    @pytest.mark.asyncio
    async def test_execute_workflow_support_request(self):
        """Test workflow execution for support request."""
        processor = MessageProcessor()
        
        classification = {"type": "support_request", "urgency": "low"}
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Need help with password"
        )
        
        result = await processor._execute_workflow(classification, context)
        
        assert result["executed"] is True
        assert result["name"] == "support_request_workflow"
        # escalation_triggered is not included in non-incident workflows

    @pytest.mark.asyncio
    async def test_execute_workflow_knowledge_query(self):
        """Test workflow execution for knowledge query."""
        processor = MessageProcessor()
        
        classification = {"type": "knowledge_query"}
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="How do I reset password?"
        )
        
        result = await processor._execute_workflow(classification, context)
        
        assert result["executed"] is True
        assert result["name"] == "knowledge_base_lookup"
        assert result["knowledge_base_used"] is True

    @pytest.mark.asyncio
    async def test_generate_response_incident(self):
        """Test response generation for incident."""
        processor = MessageProcessor()
        
        classification = {"type": "incident"}
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="System down"
        )
        workflow_result = {"executed": True}
        
        response = await processor._generate_response(None, classification, context, workflow_result)
        
        assert response is not None
        assert "Incident Acknowledged" in response
        assert "escalated" in response

    def test_update_conversation_context(self):
        """Test conversation context updating."""
        processor = MessageProcessor()
        
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Test message"
        )
        
        classification = {"type": "support_request"}
        response = "Test response"
        
        processor._update_conversation_context(context, classification, response)
        
        key = "C456:U123"
        assert key in processor.conversation_context
        assert len(processor.conversation_context[key]) == 1
        assert processor.conversation_context[key][0]["user_message"] == "Test message"
        assert processor.conversation_context[key][0]["bot_response"] == "Test response"

    def test_update_conversation_context_limit(self):
        """Test conversation context size limit."""
        processor = MessageProcessor()
        
        context = MessageContext(
            user_id="U123",
            channel_id="C456",
            channel_type="slack",
            message_text="Test message"
        )
        
        # Fill beyond limit
        key = "C456:U123"
        processor.conversation_context[key] = [{"msg": f"message {i}"} for i in range(12)]
        
        processor._update_conversation_context(context, {}, "response")
        
        # Should be limited to 10 + 1 new = 10 total (keeps last 10)
        assert len(processor.conversation_context[key]) == 10


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_openai_client(self):
        """Test OpenAI client retrieval."""
        client = get_openai_client()
        assert hasattr(client, 'classify_message')

    def test_get_channel_adapter_slack(self):
        """Test Slack adapter retrieval."""
        adapter = get_channel_adapter("slack")
        assert adapter.get_channel_type() == "slack"

    def test_get_channel_adapter_teams(self):
        """Test Teams adapter retrieval."""
        adapter = get_channel_adapter("teams")
        assert adapter.get_channel_type() == "teams"

    def test_get_channel_adapter_unsupported(self):
        """Test unsupported channel type."""
        with pytest.raises(ValueError, match="Unsupported channel type"):
            get_channel_adapter("discord") 