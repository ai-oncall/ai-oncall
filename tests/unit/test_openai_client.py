"""Unit tests for OpenAI client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ai.openai_client import OpenAIClient


class TestOpenAIClient:
    """Test OpenAI client core functionality."""
    
    @pytest.mark.asyncio
    @patch('src.ai.openai_client.AsyncOpenAI')
    async def test_classify_message_success(self, mock_openai_class):
        """Test successful message classification."""
        # Mock the AsyncOpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock the completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"type": "incident", "severity": "high", "confidence": 0.9}'
        mock_response.usage.total_tokens = 100
        mock_response.model = "gpt-4"
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        client = OpenAIClient()
        result = await client.classify_message("server is down")
        
        assert result["type"] == "incident"
        assert result["severity"] == "high"
        assert result["confidence"] == 0.9
    
    @pytest.mark.asyncio
    @patch('src.ai.openai_client.AsyncOpenAI')
    async def test_classify_message_json_parse_error(self, mock_openai_class):
        """Test handling of malformed JSON response."""
        # Mock the AsyncOpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json"
        mock_response.usage.total_tokens = 50
        mock_response.model = "gpt-4"
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        client = OpenAIClient()
        result = await client.classify_message("test message")
        
        # Should return fallback response
        assert result["type"] == "unknown"
        assert result["severity"] == "unknown"
    
    @pytest.mark.asyncio
    @patch('src.ai.openai_client.AsyncOpenAI')
    async def test_classify_message_http_error(self, mock_openai_class):
        """Test handling of HTTP errors."""
        # Mock the AsyncOpenAI client
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock HTTP error
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("HTTP 500 Error"))
        
        client = OpenAIClient()
        result = await client.classify_message("test message")
        
        # Should return fallback response
        assert result["type"] == "unknown"
        assert result["severity"] == "unknown"
    
    @pytest.mark.asyncio
    async def test_classify_message_no_client(self):
        """Test behavior when OpenAI client is not configured."""
        with patch('src.ai.openai_client.config.openai_api_key', None):
            client = OpenAIClient()
            result = await client.classify_message("test message")
            
            # Should return mock response
            assert result["type"] == "support_request"
            assert result["severity"] == "low"
    
    def test_build_classification_prompt_with_workflows(self):
        """Test dynamic prompt building from workflow config."""
        # Mock workflow config
        mock_flow_config = {
            "workflows": [
                {
                    "trigger_conditions": {
                        "classification_type": "incident",
                        "severity": ["high", "critical"]
                    }
                },
                {
                    "trigger_conditions": {
                        "classification_type": "knowledge_query",
                        "urgency": ["low", "medium"]
                    }
                }
            ]
        }
        
        client = OpenAIClient()
        client.flow_config = mock_flow_config
        
        prompt = client._build_classification_prompt()
        
        # Should contain workflow-specific types
        assert "incident" in prompt
        assert "knowledge_query" in prompt
        assert "high" in prompt
        assert "critical" in prompt 