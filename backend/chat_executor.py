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

        # Spawn Claude Code subprocess with MCP configuration
        # Use --mcp-config to point to our MCP server configuration
        process = await asyncio.create_subprocess_exec(
            "claude",
            user_message_content,  # Pass the message as a prompt
            "--mcp-config", str(mcp_config_file),
            cwd=str(work_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "DATABASE_URL": os.getenv("DATABASE_URL", "sqlite:///ai-assistant.db")}
        )

        # Stream output in chunks with timeout
        accumulated_output = []
        chunk_size = 1024  # 1KB chunks
        start_time = datetime.now(timezone.utc)
        timeout_seconds = 300  # 5 minute timeout

        try:
            # Notify streaming start
            if broadcast_callback:
                await broadcast_callback({
                    "type": "chat_stream_start",
                    "data": {
                        "message_id": assistant_msg.id,
                        "user_message_id": user_message_id
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            # Read stdout in chunks
            while True:
                # Check timeout
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    raise asyncio.TimeoutError("Execution timeout")

                try:
                    # Read chunk with 500ms timeout
                    chunk = await asyncio.wait_for(
                        process.stdout.read(chunk_size),
                        timeout=0.5
                    )

                    if not chunk:
                        # EOF reached
                        break

                    # Decode and accumulate
                    chunk_text = chunk.decode('utf-8')
                    accumulated_output.append(chunk_text)

                    # Broadcast chunk
                    if broadcast_callback:
                        await broadcast_callback({
                            "type": "chat_stream",
                            "data": {
                                "message_id": assistant_msg.id,
                                "chunk": chunk_text
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

                except asyncio.TimeoutError:
                    # No data available, check if process is still running
                    if process.returncode is not None:
                        # Process finished
                        break
                    # Otherwise continue waiting for more data

            # Wait for process to complete
            await asyncio.wait_for(process.wait(), timeout=5)

            # Read any remaining stderr
            stderr_data = await process.stderr.read()
            stderr_text = stderr_data.decode('utf-8') if stderr_data else ""

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

            # Notify error
            if broadcast_callback:
                await broadcast_callback({
                    "type": "chat_stream_error",
                    "data": {
                        "message_id": assistant_msg.id,
                        "error": "Execution timed out after 5 minutes"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            raise Exception("Claude Code execution timed out after 5 minutes")

        # Parse response
        response_text = ''.join(accumulated_output).strip()

        if not response_text:
            response_text = "I encountered an error processing your message."
            if stderr_text:
                logger.error(f"Chat execution error: {stderr_text}")
                # Include error details for debugging
                response_text += f"\n\nError details: {stderr_text[:500]}"

        # Update assistant message
        assistant_msg.content = response_text
        db.commit()

        # Notify streaming complete
        if broadcast_callback:
            await broadcast_callback({
                "type": "chat_stream_complete",
                "data": {
                    "message_id": assistant_msg.id,
                    "final_content": response_text
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

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
