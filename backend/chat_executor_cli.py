"""
Chat Executor - CLI Subprocess Version.

Uses Claude CLI subprocess (subscription-based) instead of Anthropic API (pay-per-token).
Task management is accessible via REST API endpoints + curl from Claude's Bash tool.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from models import ChatMessage
from database import SessionLocal
from chat_context import ChatContextBuilder
from logger import get_logger


logger = get_logger()

# Project root and workspace paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHAT_WORKSPACE = PROJECT_ROOT / "ai-workspace" / "chat"


async def execute_chat_message(
    user_id: str,
    user_message_id: str,
    user_message_content: str,
    broadcast_callback: Optional[callable] = None,
) -> str:
    """
    Execute chat message via Claude CLI subprocess.

    Uses claude --dangerously-skip-permissions --print with --append-system-prompt
    to keep Claude Code's default tool capabilities while adding chat-specific context.

    Returns assistant message ID.
    """
    db = SessionLocal()

    try:
        # Build context BEFORE creating placeholder (avoid empty message in history)
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

        # Prepare workspace directory
        workspace_path = CHAT_WORKSPACE
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Separate system prompt from conversation messages
        system_prompt = ""
        conversation_parts = []
        for msg in context:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg.get("content"):
                role_label = "User" if msg["role"] == "user" else "Assistant"
                conversation_parts.append(f"{role_label}: {msg['content']}")

        # Build the prompt: conversation history formatted as text
        prompt = "\n\n".join(conversation_parts)

        # Build subprocess command
        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "--print",
        ]

        if system_prompt:
            cmd.extend(["--append-system-prompt", system_prompt])

        cmd.append(prompt)

        logger.info(
            f"Executing chat via CLI subprocess (prompt length: {len(prompt)}, "
            f"system prompt length: {len(system_prompt)})"
        )

        # Build clean environment:
        # - Remove ANTHROPIC_API_KEY so Claude CLI uses subscription instead of API key
        # - Remove CLAUDECODE so nested session check doesn't block subprocess startup
        env = {k: v for k, v in os.environ.items()
               if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}

        # Spawn subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace_path),
            env=env,
        )

        # Close stdin immediately (not used)
        if process.stdin:
            process.stdin.close()

        # Wait for completion with timeout
        timeout = int(os.getenv("CHAT_CLI_TIMEOUT", "120"))
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error(f"Chat CLI subprocess timed out after {timeout}s")
            if process:
                process.kill()
                await process.wait()
            assistant_msg.content = "Sorry, the request timed out. Please try again."
            assistant_msg.messageType = "error"
            db.commit()
            return assistant_msg.id

        exit_code = process.returncode
        response_text = stdout.decode("utf-8", errors="replace").strip()

        if stderr:
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            if stderr_text:
                logger.debug(f"CLI stderr: {stderr_text}")

        if not response_text:
            if exit_code != 0:
                response_text = f"Error: CLI exited with code {exit_code}."
                assistant_msg.messageType = "error"
            else:
                response_text = "I received your message but have no response."

        # Update assistant message with response
        assistant_msg.content = response_text
        assistant_msg.message_metadata = json.dumps({
            "executor": "cli",
            "exit_code": exit_code,
        })
        db.commit()

        logger.info(
            f"Chat CLI executed: msg={assistant_msg.id}, exit_code={exit_code}, "
            f"response_length={len(response_text)}"
        )
        return assistant_msg.id

    except Exception as e:
        logger.error(f"Error executing chat message via CLI: {str(e)}")

        if "assistant_msg" in locals():
            assistant_msg.content = f"Error: {str(e)}"
            assistant_msg.messageType = "error"
            db.commit()
            return assistant_msg.id
        else:
            raise

    finally:
        db.close()
