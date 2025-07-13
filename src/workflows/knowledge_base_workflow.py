"""LangGraph-based knowledge base workflow."""

from typing import Any, Dict, List, Optional, cast

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from src.data.models import MessageContext, ProcessingResult
from src.knowledge.langchain_kb_manager import LangChainKnowledgeManager
from src.utils.logging import get_logger
from src.workflows.langgraph_engine import (
    END,
    RunnableLambda,
    StateGraph,
    WorkflowState,
)

logger = get_logger(__name__)


def create_knowledge_base_workflow(
    knowledge_base: LangChainKnowledgeManager,
) -> StateGraph:
    """Create a knowledge base workflow that:
    1. Extracts a search query from the message
    2. Searches the knowledge base
    3. Formats a response with citations
    """

    # Create nodes for the workflow
    def extract_query(state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a search query from the input message."""
        query_template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "Extract a clear search query from the user's message. "
                        "Identify key terms and concepts that would help find relevant information. "
                        "Ignore any greetings or pleasantries."
                    )
                ),
                HumanMessage(content="User message: {message}"),
            ]
        )

        chain = query_template | StrOutputParser()
        state["query"] = chain.invoke({"message": state["message"]})
        return state

    def search_knowledge_base(state: Dict[str, Any]) -> Dict[str, Any]:
        """Search the knowledge base using the extracted query."""
        state["kb_results"] = knowledge_base.search_with_relevance(
            query=state["query"],
            max_results=3,
        )
        return state

    def format_response(state: Dict[str, Any]) -> Dict[str, Any]:
        """Format a response that includes relevant information and citations."""
        response_template = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "Create a helpful response using the knowledge base results. "
                        "Include direct quotes when relevant and cite sources at the bottom of the response. "
                        "Format response in Markdown."
                    )
                ),
                HumanMessage(
                    content=(
                        "Query: {query}\n"
                        "Knowledge Base Results: {kb_results}\n"
                        "Format the response with:\n"
                        "1. Direct answer\n"
                        "2. Supporting details\n"
                        "3. Sources"
                    )
                ),
            ]
        )

        chain = response_template | StrOutputParser()
        state["response"] = chain.invoke(
            {
                "query": state["query"],
                "kb_results": state["kb_results"],
            }
        )
        return state

    # Create the workflow graph
    workflow = StateGraph(state_type=WorkflowState)

    # Add nodes
    # Wrap node functions with RunnableLambda
    extract_query_node = RunnableLambda(extract_query)
    search_kb_node = RunnableLambda(search_knowledge_base)
    format_response_node = RunnableLambda(format_response)
    
    # Add nodes
    workflow.add_node("extract_query", extract_query_node)
    workflow.add_node("search_kb", search_kb_node)
    workflow.add_node("format_response", format_response_node)

    # Set up the flow
    workflow.set_entry_point("extract_query")
    workflow.add_edge("extract_query", "search_kb")
    workflow.add_edge("search_kb", "format_response")
    workflow.add_edge("format_response", END)

    return workflow.compile()
