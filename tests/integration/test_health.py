"""Integration test for health check endpoint."""

import httpx
import pytest

from src.main import app


class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self):
        """Test that health check endpoint returns valid status."""
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            # During tests, knowledge base isn't initialized so expect "degraded"
            assert data["status"] in ["healthy", "degraded"]
            assert "version" in data
            assert "timestamp" in data
