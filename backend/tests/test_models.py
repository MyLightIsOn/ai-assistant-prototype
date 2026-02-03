"""
TDD tests for SQLAlchemy models.

These tests verify that all models are correctly defined and that relationships
and cascade deletes work as expected.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database import Base
from models import (
    User, Session as DBSession, Task, TaskExecution,
    ActivityLog, Notification, AiMemory
)


# Test database setup
@pytest.fixture(scope="function")
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a new database session for a test."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_user(db_session: Session):
    """Create a sample user for testing."""
    user = User(
        id="test-user-id",
        email="test@example.com",
        name="Test User",
        passwordHash="$2b$10$somehashedpassword",
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_task(db_session: Session, sample_user: User):
    """Create a sample task for testing."""
    task = Task(
        id="test-task-id",
        userId=sample_user.id,
        name="Test Task",
        description="A test task",
        command="research",
        args='{"topic": "AI"}',
        schedule="0 8 * * *",
        enabled=True,
        priority="default",
        notifyOn="completion,error",
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


@pytest.fixture
def sample_execution(db_session: Session, sample_task: Task):
    """Create a sample task execution for testing."""
    execution = TaskExecution(
        id="test-execution-id",
        taskId=sample_task.id,
        status="running",
        startedAt=datetime.utcnow()
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)
    return execution


# ============================================================================
# User Model Tests
# ============================================================================

def test_create_user(db_session: Session):
    """Test creating a user."""
    user = User(
        id="user-123",
        email="user@example.com",
        name="John Doe",
        passwordHash="hashedpassword123"
    )
    db_session.add(user)
    db_session.commit()

    # Verify user was created
    retrieved_user = db_session.query(User).filter_by(id="user-123").first()
    assert retrieved_user is not None
    assert retrieved_user.email == "user@example.com"
    assert retrieved_user.name == "John Doe"
    assert retrieved_user.passwordHash == "hashedpassword123"
    assert retrieved_user.createdAt is not None
    assert retrieved_user.updatedAt is not None


def test_user_email_unique_constraint(db_session: Session):
    """Test that email must be unique."""
    user1 = User(id="user-1", email="duplicate@example.com", passwordHash="hash1")
    user2 = User(id="user-2", email="duplicate@example.com", passwordHash="hash2")

    db_session.add(user1)
    db_session.commit()

    db_session.add(user2)
    with pytest.raises(Exception):  # SQLite will raise IntegrityError
        db_session.commit()


# ============================================================================
# Session Model Tests
# ============================================================================

def test_create_session(db_session: Session, sample_user: User):
    """Test creating a session."""
    session = DBSession(
        id="session-123",
        sessionToken="token-abc-xyz",
        userId=sample_user.id,
        expires=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(session)
    db_session.commit()

    # Verify session was created
    retrieved_session = db_session.query(DBSession).filter_by(id="session-123").first()
    assert retrieved_session is not None
    assert retrieved_session.sessionToken == "token-abc-xyz"
    assert retrieved_session.userId == sample_user.id


def test_session_cascade_delete(db_session: Session, sample_user: User):
    """Test that sessions are deleted when user is deleted."""
    session = DBSession(
        id="session-123",
        sessionToken="token-abc",
        userId=sample_user.id,
        expires=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(session)
    db_session.commit()

    # Delete user
    db_session.delete(sample_user)
    db_session.commit()

    # Verify session was also deleted
    retrieved_session = db_session.query(DBSession).filter_by(id="session-123").first()
    assert retrieved_session is None


# ============================================================================
# Task Model Tests
# ============================================================================

def test_create_task(db_session: Session, sample_user: User):
    """Test creating a task."""
    task = Task(
        id="task-123",
        userId=sample_user.id,
        name="Daily Backup",
        description="Backup important files",
        command="backup",
        args='{"path": "/data"}',
        schedule="0 2 * * *",
        enabled=True,
        priority="high",
        notifyOn="error"
    )
    db_session.add(task)
    db_session.commit()

    # Verify task was created
    retrieved_task = db_session.query(Task).filter_by(id="task-123").first()
    assert retrieved_task is not None
    assert retrieved_task.name == "Daily Backup"
    assert retrieved_task.command == "backup"
    assert retrieved_task.schedule == "0 2 * * *"
    assert retrieved_task.priority == "high"


def test_task_default_values(db_session: Session, sample_user: User):
    """Test that task default values are set correctly."""
    task = Task(
        id="task-default",
        userId=sample_user.id,
        name="Test Task",
        command="test",
        args="{}",
        schedule="* * * * *"
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Verify defaults
    assert task.enabled is True
    assert task.priority == "default"
    assert task.notifyOn == "completion,error"


def test_task_cascade_delete(db_session: Session, sample_user: User):
    """Test that tasks are deleted when user is deleted."""
    task = Task(
        id="task-123",
        userId=sample_user.id,
        name="Test Task",
        command="test",
        args="{}",
        schedule="* * * * *"
    )
    db_session.add(task)
    db_session.commit()

    # Delete user
    db_session.delete(sample_user)
    db_session.commit()

    # Verify task was also deleted
    retrieved_task = db_session.query(Task).filter_by(id="task-123").first()
    assert retrieved_task is None


# ============================================================================
# TaskExecution Model Tests
# ============================================================================

def test_create_task_execution(db_session: Session, sample_task: Task):
    """Test creating a task execution."""
    execution = TaskExecution(
        id="exec-123",
        taskId=sample_task.id,
        status="running",
        startedAt=datetime.utcnow()
    )
    db_session.add(execution)
    db_session.commit()

    # Verify execution was created
    retrieved_execution = db_session.query(TaskExecution).filter_by(id="exec-123").first()
    assert retrieved_execution is not None
    assert retrieved_execution.status == "running"
    assert retrieved_execution.taskId == sample_task.id


def test_task_execution_complete(db_session: Session, sample_task: Task):
    """Test completing a task execution."""
    start_time = datetime.utcnow()
    execution = TaskExecution(
        id="exec-123",
        taskId=sample_task.id,
        status="running",
        startedAt=start_time
    )
    db_session.add(execution)
    db_session.commit()

    # Complete the execution
    complete_time = datetime.utcnow()
    execution.status = "completed"
    execution.completedAt = complete_time
    execution.output = "Task completed successfully"
    execution.duration = int((complete_time - start_time).total_seconds() * 1000)
    db_session.commit()

    # Verify updates
    retrieved_execution = db_session.query(TaskExecution).filter_by(id="exec-123").first()
    assert retrieved_execution.status == "completed"
    assert retrieved_execution.completedAt is not None
    assert retrieved_execution.output == "Task completed successfully"
    assert retrieved_execution.duration >= 0


def test_task_execution_cascade_delete(db_session: Session, sample_task: Task):
    """Test that executions are deleted when task is deleted."""
    execution = TaskExecution(
        id="exec-123",
        taskId=sample_task.id,
        status="completed",
        startedAt=datetime.utcnow()
    )
    db_session.add(execution)
    db_session.commit()

    # Delete task
    db_session.delete(sample_task)
    db_session.commit()

    # Verify execution was also deleted
    retrieved_execution = db_session.query(TaskExecution).filter_by(id="exec-123").first()
    assert retrieved_execution is None


# ============================================================================
# ActivityLog Model Tests
# ============================================================================

def test_create_activity_log(db_session: Session, sample_execution: TaskExecution):
    """Test creating an activity log."""
    log = ActivityLog(
        id="log-123",
        executionId=sample_execution.id,
        type="task_start",
        message="Task started successfully",
        metadata_='{"details": "additional info"}'
    )
    db_session.add(log)
    db_session.commit()

    # Verify log was created
    retrieved_log = db_session.query(ActivityLog).filter_by(id="log-123").first()
    assert retrieved_log is not None
    assert retrieved_log.type == "task_start"
    assert retrieved_log.message == "Task started successfully"


def test_activity_log_without_execution(db_session: Session):
    """Test creating an activity log without an execution."""
    log = ActivityLog(
        id="log-standalone",
        type="notification_sent",
        message="Notification sent to user"
    )
    db_session.add(log)
    db_session.commit()

    # Verify log was created
    retrieved_log = db_session.query(ActivityLog).filter_by(id="log-standalone").first()
    assert retrieved_log is not None
    assert retrieved_log.executionId is None


def test_activity_log_cascade_delete(db_session: Session, sample_execution: TaskExecution):
    """Test that activity logs are deleted when execution is deleted."""
    log = ActivityLog(
        id="log-123",
        executionId=sample_execution.id,
        type="task_complete",
        message="Task completed"
    )
    db_session.add(log)
    db_session.commit()

    # Delete execution
    db_session.delete(sample_execution)
    db_session.commit()

    # Verify log was also deleted
    retrieved_log = db_session.query(ActivityLog).filter_by(id="log-123").first()
    assert retrieved_log is None


# ============================================================================
# Notification Model Tests
# ============================================================================

def test_create_notification(db_session: Session):
    """Test creating a notification."""
    notification = Notification(
        id="notif-123",
        title="Task Completed",
        message="Your daily backup task has completed successfully",
        priority="default",
        tags="backup,success"
    )
    db_session.add(notification)
    db_session.commit()

    # Verify notification was created
    retrieved_notif = db_session.query(Notification).filter_by(id="notif-123").first()
    assert retrieved_notif is not None
    assert retrieved_notif.title == "Task Completed"
    assert retrieved_notif.priority == "default"
    assert retrieved_notif.delivered is True


def test_notification_read_status(db_session: Session):
    """Test marking a notification as read."""
    notification = Notification(
        id="notif-123",
        title="Test",
        message="Test notification"
    )
    db_session.add(notification)
    db_session.commit()

    # Mark as read
    read_time = datetime.utcnow()
    notification.readAt = read_time
    db_session.commit()

    # Verify read status
    retrieved_notif = db_session.query(Notification).filter_by(id="notif-123").first()
    assert retrieved_notif.readAt is not None


# ============================================================================
# AiMemory Model Tests
# ============================================================================

def test_create_ai_memory(db_session: Session):
    """Test creating an AI memory entry."""
    memory = AiMemory(
        id="mem-123",
        key="user_preference_theme",
        value='{"theme": "dark"}',
        category="preference"
    )
    db_session.add(memory)
    db_session.commit()

    # Verify memory was created
    retrieved_memory = db_session.query(AiMemory).filter_by(id="mem-123").first()
    assert retrieved_memory is not None
    assert retrieved_memory.key == "user_preference_theme"
    assert retrieved_memory.category == "preference"


def test_ai_memory_unique_key_constraint(db_session: Session):
    """Test that memory key must be unique."""
    memory1 = AiMemory(id="mem-1", key="duplicate_key", value="value1")
    memory2 = AiMemory(id="mem-2", key="duplicate_key", value="value2")

    db_session.add(memory1)
    db_session.commit()

    db_session.add(memory2)
    with pytest.raises(Exception):  # SQLite will raise IntegrityError
        db_session.commit()


def test_ai_memory_update(db_session: Session):
    """Test updating an AI memory entry."""
    memory = AiMemory(
        id="mem-123",
        key="last_research_topic",
        value='{"topic": "AI"}',
        category="context"
    )
    db_session.add(memory)
    db_session.commit()

    # Update memory
    original_updated_at = memory.updatedAt
    memory.value = '{"topic": "Machine Learning"}'
    db_session.commit()
    db_session.refresh(memory)

    # Verify update
    retrieved_memory = db_session.query(AiMemory).filter_by(id="mem-123").first()
    assert retrieved_memory.value == '{"topic": "Machine Learning"}'
    assert retrieved_memory.updatedAt >= original_updated_at


# ============================================================================
# Relationship Tests
# ============================================================================

def test_user_tasks_relationship(db_session: Session, sample_user: User):
    """Test the relationship between User and Tasks."""
    # Create multiple tasks for the user
    task1 = Task(
        id="task-1",
        userId=sample_user.id,
        name="Task 1",
        command="test",
        args="{}",
        schedule="* * * * *"
    )
    task2 = Task(
        id="task-2",
        userId=sample_user.id,
        name="Task 2",
        command="test",
        args="{}",
        schedule="* * * * *"
    )
    db_session.add_all([task1, task2])
    db_session.commit()

    # Verify relationship
    db_session.refresh(sample_user)
    assert len(sample_user.tasks) == 2
    assert task1 in sample_user.tasks
    assert task2 in sample_user.tasks


def test_task_executions_relationship(db_session: Session, sample_task: Task):
    """Test the relationship between Task and TaskExecutions."""
    # Create multiple executions for the task
    exec1 = TaskExecution(
        id="exec-1",
        taskId=sample_task.id,
        status="completed",
        startedAt=datetime.utcnow()
    )
    exec2 = TaskExecution(
        id="exec-2",
        taskId=sample_task.id,
        status="completed",
        startedAt=datetime.utcnow()
    )
    db_session.add_all([exec1, exec2])
    db_session.commit()

    # Verify relationship
    db_session.refresh(sample_task)
    assert len(sample_task.executions) == 2


def test_execution_logs_relationship(db_session: Session, sample_execution: TaskExecution):
    """Test the relationship between TaskExecution and ActivityLogs."""
    # Create multiple logs for the execution
    log1 = ActivityLog(
        id="log-1",
        executionId=sample_execution.id,
        type="task_start",
        message="Started"
    )
    log2 = ActivityLog(
        id="log-2",
        executionId=sample_execution.id,
        type="task_complete",
        message="Completed"
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    # Verify relationship
    db_session.refresh(sample_execution)
    assert len(sample_execution.logs) == 2


def test_full_cascade_delete_chain(db_session: Session, sample_user: User):
    """Test cascade delete through the entire chain: User -> Task -> Execution -> Log."""
    # Create a full chain
    task = Task(
        id="task-cascade",
        userId=sample_user.id,
        name="Cascade Test",
        command="test",
        args="{}",
        schedule="* * * * *"
    )
    db_session.add(task)
    db_session.commit()

    execution = TaskExecution(
        id="exec-cascade",
        taskId=task.id,
        status="completed",
        startedAt=datetime.utcnow()
    )
    db_session.add(execution)
    db_session.commit()

    log = ActivityLog(
        id="log-cascade",
        executionId=execution.id,
        type="test",
        message="Test log"
    )
    db_session.add(log)
    db_session.commit()

    # Delete the user (should cascade delete everything)
    db_session.delete(sample_user)
    db_session.commit()

    # Verify everything was deleted
    assert db_session.query(Task).filter_by(id="task-cascade").first() is None
    assert db_session.query(TaskExecution).filter_by(id="exec-cascade").first() is None
    assert db_session.query(ActivityLog).filter_by(id="log-cascade").first() is None
