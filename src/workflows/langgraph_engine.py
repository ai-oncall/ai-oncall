"""Workflow engine using LangChain and LangGraph for orchestration."""
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

from src.data.models import MessageContext
from src.knowledge.langchain_kb_manager import LangChainKnowledgeManager
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Simplified workflow state model
class WorkflowState(BaseModel):
    """Shared state for workflow execution."""
    message: str = Field(description="Input message")
    context: MessageContext = Field(description="Message context")
    workflow_id: str = Field(default="", description="Unique workflow run ID")
    
    # Optional fields populated during execution
    kb_results: Optional[str] = Field(default=None, description="Knowledge base results")
    response: Optional[str] = Field(default=None, description="Generated response")
    error: Optional[str] = Field(default=None, description="Error message if any")
    
    # Additional optional fields
    classification: Dict[str, Any] = Field(default_factory=dict, description="Message classification")
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list, description="Actions taken in workflow")
    escalation_triggered: bool = Field(default=False, description="Whether escalation was triggered")
    knowledge_base_used: bool = Field(default=False, description="Whether knowledge base was searched")
    workflow: Dict[str, Any] = Field(default_factory=dict, description="Current workflow definition")


class WorkflowError(Exception):
    """Base exception for workflow errors."""
    pass


class LangGraphWorkflowEngine:
    """Workflow engine using LangChain for orchestration."""

    def __init__(self):
        """Initialize workflow engine."""
        self.knowledge_base = LangChainKnowledgeManager()
        self._load_workflow_config()
        self.workflow_graph = self._build_workflow_graph()

    def _load_workflow_config(self):
        """Load workflow configuration from flow.yaml."""
        try:
            workflow_file = Path("config/flow.yaml")
            if workflow_file.exists():
                with open(workflow_file, 'r') as f:
                    self.flow_config = yaml.safe_load(f)
                logger.info("Loaded workflow configuration", workflows=len(self.flow_config.get("workflows", [])))
            else:
                logger.warning("flow.yaml not found, using empty configuration")
                self.flow_config = {"workflows": [], "response_templates": {}}
        except Exception as e:
            logger.error("Error loading workflow configuration", error=str(e))
            self.flow_config = {"workflows": [], "response_templates": {}}

    def _build_workflow_graph(self) -> StateGraph:
        """Build the workflow graph using LangGraph."""
        from typing_extensions import TypedDict
        
        # Define state schema as TypedDict for LangGraph
        class WorkflowStateDict(TypedDict):
            message: str
            context: object  # MessageContext
            workflow_id: str
            classification: dict
            actions_taken: list
            escalation_triggered: bool
            knowledge_base_used: bool
            workflow: dict
            kb_results: str
            error: str
            response: str
        
        graph = StateGraph(WorkflowStateDict)

        # Add nodes that work with dictionary state
        graph.add_node("find_workflow", self._find_workflow_node)
        graph.add_node("execute_actions", self._execute_actions_node)
        graph.add_node("prepare_response", self._prepare_response_node)

        graph.set_entry_point("find_workflow")

        graph.add_conditional_edges(
            "find_workflow",
            self._decide_to_execute_node,
            {
                "execute": "execute_actions",
                "end": END,
            },
        )
        graph.add_edge("execute_actions", "prepare_response")
        graph.add_edge("prepare_response", END)

        return graph.compile()

    async def _execute_action(self, action: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow action."""
        action_type = action.get("type")
        params = action.get("params", {})

        if action_type == "search_kb":
            try:
                # LangChain will do its own logging with the context
                response = await self.knowledge_base.search_with_chain(
                    query=state["message"],
                    max_results=params.get("max_results", 3)
                )
                return {
                    "type": "search_kb",
                    "results": response,
                    "status": "success"
                }
            except Exception as e:
                return {
                    "type": "search_kb",
                    "error": str(e),
                    "status": "error"
                }
        elif action_type == "escalate":
            # Mock escalation for now
            return {
                "type": "escalate",
                "escalation_level": params.get("escalation_level", "low"),
                "status": "success"
            }
        return {
            "type": action_type,
            "status": "skipped",
            "message": f"Action type {action_type} not implemented"
        }

    def _find_workflow_node(self, state: dict) -> dict:
        """Finds the matching workflow and adds it to the state."""
        classification = state["classification"]
        logger.info("Finding matching workflow", classification=classification)
        workflow = self._find_matching_workflow(classification)
        if workflow:
            logger.info("Found workflow", workflow_name=workflow.get("name"))
            return {
                "workflow": workflow,
                "error": None,
                "workflow_id": workflow.get("name", "unknown")
            }
        else:
            logger.warning("No matching workflow found", classification=classification)
            return {
                "workflow": {},
                "error": "No matching workflow found.",
                "workflow_id": "unknown"
            }

    def _decide_to_execute_node(self, state: dict) -> str:
        """Determines if a workflow was found to execute."""
        return "execute" if state.get("workflow") and not state.get("error") else "end"

    async def _execute_actions_node(self, state: dict) -> dict:
        """Executes the actions for the found workflow."""
        workflow = state["workflow"]
        workflow_name = workflow.get("name", "unknown")
        logger.info("Executing actions for workflow", workflow_name=workflow_name)
        
        actions = workflow.get("actions", [])
        actions_taken = []
        kb_results = None
        knowledge_base_used = False
        escalation_triggered = False
        error = None

        for action in actions:
            # Skip respond action - this is handled in prepare_response_node
            if action.get("type") == "respond":
                continue
                
            try:
                result = await self._execute_action(action, state)
                actions_taken.append(result)
                if result.get("type") == "search_kb" and result.get("status") == "success":
                    knowledge_base_used = True
                    kb_results = result.get("results")
                elif result.get("type") == "escalate" and result.get("status") == "success":
                    escalation_triggered = True
            except Exception as e:
                logger.exception("Error executing action", action=action.get("type"), error=str(e))
                error = f"Failed to execute action {action.get('type')}: {e}"
                break
        
        # Return dictionary update
        return {
            "actions_taken": actions_taken,
            "knowledge_base_used": knowledge_base_used,
            "kb_results": kb_results,
            "escalation_triggered": escalation_triggered,
            "error": error
        }

    def _prepare_response_node(self, state: dict) -> dict:
        """Prepares the final response for the user."""
        workflow = state["workflow"]
        workflow_name = workflow.get("name", "unknown")
        logger.info("Preparing response for workflow", workflow_name=workflow_name)

        # Use error response if there was an error
        if state.get("error"):
            return {"response": f"Sorry, there was an error: {state['error']}"}

        # Look for respond action
        actions = workflow.get("actions", [])
        logger.info("Workflow actions", actions=actions)
        respond_action = next(
            (a for a in actions if a["type"] == "respond"),
            None,
        )
        logger.info("Found respond action", respond_action=respond_action)
        
        if not respond_action:
            return {"response": "Your request has been processed."}

        template_name = respond_action.get("params", {}).get("template")
        logger.info("Template name", template_name=template_name)
        if not template_name:
            return {"response": "Your request has been processed."}

        # Get template
        template = self.flow_config.get("response_templates", {}).get(
            template_name, "Your request has been processed."
        )
        logger.info("Template content", template=template)

        # Insert KB results if available
        response = template
        kb_results = state.get("kb_results")
        logger.info("KB results from state", kb_results=kb_results)
        if "{kb_results}" in response and kb_results:
            response = response.replace("{kb_results}", kb_results)

        logger.info("Final response", response=response)
        return {"response": response}

    async def execute_workflow(
        self, classification: Dict[str, Any], context: MessageContext
    ) -> Dict[str, Any]:
        """Execute the appropriate workflow based on message classification."""
        try:
            # Create initial state as dictionary
            initial_state = {
                "message": context.message_text,
                "context": context,
                "workflow_id": classification.get("type", "unknown"),
                "classification": classification,
                "actions_taken": [],
                "escalation_triggered": False,
                "knowledge_base_used": False,
                "workflow": {},
                "kb_results": None,
                "error": None,
                "response": None
            }

            # LangGraph returns the final state as a dictionary
            final_state = await self.workflow_graph.ainvoke(initial_state)

            # final_state should be a dictionary with all accumulated updates
            return {
                "executed": not bool(final_state.get("error")),
                "error": final_state.get("error"),
                "response": final_state.get("response", "I encountered an error processing your request."),
                "escalation_triggered": final_state.get("escalation_triggered", False),
                "knowledge_base_used": final_state.get("knowledge_base_used", False),
                "kb_results": final_state.get("kb_results"),
                "actions_taken": final_state.get("actions_taken", [])
            }

        except Exception as e:
            logger.exception("Workflow execution failed", error=str(e))
            return {
                "executed": False,
                "error": str(e),
                "response": "I encountered an error processing your request.",
                "actions_taken": [],
                "knowledge_base_used": False,
                "escalation_triggered": False,
            }

    def _find_matching_workflow(
        self, classification: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find matching workflow definition based on classification."""
        workflows = sorted(
            self.flow_config.get("workflows", []),
            key=lambda w: w.get("priority", 0),
            reverse=True,
        )

        for workflow in workflows:
            if not workflow.get("enabled", True):
                continue

            conditions = workflow.get("trigger_conditions", {})
            if not conditions:
                continue

            match = True
            for key, value in conditions.items():
                # In flow.yaml, we use 'classification_type' for the message type
                class_key = "type" if key == "classification_type" else key
                
                if class_key not in classification:
                    match = False
                    break
                
                class_value = classification[class_key]
                if isinstance(value, list):
                    if class_value not in value:
                        match = False
                        break
                elif class_value != value:
                    match = False
                    break
            
            if match:
                return workflow

        return None

    async def run(
        self, message: str, context: MessageContext, classification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Legacy method for compatibility with tests. Calls execute_workflow."""
        return await self.execute_workflow(classification, context)
