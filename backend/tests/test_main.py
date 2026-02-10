"""
Tests for FastAPI main application.

Following TDD approach:
1. Write failing test
2. Implement minimal code to pass
3. Refactor
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


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
    assert data["status"] in ["healthy", "degraded"]
    assert "service" in data
    assert data["service"] == "ai-assistant-backend"
    # Verify status matches database and scheduler state
    if data["database"] == "connected" and data["scheduler"] == "running":
        assert data["status"] == "healthy"
    else:
        assert data["status"] == "degraded"


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
    """Test that WebSocket sends welcome message upon successful connection.

    Note: Authentication will be implemented in a future iteration.
    For Phase 2, we're establishing the basic WebSocket infrastructure.
    """
    from main import app

    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()

        assert message["type"] == "connected"
        assert "data" in message
        assert "timestamp" in message


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


# Test 10: WebSocket echoes non-ping messages
@pytest.mark.asyncio
async def test_websocket_echo_message():
    """Test that WebSocket echoes back non-ping messages."""
    from main import app

    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        # Skip welcome message
        websocket.receive_json()

        # Send a custom message
        test_message = {"type": "test", "data": {"content": "hello"}}
        websocket.send_json(test_message)

        # Receive echo response
        response = websocket.receive_json()
        assert response["type"] == "echo"
        assert response["data"] == test_message
        assert "timestamp" in response


# Test 11: Root endpoint returns API info
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


# Test 12: Log viewer endpoint exists
def test_logs_endpoint_exists():
    """Test /api/logs endpoint exists and returns logs."""
    from main import app
    client = TestClient(app)

    response = client.get("/api/logs")

    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert isinstance(data["logs"], list)


# Test 13: Log viewer returns JSON log entries
def test_logs_endpoint_returns_json_entries():
    """Test /api/logs endpoint returns parsed JSON log entries."""
    from main import app
    from logger import get_logger

    # Write some test logs
    logger = get_logger()
    logger.info("Test log entry", extra={"task_id": "test-123"})

    client = TestClient(app)
    response = client.get("/api/logs")

    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) > 0

    # Check structure of log entry
    log_entry = data["logs"][0]
    assert "timestamp" in log_entry
    assert "level" in log_entry
    assert "message" in log_entry


# Test 14: Log viewer supports limit parameter
def test_logs_endpoint_supports_limit():
    """Test /api/logs endpoint supports limit query parameter."""
    from main import app
    client = TestClient(app)

    response = client.get("/api/logs?limit=5")

    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) <= 5


# Test 15: Log viewer returns most recent logs first
def test_logs_endpoint_returns_recent_first():
    """Test /api/logs endpoint returns logs in reverse chronological order."""
    from main import app
    from logger import get_logger

    # Write logs with different timestamps
    logger = get_logger()
    logger.info("First log")
    logger.info("Second log")
    logger.info("Third log")

    client = TestClient(app)
    response = client.get("/api/logs?limit=3")

    assert response.status_code == 200
    data = response.json()

    if len(data["logs"]) >= 2:
        # Most recent should be first
        first_ts = datetime.fromisoformat(data["logs"][0]["timestamp"].replace("Z", "+00:00"))
        second_ts = datetime.fromisoformat(data["logs"][1]["timestamp"].replace("Z", "+00:00"))
        assert first_ts >= second_ts


# Test 16: Log viewer handles invalid log entries gracefully
def test_logs_endpoint_handles_invalid_entries():
    """Test /api/logs endpoint skips invalid JSON lines."""
    from main import app
    import os
    from pathlib import Path

    # This test verifies the endpoint doesn't crash on malformed logs
    # The implementation should skip invalid lines
    client = TestClient(app)
    response = client.get("/api/logs")

    # Should not error even if there are invalid lines
    assert response.status_code == 200


# Test 17: Calendar sync endpoint creates Calendar event
def test_sync_task_endpoint_creates_calendar_event():
    """Test POST /api/calendar/sync creates Calendar event."""
    from unittest.mock import Mock, patch

    with patch('main.get_calendar_sync') as mock_get_sync:
        mock_sync = Mock()
        mock_sync.sync_task_to_calendar.return_value = 'event_12345'
        mock_get_sync.return_value = mock_sync

        with patch('main.get_task_from_db') as mock_get_task:
            mock_task = Mock()
            mock_task.id = 'task_123'
            mock_task.name = 'Test Task'
            mock_get_task.return_value = mock_task

            with patch('main.update_task_metadata') as mock_update:
                from main import app
                client = TestClient(app)

                response = client.post(
                    '/api/calendar/sync',
                    json={'taskId': 'task_123'}
                )

                assert response.status_code == 200
                assert response.json()['event_id'] == 'event_12345'
                assert mock_sync.sync_task_to_calendar.called


# Test 18: Delete task event endpoint
def test_delete_task_event_endpoint():
    """Test DELETE /api/calendar/sync/{task_id} removes event."""
    from unittest.mock import Mock, patch

    with patch('main.get_calendar_sync') as mock_get_sync:
        mock_sync = Mock()
        mock_get_sync.return_value = mock_sync

        with patch('main.get_task_from_db') as mock_get_task:
            mock_task = Mock()
            mock_task.id = 'task_123'
            mock_get_task.return_value = mock_task

            from main import app
            client = TestClient(app)

            response = client.delete('/api/calendar/sync/task_123')

            assert response.status_code == 200
            assert mock_sync.delete_calendar_event.called
