"""
Multi-agent task orchestration.

Coordinates sequential execution of multiple agents with fail-fast error handling,
shared context management, and optional result synthesis.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone

from claude_interface import execute_claude_task
from logger import get_logger
from .workspace import create_agent_workspace, init_shared_context
from .context import update_shared_context, read_shared_context
from .status import update_agent_status, read_agent_status, AgentStatus
from .roles import generate_agent_instructions, AgentRole
from .detector import validate_agent_metadata

logger = get_logger()


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
    broadcast_callback: Optional[callable] = None,
    timeout: Optional[int] = 1800,  # Default 30 minutes
    max_retries: int = 3
) -> AgentExecutionResult:
    """
    Execute a single agent subprocess with retry logic.

    Args:
        workspace: Path to workspace directory
        agent_name: Name of agent to execute
        broadcast_callback: Optional WebSocket broadcast function
        timeout: Timeout in seconds (default: 1800 = 30 minutes)
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        AgentExecutionResult: Execution result
    """
    agent_dir = workspace / "agents" / agent_name
    instructions_file = agent_dir / "instructions.md"

    # Read instructions
    if not instructions_file.exists():
        return AgentExecutionResult(
            agent_name=agent_name,
            status="failed",
            exit_code=1,
            output={},
            error=f"Instructions file not found: {instructions_file}"
        )

    instructions = instructions_file.read_text()

    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(max_retries):
        if attempt > 0:
            # Exponential backoff: 1min, 5min, 15min
            backoff_delays = [60, 300, 900]
            delay = backoff_delays[min(attempt - 1, len(backoff_delays) - 1)]
            logger.info(f"Retry attempt {attempt + 1}/{max_retries} for agent '{agent_name}' after {delay}s backoff")
            await asyncio.sleep(delay)

        try:
            start_time = time.time()
            exit_code = 0
            output_lines = []

            # Execute Claude subprocess
            logger.info(f"Executing agent '{agent_name}' (attempt {attempt + 1}/{max_retries})")

            async for line in execute_claude_task(
                task_description=instructions,
                workspace_path=str(agent_dir),
                timeout=timeout
            ):
                output_lines.append(line)

                # Broadcast output if callback provided
                if broadcast_callback:
                    await broadcast_callback({
                        "type": "agent_output",
                        "agent_name": agent_name,
                        "output": line
                    })

                # Check for exit code in output
                if "exit code:" in line.lower():
                    try:
                        # Extract exit code from line like "Task completed successfully (exit code: 0)"
                        exit_code = int(line.split("exit code:")[-1].strip().rstrip(")"))
                    except (ValueError, IndexError):
                        pass

            duration_ms = int((time.time() - start_time) * 1000)

            # Parse output files
            output_data = {}
            output_json_file = agent_dir / "output.json"

            if output_json_file.exists():
                try:
                    with open(output_json_file) as f:
                        output_data = json.load(f)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse output.json for agent '{agent_name}': {e}")
                    # Continue with empty output rather than failing

            # Check if execution succeeded
            if exit_code == 0:
                logger.info(f"Agent '{agent_name}' completed successfully")
                return AgentExecutionResult(
                    agent_name=agent_name,
                    status="completed",
                    exit_code=exit_code,
                    output=output_data,
                    duration_ms=duration_ms
                )
            else:
                # Non-zero exit code
                error_msg = f"Agent exited with code {exit_code}"
                logger.warning(f"Agent '{agent_name}' failed: {error_msg}")

                # If this is the last retry, return failure
                if attempt == max_retries - 1:
                    return AgentExecutionResult(
                        agent_name=agent_name,
                        status="failed",
                        exit_code=exit_code,
                        output=output_data,
                        duration_ms=duration_ms,
                        error=error_msg
                    )

                last_error = error_msg
                # Continue to next retry

        except asyncio.TimeoutError:
            error_msg = f"Agent timed out after {timeout} seconds"
            logger.error(f"Agent '{agent_name}' timed out")

            # If this is the last retry, return timeout failure
            if attempt == max_retries - 1:
                return AgentExecutionResult(
                    agent_name=agent_name,
                    status="failed",
                    exit_code=124,  # Standard timeout exit code
                    output={},
                    error=error_msg
                )

            last_error = error_msg
            # Continue to next retry

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Agent '{agent_name}' encountered error: {e}", exc_info=True)

            # If this is the last retry, return error
            if attempt == max_retries - 1:
                return AgentExecutionResult(
                    agent_name=agent_name,
                    status="failed",
                    exit_code=1,
                    output={},
                    error=error_msg
                )

            last_error = error_msg
            # Continue to next retry

    # Should never reach here, but just in case
    return AgentExecutionResult(
        agent_name=agent_name,
        status="failed",
        exit_code=1,
        output={},
        error=last_error or "All retry attempts failed"
    )


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
