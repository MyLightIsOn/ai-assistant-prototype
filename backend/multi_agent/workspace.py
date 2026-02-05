"""
Multi-agent workspace creation and management.

Creates isolated directory structures for multi-agent task execution with
standardized layout for agent coordination and file-based communication.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


def create_agent_workspace(
    execution_id: str,
    agents: Optional[List[str]] = None,
    base_path: Optional[Path] = None
) -> Path:
    """
    Create workspace directory structure for multi-agent execution.

    Args:
        execution_id: Unique execution identifier
        agents: List of agent names to create directories for
        base_path: Base directory for workspace (defaults to ai-workspace/tasks)

    Returns:
        Path: Path to created workspace directory
    """
    # Determine base path
    if base_path is None:
        project_root = Path(__file__).parent.parent.parent
        base_path = project_root / "ai-workspace" / "tasks"

    # Create main workspace directory
    workspace = base_path / execution_id
    workspace.mkdir(parents=True, exist_ok=True)

    # Create shared directory
    shared_dir = workspace / "shared"
    shared_dir.mkdir(exist_ok=True)

    # Create agents directory
    agents_dir = workspace / "agents"
    agents_dir.mkdir(exist_ok=True)

    # Create agent subdirectories if provided
    if agents:
        for agent_name in agents:
            agent_dir = agents_dir / agent_name
            agent_dir.mkdir(exist_ok=True)

            # Create placeholder files
            (agent_dir / "instructions.md").touch()

            # Create initial status file
            status = {
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "exit_code": None,
                "error": None
            }
            with open(agent_dir / "status.json", "w") as f:
                json.dump(status, f, indent=2)

    # Create task.json placeholder
    task_placeholder = {
        "execution_id": execution_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    with open(workspace / "task.json", "w") as f:
        json.dump(task_placeholder, f, indent=2)

    return workspace


def init_shared_context(
    workspace: Path,
    task_data: Dict[str, Any]
) -> None:
    """
    Initialize shared context file with task information.

    Args:
        workspace: Path to workspace directory
        task_data: Task information to include in context
    """
    context = {
        "task_id": task_data.get("id"),
        "task_name": task_data.get("name"),
        "task_description": task_data.get("description", ""),
        "completed_agents": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    context_file = workspace / "shared" / "context.json"
    with open(context_file, "w") as f:
        json.dump(context, f, indent=2)
