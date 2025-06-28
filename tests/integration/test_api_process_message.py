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
        
        # Import after mocking to ensure global message_processor uses our mock
        from fastapi.testclient import TestClient
        from src.main import app
        
        with TestClient(app) as client:
            response = client.post("/process-message", json={
                "message": "how do I restart the web server?",
                "channel_type": "slack",
                "user_id": "test_user",
                "channel_id": "test_channel"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify knowledge query workflow response
            assert "📚 **Found relevant information:**" in data["response_text"]
            assert data["classification_type"] == "knowledge_query"
            assert data["escalation_triggered"] is False  # Knowledge queries don't trigger escalation
            assert data["response_sent"] is True
            assert data["error_occurred"] is False
            assert data["error_message"] is None 