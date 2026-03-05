"""Tests for business-search template."""

import json
import os
import shutil
import tempfile

import pytest

from task_tools import _load_template, create_task_from_template, TEMPLATES_DIR


# --- Template structure tests (pass once template JSON exists) ---

def test_business_search_template_exists():
    """The business-search.json template file exists and loads."""
    tmpl = _load_template("business-search")
    assert tmpl["id"] == "business-search"
    assert "dynamic_agents" in tmpl
    assert "parameters" in tmpl


def test_business_search_template_has_all_marketplace_agents():
    """Template defines source agents for all 6 marketplaces."""
    tmpl = _load_template("business-search")
    source_agents = tmpl["dynamic_agents"]["source_agents"]
    for marketplace in ("bizbuysel", "acquire", "flippa", "empireflippers", "quietlight", "feinternational"):
        assert marketplace in source_agents, f"Missing marketplace agent: {marketplace}"


def test_business_search_template_has_suffix_agents():
    """Template has tracker, analyzer, and formatter suffix agents."""
    tmpl = _load_template("business-search")
    suffix_agents = tmpl["dynamic_agents"]["suffix_agents"]
    assert "tracker" in suffix_agents
    assert "analyzer" in suffix_agents
    assert "formatter" in suffix_agents
    # Order matters: tracker before analyzer before formatter
    assert suffix_agents.index("tracker") < suffix_agents.index("analyzer")
    assert suffix_agents.index("analyzer") < suffix_agents.index("formatter")


def test_business_search_template_has_correct_source_param():
    """dynamic_agents uses 'marketplaces' as the source param."""
    tmpl = _load_template("business-search")
    assert tmpl["dynamic_agents"]["source_param"] == "marketplaces"
    assert tmpl["dynamic_agents"]["agent_prefix"] == "marketplace_"


def test_business_search_template_has_email_report_config():
    """Template has email_report config pointing to formatter agent."""
    tmpl = _load_template("business-search")
    assert "email_report" in tmpl
    assert tmpl["email_report"]["enabled"] is True
    assert tmpl["email_report"]["formatter_agent"] == "formatter"


def test_business_search_template_default_schedule_is_weekly():
    """Template defaults to a weekly Monday morning schedule."""
    tmpl = _load_template("business-search")
    schedule = tmpl.get("default_schedule", "")
    assert schedule is not None and schedule != ""
    parts = schedule.split()
    assert len(parts) == 5
    assert parts[4] == "1"  # Monday


def test_business_search_template_parameters():
    """Template defines expected parameters with correct defaults."""
    tmpl = _load_template("business-search")
    params = tmpl["parameters"]

    assert "marketplaces" in params
    assert params["marketplaces"]["required"] is False
    assert "bizbuysel" in params["marketplaces"]["default"]

    assert "max_asking_price" in params
    assert params["max_asking_price"]["required"] is False
    assert params["max_asking_price"]["default"] == 3000000

    assert "recipient_email" in params
    assert params["recipient_email"]["required"] is False

    assert "min_revenue" in params
    assert params["min_revenue"]["required"] is False


def test_business_search_agent_instructions_contain_price_param():
    """Marketplace agent instructions reference {max_asking_price} parameter."""
    tmpl = _load_template("business-search")
    source_agents = tmpl["dynamic_agents"]["source_agents"]
    for name, agent in source_agents.items():
        assert "{max_asking_price}" in agent["instructions"], (
            f"Agent '{name}' instructions missing {{max_asking_price}} substitution"
        )


# --- Dynamic sequence building tests (require DB) ---

@pytest.fixture
def temp_templates_dir(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    from pathlib import Path
    monkeypatch.setattr("task_tools.TEMPLATES_DIR", Path(tmpdir))
    yield tmpdir
    shutil.rmtree(tmpdir)


def _write_template(directory, template_dict):
    path = os.path.join(directory, f"{template_dict['id']}.json")
    with open(path, "w") as f:
        json.dump(template_dict, f)
    return path


@pytest.fixture
def business_search_fixture():
    """Minimal business-search-like template for unit testing."""
    return {
        "id": "biz-test",
        "name": "Biz Test",
        "description": "Test template.",
        "command": "claude",
        "default_schedule": "0 7 * * 1",
        "default_priority": "default",
        "parameters": {
            "marketplaces": {
                "type": "string",
                "description": "Marketplaces",
                "required": False,
                "default": "alpha,beta",
            },
            "max_asking_price": {
                "type": "integer",
                "description": "Max price",
                "required": False,
                "default": 3000000,
            },
            "min_revenue": {
                "type": "integer",
                "description": "Min revenue",
                "required": False,
                "default": "",
            },
            "recipient_email": {
                "type": "string",
                "description": "Email",
                "required": False,
                "default": "test@example.com",
            },
        },
        "email_report": {
            "enabled": True,
            "recipient_email": "test@example.com",
            "formatter_agent": "formatter",
        },
        "dynamic_agents": {
            "source_param": "marketplaces",
            "agent_prefix": "marketplace_",
            "suffix_agents": ["tracker", "analyzer", "formatter"],
            "synthesize": False,
            "source_agents": {
                "alpha": {
                    "type": "research",
                    "instructions": "Search alpha for deals under {max_asking_price}.",
                },
                "beta": {
                    "type": "research",
                    "instructions": "Search beta for deals under {max_asking_price}.",
                },
                "gamma": {
                    "type": "research",
                    "instructions": "Search gamma for deals under {max_asking_price}.",
                },
            },
            "suffix_roles": {
                "tracker": {"type": "custom", "instructions": "Track listings."},
                "analyzer": {"type": "custom", "instructions": "Analyze listings."},
                "formatter": {"type": "custom", "instructions": "Format report."},
            },
        },
    }


@pytest.mark.asyncio
async def test_business_search_builds_correct_sequence(temp_templates_dir, business_search_fixture):
    """Correct agent sequence built for selected marketplaces."""
    _write_template(temp_templates_dir, business_search_fixture)

    from database import SessionLocal
    from models import Task
    from sqlalchemy import text
    db = SessionLocal()
    try:
        if not db.execute(text("SELECT COUNT(*) FROM User")).scalar():
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "biz-test",
            "name": "Biz Sequence Test",
            "schedule": "0 7 * * 1",
            "parameters": {"marketplaces": "alpha,gamma", "max_asking_price": 500000},
        })

        assert "Success" in result
        task = db.query(Task).filter_by(name="Biz Sequence Test").first()
        agents = task.task_metadata["agents"]

        assert agents["sequence"] == ["marketplace_alpha", "marketplace_gamma", "tracker", "analyzer", "formatter"]
        assert "marketplace_alpha" in agents["roles"]
        assert "marketplace_gamma" in agents["roles"]
        assert "marketplace_beta" not in agents["roles"]
        assert "tracker" in agents["roles"]
        assert "analyzer" in agents["roles"]
        assert "formatter" in agents["roles"]
    finally:
        db.query(Task).filter_by(name="Biz Sequence Test").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_business_search_substitutes_max_asking_price(temp_templates_dir, business_search_fixture):
    """max_asking_price parameter is substituted in agent instructions."""
    _write_template(temp_templates_dir, business_search_fixture)

    from database import SessionLocal
    from models import Task
    from sqlalchemy import text
    db = SessionLocal()
    try:
        if not db.execute(text("SELECT COUNT(*) FROM User")).scalar():
            pytest.skip("No test user in database")

        result = await create_task_from_template(db, {
            "template_id": "biz-test",
            "name": "Biz Price Sub Test",
            "schedule": "0 7 * * 1",
            "parameters": {"marketplaces": "alpha", "max_asking_price": 750000},
        })

        assert "Success" in result
        task = db.query(Task).filter_by(name="Biz Price Sub Test").first()
        agents = task.task_metadata["agents"]
        instructions = agents["roles"]["marketplace_alpha"]["instructions"]

        assert "750000" in instructions
        assert "{max_asking_price}" not in instructions
    finally:
        db.query(Task).filter_by(name="Biz Price Sub Test").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_business_search_invalid_marketplace_returns_error(temp_templates_dir, business_search_fixture):
    """All-invalid marketplace names returns error."""
    _write_template(temp_templates_dir, business_search_fixture)

    result = await create_task_from_template(None, {
        "template_id": "biz-test",
        "parameters": {"marketplaces": "notreal,alsofake"},
    })

    assert "Error" in result
