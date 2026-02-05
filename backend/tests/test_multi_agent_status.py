"""Tests for agent status tracking."""

import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_agent.status import (
    update_agent_status,
    read_agent_status,
    AgentStatus
)


def test_update_agent_status_to_running(tmp_path):
    """Test updating agent status to running."""
    workspace = tmp_path / "workspace"
    agent_dir = workspace / "agents" / "research"
    agent_dir.mkdir(parents=True)

    # Create initial status file
    status_file = agent_dir / "status.json"
    initial_status = {
        "status": "pending",
        "started_at": None,
        "completed_at": None
    }
    with open(status_file, "w") as f:
        json.dump(initial_status, f)

    # Update to running
    update_agent_status(workspace, "research", AgentStatus.RUNNING)

    # Verify update
    with open(status_file) as f:
        status = json.load(f)

    assert status["status"] == "running"
    assert status["started_at"] is not None


def test_update_agent_status_to_completed(tmp_path):
    """Test updating agent status to completed."""
    workspace = tmp_path / "workspace"
    agent_dir = workspace / "agents" / "execute"
    agent_dir.mkdir(parents=True)

    status_file = agent_dir / "status.json"
    initial_status = {"status": "running", "started_at": "2024-01-01T00:00:00Z"}
    with open(status_file, "w") as f:
        json.dump(initial_status, f)

    # Update to completed
    update_agent_status(
        workspace,
        "execute",
        AgentStatus.COMPLETED,
        exit_code=0
    )

    # Verify
    with open(status_file) as f:
        status = json.load(f)

    assert status["status"] == "completed"
    assert status["completed_at"] is not None
    assert status["exit_code"] == 0


def test_update_agent_status_to_failed(tmp_path):
    """Test updating agent status to failed with error."""
    workspace = tmp_path / "workspace"
    agent_dir = workspace / "agents" / "review"
    agent_dir.mkdir(parents=True)

    status_file = agent_dir / "status.json"
    initial_status = {"status": "running"}
    with open(status_file, "w") as f:
        json.dump(initial_status, f)

    # Update to failed
    error_message = "Agent timeout after 3 attempts"
    update_agent_status(
        workspace,
        "review",
        AgentStatus.FAILED,
        error=error_message,
        exit_code=1
    )

    # Verify
    status = read_agent_status(workspace, "review")
    assert status["status"] == "failed"
    assert status["error"] == error_message
    assert status["exit_code"] == 1


def test_read_agent_status(tmp_path):
    """Test reading agent status."""
    workspace = tmp_path / "workspace"
    agent_dir = workspace / "agents" / "research"
    agent_dir.mkdir(parents=True)

    status_data = {
        "status": "completed",
        "started_at": "2024-01-01T10:00:00Z",
        "completed_at": "2024-01-01T10:15:00Z",
        "exit_code": 0
    }
    status_file = agent_dir / "status.json"
    with open(status_file, "w") as f:
        json.dump(status_data, f)

    # Read status
    status = read_agent_status(workspace, "research")

    assert status["status"] == "completed"
    assert status["exit_code"] == 0
