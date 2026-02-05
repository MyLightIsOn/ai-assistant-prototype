"""
Task Execution Engine.

Connects APScheduler to Claude Code subprocess execution with real-time streaming,
retry logic, and comprehensive logging.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from models import Task, TaskExecution, ActivityLog
from database import get_db
from claude_interface import execute_claude_task
from logger import get_logger
from ntfy_client import send_notification
from gmail_sender import get_gmail_sender

# Setup logging
logger = get_logger()


async def execute_task(
    task_id: str,
    db: Session,
    broadcast_callback: Optional[callable] = None
) -> tuple[str, int]:
    """
    Execute a single task with Claude Code.

    Args:
        task_id: The ID of the task to execute
        db: Database session
        broadcast_callback: Optional function to broadcast WebSocket messages

    Returns:
        tuple: (output, exit_code)
    """
    # Get task from database
    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        logger.error(f"Task {task_id} not found")
        raise ValueError(f"Task {task_id} not found")

    # Create execution record
    execution = TaskExecution(
        id=str(uuid.uuid4()),
        taskId=task_id,
        status="running",
        startedAt=datetime.now(timezone.utc)
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    # Log task start
    log_entry = ActivityLog(
        id=str(uuid.uuid4()),
        executionId=execution.id,
        type="task_start",
        message=f"Task '{task.name}' started",
        metadata_={
            "task_id": task_id,
            "command": task.command,
            "args": task.args
        }
    )
    db.add(log_entry)
    db.commit()

    logger.info(f"Executing task {task_id}: {task.name}")

    # Broadcast task start
    if broadcast_callback:
        await broadcast_callback({
            "type": "task_status",
            "data": {
                "task_id": task_id,
                "status": "running",
                "execution_id": execution.id
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    # Prepare workspace directory
    project_root = Path(__file__).parent.parent
    workspace_path = project_root / "ai-workspace"
    task_workspace = workspace_path / "tasks" / execution.id
    task_workspace.mkdir(parents=True, exist_ok=True)

    # Create task description for Claude
    task_description = f"""Task: {task.name}

Description: {task.description or 'No description provided'}

Command: {task.command}
Arguments: {task.args}

Please execute this task and provide the output.
"""

    # Execute the task
    start_time = datetime.now(timezone.utc)
    output_lines = []
    exit_code = 0

    try:
        # Stream output from Claude subprocess
        async for line in execute_claude_task(
            task_description,
            str(task_workspace),
            timeout=3600  # 1 hour timeout
        ):
            output_lines.append(line)

            # Broadcast terminal output
            if broadcast_callback:
                await broadcast_callback({
                    "type": "terminal_output",
                    "data": {
                        "task_id": task_id,
                        "execution_id": execution.id,
                        "line": line
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

        # Extract exit code from last line if present
        if output_lines and "exit code:" in output_lines[-1].lower():
            try:
                exit_code = int(output_lines[-1].split(":")[-1].strip())
            except (ValueError, IndexError):
                exit_code = 0

        output = "\n".join(output_lines)

        # Update execution record
        end_time = datetime.now(timezone.utc)
        execution.status = "completed" if exit_code == 0 else "failed"
        execution.completedAt = end_time
        execution.output = output[:10000]  # Limit output size in DB
        execution.duration = int((end_time - start_time).total_seconds() * 1000)

        # Update task lastRun
        task.lastRun = start_time

        db.commit()

        # Log completion
        log_entry = ActivityLog(
            id=str(uuid.uuid4()),
            executionId=execution.id,
            type="task_complete" if exit_code == 0 else "task_error",
            message=f"Task '{task.name}' {'completed' if exit_code == 0 else 'failed'}",
            metadata_={
                "exit_code": exit_code,
                "duration_ms": execution.duration
            }
        )
        db.add(log_entry)
        db.commit()

        logger.info(f"Task {task_id} completed with exit code {exit_code}")

        # Broadcast completion
        if broadcast_callback:
            await broadcast_callback({
                "type": "task_status",
                "data": {
                    "task_id": task_id,
                    "status": execution.status,
                    "execution_id": execution.id,
                    "exit_code": exit_code
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Send notification if configured
        if should_notify(task, execution.status):
            send_notification(
                title=f"Task {'Completed' if exit_code == 0 else 'Failed'}: {task.name}",
                message=f"Duration: {execution.duration}ms\nExit code: {exit_code}",
                priority="default" if exit_code == 0 else "high",
                tags=["task", "completion" if exit_code == 0 else "error"],
                db_session=db
            )

        # Send email notification if configured
        if exit_code == 0 and should_notify(task, "completed"):
            try:
                gmail_sender = get_gmail_sender()
                gmail_sender.send_task_completion_email(task, execution)
                logger.info(f"Sent completion email for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to send completion email for task {task_id}: {e}")

        return output, exit_code

    except asyncio.TimeoutError:
        # Handle timeout
        end_time = datetime.now(timezone.utc)
        execution.status = "failed"
        execution.completedAt = end_time
        execution.output = f"Task timed out after 1 hour\n" + "\n".join(output_lines[:100])
        execution.duration = int((end_time - start_time).total_seconds() * 1000)

        # Update task lastRun
        task.lastRun = start_time

        db.commit()

        # Log timeout
        log_entry = ActivityLog(
            id=str(uuid.uuid4()),
            executionId=execution.id,
            type="task_error",
            message=f"Task '{task.name}' timed out",
            metadata_={"error": "timeout", "duration_ms": execution.duration}
        )
        db.add(log_entry)
        db.commit()

        logger.error(f"Task {task_id} timed out")

        # Broadcast timeout
        if broadcast_callback:
            await broadcast_callback({
                "type": "task_status",
                "data": {
                    "task_id": task_id,
                    "status": "failed",
                    "execution_id": execution.id,
                    "error": "timeout"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Send notification
        if should_notify(task, "failed"):
            send_notification(
                title=f"Task Timeout: {task.name}",
                message=f"Task exceeded 1 hour timeout",
                priority="urgent",
                tags=["task", "timeout", "error"],
                db_session=db
            )

        # Send email notification if configured
        if should_notify(task, "failed"):
            try:
                gmail_sender = get_gmail_sender()
                gmail_sender.send_task_failure_email(task, execution)
                logger.info(f"Sent failure email for task {task_id} (timeout)")
            except Exception as e:
                logger.error(f"Failed to send failure email for task {task_id}: {e}")

        raise

    except Exception as e:
        # Handle execution error
        end_time = datetime.now(timezone.utc)
        execution.status = "failed"
        execution.completedAt = end_time
        execution.output = f"Error: {str(e)}\n" + "\n".join(output_lines[:100])
        execution.duration = int((end_time - start_time).total_seconds() * 1000)

        # Update task lastRun
        task.lastRun = start_time

        db.commit()

        # Log error
        log_entry = ActivityLog(
            id=str(uuid.uuid4()),
            executionId=execution.id,
            type="task_error",
            message=f"Task '{task.name}' failed: {str(e)}",
            metadata_={
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": execution.duration
            }
        )
        db.add(log_entry)
        db.commit()

        logger.error(f"Task {task_id} failed: {e}")

        # Broadcast error
        if broadcast_callback:
            await broadcast_callback({
                "type": "task_status",
                "data": {
                    "task_id": task_id,
                    "status": "failed",
                    "execution_id": execution.id,
                    "error": str(e)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Send notification
        if should_notify(task, "failed"):
            send_notification(
                title=f"Task Failed: {task.name}",
                message=f"Error: {str(e)}",
                priority="urgent",
                tags=["task", "error"],
                db_session=db
            )

        # Send email notification if configured
        if should_notify(task, "failed"):
            try:
                gmail_sender = get_gmail_sender()
                gmail_sender.send_task_failure_email(task, execution)
                logger.info(f"Sent failure email for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to send failure email for task {task_id}: {e}")

        raise


def should_notify(task: Task, status: str) -> bool:
    """
    Determine if notification should be sent based on task configuration.

    Args:
        task: Task instance
        status: Execution status ("completed", "failed")

    Returns:
        bool: True if notification should be sent
    """
    notify_settings = task.notifyOn.split(",")
    notify_settings = [s.strip().lower() for s in notify_settings]

    if status == "completed" and "completion" in notify_settings:
        return True
    if status == "failed" and "error" in notify_settings:
        return True

    return False


async def execute_task_with_retry(
    task_id: str,
    db: Session,
    broadcast_callback: Optional[callable] = None,
    max_attempts: int = 3
):
    """
    Execute task with retry logic (exponential backoff: 1min, 5min, 15min).

    Args:
        task_id: Task ID to execute
        db: Database session
        broadcast_callback: Optional WebSocket broadcast function
        max_attempts: Maximum retry attempts (default: 3)
    """
    delays = [60, 300, 900]  # 1min, 5min, 15min

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Task {task_id} attempt {attempt}/{max_attempts}")
            output, exit_code = await execute_task(task_id, db, broadcast_callback)

            if exit_code == 0:
                logger.info(f"Task {task_id} succeeded on attempt {attempt}")
                return output, exit_code

            # Failed but will retry
            if attempt < max_attempts:
                delay = delays[attempt - 1]
                logger.warning(
                    f"Task {task_id} failed (attempt {attempt}), retrying in {delay}s"
                )
                await asyncio.sleep(delay)

        except Exception as e:
            if attempt < max_attempts:
                delay = delays[attempt - 1]
                logger.error(
                    f"Task {task_id} error (attempt {attempt}): {e}, retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"Task {task_id} failed after {max_attempts} attempts")
                raise

    logger.error(f"Task {task_id} failed after all retry attempts")
    return "", 1


def execute_task_wrapper(engine, task_id: str):
    """
    Wrapper function for APScheduler that runs async task execution in sync context.

    This function is called by APScheduler and needs to be a module-level function
    for proper pickling.

    Args:
        engine: SQLAlchemy engine
        task_id: Task ID to execute
    """
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Run async execution in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                execute_task_with_retry(task_id, db, broadcast_callback=None)
            )
        finally:
            loop.close()

    finally:
        db.close()
