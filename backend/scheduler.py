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
from datetime import datetime, timezone, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

from models import Task, TaskExecution, ActivityLog, DigestSettings
from database import get_db
from logger import get_logger
from executor import execute_task_wrapper


# Configure logging
logger = get_logger()


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
        self.database_url = str(engine.url)  # Store URL string for pickling
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

    def _is_one_time_task(self, task) -> bool:
        """
        Detect if task should be one-time execution vs recurring.

        One-time tasks have:
        - Specific day AND month (not wildcards)
        - nextRun set to a specific datetime

        Args:
            task: Task model instance

        Returns:
            bool: True if one-time task, False if recurring
        """
        # If nextRun is set and schedule has specific day/month, it's one-time
        if not task.nextRun:
            return False

        parts = task.schedule.split()
        if len(parts) != 5:
            return False

        # Cron format: minute hour day month day_of_week
        day = parts[2]
        month = parts[3]

        # If both day and month are specific (not wildcards), it's one-time
        return day != '*' and month != '*'

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
                # Validate task nextRun is reasonable (not > 1 year away)
                if task.nextRun:
                    one_year_from_now = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=365)
                    if task.nextRun > one_year_from_now:
                        logger.warning(
                            f"Task {task.id} scheduled far in future: {task.nextRun}. "
                            f"Skipping - may be misconfigured."
                        )
                        continue

                # Check if job already exists
                existing_job = self.scheduler.get_job(task.id)

                # Determine trigger type based on task pattern
                if self._is_one_time_task(task):
                    # Use DateTrigger for one-time execution
                    from apscheduler.triggers.date import DateTrigger
                    from pytz import UTC

                    # Calculate exact datetime from cron expression
                    # For one-time tasks, parse the cron to get the specific date/time
                    # Current year is the reference point
                    now = datetime.now(UTC)
                    current_year = now.year

                    # Parse cron parts (minute hour day month day_of_week)
                    parts = task.schedule.split()
                    minute, hour, day, month = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])

                    # Build datetime for current year
                    from pytz import UTC
                    try:
                        run_time = datetime(current_year, month, day, hour, minute, tzinfo=UTC)

                        # If the time has passed today/this year, it's a past one-time task
                        if run_time < now:
                            logger.warning(
                                f"One-time task {task.id} scheduled for past date {run_time} (now: {now}). "
                                f"Skipping scheduling - task should be disabled or updated."
                            )
                            # Remove from scheduler if it exists
                            if existing_job:
                                self.scheduler.remove_job(task.id)
                                logger.info(f"Removed past one-time task {task.id} from scheduler")
                            continue

                        trigger = DateTrigger(run_date=run_time, timezone=UTC)
                        logger.info(f"Using DateTrigger for one-time task {task.id} at {run_time} (now: {now})")
                    except ValueError as e:
                        logger.error(f"Invalid date in cron expression for task {task.id}: {e}")
                        continue
                else:
                    # Use CronTrigger for recurring tasks
                    trigger = CronTrigger.from_crontab(task.schedule, timezone=UTC)
                    logger.info(f"Using CronTrigger for recurring task {task.id}: {task.schedule}")

                if existing_job:
                    # Update existing job
                    self.scheduler.reschedule_job(
                        task.id,
                        trigger=trigger
                    )
                    logger.info(f"Updated job {task.id}: {task.name}")
                else:
                    # Add new job using imported function
                    # Pass database URL string instead of engine (engine can't be pickled)
                    job = self.scheduler.add_job(
                        func=execute_task_wrapper,
                        trigger=trigger,
                        id=task.id,
                        name=task.name,
                        args=[self.database_url, task.id],
                        replace_existing=True
                    )
                    logger.info(f"Added job {task.id}: {task.name}")

                # Update nextRun in database
                job = self.scheduler.get_job(task.id)
                if job and hasattr(job, 'next_run_time') and job.next_run_time:
                    task.nextRun = int(job.next_run_time.replace(tzinfo=None).timestamp() * 1000)
                    db.commit()

            logger.info(f"Synchronized {len(enabled_tasks)} tasks to scheduler")

            # Setup digest email jobs
            setup_digest_jobs(self.scheduler, db)

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
                taskId=task_id,
                status="running"
            )
            db.add(execution)
            db.commit()
            db.refresh(execution)

            # Log task start
            log = ActivityLog(
                executionId=execution.id,
                type="task_start",
                message=f"Task '{task.name}' started",
                metadata_={
                    "task_id": task_id,
                    "command": task.command,
                    "args": task.args
                }
            )
            db.add(log)
            db.commit()

            logger.info(f"Executing task {task_id}: {task.name}")

            # Execute the task
            start_time = datetime.now(timezone.utc)
            try:
                output, exit_code = await execute_claude_command(task.command, task.args)

                # Update execution record
                end_time = datetime.now(timezone.utc)
                execution.status = "completed" if exit_code == 0 else "failed"
                execution.completedAt = int(end_time.timestamp() * 1000)
                execution.output = output
                execution.duration = int((end_time - start_time).total_seconds() * 1000)

                # Update task lastRun
                task.lastRun = int(start_time.timestamp() * 1000)

                db.commit()

                # Log completion
                log = ActivityLog(
                    executionId=execution.id,
                    type="task_complete" if exit_code == 0 else "task_error",
                    message=f"Task '{task.name}' {'completed' if exit_code == 0 else 'failed'}",
                    metadata_={
                        "exit_code": exit_code,
                        "duration_ms": execution.duration
                    }
                )
                db.add(log)
                db.commit()

                logger.info(f"Task {task_id} completed with exit code {exit_code}")

            except Exception as e:
                # Handle execution error
                end_time = datetime.now(timezone.utc)
                execution.status = "failed"
                execution.completedAt = int(end_time.timestamp() * 1000)
                execution.output = str(e)
                execution.duration = int((end_time - start_time).total_seconds() * 1000)

                # Update task lastRun
                task.lastRun = int(start_time.timestamp() * 1000)

                db.commit()

                # Log error
                log = ActivityLog(
                    executionId=execution.id,
                    type="error",
                    message=f"Task '{task.name}' failed with error: {str(e)}",
                    metadata_={
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
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
                            executionId=None,
                            type="task_retry",
                            message=f"Task {task_id} retry attempt {attempt + 1}/{max_attempts}",
                            metadata_={
                                "task_id": task_id,
                                "attempt": attempt,
                                "next_attempt": attempt + 1,
                                "backoff_seconds": backoff_delays[attempt - 1] if attempt <= len(backoff_delays) else 0
                            }
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


# ============================================================================
# Digest Email Scheduling
# ============================================================================

def setup_digest_jobs(scheduler: BackgroundScheduler, db: Session):
    """
    Configure digest email jobs from database settings.

    This function:
    - Creates default settings if none exist
    - Schedules daily and weekly digest jobs based on settings
    - Uses APScheduler CronTrigger for precise scheduling

    Args:
        scheduler: APScheduler BackgroundScheduler instance
        db: Database session
    """
    import os
    import uuid

    # Get or create settings
    settings = db.query(DigestSettings).first()

    if not settings:
        # Create default settings
        settings = DigestSettings(
            dailyEnabled=True,
            dailyTime="20:00",
            weeklyEnabled=True,
            weeklyDay="monday",
            weeklyTime="09:00",
            recipientEmail=os.getenv("USER_EMAIL", "user@example.com")
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        logger.info("Created default DigestSettings")

    # Day name to number mapping (APScheduler uses 0=Monday)
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }

    # Schedule daily digest job
    if settings.dailyEnabled:
        hour, minute = settings.dailyTime.split(":")
        from pytz import UTC
        scheduler.add_job(
            send_daily_digest_job,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=UTC),
            id="daily_digest",
            name="Daily Digest Email",
            replace_existing=True
        )
        logger.info(f"Scheduled daily digest job at {settings.dailyTime}")

    # Schedule weekly digest job
    if settings.weeklyEnabled:
        hour, minute = settings.weeklyTime.split(":")
        day_of_week = day_map[settings.weeklyDay.lower()]
        from pytz import UTC
        scheduler.add_job(
            send_weekly_digest_job,
            CronTrigger(
                day_of_week=day_of_week,
                hour=int(hour),
                minute=int(minute),
                timezone=UTC
            ),
            id="weekly_digest",
            name="Weekly Digest Email",
            replace_existing=True
        )
        logger.info(f"Scheduled weekly digest job on {settings.weeklyDay} at {settings.weeklyTime}")


def send_daily_digest_job():
    """
    Scheduled job for sending daily digest email.

    This is a module-level function that can be pickled for APScheduler.
    It checks if daily digest is enabled and sends the email.
    """
    from database import SessionLocal
    from gmail_sender import get_gmail_sender
    from datetime import datetime

    db = SessionLocal()
    try:
        settings = db.query(DigestSettings).first()
        if settings and settings.dailyEnabled:
            logger.info(f"Sending daily digest to {settings.recipientEmail}")
            sender = get_gmail_sender()
            sender.send_daily_digest(db, settings.recipientEmail, datetime.now())
            logger.info("Daily digest sent successfully")
        else:
            logger.info("Daily digest disabled, skipping")
    except Exception as e:
        logger.error(f"Failed to send daily digest: {e}")
    finally:
        db.close()


def send_weekly_digest_job():
    """
    Scheduled job for sending weekly summary email.

    This is a module-level function that can be pickled for APScheduler.
    It checks if weekly digest is enabled and sends the email.
    """
    from database import SessionLocal
    from gmail_sender import get_gmail_sender
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        settings = db.query(DigestSettings).first()
        if settings and settings.weeklyEnabled:
            # Calculate week start (Monday of current week)
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

            logger.info(f"Sending weekly summary to {settings.recipientEmail}")
            sender = get_gmail_sender()
            sender.send_weekly_summary(db, settings.recipientEmail, week_start)
            logger.info("Weekly summary sent successfully")
        else:
            logger.info("Weekly digest disabled, skipping")
    except Exception as e:
        logger.error(f"Failed to send weekly summary: {e}")
    finally:
        db.close()
