"""Integration test for API process message endpoint."""
import pytest
import os
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.output_parsers import StrOutputParser
from src.knowledge.langchain_kb_manager import LangChainKnowledgeManager
from src.utils.config import config
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Set test environment flag
os.environ["TESTING"] = "1"

@pytest.fixture
def mock_openai_env():
    """Set up mock OpenAI environment."""
    original_key = config.openai_api_key
    config.openai_api_key = "test-key-1234"
    yield
    config.openai_api_key = original_key

@pytest.fixture
def mock_embeddings():
    """Mock OpenAI embeddings."""
    with patch('src.knowledge.langchain_kb_manager.OpenAIEmbeddings') as mock:
        embeddings = MagicMock()
        embeddings.embed_query = MagicMock(return_value=[0.1] * 768)
        mock.return_value = embeddings
        logger.info("Mocked OpenAI embeddings setup complete")
        yield mock

@pytest.fixture
def mock_chat_openai():
    """Mock ChatOpenAI."""
    with patch('src.knowledge.langchain_kb_manager.ChatOpenAI') as mock:
        instance = MagicMock()
        instance.invoke = AsyncMock(return_value="Here's a SQL query to find the best students...")
        instance.ainvoke = AsyncMock(return_value="Here's a SQL query to find the best students...")
        mock.return_value = instance
        logger.info("Mocked ChatOpenAI setup complete")
        yield mock

@pytest.fixture
def mock_vectorstore():
    """Mock Chroma vectorstore."""
    with patch('src.knowledge.langchain_kb_manager.Chroma') as mock:
        instance = MagicMock()
        # Mock the retriever
        retriever = MagicMock()
        retriever.get_relevant_documents = AsyncMock(return_value=[
            MagicMock(page_content="SQL query for best students", metadata={"source": "test.md"})
        ])
        instance.as_retriever.return_value = retriever
        mock.return_value = instance
        logger.info("Mocked Chroma vectorstore setup complete")
        yield mock

@pytest.fixture
def mock_chain_components():
    """Mock chain components."""
    with patch('src.knowledge.langchain_kb_manager.ChatPromptTemplate') as prompt_mock:
        prompt_mock_instance = MagicMock()
        prompt_mock.from_template.return_value = prompt_mock_instance
        
        with patch('src.knowledge.langchain_kb_manager.RunnablePassthrough') as runnable_mock:
            runnable_instance = MagicMock()
            runnable_mock.return_value = runnable_instance
            
            with patch('src.knowledge.langchain_kb_manager.StrOutputParser') as parser_mock:
                parser_instance = MagicMock()
                parser_mock.return_value = parser_instance
                
                logger.info("Mocked chain components setup complete")
                yield prompt_mock, runnable_mock, parser_mock

class TestApiProcessMessage:
    """Test API process message endpoint with full workflow."""
    
    @pytest.mark.asyncio
    async def test_api_should_process_message_successfully(
        self,
        mock_openai_env,
        mock_embeddings,
        mock_chat_openai,
        mock_vectorstore,
        mock_chain_components
    ):
        """Test that API processes knowledge query message and triggers correct workflow."""
        logger.info("Starting API process message test")
        
        # Create actual mock implementations that handle async properly
        sql_response = "Here's a SQL query to find the best students in class:\n```sql\nSELECT students.name, AVG(grades.score) as average_score\nFROM students\nJOIN grades ON students.id = grades.student_id\nGROUP BY students.id\nORDER BY average_score DESC\nLIMIT 10;\n```\nThis query will return the top 10 students based on their average grades."
        
        # Use a patch for the core functionality we're testing
        with patch('src.knowledge.langchain_kb_manager.LangChainKnowledgeManager.search_with_chain', 
                  new_callable=AsyncMock, return_value=sql_response):
            
            # Import app after patch is in place
            from src.main import app
            
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/process-message", json={
                    "message": "get me query to best students in the class",
                    "channel_type": "slack",
                    "user_id": "test_user",
                    "channel_id": "test_channel"
                })
                
                logger.info(f"API Response: {response.status_code}", 
                          status_code=response.status_code,
                          response_data=response.json())
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify knowledge query response
                assert "students" in data["response_text"].lower(), f"Expected 'students' in: {data['response_text']}"
                assert "sql" in data["response_text"].lower(), f"Expected 'sql' in: {data['response_text']}"
                assert data["classification_type"] == "knowledge_query"
                assert data["response_sent"] is True
                assert data["error_occurred"] is False
                
                logger.info("All test assertions passed")