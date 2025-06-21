"""Tests for AI client components."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ai.openai_client import OpenAIClient


class TestOpenAIClient:
    """Tests for OpenAIClient class."""

    def test_openai_client_initialization(self):
        """Test OpenAI client can be instantiated."""
        client = OpenAIClient()
        assert client is not None

    @patch('src.ai.openai_client.config')
    def test_openai_client_initialization_with_api_key(self, mock_config):
        """Test OpenAI client initialization with API key."""
        mock_config.openai_api_key = "test-api-key"
        mock_config.openai_timeout = 30
        mock_config.openai_base_url = None
        mock_config.openai_model = "gpt-3.5-turbo"
        
        with patch('src.ai.openai_client.AsyncOpenAI') as mock_openai:
            client = OpenAIClient()
            mock_openai.assert_called_once_with(
                api_key="test-api-key",
                timeout=30
            )

    @patch('src.ai.openai_client.config')
    def test_openai_client_initialization_with_base_url(self, mock_config):
        """Test OpenAI client initialization with custom base URL."""
        mock_config.openai_api_key = "test-api-key"
        mock_config.openai_timeout = 30
        mock_config.openai_base_url = "https://custom-api.example.com"
        mock_config.openai_model = "gpt-3.5-turbo"
        
        with patch('src.ai.openai_client.AsyncOpenAI') as mock_openai:
            client = OpenAIClient()
            mock_openai.assert_called_once_with(
                api_key="test-api-key",
                timeout=30,
                base_url="https://custom-api.example.com"
            )

    @patch('src.ai.openai_client.config')
    def test_openai_client_initialization_no_api_key(self, mock_config):
        """Test OpenAI client initialization without API key."""
        mock_config.openai_api_key = ""
        
        client = OpenAIClient()
        assert client._client is None

    @pytest.mark.asyncio
    async def test_classify_message(self):
        """Test message classification."""
        client = OpenAIClient()
        
        result = await client.classify_message("I need help with login")
        
        assert result is not None
        assert hasattr(result, 'choices')
        assert hasattr(result, 'usage')
        assert len(result.choices) > 0
        assert hasattr(result.choices[0], 'message')
        assert hasattr(result.choices[0].message, 'content')

    @pytest.mark.asyncio
    @patch('src.ai.openai_client.config')
    async def test_classify_message_with_real_client(self, mock_config):
        """Test message classification with real client."""
        mock_config.openai_api_key = "test-key"
        mock_config.openai_timeout = 30
        mock_config.openai_base_url = None
        mock_config.openai_model = "gpt-3.5-turbo"
        mock_config.openai_max_tokens = 500
        mock_config.openai_temperature = 0.7
        
        with patch('src.ai.openai_client.AsyncOpenAI') as mock_openai:
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = '{"type": "support", "confidence": 0.9}'
            mock_response.usage.total_tokens = 150
            mock_response.model = "gpt-3.5-turbo"
            
            mock_client_instance.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient()
            result = await client.classify_message("Help with login")
            
            assert result == mock_response
            mock_client_instance.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.ai.openai_client.config')
    async def test_classify_message_api_error(self, mock_config):
        """Test message classification when API call fails."""
        mock_config.openai_api_key = "test-key"
        mock_config.openai_timeout = 30
        mock_config.openai_base_url = None
        
        with patch('src.ai.openai_client.AsyncOpenAI') as mock_openai:
            mock_client_instance = AsyncMock()
            mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient()
            result = await client.classify_message("Test message")
            
            # Should return mock response on error
            assert result is not None
            assert hasattr(result, 'choices')

    @pytest.mark.asyncio
    async def test_classify_message_response_format(self):
        """Test that classification response has expected format."""
        client = OpenAIClient()
        
        result = await client.classify_message("URGENT: Server is down!")
        
        # Check response structure
        content = result.choices[0].message.content
        assert isinstance(content, str)
        
        # Content should be JSON-like string for classification
        assert "{" in content or "type" in content

    @pytest.mark.asyncio
    async def test_classify_message_token_usage(self):
        """Test that token usage is tracked."""
        client = OpenAIClient()
        
        result = await client.classify_message("Short message")
        
        assert hasattr(result.usage, 'total_tokens')
        assert isinstance(result.usage.total_tokens, int)
        assert result.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_generate_response(self):
        """Test response generation."""
        client = OpenAIClient()
        
        result = await client.generate_response("Generate helpful response", {"type": "support"})
        
        assert result is not None
        assert hasattr(result, 'choices')
        assert hasattr(result, 'usage')
        assert len(result.choices) > 0

    @pytest.mark.asyncio
    @patch('src.ai.openai_client.config')
    async def test_generate_response_with_real_client(self, mock_config):
        """Test response generation with real client."""
        mock_config.openai_api_key = "test-key"
        mock_config.openai_timeout = 30
        mock_config.openai_base_url = None
        mock_config.openai_model = "gpt-3.5-turbo"
        mock_config.openai_max_tokens = 500
        mock_config.openai_temperature = 0.7
        
        with patch('src.ai.openai_client.AsyncOpenAI') as mock_openai:
            mock_client_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "I can help you with that request."
            mock_response.usage.total_tokens = 85
            mock_response.model = "gpt-3.5-turbo"
            
            mock_client_instance.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient()
            result = await client.generate_response("Help needed", {"type": "support"})
            
            assert result == mock_response
            mock_client_instance.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.ai.openai_client.config')
    async def test_generate_response_api_error(self, mock_config):
        """Test response generation when API call fails."""
        mock_config.openai_api_key = "test-key"
        mock_config.openai_timeout = 30
        mock_config.openai_base_url = None
        
        with patch('src.ai.openai_client.AsyncOpenAI') as mock_openai:
            mock_client_instance = AsyncMock()
            mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client_instance
            
            client = OpenAIClient()
            result = await client.generate_response("Test prompt")
            
            # Should return mock response on error
            assert result is not None
            assert hasattr(result, 'choices')

    @pytest.mark.asyncio
    async def test_generate_response_with_context(self):
        """Test response generation with context."""
        client = OpenAIClient()
        
        context = {
            "classification": "incident",
            "severity": "high",
            "user_history": ["Previous support request"]
        }
        
        result = await client.generate_response("Help with incident", context)
        
        content = result.choices[0].message.content
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_generate_response_no_context(self):
        """Test response generation without context."""
        client = OpenAIClient()
        
        result = await client.generate_response("Help needed")
        
        content = result.choices[0].message.content
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_multiple_classify_calls(self):
        """Test multiple classification calls."""
        client = OpenAIClient()
        
        # Test that multiple calls work independently
        result1 = await client.classify_message("Help with password")
        result2 = await client.classify_message("Server is down")
        
        assert result1 is not None
        assert result2 is not None
        assert result1 != result2  # Should be different objects

    @pytest.mark.asyncio
    async def test_classify_empty_message(self):
        """Test classification of empty message."""
        client = OpenAIClient()
        
        result = await client.classify_message("")
        
        assert result is not None
        # Should still return a valid response structure even for empty input
        assert hasattr(result, 'choices')
        assert hasattr(result, 'usage')

    @pytest.mark.asyncio 
    async def test_classify_long_message(self):
        """Test classification of long message."""
        client = OpenAIClient()
        
        long_message = "Help me " * 100  # Create a long message
        result = await client.classify_message(long_message)
        
        assert result is not None
        assert result.usage.total_tokens > 0

    def test_mock_classification_response_structure(self):
        """Test mock classification response has correct structure."""
        client = OpenAIClient()
        mock_response = client._get_mock_classification_response()
        
        assert hasattr(mock_response, 'choices')
        assert len(mock_response.choices) > 0
        assert hasattr(mock_response.choices[0], 'message')
        assert hasattr(mock_response.choices[0].message, 'content')
        assert hasattr(mock_response, 'usage')
        assert hasattr(mock_response.usage, 'total_tokens')

    def test_mock_response_generation_structure(self):
        """Test mock response generation has correct structure."""
        client = OpenAIClient()
        mock_response = client._get_mock_response_generation()
        
        assert hasattr(mock_response, 'choices')
        assert len(mock_response.choices) > 0
        assert hasattr(mock_response.choices[0], 'message')
        assert hasattr(mock_response.choices[0].message, 'content')
        assert hasattr(mock_response, 'usage')
        assert hasattr(mock_response.usage, 'total_tokens') 