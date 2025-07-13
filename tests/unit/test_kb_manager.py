"""Unit tests for LangChain knowledge base manager."""
import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Dict, Any

from src.knowledge.langchain_kb_manager import LangChainKnowledgeManager

# Mock Document class to mimic LangChain's Document
class MockDocument:
    def __init__(self, page_content: str, metadata: dict):
        self.page_content = page_content
        self.metadata = metadata

@pytest.fixture
def kb_manager():
    """Create a knowledge base manager for testing."""
    return LangChainKnowledgeManager()

@pytest.fixture
def sample_docs() -> List[MockDocument]:
    """Sample documents for testing."""
    return [
        MockDocument(
            page_content="Critical incidents require immediate attention and have a 15-minute SLA.",
            metadata={
                "source": "incident_policies.md",
                "section": "SLAs"
            }
        )
    ]

class TestLangChainKnowledgeManager:
    """Test the LangChain knowledge base manager."""

    @pytest.mark.asyncio
    async def test_search_with_relevance(self, kb_manager, sample_docs):
        """Test knowledge base search with relevance scores."""
        # Mock all necessary LangChain components and environment
        with patch('src.knowledge.langchain_kb_manager.OpenAIEmbeddings') as mock_embeddings, \
             patch('src.knowledge.langchain_kb_manager.Chroma') as mock_chroma_class, \
             patch('src.knowledge.langchain_kb_manager.RecursiveCharacterTextSplitter'), \
             patch('src.knowledge.langchain_kb_manager.ChatOpenAI') as mock_chat, \
             patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), \
             patch('src.utils.config.config') as mock_config:

            # Mock configuration
            mock_config.openai_api_key = "test-key"
            mock_config.openai_base_url = None
            mock_config.openai_model = "gpt-4"

            # Configure mock for the Chroma vectorstore instance
            mock_vectorstore_instance = MagicMock()
            mock_retriever = AsyncMock()
            mock_retriever.aget_relevant_documents.return_value = sample_docs
            mock_vectorstore_instance.as_retriever.return_value = mock_retriever
            
            # When Chroma is instantiated inside the manager, it will use our mock
            mock_chroma_class.return_value = mock_vectorstore_instance
            
            # Mock OpenAI components
            mock_embeddings.return_value = MagicMock()
            mock_chat.return_value = MagicMock()
            
            # Test search. This will trigger the lazy initialization with our mocks.
            results = await kb_manager.search_with_relevance(
                query="What is the SLA for critical incidents?",
                max_results=1,
            )
            
            # Verify results are properly formatted
            assert len(results) == 1
            assert results[0]["source"] == "incident_policies.md"
            assert "15-minute SLA" in results[0]["content"]
            assert "relevance_score" in results[0]

    @pytest.mark.asyncio
    async def test_search_with_chain(self, kb_manager):
        """Test knowledge base search with retrieval chain."""
        with patch('src.knowledge.langchain_kb_manager.OpenAIEmbeddings'), \
             patch('src.knowledge.langchain_kb_manager.Chroma') as mock_chroma_class, \
             patch('src.knowledge.langchain_kb_manager.RecursiveCharacterTextSplitter'), \
             patch('src.knowledge.langchain_kb_manager.ChatOpenAI'), \
             patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}), \
             patch('src.utils.config.config') as mock_config:

            # Mock configuration
            mock_config.openai_api_key = "test-key"
            mock_config.openai_base_url = None
            mock_config.openai_model = "gpt-4"

            # Mock retrieval chain
            mock_chain = AsyncMock()
            mock_chain.ainvoke.return_value = "Critical incidents have a 15-minute SLA for initial response."
            
            # Initialize the KB manager and set the mock chain
            kb_manager._ensure_initialized()
            kb_manager.retrieval_chain = mock_chain
            
            # Test chain-based search
            result = await kb_manager.search_with_chain("What is the SLA for critical incidents?")
            
            assert "15-minute SLA" in result
            mock_chain.ainvoke.assert_called_once()