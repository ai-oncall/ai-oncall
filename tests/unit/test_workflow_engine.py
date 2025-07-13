"""Unit tests for workflow engine."""

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data.models import MessageContext, ProcessingResult
from src.knowledge.langchain_kb_manager import LangChainKnowledgeManager
from src.workflows.langgraph_engine import LangGraphWorkflowEngine, WorkflowError


@pytest.fixture(autouse=True)
def setup_workflow_config(workflow_engine):
    """Configure workflow engine with test workflows."""
    workflow_engine.flow_config = {
        "workflows": [
            {
                "name": "critical_incident",
                "enabled": True,
                "trigger_conditions": {
                    "classification_type": "incident",
                    "severity": ["critical"],
                },
                "actions": [
                    {"type": "escalate", "params": {"escalation_level": "high"}},
                    {"type": "create_ticket", "params": {"priority": "high"}},
                ],
            },
            {
                "name": "knowledge_query",
                "enabled": True,
                "trigger_conditions": {"classification_type": "knowledge_query"},
                "actions": [
                    {"type": "search_kb", "params": {"max_results": 3}},
                    {"type": "respond", "params": {"template": "kb_response"}},
                ],
            },
        ]
    }
    return workflow_engine


@pytest.fixture
def message_context():
    """Create a test message context."""
    return MessageContext(
        message_id="MOCK_MESSAGE_ID",
        user_id="U123456",
        channel_id="C123456",
        channel_type="slack",
        message_text="Test message",
        is_mention=True,
        timestamp=datetime.now(),
    )


@pytest.fixture
def sample_kb_results():
    """Sample knowledge base search results."""
    return [
        {
            "content": "Test knowledge base content",
            "metadata": {"source": "test.md"},
            "relevance_score": 0.9,
        }
    ]


@pytest.fixture
def workflow_engine():
    """Create a mock workflow engine."""
    engine = LangGraphWorkflowEngine()
    engine.knowledge_base.search_with_chain = AsyncMock()
    return engine


@pytest.mark.asyncio
class TestLangGraphWorkflowEngine:
    """Test the LangGraph workflow engine."""

    async def test_knowledge_workflow(self, workflow_engine, message_context):
        """Test knowledge base workflow execution."""
        # Set up test data
        classification = {"type": "knowledge_query", "confidence": 0.9}
        
        expected_response = (
            "Critical incidents have a 15-minute SLA for initial response. "
            "Source: incident_policies.md"
        )
        workflow_engine.knowledge_base.search_with_chain.return_value = expected_response

        # Execute workflow
        result = await workflow_engine.execute_workflow(classification, message_context)

        # Verify results
        assert result.get("error") is None
        assert result.get("executed", False) is True
        assert result.get("knowledge_base_used", False) is True
        assert expected_response in result.get("response", "")

    async def test_incident_workflow(self, workflow_engine, message_context):
        """Test incident workflow execution."""
        # Set up test data
        classification = {
            "type": "incident",
            "severity": "critical",
            "confidence": 0.95,
        }

        # Execute workflow
        result = await workflow_engine.execute_workflow(classification, message_context)

        # Verify results
        assert result.get("error") is None  
        assert result.get("executed", False) is True
        assert result.get("escalation_triggered", False) is True
        assert len(result.get("actions_taken", [])) > 0
        assert any(a.get("type") == "escalate" for a in result.get("actions_taken", []))

    async def test_no_matching_workflow(self, workflow_engine, message_context):
        """Test handling of unknown workflow types."""
        classification = {"type": "unknown_type", "confidence": 0.5}

        result = await workflow_engine.execute_workflow(classification, message_context)

        assert result["executed"] is False
        assert not result.get("actions_taken")
        assert "No matching workflow" in result.get("error", "")

    async def test_workflow_error_handling(self, workflow_engine, message_context):
        """Test error handling in workflow execution."""
        # Set up test data
        classification = {"type": "knowledge_query", "confidence": 0.9}

        # Simulate an error in knowledge base
        workflow_engine.knowledge_base.search_with_chain.side_effect = Exception(
            "KB search failed"
        )

        # Execute workflow
        result = await workflow_engine.execute_workflow(classification, message_context)

        # Verify error handling
        assert result["executed"] is False
        assert "error" in result
        assert "KB search failed" in result["error"]
