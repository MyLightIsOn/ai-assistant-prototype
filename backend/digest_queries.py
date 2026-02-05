"""
Database queries for digest emails.

This module provides functions to query task execution statistics
for daily and weekly digest emails.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models import Task, TaskExecution


def get_daily_digest_data(db: Session, date: datetime) -> Dict[str, Any]:
    """
    Query database for daily digest statistics.

    Args:
        db: SQLAlchemy database session
        date: Date for the digest (typically datetime.now())

    Returns:
        Dictionary with:
        - total_tasks: Total executions in last 24 hours
        - successful: Successful executions in last 24 hours
        - failed: Failed executions in last 24 hours
        - success_rate: Success rate percentage (0-100)
        - upcoming_tasks: List of next 5 upcoming tasks
    """
    # Calculate time window (last 24 hours from the given date)
    yesterday = date - timedelta(days=1)

    # Count total task executions in last 24 hours
    total_tasks = db.query(TaskExecution).filter(
        TaskExecution.startedAt >= yesterday
    ).count()

    # Count successful executions
    successful = db.query(TaskExecution).filter(
        and_(
            TaskExecution.startedAt >= yesterday,
            TaskExecution.status == 'completed'
        )
    ).count()

    # Count failed executions
    failed = db.query(TaskExecution).filter(
        and_(
            TaskExecution.startedAt >= yesterday,
            TaskExecution.status == 'failed'
        )
    ).count()

    # Calculate success rate (avoid division by zero)
    if total_tasks > 0:
        success_rate = int((successful / total_tasks) * 100)
    else:
        success_rate = 0

    # Get upcoming tasks (next 5 enabled tasks sorted by nextRun)
    upcoming_tasks_query = db.query(Task).filter(
        and_(
            Task.enabled == 1,  # SQLite Boolean is stored as integer
            Task.nextRun.isnot(None)
        )
    ).order_by(Task.nextRun.asc()).limit(5).all()

    # Format upcoming tasks
    upcoming_tasks = [
        {
            'name': task.name,
            'time': task.nextRun.strftime('%Y-%m-%d %H:%M:%S') if task.nextRun else 'Not scheduled',
            'description': task.description or 'N/A',
            'priority': task.priority
        }
        for task in upcoming_tasks_query
    ]

    return {
        'total_tasks': total_tasks,
        'successful': successful,
        'failed': failed,
        'success_rate': success_rate,
        'upcoming_tasks': upcoming_tasks
    }


def get_weekly_summary_data(db: Session, week_start: datetime) -> Dict[str, Any]:
    """
    Query database for weekly summary statistics.

    Args:
        db: SQLAlchemy database session
        week_start: Start date of the week

    Returns:
        Dictionary with:
        - total_executions: Total executions in last 7 days
        - success_count: Successful executions in last 7 days
        - failure_count: Failed executions in last 7 days
        - top_failures: List of top 3 tasks with most failures
        - avg_duration_ms: Average execution duration in milliseconds
    """
    # Calculate time window (7 days from week_start)
    week_end = week_start + timedelta(days=7)

    # Count total executions in last 7 days
    total_executions = db.query(TaskExecution).filter(
        and_(
            TaskExecution.startedAt >= week_start,
            TaskExecution.startedAt < week_end
        )
    ).count()

    # Count successful executions
    success_count = db.query(TaskExecution).filter(
        and_(
            TaskExecution.startedAt >= week_start,
            TaskExecution.startedAt < week_end,
            TaskExecution.status == 'completed'
        )
    ).count()

    # Count failed executions
    failure_count = db.query(TaskExecution).filter(
        and_(
            TaskExecution.startedAt >= week_start,
            TaskExecution.startedAt < week_end,
            TaskExecution.status == 'failed'
        )
    ).count()

    # Get top 3 tasks with most failures
    top_failures_query = db.query(
        Task.id,
        Task.name,
        func.count(TaskExecution.id).label('failure_count')
    ).join(
        TaskExecution, Task.id == TaskExecution.taskId
    ).filter(
        and_(
            TaskExecution.startedAt >= week_start,
            TaskExecution.startedAt < week_end,
            TaskExecution.status == 'failed'
        )
    ).group_by(
        Task.id, Task.name
    ).order_by(
        func.count(TaskExecution.id).desc()
    ).limit(3).all()

    # Format top failures (matching template expectations)
    top_failures = [
        {
            'task': row.name,
            'count': row.failure_count
        }
        for row in top_failures_query
    ]

    # Calculate average execution duration
    avg_duration_result = db.query(
        func.avg(TaskExecution.duration)
    ).filter(
        and_(
            TaskExecution.startedAt >= week_start,
            TaskExecution.startedAt < week_end,
            TaskExecution.duration.isnot(None)
        )
    ).scalar()

    # Handle None result (no executions with duration)
    avg_duration_ms = int(avg_duration_result) if avg_duration_result else 0

    return {
        'total_executions': total_executions,
        'success_count': success_count,
        'failure_count': failure_count,
        'top_failures': top_failures,
        'avg_duration_ms': avg_duration_ms
    }
