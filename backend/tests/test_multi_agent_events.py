"""Tests for multi-agent WebSocket broadcasting and activity logging."""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone

from multi_agent.orchestrator import execute_multi_agent_task
from multi_agent.roles import AgentRole


@pytest.mark.asyncio
async def test_agent_started_websocket_event(tmp_path):
    """Test that agent_started WebSocket event is broadcast."""
    # Create mock task
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test description"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    # Mock broadcast callback to capture events
    broadcast_mock = AsyncMock()
    events_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)
        await broadcast_mock(event)

    # Mock agent execution
    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = MagicMock(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={"findings": []},
            duration_ms=1000,
            error=None
        )

        await execute_multi_agent_task(
            task=task,
            execution_id="exec_123",
            base_path=tmp_path,
            broadcast_callback=capture_broadcast
        )

    # Verify agent_started event was broadcast
    started_events = [e for e in events_captured if e.get("type") == "agent_started"]
    assert len(started_events) == 1
    assert started_events[0]["agent_name"] == "research"
    assert "timestamp" in started_events[0]


@pytest.mark.asyncio
async def test_agent_completed_websocket_event(tmp_path):
    """Test that agent_completed WebSocket event is broadcast."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    broadcast_mock = AsyncMock()
    events_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)
        await broadcast_mock(event)

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = MagicMock(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={"findings": ["Finding 1"]},
            duration_ms=1500,
            error=None
        )

        await execute_multi_agent_task(
            task=task,
            execution_id="exec_456",
            base_path=tmp_path,
            broadcast_callback=capture_broadcast
        )

    # Verify agent_completed event
    completed_events = [e for e in events_captured if e.get("type") == "agent_completed"]
    assert len(completed_events) == 1
    assert completed_events[0]["agent_name"] == "research"
    assert completed_events[0]["status"] == "completed"
    assert completed_events[0]["duration_ms"] == 1500


@pytest.mark.asyncio
async def test_agent_failed_websocket_event(tmp_path):
    """Test that agent_failed WebSocket event is broadcast on failure."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"},
                "execute": {"type": "execute"}
            }
        }
    }

    events_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        # First agent succeeds, second fails
        mock_execute.side_effect = [
            MagicMock(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={},
                duration_ms=1000,
                error=None
            ),
            MagicMock(
                agent_name="execute",
                status="failed",
                exit_code=1,
                output={},
                duration_ms=500,
                error="Execution error"
            )
        ]

        await execute_multi_agent_task(
            task=task,
            execution_id="exec_789",
            base_path=tmp_path,
            broadcast_callback=capture_broadcast
        )

    # Verify agent_failed event
    failed_events = [e for e in events_captured if e.get("type") == "agent_failed"]
    assert len(failed_events) == 1
    assert failed_events[0]["agent_name"] == "execute"
    assert failed_events[0]["error"] == "Execution error"


@pytest.mark.asyncio
async def test_synthesis_events_when_enabled(tmp_path):
    """Test synthesis_started and synthesis_completed events."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": True,  # Enable synthesis
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    events_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute, \
         patch("multi_agent.orchestrator.synthesize_results") as mock_synthesize:

        mock_execute.return_value = MagicMock(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={"findings": []},
            duration_ms=1000,
            error=None
        )

        mock_synthesize.return_value = {
            "status": "completed",
            "synthesis": {"summary": "Test summary"},
            "duration_ms": 2000
        }

        await execute_multi_agent_task(
            task=task,
            execution_id="exec_syn",
            base_path=tmp_path,
            broadcast_callback=capture_broadcast
        )

    # Verify synthesis events
    synthesis_started = [e for e in events_captured if e.get("type") == "synthesis_started"]
    synthesis_completed = [e for e in events_captured if e.get("type") == "synthesis_completed"]

    assert len(synthesis_started) == 1
    assert len(synthesis_completed) == 1
    assert synthesis_completed[0]["duration_ms"] == 2000


@pytest.mark.asyncio
async def test_all_websocket_events_in_order(tmp_path):
    """Test that all events are broadcast in correct order."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute"],
            "synthesize": True,
            "roles": {
                "research": {"type": "research"},
                "execute": {"type": "execute"}
            }
        }
    }

    events_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute, \
         patch("multi_agent.orchestrator.synthesize_results") as mock_synthesize:

        mock_execute.side_effect = [
            MagicMock(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={},
                duration_ms=1000,
                error=None
            ),
            MagicMock(
                agent_name="execute",
                status="completed",
                exit_code=0,
                output={},
                duration_ms=2000,
                error=None
            )
        ]

        mock_synthesize.return_value = {
            "status": "completed",
            "synthesis": {},
            "duration_ms": 500
        }

        await execute_multi_agent_task(
            task=task,
            execution_id="exec_order",
            base_path=tmp_path,
            broadcast_callback=capture_broadcast
        )

    # Extract event types in order
    event_types = [e["type"] for e in events_captured if "type" in e]

    # Expected order: started, output(s), completed, started, output(s), completed, synthesis_started, synthesis_completed
    assert "agent_started" in event_types
    assert "agent_completed" in event_types
    assert "synthesis_started" in event_types
    assert "synthesis_completed" in event_types

    # Check agents processed in sequence
    agent_started_indices = [i for i, t in enumerate(event_types) if t == "agent_started"]
    assert len(agent_started_indices) == 2  # Two agents

    # First agent events should come before second agent events
    research_start = event_types.index("agent_started")
    # Find second agent_started after first
    execute_start = event_types.index("agent_started", research_start + 1)
    assert research_start < execute_start
