"""Tests for task template functionality."""

import json
import os
import tempfile
import shutil

import pytest

from task_tools import (
    list_templates,
    create_task_from_template,
    TEMPLATES_DIR,
    _load_template,
    _build_issue_selection_block,
)


@pytest.fixture
def temp_templates_dir(monkeypatch):
    """Create a temporary templates directory and patch TEMPLATES_DIR."""
    tmpdir = tempfile.mkdtemp()
    from pathlib import Path
    monkeypatch.setattr("task_tools.TEMPLATES_DIR", Path(tmpdir))
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def sample_template():
    """Return a minimal sample template dict."""
    return {
        "id": "test-tmpl",
        "name": "Test Template",
        "description": "A test template.",
        "command": "claude",
        "default_schedule": "0 9 * * *",
        "default_priority": "default",
        "parameters": {
            "repo": {
                "type": "string",
                "description": "GitHub repository",
                "required": True,
            },
            "max_issues": {
                "type": "integer",
                "description": "Max issues",
                "required": False,
                "default": 3,
            },
        },
        "prompt_template": "Fix issues in {repo}. Max: {max_issues}.",
    }


def _write_template(directory, template_dict):
    """Helper to write a template JSON file into a directory."""
    path = os.path.join(directory, f"{template_dict['id']}.json")
    with open(path, "w") as f:
        json.dump(template_dict, f)
    return path


# --- list_templates tests ---


@pytest.mark.asyncio
async def test_list_templates_shows_available(temp_templates_dir, sample_template):
    """list_templates returns formatted listing of available templates."""
    _write_template(temp_templates_dir, sample_template)

    result = await list_templates(None, {})

    assert "test-tmpl" in result
    assert "Test Template" in result
    assert "repo" in result
    assert "(required)" in result
    assert "max_issues" in result


@pytest.mark.asyncio
async def test_list_templates_empty_directory(temp_templates_dir):
    """list_templates returns message when no templates exist."""
    result = await list_templates(None, {})
    assert "No templates found" in result


@pytest.mark.asyncio
async def test_list_templates_missing_directory(monkeypatch):
    """list_templates handles missing templates directory."""
    from pathlib import Path
    monkeypatch.setattr("task_tools.TEMPLATES_DIR", Path("/nonexistent/path"))

    result = await list_templates(None, {})
    assert "No templates directory found" in result


@pytest.mark.asyncio
async def test_list_templates_skips_invalid_json(temp_templates_dir):
    """list_templates skips files with invalid JSON."""
    bad_path = os.path.join(temp_templates_dir, "bad.json")
    with open(bad_path, "w") as f:
        f.write("not json{{{")

    result = await list_templates(None, {})
    assert "No valid templates found" in result


# --- create_task_from_template tests ---


@pytest.mark.asyncio
async def test_create_task_from_template_valid(temp_templates_dir, sample_template):
    """create_task_from_template with valid params creates task with substituted prompt."""
    _write_template(temp_templates_dir, sample_template)

    # We need a real DB session for create_task delegation
    from database import SessionLocal
    from models import User, Task
    db = SessionLocal()

    try:
        user = db.query(User).first()
        if not user:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "test-tmpl",
            "name": "My Test Task",
            "schedule": "0 10 * * *",
            "parameters": {"repo": "my-org/my-repo"},
        })

        assert "Success" in result

        # Verify task was created with substituted prompt
        task = db.query(Task).filter_by(name="My Test Task").first()
        assert task is not None
        assert "Fix issues in my-org/my-repo" in task.args
        assert "Max: 3" in task.args  # default applied
        assert task.schedule == "0 10 * * *"

        # Verify template metadata
        assert task.task_metadata is not None
        meta = task.task_metadata if isinstance(task.task_metadata, dict) else json.loads(task.task_metadata)
        assert meta["template_id"] == "test-tmpl"
        assert meta["parameters"]["repo"] == "my-org/my-repo"
        assert meta["parameters"]["max_issues"] == 3

    finally:
        db.query(Task).filter_by(name="My Test Task").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_create_task_from_template_missing_required_param(temp_templates_dir, sample_template):
    """create_task_from_template returns error when required parameter is missing."""
    _write_template(temp_templates_dir, sample_template)

    result = await create_task_from_template(None, {
        "template_id": "test-tmpl",
        "parameters": {},  # missing 'repo'
    })

    assert "Error" in result
    assert "repo" in result
    assert "required" in result.lower()


@pytest.mark.asyncio
async def test_create_task_from_template_unknown_id(temp_templates_dir):
    """create_task_from_template returns error for unknown template ID."""
    result = await create_task_from_template(None, {
        "template_id": "nonexistent",
        "parameters": {},
    })

    assert "Error" in result
    assert "nonexistent" in result
    assert "not found" in result


@pytest.mark.asyncio
async def test_create_task_from_template_missing_template_id():
    """create_task_from_template returns error when template_id is missing."""
    result = await create_task_from_template(None, {
        "parameters": {"repo": "test/repo"},
    })

    assert "Error" in result
    assert "template_id" in result


@pytest.mark.asyncio
async def test_create_task_from_template_defaults_applied(temp_templates_dir, sample_template):
    """Optional parameter defaults are applied when not provided."""
    _write_template(temp_templates_dir, sample_template)

    from database import SessionLocal
    from models import User, Task
    db = SessionLocal()

    try:
        user = db.query(User).first()
        if not user:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "test-tmpl",
            "name": "Defaults Task",
            "parameters": {"repo": "owner/repo"},
        })

        assert "Success" in result
        task = db.query(Task).filter_by(name="Defaults Task").first()
        assert task is not None
        # default_schedule from template
        assert task.schedule == "0 9 * * *"
        # default max_issues=3 substituted
        assert "Max: 3" in task.args

    finally:
        db.query(Task).filter_by(name="Defaults Task").delete()
        db.commit()
        db.close()


# --- _build_issue_selection_block tests ---


def test_issue_selection_block_with_specific_issues():
    """Specific issue numbers produce a targeted selection block."""
    block = _build_issue_selection_block({"issues": "42,57"})
    assert "#42" in block
    assert "#57" in block
    assert "specific" in block.lower() or "Fix these" in block


def test_issue_selection_block_with_filter():
    """Filter-based selection produces gh issue list command."""
    block = _build_issue_selection_block({"filter": "label:enhancement", "max_issues": 5})
    assert "enhancement" in block
    assert "5" in block
    assert "gh issue list" in block


def test_issue_selection_block_defaults():
    """Default filter and max_issues are used when not specified."""
    block = _build_issue_selection_block({})
    assert "bug" in block
    assert "3" in block
