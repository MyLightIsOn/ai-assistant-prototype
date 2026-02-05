"""
Agent role templates and instruction generation.

Provides templates for built-in agent roles (Research, Execute, Review)
and supports custom role definitions.
"""

import json
from enum import Enum
from typing import Dict, Any, Optional


class AgentRole(str, Enum):
    """Built-in agent role types."""
    RESEARCH = "research"
    EXECUTE = "execute"
    REVIEW = "review"
    CUSTOM = "custom"


# ============================================================================
# Agent Role Templates
# ============================================================================

RESEARCH_TEMPLATE = """# Research Agent Instructions

## Role
You are a Research agent. Your job is to gather information, explore documentation,
and build context for the task.

## Task
{task_description}

## Previous Context
{previous_context}

## Your Mission
{custom_instructions}

Default mission: Investigate the task requirements, gather relevant documentation,
explore existing code patterns, and provide comprehensive context for implementation.

## Output Requirements
- Save findings to output.json (structured data):
  {{
    "findings": ["Finding 1", "Finding 2"],
    "documentation_links": ["url1", "url2"],
    "code_patterns": ["pattern1", "pattern2"],
    "recommendations": ["rec1", "rec2"]
  }}
- Save narrative to output.md (human-readable summary)
- Focus on gathering facts, not implementation
- Be thorough but concise

## Access
- You have access to ../shared/context.json for task details
- You can explore the codebase
- You can access documentation via MCP servers
"""

EXECUTE_TEMPLATE = """# Execute Agent Instructions

## Role
You are an Execute agent. Your job is to implement the solution based on
research findings and task requirements.

## Task
{task_description}

## Research Findings
{previous_context}

## Your Mission
{custom_instructions}

Default mission: Implement the solution using the research findings as context.
Follow best practices, write clean code, and use TDD when appropriate.

## Output Requirements
- Save implementation details to output.json:
  {{
    "files_created": ["file1.py", "file2.py"],
    "files_modified": ["file3.py"],
    "implementation_summary": "What was built...",
    "key_decisions": ["decision1", "decision2"]
  }}
- Document what you built in output.md
- Follow project conventions and coding standards
- Use the research findings to inform your implementation

## Access
- You have access to ../shared/context.json for all previous agent outputs
- You have full access to the codebase
- You can create, modify, and delete files as needed
"""

REVIEW_TEMPLATE = """# Review Agent Instructions

## Role
You are a Review agent. Your job is to assess quality, identify issues,
and suggest improvements.

## Task
{task_description}

## Implementation
{previous_context}

## Your Mission
{custom_instructions}

Default mission: Review the implementation for quality, correctness, and
best practices. Identify issues and provide actionable recommendations.

## Output Requirements
- Save review findings to output.json (structured feedback):
  {{
    "quality_score": 8.5,
    "issues": [
      {{"severity": "high", "description": "Issue 1", "location": "file:line"}},
      {{"severity": "low", "description": "Issue 2", "location": "file:line"}}
    ],
    "recommendations": ["Rec 1", "Rec 2"],
    "positive_observations": ["Good 1", "Good 2"]
  }}
- Save detailed review to output.md
- Be constructive and specific
- Prioritize issues by severity

## Access
- You have access to ../shared/context.json for all previous agent outputs
- You can read all files in the implementation
- Focus on providing actionable feedback
"""

CUSTOM_TEMPLATE = """# Custom Agent Instructions

## Role
{custom_instructions}

## Task
{task_description}

## Previous Context
{previous_context}

## Output Requirements
- Save structured output to output.json
- Save narrative output to output.md (optional)
- Follow the instructions provided in your role definition

## Access
- You have access to ../shared/context.json for task and previous agent outputs
- You can access the codebase as needed for your role
"""


def get_agent_template(
    role: AgentRole,
    custom_instructions: Optional[str] = None
) -> str:
    """
    Get template for agent role.

    Args:
        role: Agent role type
        custom_instructions: Custom instructions for CUSTOM role

    Returns:
        str: Template string
    """
    templates = {
        AgentRole.RESEARCH: RESEARCH_TEMPLATE,
        AgentRole.EXECUTE: EXECUTE_TEMPLATE,
        AgentRole.REVIEW: REVIEW_TEMPLATE,
        AgentRole.CUSTOM: CUSTOM_TEMPLATE
    }

    if role == AgentRole.CUSTOM and not custom_instructions:
        raise ValueError("custom_instructions required for CUSTOM role")

    return templates[role]


def generate_agent_instructions(
    agent_name: str,
    role_type: AgentRole,
    task_data: Dict[str, Any],
    shared_context: Dict[str, Any],
    custom_instructions: Optional[str] = None
) -> str:
    """
    Generate agent-specific instructions from template.

    Args:
        agent_name: Name of agent
        role_type: Agent role type
        task_data: Task information
        shared_context: Shared context data
        custom_instructions: Custom instructions (optional)

    Returns:
        str: Rendered instructions
    """
    template = get_agent_template(role_type, custom_instructions)

    # Build previous context string
    previous_context_parts = []
    for completed_agent in shared_context.get("completed_agents", []):
        if completed_agent in shared_context:
            agent_output = shared_context[completed_agent]
            previous_context_parts.append(
                f"## {completed_agent.title()} Agent Output\n"
                + json.dumps(agent_output, indent=2)
            )

    previous_context = "\n\n".join(previous_context_parts) if previous_context_parts else "No previous agent outputs yet."

    # Render template
    instructions = template.format(
        task_description=task_data.get("description", "No description provided"),
        previous_context=previous_context,
        custom_instructions=custom_instructions or "(Using default mission)"
    )

    return instructions

