#!/usr/bin/env python3
"""
MCP Server for Task Management.

Exposes task management tools to Claude Code via MCP protocol.
"""

import json
import sys
from pathlib import Path

from croniter import croniter
from mcp.server import Server
from mcp.types import Tool, TextContent

from database import SessionLocal
from models import Task, TaskExecution


# Initialize MCP server
server = Server("task-management")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available task management tools."""
    return [
        Tool(
            name="create_task",
            description="Create a new scheduled task",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Task name"},
                    "description": {"type": "string", "description": "Task description"},
                    "command": {"type": "string", "description": "Command to execute", "default": "claude"},
                    "args": {"type": "string", "description": "Command arguments", "default": ""},
                    "schedule": {"type": "string", "description": "Cron schedule (e.g., '0 2 * * *')"},
                    "priority": {"type": "string", "enum": ["low", "default", "high", "urgent"], "default": "default"},
                    "enabled": {"type": "boolean", "default": True}
                },
                "required": ["name", "schedule"]
            }
        ),
        Tool(
            name="list_tasks",
            description="List all tasks, optionally filtered by enabled status",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "enum": ["all", "enabled", "disabled"], "default": "all"},
                    "limit": {"type": "number", "default": 50}
                }
            }
        ),
        Tool(
            name="update_task",
            description="Update an existing task's properties",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to update"},
                    "updates": {"type": "object", "description": "Fields to update"}
                },
                "required": ["task_id", "updates"]
            }
        ),
        Tool(
            name="delete_task",
            description="Delete a task permanently",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to delete"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="execute_task",
            description="Execute a task immediately (outside its schedule)",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to execute"}
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="get_task_executions",
            description="Get execution history for a task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to query"},
                    "limit": {"type": "number", "default": 10}
                },
                "required": ["task_id"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool calls from Claude Code."""
    db = SessionLocal()

    try:
        if name == "create_task":
            return await create_task_tool(db, arguments)
        elif name == "list_tasks":
            return await list_tasks_tool(db, arguments)
        elif name == "update_task":
            return await update_task_tool(db, arguments)
        elif name == "delete_task":
            return await delete_task_tool(db, arguments)
        elif name == "execute_task":
            return await execute_task_tool(db, arguments)
        elif name == "get_task_executions":
            return await get_task_executions_tool(db, arguments)
        else:
            return [TextContent(
                type="text",
                text=f"Error: Unknown tool '{name}'"
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]
    finally:
        db.close()


async def create_task_tool(db, args: dict) -> list[TextContent]:
    """Create a new task."""
    from datetime import datetime, timezone

    try:
        # Extract arguments with defaults
        name = args["name"]
        description = args.get("description", "")
        command = args.get("command", "claude")
        task_args = args.get("args", "")
        schedule = args["schedule"]
        priority = args.get("priority", "default")
        enabled = args.get("enabled", True)

        # Get default user (for now, use first user)
        from models import User
        user = db.query(User).first()
        if not user:
            return [TextContent(
                type="text",
                text="Error: No user found in database. Create a user first."
            )]

        # Check for duplicate name
        existing = db.query(Task).filter_by(name=name).first()
        if existing:
            return [TextContent(
                type="text",
                text=f"Error: A task named '{name}' already exists (ID: {existing.id}). Please choose a different name or update the existing task."
            )]

        # Validate cron schedule (basic check)
        # Validate cron schedule using croniter
        try:
            croniter(schedule)
        except (ValueError, KeyError) as e:
            return [TextContent(
                type="text",
                text=f"Error: Invalid cron schedule '{schedule}': {str(e)}. Example: '0 9 * * *' for 9am daily."
            )]

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
            updatedAt=int(datetime.now(timezone.utc).timestamp() * 1000)
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return [TextContent(
            type="text",
            text=f"Success: Created task '{task.name}' with ID {task.id}. Schedule: {schedule}"
        )]

    except KeyError as e:
        return [TextContent(
            type="text",
            text=f"Error: Missing required parameter: {str(e)}"
        )]
    except Exception as e:
        db.rollback()
        return [TextContent(
            type="text",
            text=f"Error: Failed to create task: {str(e)}"
        )]


async def list_tasks_tool(db, args: dict) -> list[TextContent]:
    """List tasks with optional filtering."""
    filter_type = args.get("filter", "all")
    limit = args.get("limit", 50)

    query = db.query(Task)

    if filter_type == "enabled":
        query = query.filter_by(enabled=True)
    elif filter_type == "disabled":
        query = query.filter_by(enabled=False)

    tasks = query.limit(limit).all()

    if not tasks:
        return [TextContent(
            type="text",
            text="No tasks found."
        )]

    # Format task list
    task_lines = []
    for task in tasks:
        status = "✓" if task.enabled else "✗"
        task_lines.append(f"{status} {task.name} (ID: {task.id}) - Schedule: {task.schedule} - Priority: {task.priority}")

    return [TextContent(
        type="text",
        text=f"Found {len(tasks)} task(s):\n" + "\n".join(task_lines)
    )]


async def update_task_tool(db, args: dict) -> list[TextContent]:
    """Update an existing task."""
    from datetime import datetime, timezone

    task_id = args["task_id"]
    updates = args["updates"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return [TextContent(
            type="text",
            text=f"Error: Task with ID '{task_id}' not found."
        )]

    # Update fields
    allowed_fields = ["name", "description", "command", "args", "schedule", "priority", "enabled"]
    updated_fields = []

    for field, value in updates.items():
        if field in allowed_fields:
            setattr(task, field, value)
            updated_fields.append(field)

    if not updated_fields:
        return [TextContent(
            type="text",
            text="Error: No valid fields to update."
        )]

    task.updatedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
    db.commit()

    return [TextContent(
        type="text",
        text=f"Success: Updated task '{task.name}' (ID: {task_id}). Updated fields: {', '.join(updated_fields)}"
    )]


async def delete_task_tool(db, args: dict) -> list[TextContent]:
    """Delete a task."""
    task_id = args["task_id"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return [TextContent(
            type="text",
            text=f"Error: Task with ID '{task_id}' not found."
        )]

    task_name = task.name
    db.delete(task)
    db.commit()

    return [TextContent(
        type="text",
        text=f"Success: Deleted task '{task_name}' (ID: {task_id})."
    )]


async def execute_task_tool(db, args: dict) -> list[TextContent]:
    """Execute a task immediately."""
    task_id = args["task_id"]

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return [TextContent(
            type="text",
            text=f"Error: Task with ID '{task_id}' not found."
        )]

    # Trigger task execution via API
    # Note: This will be called from Claude Code subprocess, so we can't easily
    # call the executor directly. Return instruction to use API instead.
    return [TextContent(
        type="text",
        text=f"To execute task '{task.name}' (ID: {task_id}), use the /api/tasks/{task_id}/execute endpoint or tell the user the task has been queued for execution."
    )]


async def get_task_executions_tool(db, args: dict) -> list[TextContent]:
    """Get execution history for a task."""
    task_id = args["task_id"]
    limit = args.get("limit", 10)

    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        return [TextContent(
            type="text",
            text=f"Error: Task with ID '{task_id}' not found."
        )]

    executions = db.query(TaskExecution).filter_by(taskId=task_id).order_by(TaskExecution.startedAt.desc()).limit(limit).all()

    if not executions:
        return [TextContent(
            type="text",
            text=f"No execution history for task '{task.name}'."
        )]

    # Format execution history
    exec_lines = []
    for execution in executions:
        from datetime import datetime, timezone
        started = datetime.fromtimestamp(execution.startedAt / 1000, tz=timezone.utc)
        status_icon = "✓" if execution.status == "completed" else "✗"
        exec_lines.append(f"{status_icon} {started.strftime('%Y-%m-%d %H:%M:%S')} - Status: {execution.status} - Duration: {execution.duration}ms")

    return [TextContent(
        type="text",
        text=f"Last {len(executions)} execution(s) for '{task.name}':\n" + "\n".join(exec_lines)
    )]


async def main():
    """Run MCP server on stdio transport."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
