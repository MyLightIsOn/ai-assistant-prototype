"""
Test that SQLAlchemy models store timestamps as INTEGER (Unix milliseconds) instead of TEXT.

This ensures compatibility with Prisma, which expects INTEGER format for DateTime fields.
"""
import pytest
import time
from sqlalchemy import inspect, Integer, Text
from models import (
    User,
    TaskExecution,
    ActivityLog,
    Notification,
    AiMemory,
    DigestSettings,
    Base
)
from database import engine


def get_column_type(model, column_name):
    """Get the SQLAlchemy type of a column in a model."""
    mapper = inspect(model)
    column = mapper.columns[column_name]
    return column.type


def test_user_timestamps_are_integer():
    """User model timestamps should be INTEGER type."""
    assert isinstance(get_column_type(User, 'createdAt'), Integer), \
        "User.createdAt should be INTEGER type"
    assert isinstance(get_column_type(User, 'updatedAt'), Integer), \
        "User.updatedAt should be INTEGER type"


def test_task_execution_timestamps_are_integer():
    """TaskExecution model timestamps should be INTEGER type."""
    assert isinstance(get_column_type(TaskExecution, 'startedAt'), Integer), \
        "TaskExecution.startedAt should be INTEGER type"
    assert isinstance(get_column_type(TaskExecution, 'completedAt'), Integer), \
        "TaskExecution.completedAt should be INTEGER type"


def test_activity_log_created_at_is_integer():
    """ActivityLog model createdAt should be INTEGER type."""
    assert isinstance(get_column_type(ActivityLog, 'createdAt'), Integer), \
        "ActivityLog.createdAt should be INTEGER type"


def test_notification_timestamps_are_integer():
    """Notification model timestamps should be INTEGER type."""
    assert isinstance(get_column_type(Notification, 'sentAt'), Integer), \
        "Notification.sentAt should be INTEGER type"
    assert isinstance(get_column_type(Notification, 'readAt'), Integer), \
        "Notification.readAt should be INTEGER type"


def test_ai_memory_timestamps_are_integer():
    """AiMemory model timestamps should be INTEGER type."""
    assert isinstance(get_column_type(AiMemory, 'createdAt'), Integer), \
        "AiMemory.createdAt should be INTEGER type"
    assert isinstance(get_column_type(AiMemory, 'updatedAt'), Integer), \
        "AiMemory.updatedAt should be INTEGER type"


def test_digest_settings_timestamps_are_integer():
    """DigestSettings model timestamps should be INTEGER type."""
    assert isinstance(get_column_type(DigestSettings, 'createdAt'), Integer), \
        "DigestSettings.createdAt should be INTEGER type"
    assert isinstance(get_column_type(DigestSettings, 'updatedAt'), Integer), \
        "DigestSettings.updatedAt should be INTEGER type"


def test_timestamp_defaults_generate_unix_milliseconds(db_session):
    """Timestamp defaults should generate Unix milliseconds (13 digits)."""
    # Create an ActivityLog record to test default timestamp
    before = int(time.time() * 1000)

    log = ActivityLog(
        type="test",
        message="Test timestamp format"
    )
    db_session.add(log)
    db_session.commit()

    after = int(time.time() * 1000)

    # Verify createdAt is in the expected range
    assert before <= log.createdAt <= after, \
        f"createdAt should be Unix ms timestamp between {before} and {after}, got {log.createdAt}"

    # Verify it's a 13-digit number (Unix ms format)
    assert len(str(log.createdAt)) == 13, \
        f"createdAt should be 13 digits (Unix ms), got {len(str(log.createdAt))} digits"
