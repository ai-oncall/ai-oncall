"""OpenAI client wrapper for AI processing."""
from typing import Any, Dict, Optional
import json
from openai import AsyncOpenAI
from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)

class OpenAIClient:
    """Wrapper for OpenAI API interactions."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self._client = None
        if not config.openai_api_key:
            logger.warning("OpenAI API key not configured, using mock responses")
        else:
            logger.info("Using custom OpenAI base URL", base_url=config.openai_base_url)
            self._client = AsyncOpenAI(
                api_key=config.openai_api_key,
                base_url=config.openai_base_url,
                max_retries=2,
                timeout=config.openai_timeout
            )
            logger.info("OpenAI client initialized", 
                       model=config.openai_model,
                       base_url=config.openai_base_url)
    
    async def classify_message(self, prompt: str) -> Dict[str, str]:
        """Classify a message using OpenAI."""
        logger.info("Classifying message with AI", model=config.openai_model)
        
        if not self._client:
            logger.warning("OpenAI client not initialized, using mock response")
            return self._get_mock_classification_response()
        
        try:
            completion = await self._client.chat.completions.create(
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
            
            # Extract the classification from the response
            classification_text = completion.choices[0].message.content
            logger.info("Message classified successfully",
                       tokens_used=completion.usage.total_tokens,
                       model=completion.model)
            
            try:
                # Parse the JSON response
                classification = json.loads(classification_text)
                return classification
            except json.JSONDecodeError:
                logger.error("Failed to parse classification JSON", text=classification_text)
                return {"type": "unknown", "severity": "unknown"}
            
        except Exception as e:
            logger.exception("Error classifying message", error=str(e))
            return {"type": "unknown", "severity": "unknown"}
    
    async def generate_response(self, prompt: str, context: Optional[Dict] = None) -> str:
        """Generate a response using OpenAI."""
        if not self._client:
            return self._get_mock_response_generation()
            
        try:
            messages = [
                {"role": "system", "content": "You are an AI support assistant. Provide helpful and concise responses."},
                {"role": "user", "content": prompt}
            ]
            
            if context:
                messages.insert(1, {"role": "system", "content": f"Context: {json.dumps(context)}"})
            
            completion = await self._client.chat.completions.create(
                model=config.openai_model,
                messages=messages,
                temperature=config.openai_temperature,
                max_tokens=config.openai_max_tokens
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.exception("Error generating response", error=str(e))
            return "I apologize, but I'm having trouble processing your request right now."
    
    def _get_mock_classification_response(self) -> Dict[str, str]:
        """Get a mock classification response for testing."""
        return {
            "type": "support_request",
            "severity": "low"
        }
    
    def _get_mock_response_generation(self) -> str:
        """Get a mock response for testing."""
        return "I understand your request. How can I help you further?"