"""OpenAI client wrapper for AI processing."""
import json
import asyncio
from typing import Any, Dict, Optional
from openai import AsyncOpenAI
from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """Wrapper for OpenAI API interactions."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        if not config.openai_api_key:
            logger.warning("OpenAI API key not configured - using mock responses")
            self._client = None
        else:
            # Configure client with optional base URL for proxy/alternative APIs
            client_kwargs = {
                "api_key": config.openai_api_key,
                "timeout": config.openai_timeout
            }
            
            if config.openai_base_url:
                client_kwargs["base_url"] = config.openai_base_url
                logger.info("Using custom OpenAI base URL", base_url=config.openai_base_url)
            
            self._client = AsyncOpenAI(**client_kwargs)
            logger.info("OpenAI client initialized", 
                       model=config.openai_model,
                       base_url=config.openai_base_url or "default")
    
    async def classify_message(self, prompt: str) -> Any:
        """Classify a message using OpenAI."""
        logger.info("Classifying message with AI", model=config.openai_model)
        
        if not self._client:
            logger.warning("OpenAI client not configured - returning mock response")
            return self._get_mock_classification_response()
        
        try:
            response = await self._client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that classifies support messages. Respond only with valid JSON containing the classification information."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=config.openai_max_tokens,
                temperature=config.openai_temperature,
                response_format={"type": "json_object"}
            )
            
            logger.info("Message classified successfully", 
                       tokens_used=response.usage.total_tokens if response.usage else 0,
                       model=response.model)
            
            return response
            
        except Exception as e:
            logger.error("OpenAI classification failed", error=str(e))
            # Return mock response as fallback
            return self._get_mock_classification_response()
    
    async def generate_response(self, prompt: str, context: Optional[Dict] = None) -> Any:
        """Generate a response using OpenAI."""
        logger.info("Generating response with AI", model=config.openai_model)
        
        if not self._client:
            logger.warning("OpenAI client not configured - returning mock response")
            return self._get_mock_response_generation()
        
        try:
            # Build context-aware prompt
            system_message = """You are a helpful AI assistant for technical support. 
            Provide clear, concise, and actionable responses. Keep responses professional but friendly."""
            
            if context:
                system_message += f"\n\nContext: {json.dumps(context, indent=2)}"
            
            response = await self._client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=config.openai_max_tokens * 2,  # Allow more tokens for responses
                temperature=config.openai_temperature
            )
            
            logger.info("Response generated successfully",
                       tokens_used=response.usage.total_tokens if response.usage else 0,
                       model=response.model)
            
            return response
            
        except Exception as e:
            logger.error("OpenAI response generation failed", error=str(e))
            # Return mock response as fallback
            return self._get_mock_response_generation()
    
    def _get_mock_classification_response(self) -> Any:
        """Get mock classification response for testing/fallback."""
        from unittest.mock import MagicMock
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = json.dumps({
            "type": "support_request",
            "urgency": "medium", 
            "category": "general",
            "confidence": 0.8
        })
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 120
        mock_response.model = "mock-model"
        
        return mock_response
    
    def _get_mock_response_generation(self) -> Any:
        """Get mock response generation for testing/fallback."""
        from unittest.mock import MagicMock
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "I'll help you with that request. Let me look into this for you."
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 85
        mock_response.model = "mock-model"
        
        return mock_response 