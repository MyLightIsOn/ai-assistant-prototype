"""Tests for multi-agent executor integration."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Task, TaskExecution, ActivityLog
from executor import execute_task


# Setup in-memory database for testing
@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_execute_task_routes_to_multi_agent(db_session):
    """Test that multi-agent tasks are routed correctly."""
    # Create multi-agent task
    task = Task(
        id="task_multi_agent",
        userId="user_123",  # Required field
        name="Multi-Agent Test Task",
        description="Test multi-agent execution",
        command="test",
        args="",
        schedule="manual",
        notifyOn="completion,error",
        task_metadata={  # Use task_metadata instead of metadata
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
    )
    db_session.add(task)
    db_session.commit()

    # Mock multi-agent execution
    mock_result = {
        "status": "completed",
        "completed_agents": ["research", "execute"],
        "workspace": "/tmp/test_workspace"
    }

    with patch("executor.execute_multi_agent_task", new_callable=AsyncMock) as mock_multi_agent:
        mock_multi_agent.return_value = mock_result

        output, exit_code = await execute_task(task.id, db_session)

        # Verify multi-agent execution was called
        assert mock_multi_agent.called
        assert exit_code == 0

        # Verify execution record created
        execution = db_session.query(TaskExecution).filter_by(taskId=task.id).first()
        assert execution is not None
        assert execution.status == "completed"

        # Verify output contains multi-agent info
        assert "multi-agent" in output.lower() or "research" in output.lower()


@pytest.mark.asyncio
async def test_execute_task_single_agent_fallback(db_session):
    """Test that non-multi-agent tasks use single-agent execution."""
    # Create regular task (no multi-agent metadata)
    task = Task(
        id="task_single_agent",
        userId="user_123",
        name="Single-Agent Test Task",
        description="Test single-agent execution",
        command="test",
        args="",
        schedule="manual",
        notifyOn="completion,error",
        task_metadata={}
    )
    db_session.add(task)
    db_session.commit()

    # Mock single-agent execution (Claude subprocess)
    async def mock_execute_claude(*args, **kwargs):
        yield "Task output"
        yield "Task completed successfully (exit code: 0)"

    with patch("executor.execute_claude_task", side_effect=mock_execute_claude):
        output, exit_code = await execute_task(task.id, db_session)

        assert exit_code == 0

        # Verify execution record created
        execution = db_session.query(TaskExecution).filter_by(taskId=task.id).first()
        assert execution is not None
        assert execution.status == "completed"


@pytest.mark.asyncio
async def test_execute_task_multi_agent_failure(db_session):
    """Test multi-agent task failure handling."""
    # Create multi-agent task
    task = Task(
        id="task_multi_agent_fail",
        userId="user_123",
        name="Multi-Agent Fail Task",
        description="Test multi-agent failure",
        command="test",
        args="",
        schedule="manual",
        notifyOn="completion,error",
        task_metadata={
            "agents": {
                "enabled": True,
                "sequence": ["research"],
                "roles": {
                    "research": {"type": "research"}
                }
            }
        }
    )
    db_session.add(task)
    db_session.commit()

    # Mock multi-agent execution failure
    mock_result = {
        "status": "failed",
        "failed_agent": "research",
        "completed_agents": [],
        "error": "Agent failed",
        "workspace": "/tmp/test_workspace"
    }

    with patch("executor.execute_multi_agent_task", new_callable=AsyncMock) as mock_multi_agent:
        mock_multi_agent.return_value = mock_result

        output, exit_code = await execute_task(task.id, db_session)

        # Verify failure recorded
        assert exit_code == 1

        execution = db_session.query(TaskExecution).filter_by(taskId=task.id).first()
        assert execution is not None
        assert execution.status == "failed"

        # Verify output contains failure info
        assert "failed" in output.lower()


@pytest.mark.asyncio
async def test_execute_task_multi_agent_with_synthesis(db_session):
    """Test multi-agent task with synthesis."""
    # Create multi-agent task with synthesis
    task = Task(
        id="task_with_synthesis",
        userId="user_123",
        name="Multi-Agent with Synthesis",
        description="Test synthesis",
        command="test",
        args="",
        schedule="manual",
        notifyOn="completion,error",
        task_metadata={
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
    )
    db_session.add(task)
    db_session.commit()

    # Mock multi-agent execution with synthesis
    mock_result = {
        "status": "completed",
        "completed_agents": ["research", "execute"],
        "workspace": "/tmp/test_workspace",
        "synthesis": {
            "summary": "Task completed successfully",
            "key_achievements": ["Achievement 1"]
        },
        "synthesis_duration_ms": 5000
    }

    with patch("executor.execute_multi_agent_task", new_callable=AsyncMock) as mock_multi_agent:
        mock_multi_agent.return_value = mock_result

        output, exit_code = await execute_task(task.id, db_session)

        assert exit_code == 0

        execution = db_session.query(TaskExecution).filter_by(taskId=task.id).first()
        assert execution is not None

        # Verify output contains synthesis results
        assert "synthesis" in output.lower() or "summary" in output.lower()


@pytest.mark.asyncio
async def test_execute_task_activity_logs_for_agents(db_session):
    """Test that activity logs are created for multi-agent execution."""
    # Create multi-agent task
    task = Task(
        id="task_with_logs",
        userId="user_123",
        name="Multi-Agent with Logs",
        description="Test activity logs",
        command="test",
        args="",
        schedule="manual",
        notifyOn="completion,error",
        task_metadata={
            "agents": {
                "enabled": True,
                "sequence": ["research"],
                "roles": {
                    "research": {"type": "research"}
                }
            }
        }
    )
    db_session.add(task)
    db_session.commit()

    # Mock multi-agent execution
    mock_result = {
        "status": "completed",
        "completed_agents": ["research"],
        "workspace": "/tmp/test_workspace"
    }

    with patch("executor.execute_multi_agent_task", new_callable=AsyncMock) as mock_multi_agent:
        mock_multi_agent.return_value = mock_result

        await execute_task(task.id, db_session)

        # Verify activity logs created
        logs = db_session.query(ActivityLog).all()

        # Should have at least task_start and task_complete logs
        assert len(logs) >= 2
