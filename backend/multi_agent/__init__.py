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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
