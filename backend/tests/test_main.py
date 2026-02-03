"""
Tests for FastAPI main application.

Following TDD approach:
1. Write failing test
2. Implement minimal code to pass
3. Refactor
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json


# Test 1: FastAPI app can be created and runs
def test_app_creation():
    """Test that FastAPI app can be imported and created."""
    from main import app
    assert app is not None
    assert hasattr(app, 'title')


# Test 2: Health endpoint returns 200 OK
def test_health_endpoint():
    """Test /health endpoint returns service status."""
    from main import app
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert data["service"] == "ai-assistant-backend"


# Test 3: Health endpoint returns database connection status
def test_health_endpoint_includes_database_status():
    """Test /health endpoint checks database connectivity."""
    from main import app
    client = TestClient(app)

    response = client.get("/health")
    data = response.json()

    assert "database" in data
    assert data["database"] in ["connected", "disconnected"]


# Test 4: CORS middleware is configured
def test_cors_middleware_configured():
    """Test that CORS middleware allows frontend origin."""
    from main import app
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


# Test 5: WebSocket endpoint exists
@pytest.mark.asyncio
async def test_websocket_endpoint_exists():
    """Test that /ws WebSocket endpoint exists and accepts connections."""
    from main import app

    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        # Connection should establish without error
        assert websocket is not None


# Test 6: WebSocket accepts connections (auth will be added in future PR)
@pytest.mark.asyncio
async def test_websocket_accepts_connections():
    """Test that WebSocket endpoint accepts connections.

    Note: Authentication will be implemented in a future iteration.
    For Phase 2, we're establishing the basic WebSocket infrastructure.
    """
    from main import app

    client = TestClient(app)

    # Connection should succeed
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "connected"


# Test 7: WebSocket sends welcome message on connection
@pytest.mark.asyncio
async def test_websocket_sends_welcome_message():
    """Test that WebSocket sends welcome message upon successful connection."""
    from main import app
    from database import SessionLocal
    from models import User
    import bcrypt

    # Create a test user and session token
    db = SessionLocal()
    try:
        # Create test user if not exists
        user = db.query(User).filter(User.email == "test@localhost").first()
        if not user:
            password_hash = bcrypt.hashpw("testpass".encode(), bcrypt.gensalt()).decode()
            user = User(
                id="test_user_ws",
                email="test@localhost",
                passwordHash=password_hash
            )
            db.add(user)
            db.commit()

        # For now, we'll test without auth (will be added later)
        client = TestClient(app)
        with client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()

            assert message["type"] == "connected"
            assert "data" in message
            assert "timestamp" in message
    finally:
        db.close()


# Test 8: WebSocket handles ping/pong
@pytest.mark.asyncio
async def test_websocket_ping_pong():
    """Test WebSocket responds to ping with pong."""
    from main import app

    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()

        # Send ping
        websocket.send_json({"type": "ping"})

        # Receive pong
        response = websocket.receive_json()
        assert response["type"] == "pong"


# Test 9: WebSocket can broadcast to multiple clients
@pytest.mark.asyncio
async def test_websocket_broadcast_to_multiple_clients():
    """Test ConnectionManager can broadcast messages to multiple clients."""
    from main import app, manager

    client = TestClient(app)

    # Connect two clients
    with client.websocket_connect("/ws") as ws1:
        with client.websocket_connect("/ws") as ws2:
            # Skip welcome messages
            ws1.receive_json()
            ws2.receive_json()

            # Send a broadcast message (this will be tested when broadcast is implemented)
            # For now, we just verify both connections work
            assert len(manager.active_connections) >= 2


# Test 10: Root endpoint returns API info
def test_root_endpoint():
    """Test root endpoint returns API information."""
    from main import app
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "websocket" in data
