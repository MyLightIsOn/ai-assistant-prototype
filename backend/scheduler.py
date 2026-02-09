"""
Task Scheduler using APScheduler.

This module provides persistent task scheduling with retry logic for the AI Assistant.
Tasks are synchronized from the database and executed using APScheduler with SQLAlchemy
job store for persistence across restarts.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
import pytz

from models import Task, TaskExecution, ActivityLog, DigestSettings
from database import get_db
from logger import get_logger
from executor import execute_task_wrapper


# Configure logging
logger = get_logger()

# Get user timezone from environment or default to PST
USER_TIMEZONE = os.getenv('USER_TIMEZONE', 'America/Los_Angeles')
try:
    SCHEDULER_TIMEZONE = pytz.timezone(USER_TIMEZONE)
except pytz.exceptions.UnknownTimeZoneError:
    logger.warning(f"Unknown timezone '{USER_TIMEZONE}', falling back to America/Los_Angeles")
    SCHEDULER_TIMEZONE = pytz.timezone('America/Los_Angeles')


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

        # Initialize scheduler with user's timezone
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=SCHEDULER_TIMEZONE
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
                    one_year_ms = int(one_year_from_now.timestamp() * 1000)
                    if task.nextRun > one_year_ms:
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

                    # Calculate exact datetime from cron expression
                    # For one-time tasks, parse the cron to get the specific date/time
                    # Current year is the reference point
                    now = datetime.now(SCHEDULER_TIMEZONE)
                    current_year = now.year

                    # Parse cron parts (minute hour day month day_of_week)
                    parts = task.schedule.split()
                    minute, hour, day, month = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])

                    # Build datetime for current year
                    try:
                        run_time = SCHEDULER_TIMEZONE.localize(datetime(current_year, month, day, hour, minute))

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

                        trigger = DateTrigger(run_date=run_time, timezone=SCHEDULER_TIMEZONE)
                        logger.info(f"Using DateTrigger for one-time task {task.id} at {run_time} (now: {now})")
                    except ValueError as e:
                        logger.error(f"Invalid date in cron expression for task {task.id}: {e}")
                        continue
                else:
                    # Use CronTrigger for recurring tasks
                    trigger = CronTrigger.from_crontab(task.schedule, timezone=SCHEDULER_TIMEZONE)
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


async def execute_send_email(args: str) -> tuple[str, int]:
    """
    Execute send-email command using Gmail API.

    Parses args like: --to recipient@email.com --subject "Subject" --body "Body"

    Returns:
        Tuple of (output, exit_code)
    """
    import shlex
    from gmail_sender import GmailSender

    try:
        # Parse args
        tokens = shlex.split(args)
        to = None
        subject = None
        body = None

        i = 0
        while i < len(tokens):
            if tokens[i] == '--to' and i + 1 < len(tokens):
                to = tokens[i + 1]
                i += 2
            elif tokens[i] == '--subject' and i + 1 < len(tokens):
                subject = tokens[i + 1]
                i += 2
            elif tokens[i] == '--body' and i + 1 < len(tokens):
                body = tokens[i + 1]
                i += 2
            else:
                i += 1

        if not to or not subject:
            return ("Error: --to and --subject are required", 1)

        body = body or ""
        body_html = f"<html><body><p>{body}</p></body></html>"

        sender = GmailSender()
        message_id = sender.send_email(
            to=to,
            subject=subject,
            body_html=body_html,
            body_text=body
        )

        output = f"Email sent successfully to {to}\nSubject: {subject}\nBody: {body}\nMessage ID: {message_id}"
        logger.info(output)
        return (output, 0)

    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        logger.error(error_msg)
        return (error_msg, 1)


async def execute_claude_command(command: str, args: str) -> tuple[str, int]:
    """
    Execute a task command. Routes to appropriate handler based on command type.

    Args:
        command: The command to execute (e.g., "claude", "send-email")
        args: Command arguments

    Returns:
        Tuple of (output, exit_code)
    """
    import os
    from claude_interface import execute_claude_task

    logger.info(f"Executing command: {command} with args: {args}")

    # Route to appropriate handler based on command
    if command in ("send-email", "send_email"):
        return await execute_send_email(args)

    # Default: execute via Claude CLI
    # Get workspace path from environment or use default
    workspace_path = os.getenv('AI_WORKSPACE', 'ai-workspace')

    # Collect output from Claude subprocess
    output_lines = []
    exit_code = 0

    try:
        async for line in execute_claude_task(args, workspace_path, timeout=300):
            output_lines.append(line)
            logger.debug(f"Claude output: {line}")

        # Join all output lines
        output = "\n".join(output_lines)

        # Extract exit code from last line if present
        if output_lines and "exit code:" in output_lines[-1].lower():
            try:
                # Parse "Task completed successfully (exit code: 0)"
                last_line = output_lines[-1]
                exit_code = int(last_line.split("exit code:")[-1].strip().rstrip(")"))
            except:
                exit_code = 0  # Default to success if parsing fails

    except asyncio.TimeoutError:
        output = "\n".join(output_lines) + "\n\nTask timed out after 300 seconds"
        exit_code = 124  # Standard timeout exit code
    except Exception as e:
        output = "\n".join(output_lines) + f"\n\nError: {str(e)}"
        exit_code = 1

    return (output, exit_code)


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


def execute_task_wrapper(database_url: str, task_id: str):
    """
    Wrapper function for task execution that can be pickled.

    This is a module-level function that creates a TaskScheduler instance
    and executes the task with retry logic.

    Args:
        database_url: Database URL string (engine can't be pickled)
        task_id: The ID of the task to execute
    """
    # Create engine from database URL
    from sqlalchemy import create_engine
    engine = create_engine(database_url)

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
        scheduler.add_job(
            send_daily_digest_job,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=SCHEDULER_TIMEZONE),
            id="daily_digest",
            name="Daily Digest Email",
            replace_existing=True
        )
        logger.info(f"Scheduled daily digest job at {settings.dailyTime}")

    # Schedule weekly digest job
    if settings.weeklyEnabled:
        hour, minute = settings.weeklyTime.split(":")
        day_of_week = day_map[settings.weeklyDay.lower()]
        scheduler.add_job(
            send_weekly_digest_job,
            CronTrigger(
                day_of_week=day_of_week,
                hour=int(hour),
                minute=int(minute),
                timezone=SCHEDULER_TIMEZONE
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
