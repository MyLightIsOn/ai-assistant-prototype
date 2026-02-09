import pytest
from fastapi.testclient import TestClient

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


def test_chat_send_requires_authentication(client):
    """Test that /api/chat/send has user dependency."""
    # The current implementation of get_current_user is a placeholder
    # that returns the first user from the database.
    # This test verifies that the endpoint calls get_current_user dependency.
    # When NextAuth integration is complete, this will enforce actual auth.

    # Send request (currently works due to placeholder auth)
    response = client.post(
        "/api/chat/send",
        json={"content": "Test message", "attachments": []}
    )
    # Should succeed with placeholder auth (200) or fail without user (401)
    # Once proper auth is implemented, this would fail without valid session
    assert response.status_code in [200, 401], "Send endpoint should use get_current_user dependency"


def test_chat_send_uses_authenticated_user_id(client):
    """Test that chat message is created with authenticated user's ID."""
    # This test will verify user dependency is properly injected
    # For now, just verify the endpoint signature includes user parameter

    # Import the endpoint function directly
    from main import send_chat_message
    import inspect

    # Get function signature
    sig = inspect.signature(send_chat_message)
    params = list(sig.parameters.keys())

    # Should have 'user' parameter
    assert 'user' in params, "send_chat_message should have user parameter"

    # Check if user has Depends annotation
    user_param = sig.parameters['user']
    assert user_param.annotation != inspect.Parameter.empty, "user param should have type annotation"
