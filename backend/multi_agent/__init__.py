"""
Multi-Agent Orchestration Module.

Provides infrastructure for coordinating multiple Claude Code agents
working sequentially on complex tasks with file-based communication.
"""

__version__ = "1.0.0"

from .workspace import create_agent_workspace, init_shared_context
from .context import update_shared_context, read_shared_context
from .status import update_agent_status, read_agent_status
from .roles import get_agent_template, generate_agent_instructions

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
