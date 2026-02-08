import pytest
from mcp_task_server import create_task_tool
from database import SessionLocal
from models import Task


@pytest.mark.asyncio
async def test_create_task_tool():
    """Test create_task MCP tool."""
    db = SessionLocal()

    try:
        # Call tool
        result = await create_task_tool(db, {
            "name": "Test MCP Task",
            "description": "Created via MCP",
            "schedule": "0 9 * * *",
            "command": "echo",
            "args": "test",
            "priority": "default",
            "enabled": True
        })

        # Check result
        assert len(result) == 1
        assert "Success" in result[0].text or "created" in result[0].text.lower()

        # Verify in database
        task = db.query(Task).filter_by(name="Test MCP Task").first()
        assert task is not None
        assert task.schedule == "0 9 * * *"
        assert task.command == "echo"

    finally:
        # Cleanup
        db.query(Task).filter_by(name="Test MCP Task").delete()
        db.commit()
        db.close()
