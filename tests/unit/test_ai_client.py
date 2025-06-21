"""Tests for AI client components."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.ai.openai_client import OpenAIClient


class TestOpenAIClient:
    """Tests for OpenAIClient class."""

    def test_openai_client_initialization(self):
        """Test OpenAI client can be instantiated."""
        client = OpenAIClient()
        assert client is not None

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