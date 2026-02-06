"""Tests for multi-agent result synthesis."""

import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
from multi_agent.synthesis import (
    synthesize_results,
    generate_synthesis_prompt
)


@pytest.mark.asyncio
async def test_generate_synthesis_prompt(tmp_path):
    """Test generating synthesis prompt from agent outputs."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create shared context with multiple agent outputs
    context = {
        "task_description": "Implement user authentication",
        "completed_agents": ["research", "execute", "review"],
        "research": {
            "findings": ["OAuth 2.0 is industry standard", "JWT tokens recommended"],
            "summary": "Research complete on auth methods"
        },
        "execute": {
            "files_created": ["auth.py", "token.py"],
            "implementation_summary": "Implemented JWT-based auth"
        },
        "review": {
            "quality_score": 8.5,
            "issues": [],
            "recommendations": ["Add rate limiting"]
        }
    }

    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    prompt = generate_synthesis_prompt(workspace)

    # Verify prompt includes task description
    assert "Implement user authentication" in prompt

    # Verify prompt includes agent outputs
    assert "research" in prompt.lower()
    assert "execute" in prompt.lower()
    assert "review" in prompt.lower()

    # Verify structured format requested
    assert "summary" in prompt.lower()
    assert "json" in prompt.lower()


@pytest.mark.asyncio
async def test_synthesize_results_success(tmp_path):
    """Test successful result synthesis."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create shared context
    context = {
        "task_description": "Build feature X",
        "completed_agents": ["research", "execute"],
        "research": {"findings": ["Finding 1"]},
        "execute": {"files_created": ["feature.py"]}
    }

    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    # Mock Claude subprocess - simulate synthesis
    async def mock_execute_claude(*args, **kwargs):
        # Create synthesis output
        synthesis_data = {
            "summary": "Successfully implemented feature X",
            "key_achievements": [
                "Researched best practices",
                "Implemented core functionality"
            ],
            "recommendations": ["Add tests", "Document API"]
        }

        synthesis_file = workspace / "final_result.json"
        with open(synthesis_file, "w") as f:
            json.dump(synthesis_data, f, indent=2)

        yield "Synthesizing results..."
        yield "Task completed successfully (exit code: 0)"

    with patch("multi_agent.synthesis.execute_claude_task", side_effect=mock_execute_claude):
        result = await synthesize_results(workspace)

    assert result["status"] == "completed"
    assert result["synthesis"]["summary"] == "Successfully implemented feature X"
    assert len(result["synthesis"]["key_achievements"]) == 2


@pytest.mark.asyncio
async def test_synthesize_results_failure(tmp_path):
    """Test synthesis failure handling."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create shared context
    context = {
        "task_description": "Test task",
        "completed_agents": ["research"]
    }

    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    # Mock Claude subprocess - simulate failure
    async def mock_execute_claude(*args, **kwargs):
        yield "Error during synthesis"
        yield "Task failed with exit code: 1"

    with patch("multi_agent.synthesis.execute_claude_task", side_effect=mock_execute_claude), \
         patch("multi_agent.synthesis.asyncio.sleep", new_callable=AsyncMock):
        result = await synthesize_results(workspace)

    assert result["status"] == "failed"
    assert "error" in result


@pytest.mark.asyncio
async def test_synthesize_results_empty_agents(tmp_path):
    """Test synthesis with no completed agents."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create empty context
    context = {
        "task_description": "Test task",
        "completed_agents": []
    }

    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    result = await synthesize_results(workspace)

    # Should return error for no agents to synthesize
    assert result["status"] == "failed"
    assert "no completed agents" in result["error"].lower()


@pytest.mark.asyncio
async def test_synthesize_results_missing_output_file(tmp_path):
    """Test synthesis when output file is not created."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create shared context
    context = {
        "task_description": "Test task",
        "completed_agents": ["research"],
        "research": {"findings": []}
    }

    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    # Mock Claude subprocess - completes but doesn't create output
    async def mock_execute_claude(*args, **kwargs):
        yield "Task completed successfully (exit code: 0)"

    with patch("multi_agent.synthesis.execute_claude_task", side_effect=mock_execute_claude):
        result = await synthesize_results(workspace)

    # Should still complete but with empty synthesis
    assert result["status"] == "completed"
    assert result["synthesis"] == {}


@pytest.mark.asyncio
async def test_synthesize_results_invalid_json(tmp_path):
    """Test synthesis with malformed JSON output."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create shared context
    context = {
        "task_description": "Test task",
        "completed_agents": ["research"],
        "research": {"findings": []}
    }

    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    # Mock Claude subprocess - creates invalid JSON
    async def mock_execute_claude(*args, **kwargs):
        synthesis_file = workspace / "final_result.json"
        synthesis_file.write_text("{ invalid json }")
        yield "Task completed successfully (exit code: 0)"

    with patch("multi_agent.synthesis.execute_claude_task", side_effect=mock_execute_claude):
        result = await synthesize_results(workspace)

    # Should handle gracefully
    assert result["status"] == "completed"
    assert result["synthesis"] == {}


@pytest.mark.asyncio
async def test_synthesize_results_timeout(tmp_path):
    """Test synthesis timeout handling."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create shared context
    context = {
        "task_description": "Test task",
        "completed_agents": ["research"],
        "research": {"findings": []}
    }

    with open(workspace / "shared" / "context.json", "w") as f:
        json.dump(context, f)

    # Mock Claude subprocess - simulate timeout
    async def mock_execute_claude(*args, **kwargs):
        yield "Starting synthesis..."
        raise asyncio.TimeoutError("Synthesis timed out")

    with patch("multi_agent.synthesis.execute_claude_task", side_effect=mock_execute_claude), \
         patch("multi_agent.synthesis.asyncio.sleep", new_callable=AsyncMock):
        result = await synthesize_results(workspace, timeout=60)

    assert result["status"] == "failed"
    assert ("timeout" in result["error"].lower() or "timed out" in result["error"].lower())
