"""Integration test for health check endpoint."""
import pytest
from fastapi.testclient import TestClient
from src.main import app

class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check_returns_healthy(self):
        """Test that health check endpoint returns healthy status."""
        with TestClient(app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy" 