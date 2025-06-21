"""Integration tests for health endpoints."""
import pytest
import asyncio
from fastapi.testclient import TestClient
from src.main import app, main

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint returns correct response."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "debug" in data


def test_root_endpoint():
    """Test root endpoint returns welcome message."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "message" in data
    assert "AI OnCall Bot" in data["message"]


def test_health_endpoint_structure():
    """Test health endpoint returns expected structure."""
    response = client.get("/health")
    data = response.json()
    
    # Check required keys are present
    required_keys = {"status", "version", "debug"}
    assert required_keys.issubset(set(data.keys()))
    
    # Check data types
    assert isinstance(data["status"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["debug"], bool)
    
    # Check optional keys if present
    if "openai_configured" in data:
        assert isinstance(data["openai_configured"], bool)
    if "slack_configured" in data:
        assert isinstance(data["slack_configured"], bool)


 