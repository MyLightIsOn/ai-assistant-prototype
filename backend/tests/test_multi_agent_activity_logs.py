"""Tests for multi-agent activity log integration."""

import pytest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from multi_agent.orchestrator import execute_multi_agent_task
from models import ActivityLog


@pytest.mark.asyncio
async def test_agent_started_activity_log(tmp_path):
    """Test that agent_started ActivityLog is created."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    execution_id = "exec_123"
    db_mock = MagicMock(spec=Session)
    activity_logs_created = []

    def capture_add(obj):
        if isinstance(obj, ActivityLog):
            activity_logs_created.append(obj)

    db_mock.add.side_effect = capture_add
    db_mock.commit.return_value = None

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = MagicMock(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={},
            duration_ms=1000,
            error=None
        )

        await execute_multi_agent_task(
            task=task,
            execution_id=execution_id,
            base_path=tmp_path,
            db_session=db_mock
        )

    # Verify agent_started log created
    started_logs = [log for log in activity_logs_created if log.type == "agent_started"]
    assert len(started_logs) == 1
    assert started_logs[0].executionId == execution_id
    assert started_logs[0].message == "Agent 'research' started"
    assert started_logs[0].metadata_["agent_name"] == "research"
    assert started_logs[0].metadata_["role"] == "research"


@pytest.mark.asyncio
async def test_agent_completed_activity_log(tmp_path):
    """Test that agent_completed ActivityLog is created."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    execution_id = "exec_456"
    db_mock = MagicMock(spec=Session)
    activity_logs_created = []

    def capture_add(obj):
        if isinstance(obj, ActivityLog):
            activity_logs_created.append(obj)

    db_mock.add.side_effect = capture_add
    db_mock.commit.return_value = None

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = MagicMock(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={"findings": ["test"]},
            duration_ms=1500,
            error=None
        )

        await execute_multi_agent_task(
            task=task,
            execution_id=execution_id,
            base_path=tmp_path,
            db_session=db_mock
        )

    # Verify agent_completed log created
    completed_logs = [log for log in activity_logs_created if log.type == "agent_completed"]
    assert len(completed_logs) == 1
    assert completed_logs[0].executionId == execution_id
    assert completed_logs[0].message == "Agent 'research' completed successfully"
    assert completed_logs[0].metadata_["agent_name"] == "research"
    assert completed_logs[0].metadata_["duration_ms"] == 1500


@pytest.mark.asyncio
async def test_agent_failed_activity_log(tmp_path):
    """Test that agent_failed ActivityLog is created on failure."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.task_metadata = {
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

    execution_id = "exec_789"
    db_mock = MagicMock(spec=Session)
    activity_logs_created = []

    def capture_add(obj):
        if isinstance(obj, ActivityLog):
            activity_logs_created.append(obj)

    db_mock.add.side_effect = capture_add
    db_mock.commit.return_value = None

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
                error="Execution failed"
            )
        ]

        await execute_multi_agent_task(
            task=task,
            execution_id=execution_id,
            base_path=tmp_path,
            db_session=db_mock
        )

    # Verify agent_failed log created
    failed_logs = [log for log in activity_logs_created if log.type == "agent_failed"]
    assert len(failed_logs) == 1
    assert failed_logs[0].executionId == execution_id
    assert failed_logs[0].message == "Agent 'execute' failed: Execution failed"
    assert failed_logs[0].metadata_["agent_name"] == "execute"
    assert failed_logs[0].metadata_["error"] == "Execution failed"
    assert failed_logs[0].metadata_["exit_code"] == 1


@pytest.mark.asyncio
async def test_synthesis_activity_logs(tmp_path):
    """Test synthesis_started and synthesis_completed ActivityLogs."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": True,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    execution_id = "exec_syn"
    db_mock = MagicMock(spec=Session)
    activity_logs_created = []

    def capture_add(obj):
        if isinstance(obj, ActivityLog):
            activity_logs_created.append(obj)

    db_mock.add.side_effect = capture_add
    db_mock.commit.return_value = None

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute, \
         patch("multi_agent.orchestrator.synthesize_results") as mock_synthesize:

        mock_execute.return_value = MagicMock(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={},
            duration_ms=1000,
            error=None
        )

        mock_synthesize.return_value = {
            "status": "completed",
            "synthesis": {"summary": "Test"},
            "duration_ms": 2000
        }

        await execute_multi_agent_task(
            task=task,
            execution_id=execution_id,
            base_path=tmp_path,
            db_session=db_mock
        )

    # Verify synthesis logs
    synthesis_started = [log for log in activity_logs_created if log.type == "synthesis_started"]
    synthesis_completed = [log for log in activity_logs_created if log.type == "synthesis_completed"]

    assert len(synthesis_started) == 1
    assert synthesis_started[0].message == "Result synthesis started"

    assert len(synthesis_completed) == 1
    assert synthesis_completed[0].message == "Result synthesis completed"
    assert synthesis_completed[0].metadata_["duration_ms"] == 2000


@pytest.mark.asyncio
async def test_activity_logs_without_db_session(tmp_path):
    """Test that orchestrator works when db_session is None (optional)."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": False,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = MagicMock(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={},
            duration_ms=1000,
            error=None
        )

        # Should not raise when db_session is None
        result = await execute_multi_agent_task(
            task=task,
            execution_id="exec_123",
            base_path=tmp_path,
            db_session=None
        )

    assert result["status"] == "completed"
