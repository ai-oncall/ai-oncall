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


@pytest.mark.asyncio
async def test_server_startup():
    """Test that the server can start without errors (startup integration test)."""
    # This test actually calls main() to test the startup process
    task = None
    try:
        # Start the server
        task = asyncio.create_task(main())
        
        # Give it time to start (or fail)
        await asyncio.sleep(1)
        
        # If we get here without exception, startup succeeded
        assert task is not None
        assert not task.done() or not task.exception()
        
    except Exception as e:
        pytest.fail(f"Server startup failed: {e}")
    finally:
        # Clean up
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass  # Expected when cancelling 