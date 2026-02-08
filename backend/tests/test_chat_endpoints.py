import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from main import app


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


def test_chat_send_endpoint_exists(client):
    """Test that /api/chat/send endpoint is registered."""
    # Try OPTIONS request to check if endpoint exists
    response = client.options("/api/chat/send")
    # Should not be 404
    assert response.status_code != 404, "Chat send endpoint should be registered"


def test_chat_execute_endpoint_exists(client):
    """Test that /api/chat/execute endpoint is registered."""
    response = client.options("/api/chat/execute")
    assert response.status_code != 404, "Chat execute endpoint should be registered"


def test_chat_messages_endpoint_exists(client):
    """Test that /api/chat/messages endpoint is registered."""
    response = client.options("/api/chat/messages")
    assert response.status_code != 404, "Chat messages endpoint should be registered"


def test_chat_clear_endpoint_exists(client):
    """Test that /api/chat/clear endpoint is registered."""
    response = client.options("/api/chat/clear")
    assert response.status_code != 404, "Chat clear endpoint should be registered"


def test_openapi_schema_includes_chat_endpoints(client):
    """Test that chat endpoints appear in OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    paths = schema.get("paths", {})

    # Check all chat endpoints are documented
    assert "/api/chat/send" in paths, "Send endpoint should be in OpenAPI schema"
    assert "/api/chat/execute" in paths, "Execute endpoint should be in OpenAPI schema"
    assert "/api/chat/messages" in paths, "Messages endpoint should be in OpenAPI schema"
    assert "/api/chat/clear" in paths, "Clear endpoint should be in OpenAPI schema"
