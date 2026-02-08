#!/usr/bin/env python3
"""
MCP Server for Task Management.

Exposes task management tools to Claude Code via MCP protocol.
"""

import json
import sys
from pathlib import Path

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
        # More tools will be added in next tasks
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute tool calls from Claude Code."""
    db = SessionLocal()

    try:
        if name == "create_task":
            return await create_task_tool(db, arguments)
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
        parts = schedule.split()
        if len(parts) != 5:
            return [TextContent(
                type="text",
                text=f"Error: Invalid cron schedule '{schedule}'. Must have 5 parts (minute hour day month weekday). Example: '0 9 * * *' for 9am daily."
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


async def main():
    """Run MCP server on stdio transport."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
