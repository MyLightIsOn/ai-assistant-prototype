"""
Task Scheduler using APScheduler.

This module provides persistent task scheduling with retry logic for the AI Assistant.
Tasks are synchronized from the database and executed using APScheduler with SQLAlchemy
job store for persistence across restarts.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from models import Task, TaskExecution, ActivityLog
from database import get_db


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Task scheduler that manages periodic task execution with retry logic.

    Features:
    - Persistent job storage using SQLAlchemy
    - Automatic task synchronization from database
    - Retry logic with exponential backoff (1min, 5min, 15min)
    - Graceful shutdown handling
    - Activity logging for all operations
    """

    def __init__(self, engine: Engine):
        """
        Initialize the task scheduler.

        Args:
            engine: SQLAlchemy engine for database connection
        """
        self.engine = engine
        self.SessionLocal = sessionmaker(bind=engine)

        # Configure job stores
        jobstores = {
            'default': SQLAlchemyJobStore(engine=engine)
        }

        # Configure executors
        executors = {
            'default': ThreadPoolExecutor(max_workers=5)
        }

        # Configure job defaults
        job_defaults = {
            'coalesce': True,  # Combine multiple missed runs into one
            'max_instances': 1  # Only one instance of each job can run at a time
        }

        # Initialize scheduler
        from pytz import UTC
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=UTC
        )

        # Create APScheduler tables if they don't exist
        jobstores['default'].jobs_t.create(engine, checkfirst=True)

        logger.info("TaskScheduler initialized with BackgroundScheduler")

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True):
        """
        Shutdown the scheduler gracefully.

        Args:
            wait: If True, wait for running jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info(f"Scheduler shutdown (wait={wait})")

    def sync_tasks(self):
        """
        Synchronize tasks from database to scheduler.

        - Loads all enabled tasks from the database
        - Adds/updates jobs in the scheduler
        - Removes jobs for deleted or disabled tasks
        - Updates nextRun field in database
        """
        from pytz import UTC

        db = self.SessionLocal()
        try:
            # Get all enabled tasks from database
            enabled_tasks = db.query(Task).filter_by(enabled=True).all()
            enabled_task_ids = {task.id for task in enabled_tasks}

            # Get current jobs in scheduler
            current_jobs = {job.id for job in self.scheduler.get_jobs()}

            # Remove jobs for deleted or disabled tasks
            jobs_to_remove = current_jobs - enabled_task_ids
            for job_id in jobs_to_remove:
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed job {job_id} (task deleted or disabled)")

            # Add or update jobs for enabled tasks
            for task in enabled_tasks:
                # Parse cron schedule
                trigger = CronTrigger.from_crontab(task.schedule, timezone=UTC)

                # Check if job already exists
                existing_job = self.scheduler.get_job(task.id)

                if existing_job:
                    # Update existing job
                    self.scheduler.reschedule_job(
                        task.id,
                        trigger=trigger
                    )
                    logger.info(f"Updated job {task.id}: {task.name}")
                else:
                    # Add new job using module:function reference for pickling
                    job = self.scheduler.add_job(
                        func='scheduler:execute_task_wrapper',
                        trigger=trigger,
                        id=task.id,
                        name=task.name,
                        args=[self.engine, task.id],
                        replace_existing=True
                    )
                    logger.info(f"Added job {task.id}: {task.name}")

                # Update nextRun in database
                job = self.scheduler.get_job(task.id)
                if job and hasattr(job, 'next_run_time') and job.next_run_time:
                    task.nextRun = job.next_run_time.replace(tzinfo=None)
                    db.commit()

            logger.info(f"Synchronized {len(enabled_tasks)} tasks to scheduler")

        finally:
            db.close()

    async def execute_task(self, task_id: str):
        """
        Execute a single task.

        Args:
            task_id: The ID of the task to execute
        """
        db = self.SessionLocal()
        try:
            # Get task from database
            task = db.query(Task).filter_by(id=task_id).first()
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            # Create execution record
            execution = TaskExecution(
                id=str(uuid.uuid4()),
                taskId=task_id,
                status="running",
                startedAt=datetime.utcnow()
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)

            # Log task start
            log = ActivityLog(
                id=str(uuid.uuid4()),
                executionId=execution.id,
                type="task_start",
                message=f"Task '{task.name}' started",
                metadata_=json.dumps({
                    "task_id": task_id,
                    "command": task.command,
                    "args": task.args
                })
            )
            db.add(log)
            db.commit()

            logger.info(f"Executing task {task_id}: {task.name}")

            # Execute the task
            start_time = datetime.utcnow()
            try:
                output, exit_code = await execute_claude_command(task.command, task.args)

                # Update execution record
                end_time = datetime.utcnow()
                execution.status = "completed" if exit_code == 0 else "failed"
                execution.completedAt = end_time
                execution.output = output
                execution.duration = int((end_time - start_time).total_seconds() * 1000)

                # Update task lastRun
                task.lastRun = start_time

                db.commit()

                # Log completion
                log = ActivityLog(
                    id=str(uuid.uuid4()),
                    executionId=execution.id,
                    type="task_complete" if exit_code == 0 else "task_error",
                    message=f"Task '{task.name}' {'completed' if exit_code == 0 else 'failed'}",
                    metadata_=json.dumps({
                        "exit_code": exit_code,
                        "duration_ms": execution.duration
                    })
                )
                db.add(log)
                db.commit()

                logger.info(f"Task {task_id} completed with exit code {exit_code}")

            except Exception as e:
                # Handle execution error
                end_time = datetime.utcnow()
                execution.status = "failed"
                execution.completedAt = end_time
                execution.output = str(e)
                execution.duration = int((end_time - start_time).total_seconds() * 1000)

                # Update task lastRun
                task.lastRun = start_time

                db.commit()

                # Log error
                log = ActivityLog(
                    id=str(uuid.uuid4()),
                    executionId=execution.id,
                    type="error",
                    message=f"Task '{task.name}' failed with error: {str(e)}",
                    metadata_=json.dumps({
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                )
                db.add(log)
                db.commit()

                logger.error(f"Task {task_id} failed: {e}")
                raise

        finally:
            db.close()

    async def execute_task_with_retry(self, task_id: str):
        """
        Execute a task with retry logic.

        Retry logic:
        - 3 attempts maximum
        - Exponential backoff: 1min, 5min, 15min
        - Log each attempt
        - Notify only after final failure

        Args:
            task_id: The ID of the task to execute
        """
        max_attempts = 3
        backoff_delays = [60, 300, 900]  # 1min, 5min, 15min in seconds

        for attempt in range(1, max_attempts + 1):
            try:
                await self.execute_task(task_id)

                # Success - no need to retry
                if attempt > 1:
                    logger.info(f"Task {task_id} succeeded on attempt {attempt}")
                return

            except Exception as e:
                logger.warning(f"Task {task_id} failed on attempt {attempt}/{max_attempts}: {e}")

                # Log retry attempt
                if attempt < max_attempts:
                    db = self.SessionLocal()
                    try:
                        log = ActivityLog(
                            id=str(uuid.uuid4()),
                            executionId=None,
                            type="task_retry",
                            message=f"Task {task_id} retry attempt {attempt + 1}/{max_attempts}",
                            metadata_=json.dumps({
                                "task_id": task_id,
                                "attempt": attempt,
                                "next_attempt": attempt + 1,
                                "backoff_seconds": backoff_delays[attempt - 1] if attempt <= len(backoff_delays) else 0
                            })
                        )
                        db.add(log)
                        db.commit()
                    finally:
                        db.close()

                    # Wait before retry (exponential backoff)
                    delay = backoff_delays[attempt - 1]
                    logger.info(f"Retrying task {task_id} in {delay} seconds")
                    await asyncio.sleep(delay)
                else:
                    # Final failure - send notification
                    logger.error(f"Task {task_id} failed after {max_attempts} attempts")
                    await send_notification(
                        title=f"Task Failed",
                        message=f"Task {task_id} failed after {max_attempts} attempts",
                        priority="high"
                    )


async def execute_claude_command(command: str, args: str) -> tuple[str, int]:
    """
    Execute a Claude command.

    Args:
        command: The command to execute
        args: JSON string of command arguments

    Returns:
        Tuple of (output, exit_code)
    """
    # This is a placeholder for actual Claude command execution
    # In production, this would spawn a Claude Code subprocess
    logger.info(f"Executing command: {command} with args: {args}")

    # Simulate async execution
    await asyncio.sleep(0.01)

    return (f"Executed {command}", 0)


async def send_notification(title: str, message: str, priority: str = "default"):
    """
    Send a notification.

    Args:
        title: Notification title
        message: Notification message
        priority: Notification priority (low, default, high, urgent)
    """
    # This is a placeholder for actual notification sending
    # In production, this would use ntfy.sh or email
    logger.info(f"Notification: {title} - {message} (priority: {priority})")


def execute_task_wrapper(engine: Engine, task_id: str):
    """
    Wrapper function for task execution that can be pickled.

    This is a module-level function that creates a TaskScheduler instance
    and executes the task with retry logic.

    Args:
        engine: SQLAlchemy engine
        task_id: The ID of the task to execute
    """
    # Create scheduler instance
    scheduler = TaskScheduler(engine)

    # Execute task with retry using asyncio
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(scheduler.execute_task_with_retry(task_id))
    finally:
        loop.close()
