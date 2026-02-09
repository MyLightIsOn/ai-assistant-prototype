"""
Task Management Tool Handlers.

Pure Python functions for task CRUD operations.
Used by both chat_executor.py (direct API) and mcp_task_server.py (MCP protocol).
No MCP dependency - only SQLAlchemy and standard library.
"""

from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy.orm import Session

from models import Task, TaskExecution, User


async def create_task(db: Session, args: dict) -> str:
    """Create a new scheduled task. Returns result message."""
    try:
        name = args["name"]
        description = args.get("description", "")
        command = args.get("command", "claude")
        task_args = args.get("args", "")
        schedule = args["schedule"]
        priority = args.get("priority", "default")
        enabled = args.get("enabled", True)

        # Get default user
        user = db.query(User).first()
        if not user:
            return "Error: No user found in database. Create a user first."

        # Check for duplicate name
        existing = db.query(Task).filter_by(name=name).first()
        if existing:
            return f"Error: A task named '{name}' already exists (ID: {existing.id}). Please choose a different name or update the existing task."

        # Validate cron schedule
        try:
            croniter(schedule)
        except (ValueError, KeyError) as e:
            return f"Error: Invalid cron schedule '{schedule}': {str(e)}. Example: '0 9 * * *' for 9am daily."

        # Create task
        task = Task(
            userId=user.id,
            name=name,
            description=description,
            command=command,
            args=task_args,
            schedule=schedule,
            priority=priority,
            enabled=enabled,
            createdAt=int(datetime.now(timezone.utc).timestamp() * 1000),
            updatedAt=int(datetime.now(timezone.utc).timestamp() * 1000),
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return f"Success: Created task '{task.name}' with ID {task.id}. Schedule: {schedule}"

    except KeyError as e:
        return f"Error: Missing required parameter: {str(e)}"
    except Exception as e:
        db.rollback()
        return f"Error: Failed to create task: {str(e)}"


async def list_tasks(db: Session, args: dict) -> str:
    """List tasks with optional filtering. Returns result message."""
    filter_type = args.get("filter", "all")
    limit = args.get("limit", 50)

    query = db.query(Task)

    if filter_type == "enabled":
        query = query.filter_by(enabled=True)
    elif filter_type == "disabled":
        query = query.filter_by(enabled=False)

    tasks = query.limit(limit).all()

    if not tasks:
        return "No tasks found."

    task_lines = []
    for task in tasks:
        status = "enabled" if task.enabled else "disabled"
        task_lines.append(
            f"- {task.name} (ID: {task.id}) | Schedule: {task.schedule} | Priority: {task.priority} | Status: {status}"
        )

    return f"Found {len(tasks)} task(s):\n" + "\n".join(task_lines)


async def update_task(db: Session, args: dict) -> str:
    """Update an existing task. Returns result message."""
    task_id = args["task_id"]
    updates = args["updates"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    allowed_fields = ["name", "description", "command", "args", "schedule", "priority", "enabled"]
    updated_fields = []

    for field, value in updates.items():
        if field in allowed_fields:
            setattr(task, field, value)
            updated_fields.append(field)

    if not updated_fields:
        return "Error: No valid fields to update."

    task.updatedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
    db.commit()

    return f"Success: Updated task '{task.name}' (ID: {task_id}). Updated fields: {', '.join(updated_fields)}"


async def delete_task(db: Session, args: dict) -> str:
    """Delete a task. Returns result message."""
    task_id = args["task_id"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    task_name = task.name
    db.delete(task)
    db.commit()

    return f"Success: Deleted task '{task_name}' (ID: {task_id})."


async def execute_task(db: Session, args: dict) -> str:
    """Execute a task immediately. Returns result message."""
    task_id = args["task_id"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    return f"Task '{task.name}' (ID: {task_id}) has been queued for immediate execution."


async def get_task_executions(db: Session, args: dict) -> str:
    """Get execution history for a task. Returns result message."""
    task_id = args["task_id"]
    limit = args.get("limit", 10)

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return f"Error: Task with ID '{task_id}' not found."

    executions = (
        db.query(TaskExecution)
        .filter_by(taskId=task_id)
        .order_by(TaskExecution.startedAt.desc())
        .limit(limit)
        .all()
    )

    if not executions:
        return f"No execution history for task '{task.name}'."

    exec_lines = []
    for execution in executions:
        started = datetime.fromtimestamp(execution.startedAt / 1000, tz=timezone.utc)
        status_icon = "completed" if execution.status == "completed" else "failed"
        exec_lines.append(
            f"- {started.strftime('%Y-%m-%d %H:%M:%S')} | Status: {status_icon} | Duration: {execution.duration}ms"
        )

    return f"Last {len(executions)} execution(s) for '{task.name}':\n" + "\n".join(exec_lines)
