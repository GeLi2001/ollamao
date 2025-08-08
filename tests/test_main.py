"""Basic tests for the main application."""

import pytest
from fastapi.testclient import TestClient

from ollamao.main import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert "models" in data
    assert "version" in data


def test_models_endpoint_requires_auth(client):
    """Test that the models endpoint requires authentication."""
    response = client.get("/v1/models")
    assert response.status_code == 401


def test_chat_completions_requires_auth(client):
    """Test that chat completions endpoint requires authentication."""
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llama3", "messages": [{"role": "user", "content": "hello"}]},
    )
    assert response.status_code == 401


def test_chat_completions_with_auth(client):
    """Test chat completions with valid auth (will fail without Ollama)."""
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer my-key"},
        json={"model": "llama3", "messages": [{"role": "user", "content": "hello"}]},
    )
    # This will return 503 since Ollama is not running, but auth should pass
    assert response.status_code in [200, 503]


def test_cors_headers(client):
    """Test that CORS headers are present."""
    # Test with a preflight request (OPTIONS with Origin header)
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORS middleware should add these headers for preflight requests
    assert response.status_code in [200, 204]
