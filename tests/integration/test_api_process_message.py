"""Integration test for API process message endpoint."""
import pytest
from unittest.mock import patch, AsyncMock

@patch('src.core.message_processor.OpenAIClient')
class TestApiProcessMessage:
    """Test API process message endpoint with full workflow."""
    
    def test_api_should_process_message_successfully(self, mock_openai_class):
        """Test that API processes knowledge query message and triggers correct workflow."""
        # Mock OpenAI client to return knowledge query classification
        mock_client = AsyncMock()
        mock_openai_class.return_value = mock_client
        
        # Mock classification response for knowledge query (different from Slack test)
        mock_client.classify_message = AsyncMock(return_value={
            "type": "knowledge_query",
            "severity": "low",
            "confidence": 0.8
        })
        
        # Mock the additional OpenAI call for knowledge response generation
        mock_client.generate_knowledge_response = AsyncMock(return_value="📚 **Found relevant information:** Here's the query to find the best students in the class.")
        
        # Import after mocking to ensure global message_processor uses our mock
        from fastapi.testclient import TestClient
        from src.main import app
        
        with TestClient(app) as client:
            response = client.post("/process-message", json={
                "message": "get me query to best students in the class",
                "channel_type": "slack",
                "user_id": "test_user",
                "channel_id": "test_channel"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify knowledge query workflow response (from real knowledge base)
            assert "students" in data["response_text"].lower()  # Should contain student-related content
            assert "sql" in data["response_text"].lower() or "query" in data["response_text"].lower()  # Should contain SQL or query info
            assert data["classification_type"] == "knowledge_query"
            assert data["escalation_triggered"] is False  # Knowledge queries don't trigger escalation
            assert data["response_sent"] is True
            assert data["error_occurred"] is False
            assert data["error_message"] is None 