"""Tests for agent role templates."""

import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_agent.roles import (
    get_agent_template,
    generate_agent_instructions,
    AgentRole
)


def test_get_research_template():
    """Test research agent template."""
    template = get_agent_template(AgentRole.RESEARCH)

    assert "Research agent" in template
    assert "gather information" in template.lower()
    assert "output.json" in template


def test_get_execute_template():
    """Test execute agent template."""
    template = get_agent_template(AgentRole.EXECUTE)

    assert "Execute agent" in template
    assert "implement" in template.lower()
    assert "output.json" in template


def test_get_review_template():
    """Test review agent template."""
    template = get_agent_template(AgentRole.REVIEW)

    assert "Review agent" in template
    assert "quality" in template.lower()
    assert "output.json" in template


def test_get_custom_template():
    """Test custom agent template."""
    custom_instructions = "Perform security audit"
    template = get_agent_template(
        AgentRole.CUSTOM,
        custom_instructions=custom_instructions
    )

    # Template should contain placeholders, not formatted values
    assert "{custom_instructions}" in template
    assert "output.json" in template


def test_generate_agent_instructions_research():
    """Test generating instructions for research agent."""
    task_data = {
        "name": "Implement Auth",
        "description": "Add user authentication"
    }
    shared_context = {
        "task_description": "Add user authentication",
        "completed_agents": []
    }

    instructions = generate_agent_instructions(
        agent_name="research",
        role_type=AgentRole.RESEARCH,
        task_data=task_data,
        shared_context=shared_context
    )

    assert "Add user authentication" in instructions
    assert "Research agent" in instructions


def test_generate_agent_instructions_with_custom():
    """Test generating instructions with custom instructions."""
    task_data = {"name": "Test", "description": "Test task"}
    shared_context = {"task_description": "Test task"}
    custom_instructions = "Check for SQL injection vulnerabilities"

    instructions = generate_agent_instructions(
        agent_name="security",
        role_type=AgentRole.CUSTOM,
        task_data=task_data,
        shared_context=shared_context,
        custom_instructions=custom_instructions
    )

    assert custom_instructions in instructions
    assert "output.json" in instructions


def test_generate_agent_instructions_includes_previous_context():
    """Test that instructions include previous agent outputs."""
    task_data = {"name": "Test", "description": "Test"}
    shared_context = {
        "task_description": "Test",
        "completed_agents": ["research"],
        "research": {
            "findings": ["Finding 1", "Finding 2"]
        }
    }

    instructions = generate_agent_instructions(
        agent_name="execute",
        role_type=AgentRole.EXECUTE,
        task_data=task_data,
        shared_context=shared_context
    )

    assert "Finding 1" in instructions
    assert "Finding 2" in instructions
