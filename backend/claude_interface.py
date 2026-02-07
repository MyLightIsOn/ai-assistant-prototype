"""
Claude Code subprocess interface.

This module provides async functions to spawn and interact with the Claude Code CLI
as a subprocess, streaming output in real-time and handling errors gracefully.

Key features:
- Spawns Claude CLI with --dangerously-skip-permissions and --print flags for non-interactive mode
- Sets working directory to ai-workspace
- Streams stdout/stderr line-by-line
- Captures exit codes
- Handles timeouts and cleanup
- Logs all interactions
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from pathlib import Path
import os

from logger import get_logger

# Setup logging
logger = get_logger()


async def execute_claude_task(
    task_description: str,
    workspace_path: str,
    timeout: Optional[int] = None
) -> AsyncGenerator[str, None]:
    """
    Execute a Claude Code task as a subprocess and stream output.

    Args:
        task_description: Description of the task for Claude to execute
        workspace_path: Path to ai-workspace directory (working directory)
        timeout: Optional timeout in seconds (default: None = no timeout)

    Yields:
        str: Output lines from Claude subprocess (stdout and stderr)

    Raises:
        asyncio.TimeoutError: If subprocess exceeds timeout
        Exception: If subprocess encounters errors

    Example:
        async for line in execute_claude_task("Write a Python script", "/workspace"):
            print(line)
    """
    # Validate workspace path
    workspace = Path(workspace_path)
    if not workspace.exists():
        raise ValueError(f"Workspace path does not exist: {workspace_path}")
    if not workspace.is_dir():
        raise ValueError(f"Workspace path is not a directory: {workspace_path}")

    process = None
    try:
        logger.info(f"Starting Claude task: {task_description[:100]}...")
        logger.debug(f"Working directory: {workspace_path}")

        # Spawn subprocess with claude --dangerously-skip-permissions --print command and task as argument
        process = await asyncio.create_subprocess_exec(
            'claude',
            '--dangerously-skip-permissions',
            '--print',  # Non-interactive mode - print response and exit
            task_description,  # Pass task as positional argument
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=workspace_path
        )

        logger.info(f"Claude subprocess spawned (PID: {process.pid})")
        logger.debug(f"Task passed as CLI argument: {task_description[:100]}...")

        # Close stdin immediately since we're not using it
        if process.stdin:
            process.stdin.close()

        try:
            # Use communicate() instead of readline() to avoid deadlocks
            # This reads all output and waits for process to complete
            if timeout:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            else:
                stdout, stderr = await process.communicate()

            # Process and yield stdout
            if stdout:
                for line in stdout.decode('utf-8', errors='replace').splitlines():
                    if line.strip():
                        logger.debug(f"STDOUT: {line}")
                        yield line

            # Process and yield stderr
            if stderr:
                for line in stderr.decode('utf-8', errors='replace').splitlines():
                    if line.strip():
                        logger.debug(f"STDERR: {line}")
                        yield line

        except asyncio.TimeoutError:
            logger.error(f"Claude task timed out after {timeout} seconds")
            if process:
                process.kill()
                await process.wait()
            raise

        # Capture exit code
        exit_code = process.returncode
        logger.info(f"Claude task completed with exit code: {exit_code}")

        # Yield exit code information
        if exit_code == 0:
            yield f"Task completed successfully (exit code: {exit_code})"
        else:
            yield f"Task failed with exit code: {exit_code}"

    except asyncio.TimeoutError:
        # Re-raise timeout errors
        raise

    except Exception as e:
        logger.error(f"Error executing Claude task: {e}")

        # Cleanup process on error
        if process:
            try:
                process.kill()
                await process.wait()
                logger.debug("Process killed after error")
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {cleanup_error}")

        raise

    finally:
        # Final cleanup
        if process and process.returncode is None:
            try:
                process.kill()
                await process.wait()
                logger.debug("Process killed in finally block")
            except Exception as cleanup_error:
                logger.debug(f"Cleanup in finally block failed: {cleanup_error}")
