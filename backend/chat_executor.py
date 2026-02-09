"""
Chat Executor.

Uses the Anthropic API directly to handle chat messages with tool calling.
Tool handlers from mcp_task_server.py are called as Python functions.
"""

import json
import os
from typing import Optional

from anthropic import Anthropic

from models import ChatMessage
from database import SessionLocal
from chat_context import ChatContextBuilder
from task_tools import (
    create_task,
    list_tasks,
    update_task,
    delete_task,
    execute_task,
    get_task_executions,
)
from logger import get_logger


logger = get_logger()

# Tool definitions matching mcp_task_server.py
TOOLS = [
    {
        "name": "create_task",
        "description": "Create a new scheduled task",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Task name"},
                "description": {"type": "string", "description": "Task description"},
                "command": {"type": "string", "description": "Command to execute", "default": "claude"},
                "args": {"type": "string", "description": "Command arguments", "default": ""},
                "schedule": {"type": "string", "description": "Cron schedule (e.g., '0 2 * * *')"},
                "priority": {"type": "string", "enum": ["low", "default", "high", "urgent"], "default": "default"},
                "enabled": {"type": "boolean", "default": True},
            },
            "required": ["name", "schedule"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List all tasks, optionally filtered by enabled status",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter": {"type": "string", "enum": ["all", "enabled", "disabled"], "default": "all"},
                "limit": {"type": "number", "default": 50},
            },
        },
    },
    {
        "name": "update_task",
        "description": "Update an existing task's properties",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to update"},
                "updates": {"type": "object", "description": "Fields to update"},
            },
            "required": ["task_id", "updates"],
        },
    },
    {
        "name": "delete_task",
        "description": "Delete a task permanently",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to delete"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "execute_task",
        "description": "Execute a task immediately (outside its schedule)",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to execute"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "get_task_executions",
        "description": "Get execution history for a task",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID to query"},
                "limit": {"type": "number", "default": 10},
            },
            "required": ["task_id"],
        },
    },
]

# Map tool names to handler functions
TOOL_HANDLERS = {
    "create_task": create_task,
    "list_tasks": list_tasks,
    "update_task": update_task,
    "delete_task": delete_task,
    "execute_task": execute_task,
    "get_task_executions": get_task_executions,
}


async def execute_chat_message(
    user_id: str,
    user_message_id: str,
    user_message_content: str,
    broadcast_callback: Optional[callable] = None,
) -> str:
    """
    Execute chat message via Anthropic API with tool calling.

    Returns assistant message ID.
    """
    db = SessionLocal()

    try:
        # Build context BEFORE creating placeholder (to avoid empty messages in history)
        context_builder = ChatContextBuilder(db)
        context = context_builder.build_context(user_id, user_message_content)

        # Create assistant message placeholder
        assistant_msg = ChatMessage(
            userId=user_id,
            role="assistant",
            content="",
            messageType="text",
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # Separate system prompt from messages (API expects system as separate param)
        # Also filter out any empty messages
        system_prompt = None
        api_messages = []
        for msg in context:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg.get("content"):
                api_messages.append({"role": msg["role"], "content": msg["content"]})

        # Call Anthropic API
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        create_kwargs = {
            "model": "claude-sonnet-4-5-20250929",
            "max_tokens": 4096,
            "tools": TOOLS,
            "messages": api_messages,
        }
        if system_prompt:
            create_kwargs["system"] = system_prompt

        response = client.messages.create(**create_kwargs)

        # Handle tool use loop
        tool_calls_made = []
        conversation = list(api_messages)

        while response.stop_reason == "tool_use":
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input
                    logger.info(f"Tool called: {tool_name} with {json.dumps(tool_input)}")

                    # Call handler directly
                    handler = TOOL_HANDLERS.get(tool_name)
                    if handler:
                        tool_db = SessionLocal()
                        try:
                            result_text = await handler(tool_db, tool_input)
                        finally:
                            tool_db.close()
                    else:
                        result_text = f"Error: Unknown tool '{tool_name}'"

                    tool_calls_made.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": result_text,
                    })

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })

            # Add assistant response and tool results to conversation
            conversation.append({"role": "assistant", "content": response.content})
            conversation.append({"role": "user", "content": tool_results})

            # Continue conversation
            continue_kwargs = {
                "model": "claude-sonnet-4-5-20250929",
                "max_tokens": 4096,
                "tools": TOOLS,
                "messages": conversation,
            }
            if system_prompt:
                continue_kwargs["system"] = system_prompt

            response = client.messages.create(**continue_kwargs)

        # Extract final text response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        if not response_text:
            response_text = "I processed your request but have no additional response."

        # Update assistant message
        assistant_msg.content = response_text
        if tool_calls_made:
            assistant_msg.message_metadata = json.dumps({"tool_calls": tool_calls_made})
        db.commit()

        logger.info(f"Chat message executed: {assistant_msg.id}")
        return assistant_msg.id

    except Exception as e:
        logger.error(f"Error executing chat message: {str(e)}")

        if "assistant_msg" in locals():
            assistant_msg.content = f"Error: {str(e)}"
            assistant_msg.messageType = "error"
            db.commit()
            return assistant_msg.id
        else:
            raise

    finally:
        db.close()
