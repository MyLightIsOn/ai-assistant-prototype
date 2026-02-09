"""Tests for AI news multi-agent template and email report hook."""

import json
import os
import tempfile
import shutil

import pytest

from task_tools import (
    list_templates,
    create_task_from_template,
    _load_template,
    TEMPLATES_DIR,
)
from email_templates import render_ai_news_email


@pytest.fixture
def temp_templates_dir(monkeypatch):
    """Create a temporary templates directory and patch TEMPLATES_DIR."""
    tmpdir = tempfile.mkdtemp()
    from pathlib import Path
    monkeypatch.setattr("task_tools.TEMPLATES_DIR", Path(tmpdir))
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def ai_news_template():
    """Load the real ai-news template."""
    tmpl_path = TEMPLATES_DIR / "ai-news.json"
    with open(tmpl_path) as f:
        return json.load(f)


@pytest.fixture
def mini_agent_template():
    """A minimal multi-agent template for testing."""
    return {
        "id": "test-multi",
        "name": "Test Multi-Agent",
        "description": "A test multi-agent template.",
        "command": "claude",
        "default_schedule": "0 6 * * *",
        "default_priority": "default",
        "parameters": {
            "recipient_email": {
                "type": "string",
                "description": "Email to send report to",
                "required": True,
            },
            "max_items": {
                "type": "integer",
                "description": "Max items",
                "required": False,
                "default": 3,
            },
        },
        "email_report": {
            "enabled": True,
            "recipient_email": "{recipient_email}",
            "formatter_agent": "formatter",
        },
        "agents": {
            "enabled": True,
            "sequence": ["researcher", "formatter"],
            "synthesize": False,
            "roles": {
                "researcher": {
                    "type": "research",
                    "instructions": "Find {max_items} items about AI news.",
                },
                "formatter": {
                    "type": "custom",
                    "instructions": "Format report for {recipient_email}.",
                },
            },
        },
    }


def _write_template(directory, template_dict):
    path = os.path.join(directory, f"{template_dict['id']}.json")
    with open(path, "w") as f:
        json.dump(template_dict, f)
    return path


# --- Template loading tests ---


def test_ai_news_template_loads():
    """The ai-news.json template exists and has correct structure."""
    tmpl = _load_template("ai-news")
    assert tmpl["id"] == "ai-news"
    assert "agents" in tmpl
    assert tmpl["agents"]["enabled"] is True
    assert len(tmpl["agents"]["sequence"]) == 6
    assert "evaluator" in tmpl["agents"]["sequence"]
    assert "formatter" in tmpl["agents"]["sequence"]
    assert "email_report" in tmpl
    assert tmpl["email_report"]["enabled"] is True


def test_ai_news_template_has_required_params():
    """Template requires recipient_email."""
    tmpl = _load_template("ai-news")
    params = tmpl["parameters"]
    assert params["recipient_email"]["required"] is True
    assert params["max_items_per_topic"]["required"] is False
    assert params["max_items_per_topic"]["default"] == 5


@pytest.mark.asyncio
async def test_list_templates_shows_ai_news(temp_templates_dir, mini_agent_template):
    """list_templates shows multi-agent templates."""
    _write_template(temp_templates_dir, mini_agent_template)
    result = await list_templates(None, {})
    assert "test-multi" in result
    assert "Test Multi-Agent" in result
    assert "recipient_email" in result


# --- Multi-agent metadata merging tests ---


@pytest.mark.asyncio
async def test_create_task_merges_agents_config(temp_templates_dir, mini_agent_template):
    """create_task_from_template merges agents block into task_metadata."""
    _write_template(temp_templates_dir, mini_agent_template)

    from database import SessionLocal
    from models import User, Task
    db = SessionLocal()

    try:
        user = db.query(User).first()
        if not user:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "test-multi",
            "name": "News Test Task",
            "schedule": "0 6 * * *",
            "parameters": {"recipient_email": "test@example.com"},
        })

        assert "Success" in result

        task = db.query(Task).filter_by(name="News Test Task").first()
        assert task is not None

        meta = task.task_metadata
        assert isinstance(meta, dict)

        # Verify agents config was merged
        assert "agents" in meta
        assert meta["agents"]["enabled"] is True
        assert meta["agents"]["sequence"] == ["researcher", "formatter"]

        # Verify email_report config was merged
        assert "email_report" in meta
        assert meta["email_report"]["enabled"] is True
        assert meta["email_report"]["recipient_email"] == "test@example.com"

    finally:
        db.query(Task).filter_by(name="News Test Task").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_param_substitution_in_agent_instructions(temp_templates_dir, mini_agent_template):
    """Parameters are substituted into agent instruction strings."""
    _write_template(temp_templates_dir, mini_agent_template)

    from database import SessionLocal
    from models import User, Task
    db = SessionLocal()

    try:
        user = db.query(User).first()
        if not user:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "test-multi",
            "name": "Substitution Test",
            "schedule": "0 6 * * *",
            "parameters": {"recipient_email": "user@test.com", "max_items": 10},
        })

        assert "Success" in result

        task = db.query(Task).filter_by(name="Substitution Test").first()
        meta = task.task_metadata

        # Check researcher instructions had {max_items} substituted
        researcher_instructions = meta["agents"]["roles"]["researcher"]["instructions"]
        assert "10" in researcher_instructions
        assert "{max_items}" not in researcher_instructions

        # Check formatter instructions had {recipient_email} substituted
        formatter_instructions = meta["agents"]["roles"]["formatter"]["instructions"]
        assert "user@test.com" in formatter_instructions
        assert "{recipient_email}" not in formatter_instructions

    finally:
        db.query(Task).filter_by(name="Substitution Test").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_missing_recipient_email_returns_error(temp_templates_dir, mini_agent_template):
    """Missing required recipient_email parameter returns error."""
    _write_template(temp_templates_dir, mini_agent_template)

    result = await create_task_from_template(None, {
        "template_id": "test-multi",
        "parameters": {},
    })

    assert "Error" in result
    assert "recipient_email" in result


@pytest.mark.asyncio
async def test_defaults_applied_to_agent_instructions(temp_templates_dir, mini_agent_template):
    """Default parameter values are substituted into agent instructions."""
    _write_template(temp_templates_dir, mini_agent_template)

    from database import SessionLocal
    from models import User, Task
    db = SessionLocal()

    try:
        user = db.query(User).first()
        if not user:
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "test-multi",
            "name": "Defaults Agent Test",
            "schedule": "0 6 * * *",
            "parameters": {"recipient_email": "a@b.com"},
        })

        assert "Success" in result

        task = db.query(Task).filter_by(name="Defaults Agent Test").first()
        meta = task.task_metadata

        # Default max_items=3 should be substituted
        researcher_instructions = meta["agents"]["roles"]["researcher"]["instructions"]
        assert "3" in researcher_instructions

    finally:
        db.query(Task).filter_by(name="Defaults Agent Test").delete()
        db.commit()
        db.close()


# --- Executor email hook tests ---


@pytest.mark.asyncio
async def test_email_hook_reads_formatter_output(tmp_path):
    """Email hook reads formatter output.json from workspace."""
    # Create mock workspace structure
    formatter_dir = tmp_path / "agents" / "formatter"
    formatter_dir.mkdir(parents=True)

    formatter_output = {
        "subject": "AI Daily News - 2026-02-09",
        "html": "<html><body><h1>News</h1></body></html>",
        "text": "News\n===\nItem 1",
        "item_count": 5,
    }
    with open(formatter_dir / "output.json", "w") as f:
        json.dump(formatter_output, f)

    # Read it back as the executor would
    output_path = tmp_path / "agents" / "formatter" / "output.json"
    assert output_path.exists()

    with open(output_path) as f:
        data = json.load(f)

    assert data["subject"] == "AI Daily News - 2026-02-09"
    assert "<h1>News</h1>" in data["html"]
    assert data["text"].startswith("News")


# --- Fallback email template tests ---


def test_render_ai_news_email_basic():
    """Fallback template renders sections from evaluator data."""
    news_data = {
        "industry": {
            "items": [
                {
                    "title": "OpenAI raises $10B",
                    "url": "https://techcrunch.com/openai",
                    "source": "TechCrunch",
                    "summary": "OpenAI raised $10B in new funding.",
                    "confidence": "high",
                }
            ],
            "removed_count": 0,
        },
        "repos": {
            "items": [
                {
                    "title": "awesome-llm",
                    "url": "https://github.com/user/awesome-llm",
                    "description": "A curated list of LLM resources.",
                    "confidence": "medium",
                }
            ],
            "removed_count": 0,
        },
        "quality_report": {
            "total_items_received": 5,
            "duplicates_removed": 1,
            "low_confidence_flagged": 0,
            "items_after_evaluation": 2,
        },
    }

    html, text = render_ai_news_email(news_data)

    # HTML checks
    assert "AI Daily News" in html
    assert "OpenAI raises $10B" in html
    assert "awesome-llm" in html
    assert "techcrunch.com" in html
    assert "medium" in html  # confidence badge
    assert "Duplicates removed: 1" in html

    # Text checks
    assert "AI Daily News" in text
    assert "OpenAI raises $10B" in text
    assert "awesome-llm" in text


def test_render_ai_news_email_empty():
    """Fallback template handles empty data gracefully."""
    html, text = render_ai_news_email({})
    assert "AI Daily News" in html
    assert "0 items" in html


def test_render_ai_news_email_low_confidence_badge():
    """Low confidence items get a red badge."""
    news_data = {
        "technical": {
            "items": [
                {
                    "title": "Suspicious Item",
                    "url": "https://example.com",
                    "summary": "Vague summary.",
                    "confidence": "low",
                }
            ]
        }
    }

    html, text = render_ai_news_email(news_data)
    assert "low confidence" in html
    assert "#ef4444" in html  # red badge color
