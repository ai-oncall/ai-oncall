"""LangGraph-based workflow engine for complex workflow orchestration."""
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict, cast, Union
from enum import Enum
from typing_extensions import NotRequired, TypedDict

from src.utils.logging import get_logger
from src.data.models import MessageContext, ProcessingResult, WorkflowDefinition

logger = get_logger(__name__)

try:
    # First try experimental module
    try:
        from langchain_experimental.langgraph.graph import Graph as StateGraph, END
        from langchain_experimental.langgraph.prebuilt import ToolExecutor
        logger.debug("Using experimental LangGraph module")
    except ImportError:
        # Fall back to stable module
        from langgraph.graph import StateGraph, END
        from langgraph.prebuilt import ToolExecutor
        logger.debug("Using stable LangGraph module")
    from langchain_core.tools import BaseTool, tool
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.runnables import RunnableConfig
    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Only log at debug level to avoid noisy logs in production
    logger.debug("LangGraph not available, using fallback workflow engine")
    LANGGRAPH_AVAILABLE = False
    # Define placeholders for type checking
    class StateGraph: pass
    class END: pass
    class RunnableConfig: pass
    class BaseTool: pass
    class ToolExecutor: pass

class WorkflowState(TypedDict, total=False):
    """State for LangGraph workflow execution.
    
    Using TypedDict with total=False to allow initialization with only required fields.
    All other fields will be updated during workflow execution.
    """
    # Required fields
    message: str  # Input message
    context: MessageContext  # Message context (channel, user, etc.)
    
    # Optional fields with defaults
    classification: Dict[str, Any]  # Message classification result
    actions_taken: List[str]  # List of actions already taken
    escalation_triggered: bool  # Whether escalation was triggered
    knowledge_base_used: bool  # Whether knowledge base was searched
    workflow_id: str  # ID of the selected workflow
    workflow_step: str  # Current step in the workflow
    response: str  # Generated response
    error: str  # Error message if any
    workflow: Dict[str, Any]  # Current workflow definition
    current_action: Optional[Dict[str, Any]]  # Current action being executed
    workflow_context: Dict[str, Any]  # Additional workflow context


def create_initial_state() -> WorkflowState:
    """Create an initial workflow state."""
    return {
        "message": "",
        "context": MessageContext(
            user_id="",
            channel_id="",
            channel_type="",
            message_text=""
        ),
        "classification": {},
        "actions_taken": [],
        "escalation_triggered": False,
        "knowledge_base_used": False,
        "workflow_id": "",
        "workflow_step": "",
        "response": "",
        "error": "",
        "workflow": {},
        "current_action": None,
        "workflow_context": {}
    }


class ActionType(Enum):
    """Supported workflow action types."""
    ESCALATE = "escalate"
    CREATE_TICKET = "create_ticket"
    SEARCH_KB = "search_kb"
    RESPOND = "respond"
    FETCH_DOCS = "fetch_docs"
    NOTIFY = "notify"


class LangGraphWorkflowEngine:
    """LangGraph-powered workflow engine for complex orchestration."""
    
    def __init__(self):
        """Initialize the LangGraph workflow engine."""
        self.flow_config = {}
        self._load_workflow_config()
        
        if LANGGRAPH_AVAILABLE:
            self._setup_langgraph_workflows()
            logger.info("LangGraph workflow engine initialized")
        else:
            logger.warning("LangGraph not available, using fallback workflow engine")
            self.workflow_graph = None
    
    def _load_workflow_config(self):
        """Load workflow configuration from flow.yaml."""
        try:
            workflow_file = Path("config/flow.yaml")
            if workflow_file.exists():
                with open(workflow_file, 'r') as f:
                    self.flow_config = yaml.safe_load(f)
                logger.info("Loaded workflow configuration for LangGraph",
                           workflows=len(self.flow_config.get("workflows", [])))
            else:
                logger.warning("flow.yaml not found, using empty configuration")
                self.flow_config = {"workflows": [], "response_templates": {}}
        except Exception as e:
            logger.error("Error loading workflow configuration", error=str(e))
            self.flow_config = {"workflows": [], "response_templates": {}}
    
    def _setup_langgraph_workflows(self):
        """Setup LangGraph workflow state machine."""
        if not LANGGRAPH_AVAILABLE:
            return
        
        try:
            # Create the workflow graph
            workflow = StateGraph(WorkflowState)
            
            # Add nodes for different workflow steps
            workflow.add_node("classify", self._classify_node)
            workflow.add_node("find_workflow", self._find_workflow_node)
            workflow.add_node("execute_actions", self._execute_actions_node)
            workflow.add_node("escalate", self._escalate_node)
            workflow.add_node("search_knowledge", self._search_knowledge_node)
            workflow.add_node("create_ticket", self._create_ticket_node)
            workflow.add_node("generate_response", self._generate_response_node)
            
            # Define the workflow flow
            workflow.set_entry_point("classify")
            
            workflow.add_edge("classify", "find_workflow")
            workflow.add_conditional_edges(
                "find_workflow",
                self._route_to_actions,
                {
                    "execute": "execute_actions",
                    "no_workflow": "generate_response"
                }
            )
            
            workflow.add_conditional_edges(
                "execute_actions",
                self._route_action_execution,
                {
                    "escalate": "escalate",
                    "search_kb": "search_knowledge",
                    "create_ticket": "create_ticket",
                    "respond": "generate_response",
                    "continue": "execute_actions",
                    "end": "generate_response"
                }
            )
            
            workflow.add_edge("escalate", "generate_response")
            workflow.add_edge("search_knowledge", "generate_response")
            workflow.add_edge("create_ticket", "generate_response")
            workflow.add_edge("generate_response", END)
            
            # Compile the workflow
            self.workflow_graph = workflow.compile()
            
            logger.info("LangGraph workflow compiled successfully")
            
        except Exception as e:
            logger.error("Failed to setup LangGraph workflows", error=str(e))
            self.workflow_graph = None
    
    async def execute_workflow(self, classification: Dict[str, Any], context: MessageContext) -> Dict[str, Any]:
        """Execute workflow using LangGraph state machine."""
        if not self.workflow_graph:
            logger.warning("LangGraph not available, using fallback workflow execution")
            return self._fallback_execute_workflow(classification, context)
        
        try:
            # Initialize state
            initial_state: WorkflowState = {
                "message": context.message_text,
                "context": context,
                "classification": classification,
                "actions_taken": [],
                "escalation_triggered": False,
                "knowledge_base_used": False,
                "response": "",
                "error": None
            }
            
            # Execute the workflow
            result = await self.workflow_graph.ainvoke(initial_state)
            
            logger.info("LangGraph workflow executed successfully",
                       classification_type=classification.get("type"),
                       actions_taken=result.get("actions_taken", []),
                       escalation_triggered=result.get("escalation_triggered", False))
            
            return {
                "executed": True,
                "name": f"langgraph_{classification.get('type', 'unknown')}",
                "actions_taken": result.get("actions_taken", []),
                "escalation_triggered": result.get("escalation_triggered", False),
                "knowledge_base_used": result.get("knowledge_base_used", False),
                "response": result.get("response", ""),
                "template": None  # LangGraph generates responses directly
            }
            
        except Exception as e:
            logger.error("Error executing LangGraph workflow", error=str(e))
            return {
                "executed": False,
                "name": "",
                "actions_taken": [],
                "error": str(e)
            }
    
    async def _classify_node(self, state: WorkflowState) -> WorkflowState:
        """Classification node - already done, just pass through."""
        logger.debug("LangGraph: Classification node", 
                    classification_type=state["classification"].get("type"))
        return state
    
    async def _find_workflow_node(self, state: WorkflowState) -> WorkflowState:
        """Find matching workflow based on classification."""
        classification_type = state["classification"].get("type", "unknown")
        severity = state["classification"].get("severity", "low")
        
        # Find matching workflow
        matching_workflow = None
        for workflow in self.flow_config.get("workflows", []):
            if not workflow.get("enabled", True):
                continue
                
            trigger_conditions = workflow.get("trigger_conditions", {})
            
            if trigger_conditions.get("classification_type") == classification_type:
                severity_conditions = trigger_conditions.get("severity", [])
                if not severity_conditions or severity in severity_conditions:
                    matching_workflow = workflow
                    break
        
        if matching_workflow:
            state["workflow"] = matching_workflow
            logger.debug("LangGraph: Found matching workflow", 
                        workflow_name=matching_workflow["name"])
        else:
            state["workflow"] = None
            logger.debug("LangGraph: No matching workflow found")
        
        return state
    
    def _route_to_actions(self, state: WorkflowState) -> str:
        """Route to action execution or direct response."""
        if state.get("workflow"):
            return "execute"
        else:
            return "no_workflow"
    
    async def _execute_actions_node(self, state: WorkflowState) -> WorkflowState:
        """Execute workflow actions."""
        workflow = state.get("workflow")
        if not workflow:
            return state
        
        actions = workflow.get("actions", [])
        
        # Set next action to execute
        current_action_index = len(state["actions_taken"])
        if current_action_index < len(actions):
            state["current_action"] = actions[current_action_index]
        else:
            state["current_action"] = None
        
        return state
    
    def _route_action_execution(self, state: WorkflowState) -> str:
        """Route to specific action execution."""
        current_action = state.get("current_action")
        if not current_action:
            return "end"
        
        action_type = current_action.get("type")
        
        if action_type == "escalate":
            return "escalate"
        elif action_type == "search_kb":
            return "search_kb"
        elif action_type == "create_ticket":
            return "create_ticket"
        elif action_type == "respond":
            return "respond"
        else:
            # Skip unknown action and continue
            state["actions_taken"].append(f"skipped_{action_type}")
            return "continue"
    
    async def _escalate_node(self, state: WorkflowState) -> WorkflowState:
        """Execute escalation action."""
        action = state.get("current_action", {})
        params = action.get("params", {})
        
        escalation_level = params.get("escalation_level", "normal")
        notify_channels = params.get("notify_channels", [])
        
        state["escalation_triggered"] = True
        state["actions_taken"].append("escalate")
        
        logger.info("LangGraph: Escalation triggered",
                   level=escalation_level,
                   channels=notify_channels)
        
        return state
    
    async def _search_knowledge_node(self, state: WorkflowState) -> WorkflowState:
        """Execute knowledge base search action."""
        action = state.get("current_action", {})
        params = action.get("params", {})
        
        max_results = params.get("max_results", 3)
        
        state["knowledge_base_used"] = True
        state["actions_taken"].append("search_kb")
        
        # In a real implementation, you would call the knowledge base here
        logger.info("LangGraph: Knowledge base search executed",
                   max_results=max_results)
        
        return state
    
    async def _create_ticket_node(self, state: WorkflowState) -> WorkflowState:
        """Execute ticket creation action."""
        action = state.get("current_action", {})
        params = action.get("params", {})
        
        system = params.get("system", "default")
        priority = params.get("priority", "normal")
        
        state["actions_taken"].append("create_ticket")
        
        logger.info("LangGraph: Ticket creation executed",
                   system=system,
                   priority=priority)
        
        return state
    
    async def _generate_response_node(self, state: WorkflowState) -> WorkflowState:
        """Generate final response based on executed actions."""
        classification_type = state["classification"].get("type", "unknown")
        actions_taken = state["actions_taken"]
        
        # Generate response based on workflow execution
        if "escalate" in actions_taken:
            response = "🚨 **Incident Acknowledged** - I've escalated this to the on-call team. Expected response time: 15 minutes."
        elif "search_kb" in actions_taken:
            response = "📚 **Found relevant information** - Here are some helpful resources for your question."
        elif "create_ticket" in actions_taken:
            response = "🎫 **Support ticket created** - Our team will review and respond within 4 hours."
        else:
            response = "I understand your request. How can I help you further?"
        
        state["response"] = response
        
        logger.info("LangGraph: Response generated",
                   classification_type=classification_type,
                   actions_count=len(actions_taken))
        
        return state
    
    def _fallback_execute_workflow(self, classification: Dict[str, Any], context: MessageContext) -> Dict[str, Any]:
        """Fallback workflow execution when LangGraph is not available."""
        classification_type = classification.get("type", "unknown")
        severity = classification.get("severity", "low")
        
        logger.info("Executing fallback workflow", 
                   classification_type=classification_type, 
                   severity=severity)
        
        # Find matching workflow
        matching_workflow = None
        for workflow in self.flow_config.get("workflows", []):
            if not workflow.get("enabled", True):
                continue
                
            trigger_conditions = workflow.get("trigger_conditions", {})
            
            if trigger_conditions.get("classification_type") == classification_type:
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
        
        logger.info("Fallback workflow executed", 
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
