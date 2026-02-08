import pytest
from mcp_task_server import (
    create_task_tool,
    list_tasks_tool,
    update_task_tool,
    delete_task_tool,
    get_task_executions_tool
)
from database import SessionLocal
from models import Task, User
from datetime import datetime, timezone


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


@pytest.mark.asyncio
async def test_list_tasks_tool():
    """Test list_tasks MCP tool."""
    db = SessionLocal()

    try:
        # Create test tasks
        user = db.query(User).first()
        db.add(Task(userId=user.id, name="Task 1", schedule="0 9 * * *", command="echo", args="", enabled=True,
                    createdAt=int(datetime.now(timezone.utc).timestamp() * 1000),
                    updatedAt=int(datetime.now(timezone.utc).timestamp() * 1000)))
        db.add(Task(userId=user.id, name="Task 2", schedule="0 10 * * *", command="echo", args="", enabled=False,
                    createdAt=int(datetime.now(timezone.utc).timestamp() * 1000),
                    updatedAt=int(datetime.now(timezone.utc).timestamp() * 1000)))
        db.commit()

        # Test list all
        result = await list_tasks_tool(db, {"filter": "all"})
        assert "Task 1" in result[0].text or "Found" in result[0].text

        # Test list enabled only
        result = await list_tasks_tool(db, {"filter": "enabled"})
        assert "Task 1" in result[0].text

    finally:
        db.query(Task).filter(Task.name.in_(["Task 1", "Task 2"])).delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_update_task_tool():
    """Test update_task MCP tool."""
    db = SessionLocal()

    try:
        # Create test task
        user = db.query(User).first()
        task = Task(userId=user.id, name="Update Test", schedule="0 9 * * *", command="echo", args="",
                    createdAt=int(datetime.now(timezone.utc).timestamp() * 1000),
                    updatedAt=int(datetime.now(timezone.utc).timestamp() * 1000))
        db.add(task)
        db.commit()
        db.refresh(task)

        # Update task
        result = await update_task_tool(db, {
            "task_id": task.id,
            "updates": {"schedule": "0 10 * * *", "description": "Updated"}
        })

        assert "Success" in result[0].text

        # Verify update
        db.refresh(task)
        assert task.schedule == "0 10 * * *"
        assert task.description == "Updated"

    finally:
        db.query(Task).filter_by(name="Update Test").delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_delete_task_tool():
    """Test delete_task MCP tool."""
    db = SessionLocal()

    try:
        # Create test task
        user = db.query(User).first()
        task = Task(userId=user.id, name="Delete Test", schedule="0 9 * * *", command="echo", args="",
                    createdAt=int(datetime.now(timezone.utc).timestamp() * 1000),
                    updatedAt=int(datetime.now(timezone.utc).timestamp() * 1000))
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

        # Delete task
        result = await delete_task_tool(db, {"task_id": task_id})
        assert "Success" in result[0].text or "Deleted" in result[0].text

        # Verify deletion
        deleted_task = db.query(Task).filter_by(id=task_id).first()
        assert deleted_task is None

    finally:
        # Cleanup (just in case)
        db.query(Task).filter_by(name="Delete Test").delete()
        db.commit()
        db.close()
