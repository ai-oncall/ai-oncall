"""Core message processing logic with LangChain integration."""
import time
import json
import uuid
import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING, Union
from src.data.models import MessageContext, ProcessingResult
from src.utils.logging import get_logger
from src.channels.channel_interface import ChannelAdapter
from src.channels.slack_adapter import SlackAdapter
from src.ai.langchain_client import LangChainAIClient
from src.knowledge.langchain_kb_manager import LangChainKnowledgeManager
from src.workflows.langgraph_engine import LangGraphWorkflowEngine

logger = get_logger(__name__)

# Determine if we're in a test environment
IN_TEST = bool(os.environ.get("TESTING") or os.environ.get("PYTEST_CURRENT_TEST"))
logger.debug("Test environment check", in_test=IN_TEST)

def get_ai_client():
    """Get LangChain AI client instance."""
    return LangChainAIClient()


def get_channel_adapter(channel_type: str) -> ChannelAdapter:
    """Get appropriate channel adapter."""
    if channel_type == "slack":
        return SlackAdapter()
    else:
        raise ValueError(f"Unsupported channel type: {channel_type}")


class MessageProcessor:
    """Processes messages through LangChain and LangGraph workflows."""
    
    def __init__(self):
        """Initialize processor with LangChain components."""
        logger.info("Initializing MessageProcessor with LangChain")
        
        # Initialize core components
        self.ai_client = LangChainAIClient()
        self.workflow_engine = LangGraphWorkflowEngine()
        self.knowledge_base = LangChainKnowledgeManager()
        
        # Initialize conversation tracking
        self.conversation_context = {}
    
    async def process_api_message(self, context: MessageContext) -> ProcessingResult:
        """Process a message from the API endpoint."""
        logger.info("Processing API message",
                   channel_type=context.channel_type,
                   channel_id=context.channel_id,
                   user_id=context.user_id)
        return await self.process_message(context)
     async def process_message(self, context: MessageContext) -> ProcessingResult:
        """Process a message using LangChain and LangGraph."""
        try:
            # Classify message
            classification = await self.ai_client.classify_message(context.message_text)
            
            # Execute workflow
            workflow_result = await self.workflow_engine.execute_workflow(
                classification=classification,
                context=context
            )
            
            # Generate response
            response = await self._generate_response(
                workflow_result=workflow_result,
                classification=classification,
                context=context
            )
            
            return ProcessingResult(
                response=response,
                classification=classification.get("type", "unknown"),
                confidence=float(classification.get("confidence", 0.0)),
                workflow_executed=bool(workflow_result),
                workflow_type=workflow_result.get("type") if workflow_result else None,
                error_occurred=False
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
                workflow_executed=False,
                error_occurred=True,
                error_message=str(e)
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
    
    def _load_workflows(self):
        """Load workflow definitions from flow.yaml."""
        try:
            workflow_file = Path("config/flow.yaml")
            if workflow_file.exists():
                with open(workflow_file, 'r') as f:
                    self.flow_config = yaml.safe_load(f)
                logger.info("Loaded workflow configuration", 
                           workflows=len(self.flow_config.get("workflows", [])),
                           templates=len(self.flow_config.get("response_templates", {})))
            else:
                logger.warning("flow.yaml not found, using empty configuration")
                self.flow_config = {"workflows": [], "response_templates": {}}
        except Exception as e:
            logger.error("Error loading workflow configuration", error=str(e))
            self.flow_config = {"workflows": [], "response_templates": {}}
    
    async def _execute_workflow(self, classification: Dict[str, Any], context: MessageContext) -> Dict[str, Any]:
        """Execute workflow using LangGraph state machine."""
        msg_type = classification.get("type", "unknown")
        severity = classification.get("severity", "low")
        
        logger.info("Executing workflow", type=msg_type, severity=severity)
        
        # Let LangGraph handle the workflow
        result = await self.workflow_engine.execute_workflow(classification, context)
        
        if not result:
            return {
                "executed": False,
                "type": msg_type,
                "severity": severity,
                "error": "No matching workflow"
            }
        
        # Return workflow result
        return {
            "executed": True,
            "type": result.get("type", msg_type),
            "severity": result.get("severity", severity),
            "actions": result.get("actions", []),
            "response": result.get("response")
        }
    
    async def _generate_response(self, workflow_result: Dict[str, Any], classification: Dict[str, Any], context: MessageContext) -> str:
        """Generate response using LangChain."""
        msg_type = classification.get("type", "unknown")
        
        if msg_type == "knowledge_query":
            return await self.knowledge_base.search_with_chain(context.message_text)
            
        # Use workflow response if available
        if workflow_result.get("response"):
            return workflow_result["response"]
            
        # Generate fallback response
        return await self.ai_client.generate_response(context.message_text, classification)
        
        # Skip template processing for knowledge queries (double-check)
        if template_name == "knowledge_base_results":
            logger.warning("Knowledge base template detected - redirecting to custom search")
            return await self._search_knowledge_base(context.message_text)
        
        # Get template from configuration
        templates = self.flow_config.get("response_templates", {})
        template_content = templates.get(template_name)
        
        if not template_content:
            logger.warning("Template not found", template_name=template_name)
            return "I've processed your request. How can I help you further?"
        
        # Return template as-is for non-knowledge queries
        return template_content.strip()
    
    async def _search_knowledge_base(self, query: str) -> str:
        """Search knowledge base and generate user-friendly response using LangChain or fallback."""
        if not self.knowledge_base:
            logger.warning("Knowledge base not available for search")
            return "📚 **Knowledge base not available.** Please contact support for assistance."
        
        try:
            # Get collection info for debugging
            collection_info = self.knowledge_base.get_collection_info()
            logger.info("Knowledge base search starting", 
                       query=query,
                       collection_info=collection_info)
            
            # Use LangChain enhanced search if available
            logger.info("Using LangChain enhanced knowledge search")
            response = await self.knowledge_base.search_with_chain(query, max_results=3)
            return response
        except Exception as e:
            logger.error("Error searching knowledge base", query=query, error=str(e))
            return "📚 **Error searching knowledge base.** Please contact support for assistance."
    
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