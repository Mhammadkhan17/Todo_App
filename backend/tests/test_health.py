#!/usr/bin/env python3
"""
Test health endpoints

Tests for health check and basic API functionality.
"""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Test root endpoint serves the HTML gateway page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Todo API Backend Online" in response.text
    assert "./api/docs" in response.text


def test_health_check_endpoint(client: TestClient):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "Service is healthy" in data["message"]


def test_404_endpoint(client: TestClient):
    """Test 404 error handling."""
    response = client.get("/nonexistent")
    assert response.status_code == 404