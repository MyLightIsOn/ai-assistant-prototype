"""
Multi-agent task detection and metadata validation.

Determines if a task should use multi-agent execution and validates
the agent configuration metadata.
"""

from typing import Dict, Any, Optional


def is_multi_agent_task(task_metadata: Optional[Dict[str, Any]]) -> bool:
    """
    Check if task should use multi-agent execution.

    Args:
        task_metadata: Task metadata dictionary

    Returns:
        bool: True if multi-agent mode enabled
    """
    if not task_metadata:
        return False

    agents_config = task_metadata.get("agents")
    if not agents_config:
        return False

    return agents_config.get("enabled", False) is True


def get_agent_config(task_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract agent configuration from task metadata.

    Args:
        task_metadata: Task metadata dictionary

    Returns:
        dict: Agent configuration

    Raises:
        ValueError: If task is not configured for multi-agent execution
    """
    if not is_multi_agent_task(task_metadata):
        raise ValueError("Task is not configured for multi-agent execution")

    return task_metadata["agents"]


def validate_agent_metadata(task_metadata: Dict[str, Any]) -> None:
    """
    Validate agent metadata structure.

    Args:
        task_metadata: Task metadata to validate

    Raises:
        ValueError: If metadata is invalid
    """
    if not is_multi_agent_task(task_metadata):
        raise ValueError("Multi-agent not enabled in metadata")

    agents_config = task_metadata["agents"]

    # Validate sequence exists
    if "sequence" not in agents_config:
        raise ValueError("Missing 'sequence' in agent configuration")

    sequence = agents_config["sequence"]
    if not sequence or len(sequence) == 0:
        raise ValueError("Agent sequence cannot be empty")

    # Validate roles defined
    if "roles" not in agents_config:
        raise ValueError("Missing 'roles' in agent configuration")

    roles = agents_config["roles"]

    # Validate each agent in sequence has role defined
    for agent_name in sequence:
        if agent_name not in roles:
            raise ValueError(
                f"Agent '{agent_name}' in sequence but not defined in roles"
            )

        role_config = roles[agent_name]
        if "type" not in role_config:
            raise ValueError(
                f"Agent '{agent_name}' missing 'type' in role configuration"
            )
