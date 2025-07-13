"""Shared test fixtures and configuration."""

import os
from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.message_processor import MessageProcessor
from src.data.models import MessageContext
from src.knowledge.langchain_kb_manager import LangChainKnowledgeManager
from src.workflows.langgraph_engine import LangGraphWorkflowEngine

# Ensure we're in test mode
os.environ["TESTING"] = "1"


@pytest.fixture
def message_context():
    """Create a message context for testing."""
    return MessageContext(
        message_id="MOCK_MESSAGE_ID",
        message_text="test message",
        channel_type="slack",
        channel_id="C123456",
        user_id="U123456",
        timestamp=datetime.now(),
        is_mention=True,
    )


@pytest.fixture
def sample_kb_results():
    """Sample knowledge base search results."""
    return [
        {
            "page_content": "Critical incidents have a 15-minute SLA for initial response.",
            "metadata": {
                "source": "incident_policies.md",
                "section": "SLAs",
                "relevance_score": 0.95,
            },
        },
        {
            "page_content": "Standard support tickets have a 4-hour response time.",
            "metadata": {
                "source": "support_slas.md",
                "section": "Response Times",
                "relevance_score": 0.85,
            },
        },
    ]


@pytest.fixture
def kb_manager():
    """Create a mocked knowledge base manager."""
    with patch("langchain_community.vectorstores.Chroma") as mock_chroma:
        manager = LangChainKnowledgeManager()
        # Configure mock retriever
        mock_retriever = AsyncMock()
        mock_chroma.as_retriever.return_value = mock_retriever
        manager.vectorstore = mock_chroma
        yield manager


@pytest.fixture
def message_processor(kb_manager, workflow_engine):
    """Create a message processor with mocked dependencies."""
    with patch("src.core.message_processor.LangChainAIClient") as mock_ai:
        processor = MessageProcessor()
        # Configure mock AI client
        mock_client = AsyncMock()
        mock_ai.return_value = mock_client
        processor.ai_client = mock_client
        processor.knowledge_base = kb_manager
        processor.workflow_engine = workflow_engine
        yield processor


@pytest.fixture
def workflow_engine():
    """Create a workflow engine with mocked dependencies."""
    engine = LangGraphWorkflowEngine()
    engine.knowledge_base = MagicMock(spec=LangChainKnowledgeManager)
    engine.knowledge_base.search_with_chain = AsyncMock()
    return engine
