"""
End-to-end integration tests for multi-agent orchestration workflow.

Tests complete multi-agent execution flow including:
- Sequential agent execution (research -> execute -> review)
- WebSocket event broadcasting
- Activity log creation
- Synthesis workflow (enabled/disabled)
- Agent failure scenarios
"""

import pytest
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Task, TaskExecution, ActivityLog
from multi_agent.orchestrator import (
    execute_multi_agent_task,
    AgentExecutionResult
)


# Setup in-memory database for integration testing
@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def mock_task():
    """Create a mock multi-agent task."""
    task = MagicMock()
    task.id = f"task_{uuid.uuid4().hex[:8]}"
    task.name = "Integration Test Task"
    task.description = "Test multi-agent integration"
    return task


# Test 1: Complete multi-agent workflow (research -> execute -> review)
@pytest.mark.asyncio
async def test_complete_multi_agent_workflow(mock_task, tmp_workspace, db_session):
    """
    Test full multi-agent execution flow with three agents in sequence.

    Verifies:
    - All agents execute in correct order
    - WebSocket events are broadcast
    - Activity logs are created for each lifecycle event
    - Workspace structure is maintained
    """
    mock_task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute", "review"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"},
                "execute": {"type": "execute"},
                "review": {"type": "review"}
            }
        }
    }

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"

    # Capture broadcast events and activity logs
    events_captured = []
    logs_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    def capture_log_add(obj):
        if isinstance(obj, ActivityLog):
            logs_captured.append(obj)

    db_session.add = MagicMock(side_effect=capture_log_add)
    db_session.commit = MagicMock()

    # Mock agent execution - all succeed
    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.side_effect = [
            AgentExecutionResult(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={"findings": ["Finding 1", "Finding 2"]},
                duration_ms=1000
            ),
            AgentExecutionResult(
                agent_name="execute",
                status="completed",
                exit_code=0,
                output={"files_created": ["main.py", "test.py"]},
                duration_ms=2000
            ),
            AgentExecutionResult(
                agent_name="review",
                status="completed",
                exit_code=0,
                output={"review_status": "passed"},
                duration_ms=1500
            )
        ]

        result = await execute_multi_agent_task(
            task=mock_task,
            execution_id=execution_id,
            base_path=tmp_workspace.parent,
            broadcast_callback=capture_broadcast,
            db_session=db_session
        )

    # Verify overall result
    assert result["status"] == "completed"
    assert len(result["completed_agents"]) == 3
    assert result["completed_agents"] == ["research", "execute", "review"]
    assert "workspace" in result

    # Verify WebSocket events broadcast in correct order
    event_types = [e["type"] for e in events_captured if "type" in e]

    # Should have: started, completed for each agent (6 events minimum)
    agent_started_events = [e for e in events_captured if e.get("type") == "agent_started"]
    agent_completed_events = [e for e in events_captured if e.get("type") == "agent_completed"]

    assert len(agent_started_events) == 3
    assert len(agent_completed_events) == 3

    # Verify agents executed in sequence
    started_names = [e["agent_name"] for e in agent_started_events]
    assert started_names == ["research", "execute", "review"]

    completed_names = [e["agent_name"] for e in agent_completed_events]
    assert completed_names == ["research", "execute", "review"]

    # Verify activity logs created for all lifecycle events
    log_types = [log.type for log in logs_captured]

    # Should have: started, completed for each agent
    assert log_types.count("agent_started") == 3
    assert log_types.count("agent_completed") == 3

    # Verify workspace structure
    workspace = Path(result["workspace"])
    assert workspace.exists()
    assert (workspace / "task.json").exists()
    assert (workspace / "shared" / "context.json").exists()
    assert (workspace / "agents" / "research").exists()
    assert (workspace / "agents" / "execute").exists()
    assert (workspace / "agents" / "review").exists()


# Test 2: Multi-agent workflow with synthesis enabled
@pytest.mark.asyncio
async def test_multi_agent_workflow_with_synthesis(mock_task, tmp_workspace, db_session):
    """
    Test multi-agent execution with synthesis enabled.

    Verifies:
    - Synthesis runs after all agents complete
    - synthesis_started and synthesis_completed events broadcast
    - Synthesis activity logs created
    - Synthesis result included in output
    """
    mock_task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute"],
            "synthesize": True,  # Enable synthesis
            "roles": {
                "research": {"type": "research"},
                "execute": {"type": "execute"}
            }
        }
    }

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    events_captured = []
    logs_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    def capture_log_add(obj):
        if isinstance(obj, ActivityLog):
            logs_captured.append(obj)

    db_session.add = MagicMock(side_effect=capture_log_add)
    db_session.commit = MagicMock()

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute, \
         patch("multi_agent.orchestrator.synthesize_results") as mock_synthesize:

        mock_execute.side_effect = [
            AgentExecutionResult(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={"findings": ["Finding 1"]},
                duration_ms=1000
            ),
            AgentExecutionResult(
                agent_name="execute",
                status="completed",
                exit_code=0,
                output={"files_created": ["main.py"]},
                duration_ms=2000
            )
        ]

        mock_synthesize.return_value = {
            "status": "completed",
            "synthesis": {
                "summary": "Task completed successfully",
                "key_achievements": ["Research completed", "Code implemented"]
            },
            "duration_ms": 3000
        }

        result = await execute_multi_agent_task(
            task=mock_task,
            execution_id=execution_id,
            base_path=tmp_workspace.parent,
            broadcast_callback=capture_broadcast,
            db_session=db_session
        )

    # Verify result includes synthesis
    assert result["status"] == "completed"
    assert "synthesis" in result
    assert result["synthesis"]["summary"] == "Task completed successfully"

    # Verify synthesis WebSocket events
    synthesis_started = [e for e in events_captured if e.get("type") == "synthesis_started"]
    synthesis_completed = [e for e in events_captured if e.get("type") == "synthesis_completed"]

    assert len(synthesis_started) == 1
    assert len(synthesis_completed) == 1
    assert synthesis_completed[0]["duration_ms"] == 3000

    # Verify synthesis activity logs
    log_types = [log.type for log in logs_captured]
    assert "synthesis_started" in log_types
    assert "synthesis_completed" in log_types

    synthesis_complete_logs = [log for log in logs_captured if log.type == "synthesis_completed"]
    assert len(synthesis_complete_logs) == 1
    assert synthesis_complete_logs[0].metadata_["duration_ms"] == 3000


# Test 3: Multi-agent workflow with synthesis disabled
@pytest.mark.asyncio
async def test_multi_agent_workflow_without_synthesis(mock_task, tmp_workspace, db_session):
    """
    Test multi-agent execution with synthesis disabled.

    Verifies:
    - No synthesis runs
    - No synthesis events broadcast
    - No synthesis activity logs created
    """
    mock_task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,  # Explicitly disabled
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    events_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    db_session.add = MagicMock()
    db_session.commit = MagicMock()

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = AgentExecutionResult(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={"findings": []},
            duration_ms=1000
        )

        result = await execute_multi_agent_task(
            task=mock_task,
            execution_id=execution_id,
            base_path=tmp_workspace.parent,
            broadcast_callback=capture_broadcast,
            db_session=db_session
        )

    # Verify no synthesis in result
    assert result["status"] == "completed"
    assert "synthesis" not in result

    # Verify no synthesis events
    event_types = [e.get("type") for e in events_captured]
    assert "synthesis_started" not in event_types
    assert "synthesis_completed" not in event_types


# Test 4: Agent failure scenario (fail-fast behavior)
@pytest.mark.asyncio
async def test_agent_failure_stops_execution(mock_task, tmp_workspace, db_session):
    """
    Test that agent failure stops execution (fail-fast).

    Verifies:
    - First agent completes successfully
    - Second agent fails
    - Third agent does not execute
    - agent_failed event broadcast
    - agent_failed activity log created
    - Overall status is 'failed'
    """
    mock_task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute", "review"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"},
                "execute": {"type": "execute"},
                "review": {"type": "review"}
            }
        }
    }

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    events_captured = []
    logs_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    def capture_log_add(obj):
        if isinstance(obj, ActivityLog):
            logs_captured.append(obj)

    db_session.add = MagicMock(side_effect=capture_log_add)
    db_session.commit = MagicMock()

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        # Research succeeds, execute fails, review should not run
        mock_execute.side_effect = [
            AgentExecutionResult(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={"findings": []},
                duration_ms=1000
            ),
            AgentExecutionResult(
                agent_name="execute",
                status="failed",
                exit_code=1,
                output={},
                duration_ms=500,
                error="Execution failed: syntax error"
            )
        ]

        result = await execute_multi_agent_task(
            task=mock_task,
            execution_id=execution_id,
            base_path=tmp_workspace.parent,
            broadcast_callback=capture_broadcast,
            db_session=db_session
        )

    # Verify fail-fast behavior
    assert result["status"] == "failed"
    assert result["failed_agent"] == "execute"
    assert len(result["completed_agents"]) == 1
    assert "research" in result["completed_agents"]
    assert "review" not in result["completed_agents"]  # Should not have run

    # Verify only 2 agents executed (research + execute, review skipped)
    assert mock_execute.call_count == 2

    # Verify agent_failed event broadcast
    failed_events = [e for e in events_captured if e.get("type") == "agent_failed"]
    assert len(failed_events) == 1
    assert failed_events[0]["agent_name"] == "execute"
    assert "syntax error" in failed_events[0]["error"]

    # Verify agent_failed activity log
    failed_logs = [log for log in logs_captured if log.type == "agent_failed"]
    assert len(failed_logs) == 1
    assert failed_logs[0].metadata_["agent_name"] == "execute"
    assert "syntax error" in failed_logs[0].metadata_["error"]


# Test 5: WebSocket event order and content validation
@pytest.mark.asyncio
async def test_websocket_event_order_and_content(mock_task, tmp_workspace, db_session):
    """
    Test that WebSocket events are broadcast in correct order with proper content.

    Verifies:
    - Events contain required fields
    - Events are in sequential order
    - Timestamps are present and valid
    """
    mock_task.task_metadata = {
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

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    events_captured = []

    async def capture_broadcast(event):
        events_captured.append(event)

    db_session.add = MagicMock()
    db_session.commit = MagicMock()

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute, \
         patch("multi_agent.orchestrator.synthesize_results") as mock_synthesize:

        mock_execute.side_effect = [
            AgentExecutionResult(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={"findings": []},
                duration_ms=1000
            ),
            AgentExecutionResult(
                agent_name="execute",
                status="completed",
                exit_code=0,
                output={},
                duration_ms=2000
            )
        ]

        mock_synthesize.return_value = {
            "status": "completed",
            "synthesis": {},
            "duration_ms": 500
        }

        result = await execute_multi_agent_task(
            task=mock_task,
            execution_id=execution_id,
            base_path=tmp_workspace.parent,
            broadcast_callback=capture_broadcast,
            db_session=db_session
        )

    # Verify all events have required fields
    for event in events_captured:
        assert "type" in event
        assert "timestamp" in event

    # Extract agent lifecycle events in order
    lifecycle_events = [
        e for e in events_captured
        if e.get("type") in ["agent_started", "agent_completed", "agent_failed"]
    ]

    # Expected order: research started, research completed, execute started, execute completed
    assert len(lifecycle_events) >= 4
    assert lifecycle_events[0]["type"] == "agent_started"
    assert lifecycle_events[0]["agent_name"] == "research"

    assert lifecycle_events[1]["type"] == "agent_completed"
    assert lifecycle_events[1]["agent_name"] == "research"
    assert lifecycle_events[1]["duration_ms"] == 1000

    assert lifecycle_events[2]["type"] == "agent_started"
    assert lifecycle_events[2]["agent_name"] == "execute"

    assert lifecycle_events[3]["type"] == "agent_completed"
    assert lifecycle_events[3]["agent_name"] == "execute"
    assert lifecycle_events[3]["duration_ms"] == 2000

    # Verify synthesis events come after all agent events
    synthesis_started_events = [e for e in events_captured if e.get("type") == "synthesis_started"]
    synthesis_completed_events = [e for e in events_captured if e.get("type") == "synthesis_completed"]

    assert len(synthesis_started_events) == 1
    assert len(synthesis_completed_events) == 1

    # Synthesis events should come after all agent events
    synthesis_start_index = events_captured.index(synthesis_started_events[0])
    last_agent_event_index = events_captured.index(lifecycle_events[-1])
    assert synthesis_start_index > last_agent_event_index


# Test 6: Activity log creation and content validation
@pytest.mark.asyncio
async def test_activity_log_creation_and_content(mock_task, tmp_workspace, db_session):
    """
    Test that activity logs are created with correct content.

    Verifies:
    - All lifecycle events create activity logs
    - Logs contain correct metadata
    - Execution IDs are consistent
    """
    mock_task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    logs_captured = []

    def capture_log_add(obj):
        if isinstance(obj, ActivityLog):
            logs_captured.append(obj)

    db_session.add = MagicMock(side_effect=capture_log_add)
    db_session.commit = MagicMock()

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = AgentExecutionResult(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={"findings": ["test"]},
            duration_ms=1500
        )

        result = await execute_multi_agent_task(
            task=mock_task,
            execution_id=execution_id,
            base_path=tmp_workspace.parent,
            broadcast_callback=None,
            db_session=db_session
        )

    # Verify agent_started log
    started_logs = [log for log in logs_captured if log.type == "agent_started"]
    assert len(started_logs) == 1
    assert started_logs[0].executionId == execution_id
    assert started_logs[0].message == "Agent 'research' started"
    assert started_logs[0].metadata_["agent_name"] == "research"
    assert started_logs[0].metadata_["role"] == "research"

    # Verify agent_completed log
    completed_logs = [log for log in logs_captured if log.type == "agent_completed"]
    assert len(completed_logs) == 1
    assert completed_logs[0].executionId == execution_id
    assert completed_logs[0].message == "Agent 'research' completed successfully"
    assert completed_logs[0].metadata_["agent_name"] == "research"
    assert completed_logs[0].metadata_["duration_ms"] == 1500


# Test 7: Multi-agent workflow without database session (optional db_session)
@pytest.mark.asyncio
async def test_multi_agent_workflow_without_db_session(mock_task, tmp_workspace):
    """
    Test that multi-agent orchestrator works when db_session is None.

    Verifies:
    - Execution completes successfully
    - No activity logs attempted (graceful handling)
    """
    mock_task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    execution_id = f"exec_{uuid.uuid4().hex[:8]}"

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = AgentExecutionResult(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={},
            duration_ms=1000
        )

        # Should not raise when db_session is None
        result = await execute_multi_agent_task(
            task=mock_task,
            execution_id=execution_id,
            base_path=tmp_workspace.parent,
            broadcast_callback=None,
            db_session=None
        )

    assert result["status"] == "completed"
    assert len(result["completed_agents"]) == 1
