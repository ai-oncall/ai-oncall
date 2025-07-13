"""Consolidated integration tests for API processing."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.main import app


@pytest.fixture
def client():
    """Test client for the FastAPI application."""
    return TestClient(app)


def test_api_process_message(client):
    """Test the /api/v1/process_message endpoint."""
    with patch("src.core.message_processor.MessageProcessor.process_api_message") as mock_process:
        # Mock the processor response
        mock_process.return_value = {
            "response_text": "Test response",
            "classification_type": "knowledge_query",
            "confidence": 0.9,
            "workflow_executed": True,
            "escalation_triggered": False,
            "processing_time_ms": 150,
            "response_sent": True,
            "error_occurred": False,
            "error_message": None
        }

        response = client.post(
            "/api/v1/process_message",
            json={"message": "test message"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response_text"] == "Test response"
        assert data["classification_type"] == "knowledge_query"
        mock_process.assert_called_once()
