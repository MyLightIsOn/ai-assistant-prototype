"""
Multi-Agent Orchestration Module.

Provides infrastructure for coordinating multiple Claude Code agents
working sequentially on complex tasks with file-based communication.
"""

__version__ = "0.1.0"

# Lazy imports to avoid import errors during development
__all__ = [
    "create_agent_workspace",
    "init_shared_context",
    "update_shared_context",
    "read_shared_context",
    "update_agent_status",
    "read_agent_status",
    "get_agent_template",
    "generate_agent_instructions",
    "is_multi_agent_task",
    "get_agent_config",
    "validate_agent_metadata",
    "execute_multi_agent_task",
    "prepare_agent_execution",
    "AgentExecutionResult",
    "synthesize_results",
    "generate_synthesis_prompt",
]


def __getattr__(name):
    """Lazy import on attribute access."""
    if name == "create_agent_workspace" or name == "init_shared_context":
        from .workspace import create_agent_workspace, init_shared_context
        return locals()[name]
    elif name == "update_shared_context" or name == "read_shared_context":
        from .context import update_shared_context, read_shared_context
        return locals()[name]
    elif name == "update_agent_status" or name == "read_agent_status":
        from .status import update_agent_status, read_agent_status
        return locals()[name]
    elif name == "get_agent_template" or name == "generate_agent_instructions":
        from .roles import get_agent_template, generate_agent_instructions
        return locals()[name]
    elif name == "is_multi_agent_task" or name == "get_agent_config" or name == "validate_agent_metadata":
        from .detector import is_multi_agent_task, get_agent_config, validate_agent_metadata
        return locals()[name]
    elif name == "execute_multi_agent_task" or name == "prepare_agent_execution" or name == "AgentExecutionResult":
        from .orchestrator import execute_multi_agent_task, prepare_agent_execution, AgentExecutionResult
        return locals()[name]
    elif name == "synthesize_results" or name == "generate_synthesis_prompt":
        from .synthesis import synthesize_results, generate_synthesis_prompt
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
