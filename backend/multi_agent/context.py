"""
Shared context management for multi-agent coordination.

Provides functions to read and update the shared context file that
agents use to communicate results and coordinate work.
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone


def read_shared_context(workspace: Path) -> Dict[str, Any]:
    """
    Read shared context from workspace.

    Args:
        workspace: Path to workspace directory

    Returns:
        dict: Shared context data
    """
    context_file = workspace / "shared" / "context.json"

    if not context_file.exists():
        raise FileNotFoundError(f"Context file not found: {context_file}")

    with open(context_file) as f:
        return json.load(f)


def update_shared_context(
    workspace: Path,
    agent_name: str,
    agent_output: Dict[str, Any]
) -> None:
    """
    Update shared context with agent output.

    WARNING: This function uses read-modify-write without locking.
    Safe for sequential execution only. Add file locking before
    enabling parallel agent execution.

    Args:
        workspace: Path to workspace directory
        agent_name: Name of agent providing output
        agent_output: Agent's output data

    Raises:
        ValueError: If agent_output is not JSON-serializable
        FileNotFoundError: If context file doesn't exist
    """
    # Validate agent_output is JSON-serializable
    try:
        json.dumps(agent_output)
    except (TypeError, ValueError) as e:
        raise ValueError(f"agent_output must be JSON-serializable: {e}")

    context_file = workspace / "shared" / "context.json"

    if not context_file.exists():
        raise FileNotFoundError(f"Context file not found: {context_file}")

    # Read current context
    with open(context_file) as f:
        context = json.load(f)

    # Add agent to completed list if not already there
    if agent_name not in context["completed_agents"]:
        context["completed_agents"].append(agent_name)

    # Add agent's output
    context[agent_name] = agent_output

    # Add timestamp
    context[f"{agent_name}_completed_at"] = datetime.now(timezone.utc).isoformat()

    # Write updated context
    with open(context_file, "w") as f:
        json.dump(context, f, indent=2)


def append_agent_output(
    workspace: Path,
    agent_name: str,
    output_data: Dict[str, Any]
) -> None:
    """
    Append agent output to shared context.

    Alias for update_shared_context for clearer API.

    Args:
        workspace: Path to workspace directory
        agent_name: Name of agent
        output_data: Output data to append
    """
    update_shared_context(workspace, agent_name, output_data)
