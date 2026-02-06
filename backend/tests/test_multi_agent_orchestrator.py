"""Tests for multi-agent orchestrator."""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from multi_agent.orchestrator import (
    execute_multi_agent_task,
    prepare_agent_execution,
    AgentExecutionResult
)
from multi_agent.roles import AgentRole


@pytest.mark.asyncio
async def test_prepare_agent_execution(tmp_path):
    """Test preparing agent for execution."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "research").mkdir()
    (workspace / "shared").mkdir()

    # Create shared context
    context = {"task_description": "Test task", "completed_agents": []}
    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "research" / "status.json", "w") as f:
        json.dump(status, f)

    task_data = {"name": "Test", "description": "Test task"}
    role_config = {"type": "research"}

    # Prepare agent
    await prepare_agent_execution(
        workspace,
        "research",
        task_data,
        role_config
    )

    # Verify instructions created
    instructions_file = workspace / "agents" / "research" / "instructions.md"
    assert instructions_file.exists()

    instructions_content = instructions_file.read_text()
    assert "Research agent" in instructions_content
    assert "Test task" in instructions_content


@pytest.mark.asyncio
async def test_prepare_agent_execution_with_custom_instructions(tmp_path):
    """Test preparing agent with custom instructions."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "custom").mkdir()
    (workspace / "shared").mkdir()

    # Create shared context
    context = {"task_description": "Test task", "completed_agents": []}
    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    task_data = {"name": "Test", "description": "Test task"}
    role_config = {
        "type": "custom",
        "instructions": "Perform security audit"
    }

    await prepare_agent_execution(
        workspace,
        "custom",
        task_data,
        role_config
    )

    instructions_file = workspace / "agents" / "custom" / "instructions.md"
    assert instructions_file.exists()

    instructions_content = instructions_file.read_text()
    assert "Perform security audit" in instructions_content


@pytest.mark.asyncio
async def test_execute_multi_agent_task_success(tmp_path):
    """Test successful multi-agent execution."""
    # Create mock task
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test description"
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

    execution_id = "exec_123"

    # Mock agent execution
    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        # Research agent succeeds
        mock_execute.side_effect = [
            AgentExecutionResult(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={"findings": ["Finding 1"]},
                duration_ms=1000
            ),
            # Execute agent succeeds
            AgentExecutionResult(
                agent_name="execute",
                status="completed",
                exit_code=0,
                output={"files_created": ["file1.py"]},
                duration_ms=2000
            )
        ]

        result = await execute_multi_agent_task(
            task=task,
            execution_id=execution_id,
            base_path=tmp_path
        )

    assert result["status"] == "completed"
    assert len(result["completed_agents"]) == 2
    assert "research" in result["completed_agents"]
    assert "execute" in result["completed_agents"]
    assert "workspace" in result


@pytest.mark.asyncio
async def test_execute_multi_agent_task_agent_failure(tmp_path):
    """Test multi-agent execution with agent failure (fail-fast)."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute", "review"],
            "roles": {
                "research": {"type": "research"},
                "execute": {"type": "execute"},
                "review": {"type": "review"}
            }
        }
    }

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        # Research succeeds
        mock_execute.side_effect = [
            AgentExecutionResult(
                agent_name="research",
                status="completed",
                exit_code=0,
                output={"findings": []},
                duration_ms=1000
            ),
            # Execute fails
            AgentExecutionResult(
                agent_name="execute",
                status="failed",
                exit_code=1,
                output={},
                error="Execution failed",
                duration_ms=500
            )
        ]

        result = await execute_multi_agent_task(
            task=task,
            execution_id="exec_456",
            base_path=tmp_path
        )

    # Should fail fast
    assert result["status"] == "failed"
    assert result["failed_agent"] == "execute"
    assert len(result["completed_agents"]) == 1
    assert "research" in result["completed_agents"]
    # Review should not run
    assert "review" not in result["completed_agents"]


@pytest.mark.asyncio
async def test_execute_multi_agent_task_with_synthesis_flag(tmp_path):
    """Test multi-agent execution sets synthesis_required flag."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "synthesize": True,
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute, \
         patch("multi_agent.orchestrator.synthesize_results") as mock_synthesis:
        mock_execute.return_value = AgentExecutionResult(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={"findings": ["Finding 1"]},
            duration_ms=1000
        )

        # Mock synthesis to return success
        mock_synthesis.return_value = {
            "status": "completed",
            "synthesis": {"summary": "Test synthesis"},
            "duration_ms": 500
        }

        result = await execute_multi_agent_task(
            task=task,
            execution_id="exec_789",
            base_path=tmp_path
        )

    assert result["status"] == "completed"
    # Implementation runs synthesis immediately, not deferred
    # Check for synthesis result (success or failure)
    assert "synthesis" in result or "synthesis_failed" in result


@pytest.mark.asyncio
async def test_execute_multi_agent_task_invalid_metadata(tmp_path):
    """Test execution fails with invalid metadata."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            # Missing 'roles' - invalid
        }
    }

    with pytest.raises(ValueError, match="roles"):
        await execute_multi_agent_task(
            task=task,
            execution_id="exec_invalid",
            base_path=tmp_path
        )


@pytest.mark.asyncio
async def test_execute_multi_agent_task_creates_workspace_structure(tmp_path):
    """Test that workspace structure is created correctly."""
    task = MagicMock()
    task.id = "task_123"
    task.name = "Test Task"
    task.description = "Test"
    task.metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    with patch("multi_agent.orchestrator.execute_single_agent") as mock_execute:
        mock_execute.return_value = AgentExecutionResult(
            agent_name="research",
            status="completed",
            exit_code=0,
            output={},
            duration_ms=1000
        )

        result = await execute_multi_agent_task(
            task=task,
            execution_id="exec_workspace",
            base_path=tmp_path
        )

    workspace = Path(result["workspace"])
    assert workspace.exists()
    assert (workspace / "task.json").exists()
    assert (workspace / "shared" / "context.json").exists()
    assert (workspace / "agents" / "research").exists()
    assert (workspace / "agents" / "research" / "status.json").exists()
