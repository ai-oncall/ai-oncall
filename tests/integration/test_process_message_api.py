"""Integration tests for /process-message API endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app

# Create a test client
client = TestClient(app)


@patch('src.ai.openai_client.OpenAIClient')
class TestProcessMessageAPI:
    """Test /process-message API endpoint functionality."""

    def setup_method(self, method):
        """Set up common test data."""
        pass

    def test_process_message_api_flow(self, mock_openai_class):
        """Test complete API message processing flow."""
        # Set up mock OpenAI client
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "I'll help you with your password reset request."
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client
        
        # Test a support request
        response = client.post("/process-message", json={
            "message": "I need help with my password reset",
            "user_id": "test-user",
            "channel_type": "api",
            "channel_id": "api-channel"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "response_text" in data
        assert "classification_type" in data
        assert "processing_time_ms" in data
        assert "workflow_executed" in data
        
        # Check that we get a meaningful response
        assert data["response_text"] is not None
        assert len(data["response_text"]) > 0
        assert data["processing_time_ms"] >= 0
        assert isinstance(data["workflow_executed"], bool)

    def test_process_message_incident_flow(self, mock_openai_class):
        """Test incident message processing flow."""
        
        response = client.post("/process-message", json={
            "message": "URGENT: Production server is down!",
            "user_id": "ops-user",
            "channel_type": "api", 
            "channel_id": "ops-channel"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should provide response
        assert data["response_text"] is not None
        assert len(data["response_text"]) > 0

    def test_process_message_question_flow(self, mock_openai_class):
        """Test question message processing flow."""
        response = client.post("/process-message", json={
            "message": "How do I configure the SSL certificate?",
            "user_id": "dev-user",
            "channel_type": "api",
            "channel_id": "dev-channel"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should provide helpful response
        assert data["response_text"] is not None
        assert len(data["response_text"]) > 0
        assert data["processing_time_ms"] >= 0

    def test_process_message_with_thread(self, mock_openai_class):
        """Test message processing with thread context."""
        response = client.post("/process-message", json={
            "message": "Follow up on the previous issue",
            "user_id": "test-user",
            "channel_type": "api",
            "channel_id": "test-channel",
            "thread_ts": "1234567890.123"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["response_text"] is not None
        assert data["classification_type"] is not None

    def test_process_message_with_mention(self, mock_openai_class):
        """Test message processing with bot mention."""
        response = client.post("/process-message", json={
            "message": "@bot please help me with this issue",
            "user_id": "test-user",
            "channel_type": "api", 
            "channel_id": "test-channel",
            "is_mention": True
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["response_text"] is not None
        assert len(data["response_text"]) > 0

    def test_process_message_validation_error(self, mock_openai_class):
        """Test message processing with invalid input."""
        # Empty message should fail validation
        response = client.post("/process-message", json={
            "message": "",
            "user_id": "test-user",
            "channel_type": "api",
            "channel_id": "test-channel"
        })
        
        assert response.status_code == 422  # Validation error

    def test_process_message_missing_fields(self, mock_openai_class):
        """Test message processing with missing required fields."""
        # Test completely empty request
        response = client.post("/process-message", json={})
        
        assert response.status_code == 422  # Validation error

    def test_process_message_response_consistency(self, mock_openai_class):
        """Test that response format is consistent across different message types."""
        test_messages = [
            "Help me reset my password",
            "Server is down - urgent!",
            "How do I configure HTTPS?",
            "Thank you for the assistance"
        ]
        
        for message in test_messages:
            response = client.post("/process-message", json={
                "message": message,
                "user_id": "test-user",
                "channel_type": "api",
                "channel_id": "test-channel"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Check consistent response structure
            required_fields = [
                "response_text", "classification_type", "confidence",
                "workflow_executed", "escalation_triggered", 
                "processing_time_ms", "response_sent", "error_occurred"
            ]
            
            for field in required_fields:
                assert field in data, f"Missing field {field} for message: {message}"
            
            # Check response_text is always provided
            assert data["response_text"] is not None, f"No response_text for message: {message}"
            assert len(data["response_text"]) > 0, f"Empty response_text for message: {message}"

    def test_process_message_performance(self, mock_openai_class):
        """Test that message processing completes within reasonable time."""
        response = client.post("/process-message", json={
            "message": "Performance test message",
            "user_id": "perf-user",
            "channel_type": "api",
            "channel_id": "perf-channel"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should complete within 5 seconds (5000ms)
        assert data["processing_time_ms"] < 5000
        assert data["response_text"] is not None

    def test_process_message_error_handling(self, mock_openai_class):
        """Test that errors are handled gracefully."""
        # Test with potentially problematic content
        response = client.post("/process-message", json={
            "message": "Special chars: <>&\"'{}[]",
            "user_id": "test-user",
            "channel_type": "api",
            "channel_id": "test-channel"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle gracefully
        assert data["error_occurred"] is False
        assert data["response_text"] is not None

    def test_process_message_different_channel_types(self, mock_openai_class):
        """Test message processing with different channel types."""
        # Only test supported channel types
        channel_types = ["api", "slack", "teams"]
        
        for channel_type in channel_types:
            response = client.post("/process-message", json={
                "message": f"Test message for {channel_type}",
                "user_id": "test-user",
                "channel_type": channel_type,
                "channel_id": f"{channel_type}-channel"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["response_text"] is not None
            assert len(data["response_text"]) > 0

    def test_process_message_with_metadata(self, mock_openai_class):
        """Test message processing with custom metadata."""
        response = client.post("/process-message", json={
            "message": "Test message with metadata",
            "user_id": "test-user",
            "channel_type": "api",
            "channel_id": "test-channel",
            "metadata": {
                "source": "mobile_app",
                "version": "1.2.3",
                "priority": "high"
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["response_text"] is not None
        assert data["error_occurred"] is False

    def test_process_message_long_text(self, mock_openai_class):
        """Test message processing with long text input."""
        long_message = "This is a very long message. " * 100  # ~3000 characters
        
        response = client.post("/process-message", json={
            "message": long_message,
            "user_id": "test-user",
            "channel_type": "api",
            "channel_id": "test-channel"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["response_text"] is not None
        assert data["error_occurred"] is False

    def test_process_message_confidence_scores(self, mock_openai_class):
        """Test that confidence scores are returned properly."""
        response = client.post("/process-message", json={
            "message": "I need urgent help with server issues",
            "user_id": "test-user",
            "channel_type": "api",
            "channel_id": "test-channel"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
        assert 0.0 <= data["confidence"] <= 1.0 