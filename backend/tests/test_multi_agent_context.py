"""Tests for shared context management."""

import json
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_agent.context import (
    read_shared_context,
    update_shared_context,
    append_agent_output
)


def test_read_shared_context(tmp_path):
    """Test reading shared context file."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Create context file
    context_data = {
        "task_id": "task_123",
        "completed_agents": ["research"]
    }
    context_file = workspace / "shared" / "context.json"
    with open(context_file, "w") as f:
        json.dump(context_data, f)

    # Read context
    context = read_shared_context(workspace)

    assert context["task_id"] == "task_123"
    assert "research" in context["completed_agents"]


def test_update_shared_context(tmp_path):
    """Test updating shared context with agent output."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Initialize context
    initial_context = {
        "task_id": "task_123",
        "completed_agents": []
    }
    context_file = workspace / "shared" / "context.json"
    with open(context_file, "w") as f:
        json.dump(initial_context, f)

    # Update context
    agent_output = {
        "findings": ["Finding 1", "Finding 2"],
        "summary": "Research complete"
    }
    update_shared_context(workspace, "research", agent_output)

    # Verify update
    with open(context_file) as f:
        context = json.load(f)

    assert "research" in context["completed_agents"]
    assert context["research"]["findings"] == ["Finding 1", "Finding 2"]
    assert context["research"]["summary"] == "Research complete"


def test_append_agent_output_to_context(tmp_path):
    """Test appending multiple agent outputs."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    # Initialize context
    context = {"task_id": "task_123", "completed_agents": []}
    context_file = workspace / "shared" / "context.json"
    with open(context_file, "w") as f:
        json.dump(context, f)

    # Add research output
    append_agent_output(workspace, "research", {"data": "research data"})

    # Add execute output
    append_agent_output(workspace, "execute", {"data": "execute data"})

    # Verify both added
    final_context = read_shared_context(workspace)
    assert len(final_context["completed_agents"]) == 2
    assert "research" in final_context["completed_agents"]
    assert "execute" in final_context["completed_agents"]
