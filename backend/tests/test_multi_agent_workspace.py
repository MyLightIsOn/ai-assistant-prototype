"""Tests for multi-agent workspace creation and management."""

import json
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_agent.workspace import (
    create_agent_workspace,
    init_shared_context
)


def test_create_agent_workspace(tmp_path):
    """Test workspace directory structure creation."""
    execution_id = "test_exec_123"
    workspace = create_agent_workspace(execution_id, base_path=tmp_path)

    # Verify main workspace created
    assert workspace.exists()
    assert workspace.name == execution_id

    # Verify subdirectories created
    assert (workspace / "shared").exists()
    assert (workspace / "agents").exists()

    # Verify task.json placeholder exists
    assert (workspace / "task.json").exists()


def test_create_agent_workspace_with_agents(tmp_path):
    """Test workspace creates agent directories."""
    execution_id = "test_exec_456"
    agents = ["research", "execute", "review"]

    workspace = create_agent_workspace(
        execution_id,
        agents=agents,
        base_path=tmp_path
    )

    # Verify agent directories created
    for agent in agents:
        agent_dir = workspace / "agents" / agent
        assert agent_dir.exists()
        assert (agent_dir / "instructions.md").exists()
        assert (agent_dir / "status.json").exists()


def test_init_shared_context(tmp_path):
    """Test shared context initialization."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    task_data = {
        "id": "task_123",
        "name": "Test Task",
        "description": "Test description"
    }

    init_shared_context(workspace, task_data)

    # Verify context file created
    context_file = workspace / "shared" / "context.json"
    assert context_file.exists()

    # Verify content
    with open(context_file) as f:
        context = json.load(f)

    assert context["task_description"] == "Test description"
    assert context["completed_agents"] == []
    assert "task_id" in context


def test_create_agent_workspace_validates_execution_id(tmp_path):
    """Test that empty execution_id raises ValueError."""
    with pytest.raises(ValueError, match="execution_id must be non-empty"):
        create_agent_workspace("", base_path=tmp_path)

    with pytest.raises(ValueError, match="execution_id must be non-empty"):
        create_agent_workspace("   ", base_path=tmp_path)


def test_init_shared_context_validates_json_serializable(tmp_path):
    """Test that non-serializable task_data raises ValueError."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    (workspace / "shared").mkdir()

    from datetime import datetime
    task_data = {
        "id": "123",
        "date": datetime.now()  # Not JSON-serializable
    }

    with pytest.raises(ValueError, match="must be JSON-serializable"):
        init_shared_context(workspace, task_data)


def test_init_shared_context_validates_workspace_exists(tmp_path):
    """Test that non-existent workspace raises FileNotFoundError."""
    workspace = tmp_path / "nonexistent"
    task_data = {"id": "123", "name": "Test"}

    with pytest.raises(FileNotFoundError, match="Workspace directory not found"):
        init_shared_context(workspace, task_data)
