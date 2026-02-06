"""Tests for multi-agent task detection."""

import pytest
from multi_agent.detector import (
    is_multi_agent_task,
    get_agent_config,
    validate_agent_metadata
)


def test_is_multi_agent_task_true():
    """Test detecting multi-agent task."""
    task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute"]
        }
    }

    assert is_multi_agent_task(task_metadata) is True


def test_is_multi_agent_task_false_no_agents():
    """Test task without agents config."""
    task_metadata = {}

    assert is_multi_agent_task(task_metadata) is False


def test_is_multi_agent_task_false_disabled():
    """Test task with agents disabled."""
    task_metadata = {
        "agents": {
            "enabled": False
        }
    }

    assert is_multi_agent_task(task_metadata) is False


def test_is_multi_agent_task_none_metadata():
    """Test with None metadata."""
    assert is_multi_agent_task(None) is False


def test_get_agent_config():
    """Test extracting agent configuration."""
    task_metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute", "review"],
            "synthesize": True,
            "roles": {
                "research": {"type": "research"},
                "execute": {"type": "execute"},
                "review": {"type": "review"}
            }
        }
    }

    config = get_agent_config(task_metadata)

    assert config["sequence"] == ["research", "execute", "review"]
    assert config["synthesize"] is True
    assert "research" in config["roles"]


def test_get_agent_config_raises_for_non_multi_agent():
    """Test get_agent_config raises for non multi-agent task."""
    task_metadata = {"agents": {"enabled": False}}

    with pytest.raises(ValueError, match="not configured for multi-agent"):
        get_agent_config(task_metadata)


def test_validate_agent_metadata_valid():
    """Test validating valid metadata."""
    metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "roles": {
                "research": {"type": "research"}
            }
        }
    }

    # Should not raise
    validate_agent_metadata(metadata)


def test_validate_agent_metadata_missing_sequence():
    """Test validation fails for missing sequence."""
    metadata = {
        "agents": {
            "enabled": True,
            "roles": {"research": {"type": "research"}}
        }
    }

    with pytest.raises(ValueError, match="sequence"):
        validate_agent_metadata(metadata)


def test_validate_agent_metadata_empty_sequence():
    """Test validation fails for empty sequence."""
    metadata = {
        "agents": {
            "enabled": True,
            "sequence": [],
            "roles": {}
        }
    }

    with pytest.raises(ValueError, match="sequence"):
        validate_agent_metadata(metadata)


def test_validate_agent_metadata_missing_role():
    """Test validation fails when agent in sequence not in roles."""
    metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research", "execute"],
            "roles": {
                "research": {"type": "research"}
                # Missing execute role
            }
        }
    }

    with pytest.raises(ValueError, match="execute"):
        validate_agent_metadata(metadata)


def test_validate_agent_metadata_missing_role_type():
    """Test validation fails when role missing 'type' field."""
    metadata = {
        "agents": {
            "enabled": True,
            "sequence": ["research"],
            "roles": {
                "research": {}  # Missing 'type'
            }
        }
    }

    with pytest.raises(ValueError, match="type"):
        validate_agent_metadata(metadata)
