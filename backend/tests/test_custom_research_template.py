"""Tests for custom-research dynamic_agents template support."""

import json
import os
import shutil
import tempfile

import pytest

from task_tools import create_task_from_template, _load_template, TEMPLATES_DIR


@pytest.fixture
def temp_templates_dir(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    from pathlib import Path
    monkeypatch.setattr("task_tools.TEMPLATES_DIR", Path(tmpdir))
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def dynamic_template():
    return {
        "id": "dynamic-test",
        "name": "Dynamic Test",
        "description": "A template with dynamic_agents.",
        "command": "claude",
        "default_schedule": "0 9 * * *",
        "default_priority": "default",
        "parameters": {
            "topic": {"type": "string", "description": "Topic", "required": True},
            "sources": {
                "type": "string",
                "description": "Comma-separated sources",
                "required": False,
                "default": "news,papers",
            },
            "max_items_per_source": {
                "type": "integer",
                "description": "Max items",
                "required": False,
                "default": 5,
            },
        },
        "email_report": {
            "enabled": True,
            "recipient_email": "test@example.com",
            "formatter_agent": "formatter",
        },
        "dynamic_agents": {
            "source_param": "sources",
            "agent_prefix": "research_",
            "suffix_agents": ["evaluator", "formatter"],
            "synthesize": False,
            "source_agents": {
                "news": {
                    "type": "research",
                    "instructions": "Search news about {topic}. Max {max_items_per_source} items.",
                },
                "papers": {
                    "type": "research",
                    "instructions": "Find papers about {topic}. Max {max_items_per_source} items.",
                },
                "repos": {
                    "type": "research",
                    "instructions": "Find repos for {topic}. Max {max_items_per_source} items.",
                },
            },
            "suffix_roles": {
                "evaluator": {"type": "custom", "instructions": "Evaluate results for {topic}."},
                "formatter": {"type": "custom", "instructions": "Format report for {topic}."},
            },
        },
    }


def _write_template(directory, template_dict):
    path = os.path.join(directory, f"{template_dict['id']}.json")
    with open(path, "w") as f:
        json.dump(template_dict, f)
    return path


# --- Template structure tests ---


def test_custom_research_template_exists():
    """The custom-research.json template file exists and loads."""
    tmpl = _load_template("custom-research")
    assert tmpl["id"] == "custom-research"
    assert "dynamic_agents" in tmpl
    assert "parameters" in tmpl
    assert tmpl["parameters"]["topic"]["required"] is True


def test_custom_research_template_has_all_sources():
    """Template defines agents for all 5 source types."""
    tmpl = _load_template("custom-research")
    source_agents = tmpl["dynamic_agents"]["source_agents"]
    for source in ("news", "papers", "repos", "blogs", "social"):
        assert source in source_agents, f"Missing source agent: {source}"


def test_custom_research_template_has_suffix_roles():
    """Template has evaluator and formatter suffix roles."""
    tmpl = _load_template("custom-research")
    suffix_roles = tmpl["dynamic_agents"]["suffix_roles"]
    assert "evaluator" in suffix_roles
    assert "formatter" in suffix_roles


# --- Dynamic sequence building tests ---


@pytest.mark.asyncio
async def test_dynamic_agents_builds_correct_sequence(temp_templates_dir, dynamic_template):
    """create_task_from_template builds correct sequence from sources parameter."""
    _write_template(temp_templates_dir, dynamic_template)

    from database import SessionLocal
    from models import Task
    db = SessionLocal()

    try:
        from sqlalchemy import text
        user_exists = db.execute(text("SELECT COUNT(*) FROM User")).scalar()
        if not user_exists:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "dynamic-test",
            "name": "Dynamic Sequence Test",
            "schedule": "0 9 * * *",
            "parameters": {"topic": "quantum computing", "sources": "news,repos"},
        })

        assert "Success" in result

        task = db.query(Task).filter_by(name="Dynamic Sequence Test").first()
        assert task is not None

        meta = task.task_metadata
        agents = meta["agents"]

        # Sequence: research_news, research_repos, evaluator, formatter
        assert agents["sequence"] == ["research_news", "research_repos", "evaluator", "formatter"]

        # Roles: only the selected sources + suffix
        assert "research_news" in agents["roles"]
        assert "research_repos" in agents["roles"]
        assert "evaluator" in agents["roles"]
        assert "formatter" in agents["roles"]
        # Papers not requested -> not in roles
        assert "research_papers" not in agents["roles"]

    finally:
        db.query(Task).filter_by(name="Dynamic Sequence Test").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_dynamic_agents_substitutes_params_in_instructions(temp_templates_dir, dynamic_template):
    """Parameters are substituted in dynamically built agent instructions."""
    _write_template(temp_templates_dir, dynamic_template)

    from database import SessionLocal
    from models import Task
    db = SessionLocal()

    try:
        from sqlalchemy import text
        user_exists = db.execute(text("SELECT COUNT(*) FROM User")).scalar()
        if not user_exists:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "dynamic-test",
            "name": "Dynamic Substitution Test",
            "schedule": "0 9 * * *",
            "parameters": {
                "topic": "Rust async",
                "sources": "papers",
                "max_items_per_source": 10,
            },
        })

        assert "Success" in result

        task = db.query(Task).filter_by(name="Dynamic Substitution Test").first()
        meta = task.task_metadata
        agents = meta["agents"]

        papers_instructions = agents["roles"]["research_papers"]["instructions"]
        assert "Rust async" in papers_instructions
        assert "{topic}" not in papers_instructions
        assert "10" in papers_instructions
        assert "{max_items_per_source}" not in papers_instructions

        formatter_instructions = agents["roles"]["formatter"]["instructions"]
        assert "Rust async" in formatter_instructions
        assert "{topic}" not in formatter_instructions

    finally:
        db.query(Task).filter_by(name="Dynamic Substitution Test").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_dynamic_agents_invalid_source_returns_error(temp_templates_dir, dynamic_template):
    """All-invalid sources in sources parameter returns error."""
    _write_template(temp_templates_dir, dynamic_template)

    result = await create_task_from_template(None, {
        "template_id": "dynamic-test",
        "parameters": {"topic": "AI", "sources": "invalid_source,another_bad"},
    })

    assert "Error" in result


@pytest.mark.asyncio
async def test_dynamic_agents_uses_default_sources(temp_templates_dir, dynamic_template):
    """When sources not provided, uses default from template."""
    _write_template(temp_templates_dir, dynamic_template)

    from database import SessionLocal
    from models import Task
    db = SessionLocal()

    try:
        from sqlalchemy import text
        user_exists = db.execute(text("SELECT COUNT(*) FROM User")).scalar()
        if not user_exists:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "dynamic-test",
            "name": "Dynamic Default Sources Test",
            "schedule": "0 9 * * *",
            "parameters": {"topic": "AI safety"},
            # sources not provided -> defaults to "news,papers"
        })

        assert "Success" in result

        task = db.query(Task).filter_by(name="Dynamic Default Sources Test").first()
        meta = task.task_metadata
        agents = meta["agents"]

        # Default sources in fixture are "news,papers"
        assert "research_news" in agents["roles"]
        assert "research_papers" in agents["roles"]
        assert "research_repos" not in agents["roles"]

    finally:
        db.query(Task).filter_by(name="Dynamic Default Sources Test").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_dynamic_agents_skips_unknown_sources_in_mixed_list(temp_templates_dir, dynamic_template):
    """Unknown source types in a mixed sources list are skipped (valid ones proceed)."""
    _write_template(temp_templates_dir, dynamic_template)

    from database import SessionLocal
    from models import Task
    db = SessionLocal()

    try:
        from sqlalchemy import text
        user_exists = db.execute(text("SELECT COUNT(*) FROM User")).scalar()
        if not user_exists:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "dynamic-test",
            "name": "Dynamic Mixed Sources Test",
            "schedule": "0 9 * * *",
            "parameters": {"topic": "AI", "sources": "news,unknown_source"},
        })

        assert "Success" in result

        task = db.query(Task).filter_by(name="Dynamic Mixed Sources Test").first()
        meta = task.task_metadata
        agents = meta["agents"]

        # Only 'news' is valid; unknown_source is silently skipped
        assert "research_news" in agents["roles"]
        assert "research_unknown_source" not in agents["roles"]
        assert "research_news" in agents["sequence"]

    finally:
        db.query(Task).filter_by(name="Dynamic Mixed Sources Test").delete()
        db.commit()
        db.close()
