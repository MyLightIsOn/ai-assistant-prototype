"""
Multi-agent task orchestration.

Coordinates sequential execution of multiple agents with fail-fast error handling,
shared context management, and optional result synthesis.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from .workspace import create_agent_workspace, init_shared_context
from .context import update_shared_context, read_shared_context
from .status import update_agent_status, read_agent_status, AgentStatus
from .roles import generate_agent_instructions, AgentRole
from .detector import validate_agent_metadata


@dataclass
class AgentExecutionResult:
    """Result from executing a single agent."""
    agent_name: str
    status: str
    exit_code: int
    output: Dict[str, Any]
    duration_ms: int = 0
    error: Optional[str] = None


async def prepare_agent_execution(
    workspace: Path,
    agent_name: str,
    task_data: Dict[str, Any],
    role_config: Dict[str, Any]
) -> None:
    """
    Prepare agent for execution by generating instructions.

    Args:
        workspace: Path to workspace directory
        agent_name: Name of agent
        task_data: Task information
        role_config: Agent role configuration
    """
    # Read shared context
    shared_context = read_shared_context(workspace)

    # Determine role type
    role_type_str = role_config.get("type", "custom")
    role_type = AgentRole(role_type_str)

    # Get custom instructions if provided
    custom_instructions = role_config.get("instructions")

    # Generate instructions
    instructions = generate_agent_instructions(
        agent_name=agent_name,
        role_type=role_type,
        task_data=task_data,
        shared_context=shared_context,
        custom_instructions=custom_instructions
    )

    # Write instructions to agent directory
    instructions_file = workspace / "agents" / agent_name / "instructions.md"
    instructions_file.write_text(instructions)


async def execute_single_agent(
    workspace: Path,
    agent_name: str,
    broadcast_callback: Optional[callable] = None
) -> AgentExecutionResult:
    """
    Execute a single agent subprocess.

    This is a placeholder that will be implemented to spawn Claude Code subprocess.
    For testing, this function can be mocked.

    Args:
        workspace: Path to workspace directory
        agent_name: Name of agent to execute
        broadcast_callback: Optional WebSocket broadcast function

    Returns:
        AgentExecutionResult: Execution result
    """
    # This will be implemented in Task 3.3 to spawn Claude subprocess
    # For now, return mock result for testing
    raise NotImplementedError("execute_single_agent not yet implemented")


async def execute_multi_agent_task(
    task: Any,
    execution_id: str,
    base_path: Optional[Path] = None,
    broadcast_callback: Optional[callable] = None
) -> Dict[str, Any]:
    """
    Execute multi-agent task with sequential agent coordination.

    Args:
        task: Task object with metadata.agents configuration
        execution_id: Unique execution identifier
        base_path: Base path for workspace (optional, for testing)
        broadcast_callback: Optional WebSocket broadcast function

    Returns:
        dict: Execution result with status and agent details
    """
    # Validate metadata
    validate_agent_metadata(task.metadata)

    # Extract agent configuration
    agent_config = task.metadata["agents"]
    sequence = agent_config["sequence"]
    roles = agent_config["roles"]
    synthesize = agent_config.get("synthesize", False)

    # Create workspace
    workspace = create_agent_workspace(
        execution_id=execution_id,
        agents=sequence,
        base_path=base_path
    )

    # Initialize shared context
    task_data = {
        "id": task.id,
        "name": task.name,
        "description": task.description
    }
    init_shared_context(workspace, task_data)

    # Write full task to workspace
    with open(workspace / "task.json", "w") as f:
        json.dump({
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "metadata": task.metadata
        }, f, indent=2)

    # Execute agents sequentially
    completed_agents: List[str] = []

    for agent_name in sequence:
        role_config = roles[agent_name]

        # Prepare agent
        await prepare_agent_execution(
            workspace=workspace,
            agent_name=agent_name,
            task_data=task_data,
            role_config=role_config
        )

        # Update status to running
        update_agent_status(workspace, agent_name, AgentStatus.RUNNING)

        # Execute agent
        try:
            result = await execute_single_agent(
                workspace=workspace,
                agent_name=agent_name,
                broadcast_callback=broadcast_callback
            )

            # Check if failed
            if result.status == "failed" or result.exit_code != 0:
                # Fail fast
                update_agent_status(
                    workspace,
                    agent_name,
                    AgentStatus.FAILED,
                    exit_code=result.exit_code,
                    error=result.error
                )

                return {
                    "status": "failed",
                    "failed_agent": agent_name,
                    "completed_agents": completed_agents,
                    "error": result.error or f"Agent {agent_name} failed",
                    "workspace": str(workspace)
                }

            # Agent succeeded
            update_agent_status(
                workspace,
                agent_name,
                AgentStatus.COMPLETED,
                exit_code=0
            )

            # Update shared context
            update_shared_context(workspace, agent_name, result.output)

            completed_agents.append(agent_name)

        except Exception as e:
            # Unexpected error
            update_agent_status(
                workspace,
                agent_name,
                AgentStatus.FAILED,
                error=str(e)
            )

            return {
                "status": "failed",
                "failed_agent": agent_name,
                "completed_agents": completed_agents,
                "error": str(e),
                "workspace": str(workspace)
            }

    # All agents completed successfully
    result = {
        "status": "completed",
        "completed_agents": completed_agents,
        "workspace": str(workspace)
    }

    # Add synthesis placeholder
    if synthesize:
        result["synthesis_required"] = True

    return result
