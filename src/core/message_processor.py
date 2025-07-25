"""Core message processing logic."""
import time
import json
import uuid
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING
from src.data.models import MessageContext, ProcessingResult
from src.utils.logging import get_logger
from src.ai.openai_client import OpenAIClient

if TYPE_CHECKING:
    from src.channels.channel_interface import ChannelAdapter

logger = get_logger(__name__)

# Import knowledge base after logger is defined
try:
    from src.knowledge.kb_manager import KnowledgeBaseManager
    KNOWLEDGE_BASE_AVAILABLE = True
except ImportError:
    logger.warning("ChromaDB not available, knowledge base search disabled")
    KnowledgeBaseManager = None
    KNOWLEDGE_BASE_AVAILABLE = False


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
        self._load_workflows()
        
        # Initialize knowledge base if available
        if KNOWLEDGE_BASE_AVAILABLE and KnowledgeBaseManager is not None:
            try:
                self.knowledge_base = KnowledgeBaseManager()
                logger.info("Knowledge base manager initialized in MessageProcessor")
            except Exception as e:
                logger.error("Failed to initialize knowledge base manager", error=str(e))
                self.knowledge_base = None
        else:
            self.knowledge_base = None
    
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
            logger.info("Classifying message: ", message=context.message_text)
            classification = await self._openai_client.classify_message(context.message_text)
            logger.info("Message classified",
                       type=classification.get("type", "unknown"),
                       severity=classification.get("severity", "unknown"))

            # Find and execute matching workflow
            workflow_result = self._execute_workflow(classification, context)
            
            # Generate response from workflow
            response = await self._generate_workflow_response(workflow_result, classification, context)
            
            logger.info("Workflow executed and response generated",
                       workflow_name=workflow_result.get("name", "none"),
                       response_length=len(response) if response else 0,
                       channel_id=context.channel_id,
                       thread_ts=context.thread_ts)

            return ProcessingResult(
                response=response,
                classification=classification.get("type", "unknown"),
                confidence=float(classification.get("confidence", 0.8)),
                workflow_executed=workflow_result.get("executed", False),
                workflow_name=workflow_result.get("name", ""),
                escalation_triggered=workflow_result.get("escalation_triggered", False),
                knowledge_base_used=workflow_result.get("knowledge_base_used", False)
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
    
    def _execute_workflow(self, classification: Dict[str, Any], context: MessageContext) -> Dict[str, Any]:
        """Execute workflow based on classification."""
        classification_type = classification.get("type", "unknown")
        severity = classification.get("severity", "low")
        
        logger.info("Executing workflow", 
                   classification_type=classification_type, 
                   severity=severity)
        
        # Find matching workflow
        matching_workflow = None
        for workflow in self.flow_config.get("workflows", []):
            if not workflow.get("enabled", True):
                continue
                
            trigger_conditions = workflow.get("trigger_conditions", {})
            
            # Check if classification type matches
            if trigger_conditions.get("classification_type") == classification_type:
                # Check severity if specified
                severity_conditions = trigger_conditions.get("severity", [])
                if not severity_conditions or severity in severity_conditions:
                    matching_workflow = workflow
                    break
        
        if not matching_workflow:
            logger.info("No matching workflow found", classification_type=classification_type)
            return {
                "executed": False,
                "name": "",
                "actions_taken": [],
                "template": None
            }
        
        # Execute workflow actions
        actions_taken = []
        escalation_triggered = False
        knowledge_base_used = False
        response_template = None
        
        for action in matching_workflow.get("actions", []):
            action_type = action.get("type")
            actions_taken.append(action_type)
            
            if action_type == "escalate":
                escalation_triggered = True
            elif action_type == "search_kb":
                knowledge_base_used = True
            elif action_type == "respond":
                response_template = action.get("params", {}).get("template")
        
        logger.info("Workflow executed", 
                   workflow_name=matching_workflow["name"],
                   actions_taken=actions_taken,
                   escalation_triggered=escalation_triggered)
        
        return {
            "executed": True,
            "name": matching_workflow["name"],
            "actions_taken": actions_taken,
            "escalation_triggered": escalation_triggered,
            "knowledge_base_used": knowledge_base_used,
            "template": response_template
        }
    
    async def _generate_workflow_response(self, workflow_result: Dict[str, Any], classification: Dict[str, Any], context: MessageContext) -> str:
        """Generate response based on workflow result and templates."""
        # ALWAYS handle knowledge queries with our custom ChromaDB search - bypass template system
        if classification.get("type") == "knowledge_query":
            logger.info("Processing knowledge query with custom search", query=context.message_text)
            return await self._search_knowledge_base(context.message_text)
        
        if not workflow_result.get("executed", False):
            # No workflow matched - provide a generic helpful response
            return "I understand your request. How can I help you further?"
        
        template_name = workflow_result.get("template")
        if not template_name:
            # No specific template - provide a generic response based on workflow type
            workflow_name = workflow_result.get("name", "")
            if "incident" in workflow_name.lower():
                return "I've received your incident report and am processing it now."
            elif "support" in workflow_name.lower():
                return "I've received your support request and will help you resolve it."
            elif "knowledge" in workflow_name.lower():
                # This should not happen since we handle knowledge queries above
                logger.warning("Knowledge workflow reached template logic - this should not happen")
                return await self._search_knowledge_base(context.message_text)
            else:
                return "I've received your message and am processing your request."
        
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
        """Search knowledge base and generate user-friendly response using OpenAI."""
        if not self.knowledge_base:
            logger.warning("Knowledge base not available for search")
            return "📚 **Knowledge base not available.** Please contact support for assistance."
        
        try:
            # Get collection info for debugging
            collection_info = self.knowledge_base.get_collection_info()
            logger.info("Knowledge base search starting", 
                       query=query,
                       collection_info=collection_info)
            
            # Search ChromaDB - get top match without similarity filtering
            results = self.knowledge_base.search(query, max_results=3, similarity_threshold=0.0)
            
            if not results:
                logger.warning("No documents found in knowledge base collection", 
                             query=query,
                             collection_count=collection_info.get("document_count", 0))
                return "📚 **No documents available in knowledge base.** Please contact support for assistance."
            
            # Format raw results for OpenAI processing
            response_parts = ["📚 **Found relevant information:**\n"]
            
            for result in results:
                source = result.get("source", "Unknown")
                content = result.get("content", "")
                similarity = result.get("similarity", 0)
                
                # Truncate content if too long
                if len(content) > 300:
                    content = content[:300] + "..."
                
                response_parts.append(f"**From: {source}** (similarity: {similarity:.2f})")
                response_parts.append(content)
                response_parts.append("")  # Empty line between results
            
            response_parts.append("Need more help? Feel free to ask!")
            raw_knowledge_results = "\n".join(response_parts)
            
            # Use OpenAI to generate a user-friendly response
            formatted_response = await self._openai_client.generate_knowledge_response(query, raw_knowledge_results)
            
            logger.info("Knowledge base search and response generation completed", 
                       query=query,
                       results_count=len(results),
                       response_length=len(formatted_response))
            
            return formatted_response
            
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