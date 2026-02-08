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
    """Create a new task - implementation placeholder."""
    # Will be implemented in next task
    return [TextContent(
        type="text",
        text="create_task not yet implemented"
    )]


async def main():
    """Run MCP server on stdio transport."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
