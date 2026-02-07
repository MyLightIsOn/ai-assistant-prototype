"""
SQLAlchemy models and Pydantic schemas for the AI Assistant backend.

These models EXACTLY mirror the Prisma schema defined in frontend/prisma/schema.prisma.
Any changes to the Prisma schema should be reflected here to maintain database consistency.
"""

from datetime import datetime
from typing import Optional, List
import time
import random
import string

from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict

from database import Base


# ============================================================================
# ID Generation (CUID-compatible)
# ============================================================================

def generate_cuid() -> str:
    """
    Generate a CUID-compatible ID using Python standard library.

    Format: c + timestamp(base36) + counter(base36) + fingerprint + random

    This mimics Prisma's cuid() format:
    - Starts with 'c'
    - Timestamp in base36 for compactness
    - Counter for same-millisecond uniqueness
    - 4-char fingerprint for machine identification
    - 8-char random suffix for additional entropy

    Example output: clh1234abcd5678efgh9012ijkl
    Length: ~25-30 characters (compatible with Prisma CUID spec)
    """
    # Timestamp in milliseconds, converted to base36
    timestamp = int(time.time() * 1000)
    timestamp_b36 = _to_base36(timestamp)

    # Counter (0-1679615) in base36 for same-millisecond uniqueness
    counter = random.randint(0, 36**4 - 1)
    counter_b36 = _to_base36(counter).zfill(4)

    # 4-character fingerprint (stable per process)
    fingerprint = _get_fingerprint()

    # 8-character random suffix
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    return f"c{timestamp_b36}{counter_b36}{fingerprint}{random_suffix}"


def _to_base36(num: int) -> str:
    """Convert integer to base36 string (0-9, a-z)."""
    chars = string.digits + string.ascii_lowercase
    if num == 0:
        return '0'

    result = []
    while num:
        num, rem = divmod(num, 36)
        result.append(chars[rem])
    return ''.join(reversed(result))


def _get_fingerprint() -> str:
    """
    Get a 4-character fingerprint for this process.
    Uses process ID for uniqueness across concurrent processes.
    """
    import os
    pid = os.getpid()
    # Convert PID to base36 and take last 4 chars
    return _to_base36(pid)[-4:].zfill(4)


# ============================================================================
# SQLAlchemy Models (Database Layer)
# ============================================================================

class User(Base):
    """User model - mirrors Prisma User model."""
    __tablename__ = "User"

    id = Column(String, primary_key=True, default=generate_cuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    passwordHash = Column(String, nullable=False)
    createdAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000))
    updatedAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000), onupdate=lambda: int(time.time() * 1000))

    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")


class Session(Base):
    """Session model - mirrors Prisma Session model."""
    __tablename__ = "Session"

    id = Column(String, primary_key=True, default=generate_cuid)
    sessionToken = Column(String, unique=True, nullable=False, index=True)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    expires = Column(DateTime, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")


class Task(Base):
    """Task model - mirrors Prisma Task model.

    Note: The 'metadata' column is mapped to 'task_metadata' attribute in Python
    to avoid conflict with SQLAlchemy's reserved 'metadata' attribute.
    """
    __tablename__ = "Task"

    id = Column(String, primary_key=True, default=generate_cuid)
    userId = Column(String, ForeignKey("User.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    command = Column(String, nullable=False)
    args = Column(String, nullable=False)  # JSON string
    schedule = Column(String, nullable=False)  # Cron format
    enabled = Column(Boolean, nullable=False, default=True)
    priority = Column(String, nullable=False, default="default")
    notifyOn = Column(String, nullable=False, default="completion,error")
    task_metadata = Column("metadata", JSON, nullable=True)  # JSON object, mapped from 'metadata' column
    createdAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000))
    updatedAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000), onupdate=lambda: int(time.time() * 1000))
    lastRun = Column(Integer, nullable=True)
    nextRun = Column(Integer, nullable=True)

    # Relationships
    user = relationship("User", back_populates="tasks")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")


class TaskExecution(Base):
    """TaskExecution model - mirrors Prisma TaskExecution model."""
    __tablename__ = "TaskExecution"

    id = Column(String, primary_key=True, default=generate_cuid)
    taskId = Column(String, ForeignKey("Task.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False)  # "running", "completed", "failed"
    startedAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000))
    completedAt = Column(Integer, nullable=True)
    output = Column(Text, nullable=True)  # Use Text for potentially large output
    duration = Column(Integer, nullable=True)  # Milliseconds

    # Relationships
    task = relationship("Task", back_populates="executions")
    logs = relationship("ActivityLog", back_populates="execution", cascade="all, delete-orphan")


class ActivityLog(Base):
    """ActivityLog model - mirrors Prisma ActivityLog model.

    Note: The 'metadata' column is mapped to 'metadata_' attribute in Python
    to avoid conflict with SQLAlchemy's reserved 'metadata' attribute.
    """
    __tablename__ = "ActivityLog"

    id = Column(String, primary_key=True, default=generate_cuid)
    executionId = Column(String, ForeignKey("TaskExecution.id"), nullable=True)
    type = Column(String, nullable=False)  # "task_start", "task_complete", "notification_sent", "error"
    message = Column(String, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)  # JSON object, mapped from 'metadata' column
    createdAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000))

    # Relationships
    execution = relationship("TaskExecution", back_populates="logs")


class Notification(Base):
    """Notification model - mirrors Prisma Notification model."""
    __tablename__ = "Notification"

    id = Column(String, primary_key=True, default=generate_cuid)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    priority = Column(String, nullable=False, default="default")
    tags = Column(String, nullable=True)  # Comma-separated
    sentAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000))
    delivered = Column(Boolean, nullable=False, default=True)
    readAt = Column(Integer, nullable=True)


class AiMemory(Base):
    """AiMemory model - mirrors Prisma AiMemory model."""
    __tablename__ = "AiMemory"

    id = Column(String, primary_key=True, default=generate_cuid)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)  # JSON string
    category = Column(String, nullable=True)  # "preference", "context", "fact"
    createdAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000))
    updatedAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000), onupdate=lambda: int(time.time() * 1000))


class DigestSettings(Base):
    """DigestSettings model - mirrors Prisma DigestSettings model."""
    __tablename__ = "DigestSettings"

    id = Column(String, primary_key=True, default=generate_cuid)
    dailyEnabled = Column(Boolean, nullable=False, default=True)
    dailyTime = Column(String, nullable=False, default="20:00")  # "HH:MM" format (24-hour)
    weeklyEnabled = Column(Boolean, nullable=False, default=True)
    weeklyDay = Column(String, nullable=False, default="monday")  # lowercase day name
    weeklyTime = Column(String, nullable=False, default="09:00")  # "HH:MM" format (24-hour)
    recipientEmail = Column(String, nullable=False)
    createdAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000))
    updatedAt = Column(Integer, nullable=False, default=lambda: int(time.time() * 1000), onupdate=lambda: int(time.time() * 1000))


# ============================================================================
# Pydantic Schemas (API Layer)
# ============================================================================

class TaskBase(BaseModel):
    """Base schema for Task data."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    command: str = Field(..., min_length=1)
    args: str = Field(default="{}")  # JSON string
    schedule: str = Field(..., pattern=r"^(@(annually|yearly|monthly|weekly|daily|hourly|reboot))|(@every (\d+(ns|us|µs|ms|s|m|h))+)|((((\d+,)+\d+|(\d+(\/|-)\d+)|\d+|\*) ?){5,7})$")
    enabled: bool = True
    priority: str = Field(default="default", pattern=r"^(low|default|high|urgent)$")
    notifyOn: str = Field(default="completion,error")

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(TaskBase):
    """Schema for creating a new Task."""
    userId: str


class TaskUpdate(BaseModel):
    """Schema for updating an existing Task."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    command: Optional[str] = Field(None, min_length=1)
    args: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None
    priority: Optional[str] = Field(None, pattern=r"^(low|default|high|urgent)$")
    notifyOn: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(TaskBase):
    """Schema for Task responses."""
    id: str
    userId: str
    createdAt: datetime
    updatedAt: datetime
    lastRun: Optional[datetime] = None
    nextRun: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExecutionBase(BaseModel):
    """Base schema for TaskExecution data."""
    status: str = Field(..., pattern=r"^(running|completed|failed)$")
    output: Optional[str] = None
    duration: Optional[int] = None  # Milliseconds

    model_config = ConfigDict(from_attributes=True)


class ExecutionCreate(ExecutionBase):
    """Schema for creating a new TaskExecution."""
    taskId: str


class ExecutionUpdate(BaseModel):
    """Schema for updating an existing TaskExecution."""
    status: Optional[str] = Field(None, pattern=r"^(running|completed|failed)$")
    completedAt: Optional[datetime] = None
    output: Optional[str] = None
    duration: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ExecutionResponse(ExecutionBase):
    """Schema for TaskExecution responses."""
    id: str
    taskId: str
    startedAt: datetime
    completedAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ActivityLogResponse(BaseModel):
    """Schema for ActivityLog responses.

    Note: Uses 'metadata_' to match the SQLAlchemy model attribute name.
    """
    id: str
    executionId: Optional[str] = None
    type: str
    message: str
    metadata_: Optional[str] = Field(None, alias="metadata")  # Maps to 'metadata' in JSON
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class NotificationCreate(BaseModel):
    """Schema for creating a new Notification."""
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    priority: str = Field(default="default", pattern=r"^(low|default|high|urgent)$")
    tags: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(NotificationCreate):
    """Schema for Notification responses."""
    id: str
    sentAt: datetime
    delivered: bool
    readAt: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AiMemoryCreate(BaseModel):
    """Schema for creating a new AiMemory entry."""
    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)  # JSON string
    category: Optional[str] = Field(None, pattern=r"^(preference|context|fact)$")

    model_config = ConfigDict(from_attributes=True)


class AiMemoryUpdate(BaseModel):
    """Schema for updating an existing AiMemory entry."""
    value: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = Field(None, pattern=r"^(preference|context|fact)$")

    model_config = ConfigDict(from_attributes=True)


class AiMemoryResponse(AiMemoryCreate):
    """Schema for AiMemory responses."""
    id: str
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)


class DigestSettingsBase(BaseModel):
    """Base schema for DigestSettings data."""
    dailyEnabled: bool = True
    dailyTime: str = Field(default="20:00", pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    weeklyEnabled: bool = True
    weeklyDay: str = Field(default="monday", pattern=r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$")
    weeklyTime: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    recipientEmail: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    model_config = ConfigDict(from_attributes=True)


class DigestSettingsUpdate(BaseModel):
    """Schema for updating DigestSettings."""
    dailyEnabled: Optional[bool] = None
    dailyTime: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    weeklyEnabled: Optional[bool] = None
    weeklyDay: Optional[str] = Field(None, pattern=r"^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$")
    weeklyTime: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    recipientEmail: Optional[str] = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    model_config = ConfigDict(from_attributes=True)


class DigestSettingsResponse(DigestSettingsBase):
    """Schema for DigestSettings responses."""
    id: str
    createdAt: datetime
    updatedAt: datetime

    model_config = ConfigDict(from_attributes=True)
