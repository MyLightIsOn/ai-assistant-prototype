"""
Chat Executor.

Manages Claude Code subprocess execution for chat messages with MCP integration.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import os

from sqlalchemy.orm import Session

from models import ChatMessage
from database import SessionLocal
from chat_context import ChatContextBuilder
from logger import get_logger


logger = get_logger()


async def execute_chat_message(
    user_id: str,
    user_message_id: str,
    user_message_content: str,
    broadcast_callback: Optional[callable] = None
) -> str:
    """
    Execute chat message via Claude Code subprocess with MCP integration.

    Returns assistant message ID.
    """
    db = SessionLocal()

    try:
        # Create assistant message placeholder
        assistant_msg = ChatMessage(
            userId=user_id,
            role="assistant",
            content="",  # Will be filled by subprocess
            messageType="text"
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # Build context
        context_builder = ChatContextBuilder(db)
        context = context_builder.build_context(user_id, user_message_content)

        # Create working directory
        work_dir = Path(f"ai-workspace/chat/{assistant_msg.id}")
        work_dir.mkdir(parents=True, exist_ok=True)

        # Write context to file
        context_file = work_dir / "context.json"
        context_file.write_text(json.dumps({"messages": context}, indent=2))

        # Create MCP configuration for Claude Code
        # Point to our MCP task server
        mcp_config = {
            "mcpServers": {
                "task-management": {
                    "command": "python3",
                    "args": [
                        str(Path(__file__).parent / "mcp_task_server.py")
                    ],
                    "env": {
                        "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///ai-assistant.db")
                    }
                }
            }
        }

        mcp_config_file = work_dir / "mcp_config.json"
        mcp_config_file.write_text(json.dumps(mcp_config, indent=2))

        # Spawn Claude Code subprocess
        # Use -p/--print for non-interactive output
        process = await asyncio.create_subprocess_exec(
            "claude",
            "-p",  # Non-interactive mode
            user_message_content,  # Prompt
            "--mcp-config", str(mcp_config_file),  # Enable MCP tools
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///ai-assistant.db")}
        )

        # Read output with timeout
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            # Try graceful shutdown first
            process.terminate()  # SIGTERM
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                # Force kill if graceful fails
                process.kill()  # SIGKILL
                await process.wait()

            # Log timeout for debugging
            logger.error(f"Claude Code execution timed out for message {assistant_msg.id}")

            raise Exception("Claude Code execution timed out after 5 minutes")

        # Parse response
        response_text = stdout.decode('utf-8').strip()

        if not response_text:
            response_text = "I encountered an error processing your message."
            if stderr:
                error_text = stderr.decode('utf-8')
                logger.error(f"Chat execution error: {error_text}")
                # Include error details for debugging
                response_text += f"\n\nError details: {error_text[:500]}"

        # Update assistant message
        assistant_msg.content = response_text
        db.commit()

        logger.info(f"Chat message executed: {assistant_msg.id}")

        return assistant_msg.id

    except Exception as e:
        logger.error(f"Error executing chat message: {str(e)}")

        # Create error message
        if 'assistant_msg' in locals():
            assistant_msg.content = f"Error: {str(e)}"
            assistant_msg.messageType = "error"
            db.commit()
            return assistant_msg.id
        else:
            raise

    finally:
        db.close()
