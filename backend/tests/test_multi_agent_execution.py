"""Tests for agent execution with Claude subprocess."""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from multi_agent.orchestrator import (
    execute_single_agent,
    AgentExecutionResult
)


@pytest.mark.asyncio
async def test_execute_single_agent_success(tmp_path):
    """Test successful agent execution."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "research").mkdir()

    # Create instructions file
    instructions = "# Research Agent Instructions\nGather information..."
    (workspace / "agents" / "research" / "instructions.md").write_text(instructions)

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "research" / "status.json", "w") as f:
        json.dump(status, f)

    # Mock Claude subprocess - simulate successful execution
    async def mock_execute_claude(*args, **kwargs):
        # Simulate Claude creating output files
        agent_dir = workspace / "agents" / "research"

        # Create output.json
        output_data = {
            "findings": ["Finding 1", "Finding 2"],
            "summary": "Research complete"
        }
        with open(agent_dir / "output.json", "w") as f:
            json.dump(output_data, f, indent=2)

        # Create output.md
        (agent_dir / "output.md").write_text("# Research Results\nDetailed findings...")

        # Yield some output
        yield "Starting research..."
        yield "Found relevant information"
        yield "Task completed successfully (exit code: 0)"

    with patch("multi_agent.orchestrator.execute_claude_task", side_effect=mock_execute_claude):
        result = await execute_single_agent(
            workspace=workspace,
            agent_name="research"
        )

    assert result.agent_name == "research"
    assert result.status == "completed"
    assert result.exit_code == 0
    assert result.output["findings"] == ["Finding 1", "Finding 2"]
    assert result.duration_ms >= 0  # Can be 0 for fast mocked execution


@pytest.mark.asyncio
async def test_execute_single_agent_failure_exit_code(tmp_path):
    """Test agent execution with non-zero exit code."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "execute").mkdir()

    # Create instructions file
    (workspace / "agents" / "execute" / "instructions.md").write_text("Execute task")

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "execute" / "status.json", "w") as f:
        json.dump(status, f)

    # Mock Claude subprocess - simulate failure
    async def mock_execute_claude(*args, **kwargs):
        yield "Error occurred"
        yield "Task failed with exit code: 1"

    # Mock asyncio.sleep to avoid retry delays
    with patch("multi_agent.orchestrator.execute_claude_task", side_effect=mock_execute_claude), \
         patch("multi_agent.orchestrator.asyncio.sleep", new_callable=AsyncMock):
        result = await execute_single_agent(
            workspace=workspace,
            agent_name="execute"
        )

    assert result.status == "failed"
    assert result.exit_code == 1
    assert result.error is not None


@pytest.mark.asyncio
async def test_execute_single_agent_timeout(tmp_path):
    """Test agent execution with timeout."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "research").mkdir()

    # Create instructions file
    (workspace / "agents" / "research" / "instructions.md").write_text("Research")

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "research" / "status.json", "w") as f:
        json.dump(status, f)

    # Mock Claude subprocess - simulate timeout by raising during iteration
    async def mock_execute_claude(*args, **kwargs):
        yield "Starting task..."
        raise asyncio.TimeoutError("Task timed out")

    # Mock asyncio.sleep to avoid retry delays
    with patch("multi_agent.orchestrator.execute_claude_task", side_effect=mock_execute_claude), \
         patch("multi_agent.orchestrator.asyncio.sleep", new_callable=AsyncMock):
        result = await execute_single_agent(
            workspace=workspace,
            agent_name="research",
            timeout=60
        )

    assert result.status == "failed"
    assert ("timeout" in result.error.lower() or "timed out" in result.error.lower())


@pytest.mark.asyncio
async def test_execute_single_agent_retry_logic(tmp_path):
    """Test agent execution retry logic on failure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "execute").mkdir()

    # Create instructions file
    (workspace / "agents" / "execute" / "instructions.md").write_text("Execute")

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "execute" / "status.json", "w") as f:
        json.dump(status, f)

    call_count = 0

    # Mock Claude subprocess - fail twice, succeed on third
    async def mock_execute_claude(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count <= 2:
            # First two attempts fail
            yield "Error occurred"
            yield "Task failed with exit code: 1"
        else:
            # Third attempt succeeds
            agent_dir = workspace / "agents" / "execute"
            output_data = {"success": True}
            with open(agent_dir / "output.json", "w") as f:
                json.dump(output_data, f)
            yield "Success"
            yield "Task completed successfully (exit code: 0)"

    # Mock asyncio.sleep to avoid delays
    with patch("multi_agent.orchestrator.execute_claude_task", side_effect=mock_execute_claude), \
         patch("multi_agent.orchestrator.asyncio.sleep", new_callable=AsyncMock):
        result = await execute_single_agent(
            workspace=workspace,
            agent_name="execute",
            max_retries=3
        )

    # Should succeed on third attempt
    assert result.status == "completed"
    assert result.exit_code == 0
    assert call_count == 3


@pytest.mark.asyncio
async def test_execute_single_agent_all_retries_fail(tmp_path):
    """Test agent execution when all retries fail."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "execute").mkdir()

    # Create instructions file
    (workspace / "agents" / "execute" / "instructions.md").write_text("Execute")

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "execute" / "status.json", "w") as f:
        json.dump(status, f)

    call_count = 0

    # Mock Claude subprocess - always fails
    async def mock_execute_claude(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        yield "Error occurred"
        yield "Task failed with exit code: 1"

    # Mock asyncio.sleep to avoid delays
    with patch("multi_agent.orchestrator.execute_claude_task", side_effect=mock_execute_claude), \
         patch("multi_agent.orchestrator.asyncio.sleep", new_callable=AsyncMock):
        result = await execute_single_agent(
            workspace=workspace,
            agent_name="execute",
            max_retries=3
        )

    # Should fail after all retries exhausted
    assert result.status == "failed"
    assert call_count == 3  # Should try 3 times


@pytest.mark.asyncio
async def test_execute_single_agent_missing_output_json(tmp_path):
    """Test agent execution when output.json is missing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "research").mkdir()

    # Create instructions file
    (workspace / "agents" / "research" / "instructions.md").write_text("Research")

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "research" / "status.json", "w") as f:
        json.dump(status, f)

    # Mock Claude subprocess - succeeds but doesn't create output.json
    async def mock_execute_claude(*args, **kwargs):
        yield "Task completed successfully (exit code: 0)"

    with patch("multi_agent.orchestrator.execute_claude_task", side_effect=mock_execute_claude):
        result = await execute_single_agent(
            workspace=workspace,
            agent_name="research"
        )

    # Should still complete but with empty output
    assert result.status == "completed"
    assert result.exit_code == 0
    assert result.output == {}


@pytest.mark.asyncio
async def test_execute_single_agent_invalid_output_json(tmp_path):
    """Test agent execution when output.json is malformed."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "agents").mkdir()
    (workspace / "agents" / "research").mkdir()

    # Create instructions file
    (workspace / "agents" / "research" / "instructions.md").write_text("Research")

    # Create status file
    status = {"status": "pending"}
    with open(workspace / "agents" / "research" / "status.json", "w") as f:
        json.dump(status, f)

    # Mock Claude subprocess - creates invalid JSON
    async def mock_execute_claude(*args, **kwargs):
        agent_dir = workspace / "agents" / "research"
        (agent_dir / "output.json").write_text("{ invalid json }")
        yield "Task completed successfully (exit code: 0)"

    with patch("multi_agent.orchestrator.execute_claude_task", side_effect=mock_execute_claude):
        result = await execute_single_agent(
            workspace=workspace,
            agent_name="research"
        )

    # Should handle gracefully with empty output
    assert result.status == "completed"
    assert result.output == {}
