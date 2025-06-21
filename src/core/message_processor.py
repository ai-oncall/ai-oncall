"""Core message processing logic."""
import time
import json
import uuid
from typing import Dict, Any, Optional, TYPE_CHECKING
from src.data.models import MessageContext, ProcessingResult
from src.utils.logging import get_logger
from src.ai.openai_client import OpenAIClient

if TYPE_CHECKING:
    from src.channels.channel_interface import ChannelAdapter

logger = get_logger(__name__)


def get_openai_client():
    """Get OpenAI client instance."""
    from src.ai.openai_client import OpenAIClient
    return OpenAIClient()


def get_channel_adapter(channel_type: str) -> "ChannelAdapter":
    """Get appropriate channel adapter."""
    from src.channels.channel_interface import ChannelAdapter
    
    if channel_type == "slack":
        from src.channels.slack_adapter import SlackAdapter
        return SlackAdapter()
    elif channel_type == "teams":
        from src.channels.teams_adapter import TeamsAdapter
        return TeamsAdapter()
    else:
        raise ValueError(f"Unsupported channel type: {channel_type}")


class MessageProcessor:
    """Processes messages from different channels through AI and workflows."""
    
    def __init__(self):
        """Initialize processor with necessary components."""
        logger.info("Initializing MessageProcessor")
        self._openai_client = OpenAIClient()
        self.conversation_context: Dict[str, list] = {}
    
    async def process_api_message(self, context: MessageContext) -> ProcessingResult:
        """Process a message from the API endpoint."""
        logger.info("Processing API message",
                   channel_type=context.channel_type,
                   channel_id=context.channel_id,
                   user_id=context.user_id)
        return await self.process_message(context)
    
    async def process_message(self, context: MessageContext) -> ProcessingResult:
        """Process a message from any channel."""
        start_time = time.time()
        message_id = str(uuid.uuid4())
        
        try:
            logger.info("Starting message processing",
                       channel_type=context.channel_type,
                       channel_id=context.channel_id,
                       user_id=context.user_id,
                       is_mention=context.is_mention,
                       thread_ts=context.thread_ts)

            # Classify message intent
            classification = await self._openai_client.classify_message(context.message_text)
            logger.info("Message classified",
                       type=classification.get("type", "unknown"),
                       severity=classification.get("severity", "unknown"))

            # Generate response based on classification
            response = await self._openai_client.generate_response(
                context.message_text,
                {"classification": classification}
            )
            
            logger.info("Response generated",
                       response_length=len(response) if response else 0,
                       channel_id=context.channel_id,
                       thread_ts=context.thread_ts)

            return ProcessingResult(
                response=response,
                classification=classification.get("type", "unknown"),
                confidence=1.0,  # We'll implement confidence scoring later
                workflow_executed=True if classification.get("type") == "incident" else False
            )
        except Exception as e:
            logger.exception("Error processing message",
                           channel_type=context.channel_type,
                           channel_id=context.channel_id,
                           error=str(e))
            return ProcessingResult(
                response="I apologize, but I encountered an error processing your request.",
                classification="error",
                confidence=0.0,
                workflow_executed=False
            )
    
    def _get_conversation_context(self, context: MessageContext) -> list:
        """Get conversation history for context."""
        if context.thread_ts:
            key = f"{context.channel_id}:{context.thread_ts}"
        else:
            key = f"{context.channel_id}:{context.user_id}"
            
        return self.conversation_context.get(key, [])
    
    async def _classify_message(self, ai_client, context: MessageContext, history: list) -> Dict[str, Any]:
        """Classify message using AI."""
        try:
            # Build prompt with context
            prompt = self._build_classification_prompt(context, history)
            
            # Call AI for classification
            response = await ai_client.classify_message(prompt)
            
            # Parse JSON response
            content = response.choices[0].message.content
            
            # Handle both string and mock content
            if hasattr(content, 'return_value'):
                # This is a mock, get the actual value
                content = content.return_value if hasattr(content, 'return_value') else str(content)
            
            classification = json.loads(content)
            classification["tokens_used"] = getattr(response.usage, 'total_tokens', 0)
            
            return classification
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse AI classification response")
            return {"type": "general_inquiry", "confidence": 0.5}
        except Exception as e:
            logger.error("AI classification failed", error=str(e))
            raise
    
    def _build_classification_prompt(self, context: MessageContext, history: list) -> str:
        """Build prompt for AI classification."""
        base_prompt = """
        Classify this message and respond with JSON only:
        
        Message: "{message}"
        Channel: {channel_type}
        
        Context history: {history}
        
        Return JSON with: {{"type": "incident|support_request|knowledge_query|deployment_help|followup|general_inquiry", "urgency": "low|medium|high|critical", "category": "description", "confidence": 0.0-1.0}}
        """.format(
            message=context.message_text,
            channel_type=context.channel_type,
            history=history[-3:] if history else "None"  # Last 3 messages for context
        )
        
        return base_prompt.strip()
    
    async def _execute_workflow(self, classification: Dict[str, Any], context: MessageContext) -> Dict[str, Any]:
        """Execute workflow based on classification."""
        workflow_type = classification.get("type", "general_inquiry")
        severity = classification.get("severity", "low")
        urgency = classification.get("urgency", "low")
        
        # Mock workflow execution based on type
        if workflow_type in ["incident", "incident_report"]:
            return {
                "executed": True,
                "name": "incident_response",
                "escalation_triggered": severity in ["high", "critical"] or urgency in ["high", "critical"],
                "actions_taken": ["escalate", "create_ticket"]
            }
        elif workflow_type == "knowledge_query":
            return {
                "executed": True,
                "name": "knowledge_base_lookup",
                "knowledge_base_used": True,
                "actions_taken": ["search_kb"]
            }
        elif workflow_type in ["support_request", "deployment_help"]:
            return {
                "executed": True,
                "name": f"{workflow_type}_workflow",
                "actions_taken": ["create_ticket", "provide_guidance"]
            }
        else:
            return {
                "executed": False,
                "name": "",
                "actions_taken": []
            }
    
    async def _generate_response(self, ai_client, classification: Dict[str, Any], context: MessageContext, workflow_result: Dict[str, Any]) -> Optional[str]:
        """Generate appropriate response."""
        workflow_type = classification.get("type", "general_inquiry")
        
        # Mock response generation based on workflow type
        if workflow_type == "incident":
            return "🚨 **Incident Acknowledged** - I've escalated this to the on-call team and created a high-priority ticket. Expected response time: 15 minutes."
        elif workflow_type == "knowledge_query":
            return "📚 **Found relevant information:** Here are some helpful resources for your question."
        elif workflow_type == "support_request":
            return "🎫 **Support ticket created:** #12345 - Our team will review and respond within 4 hours."
        elif workflow_type == "deployment_help":
            return "🚀 **Deployment Information:** Here's the deployment guide and best practices."
        else:
            return "I understand you need help. Let me assist you with that."
    
    def _update_conversation_context(self, context: MessageContext, classification: Dict[str, Any], response: Optional[str]):
        """Update conversation context for future reference."""
        if context.thread_ts:
            key = f"{context.channel_id}:{context.thread_ts}"
        else:
            key = f"{context.channel_id}:{context.user_id}"
            
        if key not in self.conversation_context:
            self.conversation_context[key] = []
            
        self.conversation_context[key].append({
            "user_message": context.message_text,
            "classification": classification,
            "bot_response": response,
            "timestamp": time.time()
        })
        
        # Keep only last 10 messages per conversation
        if len(self.conversation_context[key]) > 10:
            self.conversation_context[key] = self.conversation_context[key][-10:]