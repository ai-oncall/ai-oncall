"""OpenAI client wrapper for AI processing."""
from typing import Any, Dict, Optional
import json
import yaml
from pathlib import Path
from openai import AsyncOpenAI
from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)

class OpenAIClient:
    """Wrapper for OpenAI API interactions."""
    
    def __init__(self):
        """Initialize the OpenAI client."""
        self._client = None
        self._load_workflow_config()
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
                        "content": self._build_classification_prompt()
                    },
                    {
                        "role": "user", 
                        "content": f"Classify this message: {prompt}"
                    }
                ],
                max_tokens=config.openai_max_tokens,
                temperature=config.openai_temperature,
                response_format={"type": "json_object"}
            )
            
            # Extract the classification from the response
            classification_text = completion.choices[0].message.content
            if not classification_text:
                logger.error("Empty classification response from OpenAI")
                return {"type": "unknown", "severity": "unknown"}
                
            logger.info("Message classified successfully",
                       tokens_used=completion.usage.total_tokens if completion.usage else 0,
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
                context_message = {"role": "system", "content": f"Context: {json.dumps(context)}"}
                messages.insert(1, context_message)
            
            completion = await self._client.chat.completions.create(
                model=config.openai_model,
                messages=messages,
                temperature=config.openai_temperature,
                max_tokens=config.openai_max_tokens
            )

            logger.info("Response generated successfully")
            
            content = completion.choices[0].message.content
            return content if content else "I apologize, but I'm having trouble processing your request right now."
            
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
    
    def _load_workflow_config(self):
        """Load workflow configuration from flow.yaml to extract classification types."""
        try:
            workflow_file = Path("config/flow.yaml")
            if workflow_file.exists():
                with open(workflow_file, 'r') as f:
                    self.flow_config = yaml.safe_load(f)
                logger.info("Loaded workflow config for classification", 
                           workflows=len(self.flow_config.get("workflows", [])))
            else:
                logger.warning("flow.yaml not found, using default classification types")
                self.flow_config = {"workflows": []}
        except Exception as e:
            logger.error("Error loading workflow config", error=str(e))
            self.flow_config = {"workflows": []}
    
    def _build_classification_prompt(self) -> str:
        """Build classification prompt dynamically from workflow configuration."""
        # Extract unique classification types from workflows
        classification_types = set()
        severity_values = set()
        urgency_values = set()
        
        for workflow in self.flow_config.get("workflows", []):
            trigger_conditions = workflow.get("trigger_conditions", {})
            
            # Get classification type
            if "classification_type" in trigger_conditions:
                classification_types.add(trigger_conditions["classification_type"])
            
            # Get severity values
            if "severity" in trigger_conditions:
                severity_list = trigger_conditions["severity"]
                if isinstance(severity_list, list):
                    severity_values.update(severity_list)
                else:
                    severity_values.add(severity_list)
            
            # Get urgency values  
            if "urgency" in trigger_conditions:
                urgency_list = trigger_conditions["urgency"]
                if isinstance(urgency_list, list):
                    urgency_values.update(urgency_list)
                else:
                    urgency_values.add(urgency_list)
        
        # Fallback to default types if no workflows found
        if not classification_types:
            classification_types = {"incident", "knowledge_query", "support_request", "deployment_help"}
            logger.warning("No classification types found in workflows, using defaults")
        
        if not severity_values:
            severity_values = {"low", "medium", "high", "critical"}
        
        if not urgency_values:
            urgency_values = {"low", "medium", "high"}
        
        # Build dynamic prompt
        types_list = " | ".join(sorted(classification_types))
        severity_list = " | ".join(sorted(severity_values))
        urgency_list = " | ".join(sorted(urgency_values))
        
        prompt = f"""You are a message classifier for an IT support system. Classify the message into one of these exact types based on the configured workflows:

Classification Types: {types_list}

Guidelines:
- "incident" - System outages, production issues, critical failures, servers down, service disruptions
- "knowledge_query" - Questions asking for information, how-to guides, documentation requests  
- "support_request" - Help requests, user issues, non-critical problems, general assistance
- "deployment_help" - Deployment help, release questions, deployment guides

Severity levels: {severity_list}
Urgency levels: {urgency_list}

Respond ONLY with valid JSON in this format:
{{"type": "{types_list}", "severity": "{severity_list}", "urgency": "{urgency_list}", "confidence": 0.8}}

Include all fields. Use "low" as default for severity/urgency if not clearly specified."""
        
        return prompt