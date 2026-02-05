"""
Agent status tracking for multi-agent orchestration.

Manages status.json files for each agent to track execution state,
timestamps, and errors.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


class AgentStatus(str, Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def update_agent_status(
    workspace: Path,
    agent_name: str,
    status: AgentStatus,
    exit_code: Optional[int] = None,
    error: Optional[str] = None
) -> None:
    """
    Update agent status file.

    WARNING: This function uses read-modify-write without locking.
    Safe for sequential execution only. Add file locking before
    enabling parallel agent execution.

    Args:
        workspace: Path to workspace directory
        agent_name: Name of agent
        status: New status
        exit_code: Process exit code (optional)
        error: Error message (optional)

    Raises:
        FileNotFoundError: If status file doesn't exist
    """
    status_file = workspace / "agents" / agent_name / "status.json"

    if not status_file.exists():
        raise FileNotFoundError(f"Status file not found: {status_file}")

    # Read current status
    with open(status_file) as f:
        status_data = json.load(f)

    # Update status
    status_data["status"] = status.value

    # Update timestamps based on status
    if status == AgentStatus.RUNNING:
        status_data["started_at"] = datetime.now(timezone.utc).isoformat()
    elif status in [AgentStatus.COMPLETED, AgentStatus.FAILED]:
        status_data["completed_at"] = datetime.now(timezone.utc).isoformat()

    # Update exit code if provided
    if exit_code is not None:
        status_data["exit_code"] = exit_code

    # Update error if provided
    if error is not None:
        status_data["error"] = error

    # Write updated status
    with open(status_file, "w") as f:
        json.dump(status_data, f, indent=2)


def read_agent_status(workspace: Path, agent_name: str) -> Dict[str, Any]:
    """
    Read agent status from file.

    Args:
        workspace: Path to workspace directory
        agent_name: Name of agent

    Returns:
        dict: Status data
    """
    status_file = workspace / "agents" / agent_name / "status.json"

    if not status_file.exists():
        raise FileNotFoundError(f"Status file not found: {status_file}")

    with open(status_file) as f:
        return json.load(f)
