"""Tests for database queries used in digest emails (TDD)."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database import get_db, SessionLocal, Base, engine
from models import User, Task, TaskExecution
from digest_queries import (
    get_daily_digest_data,
    get_weekly_summary_data
)


@pytest.fixture
def db() -> Session:
    """Create a test database session."""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up tables after test
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_tasks(db: Session):
    """Create sample tasks for testing."""
    # Create a user first (required for foreign key)
    user = User(
        id='user_1',
        email='test@example.com',
        name='Test User',
        passwordHash='$2b$12$dummy_hash',
        createdAt=datetime.now(),
        updatedAt=datetime.now()
    )
    db.add(user)
    db.commit()

    tasks = []

    # Task 1: Has recent executions
    task1 = Task(
        id='task_1',
        userId='user_1',
        name='Daily Backup',
        description='Backup database',
        command='backup',
        args='{}',
        schedule='0 3 * * *',
        enabled=1,  # Use integer for SQLite Boolean
        priority='default',
        notifyOn='completion,error',
        createdAt=datetime.now() - timedelta(days=30),
        updatedAt=datetime.now(),
        lastRun=datetime.now() - timedelta(hours=12),
        nextRun=datetime.now() + timedelta(hours=12)
    )
    db.add(task1)
    tasks.append(task1)

    # Task 2: Another active task
    task2 = Task(
        id='task_2',
        userId='user_1',
        name='Research Summary',
        description='Daily research',
        command='research',
        args='{}',
        schedule='0 8 * * *',
        enabled=1,  # Use integer for SQLite Boolean
        priority='high',
        notifyOn='completion',
        createdAt=datetime.now() - timedelta(days=20),
        updatedAt=datetime.now(),
        lastRun=datetime.now() - timedelta(hours=8),
        nextRun=datetime.now() + timedelta(hours=16)
    )
    db.add(task2)
    tasks.append(task2)

    # Task 3: Disabled task
    task3 = Task(
        id='task_3',
        userId='user_1',
        name='Disabled Task',
        description='Not running',
        command='nothing',
        args='{}',
        schedule='0 0 * * *',
        enabled=0,  # Use integer for SQLite Boolean
        priority='low',
        notifyOn='error',
        createdAt=datetime.now() - timedelta(days=10),
        updatedAt=datetime.now(),
        lastRun=None,
        nextRun=None
    )
    db.add(task3)
    tasks.append(task3)

    db.commit()
    return tasks


@pytest.fixture
def sample_executions(db: Session, sample_tasks):
    """Create sample task executions for testing."""
    executions = []
    now = datetime.now()

    # Last 24 hours - 3 successful, 1 failed
    # Successful execution 1 (task_1, 12 hours ago)
    exec1 = TaskExecution(
        id='exec_1',
        taskId='task_1',
        status='completed',
        startedAt=now - timedelta(hours=12),
        completedAt=now - timedelta(hours=12, minutes=-5),
        output='Backup completed',
        duration=5000  # 5 seconds
    )
    db.add(exec1)
    executions.append(exec1)

    # Successful execution 2 (task_2, 8 hours ago)
    exec2 = TaskExecution(
        id='exec_2',
        taskId='task_2',
        status='completed',
        startedAt=now - timedelta(hours=8),
        completedAt=now - timedelta(hours=8, minutes=-3),
        output='Research completed',
        duration=3000  # 3 seconds
    )
    db.add(exec2)
    executions.append(exec2)

    # Failed execution (task_1, 6 hours ago)
    exec3 = TaskExecution(
        id='exec_3',
        taskId='task_1',
        status='failed',
        startedAt=now - timedelta(hours=6),
        completedAt=now - timedelta(hours=6, minutes=-1),
        output='Error: Connection timeout',
        duration=1000  # 1 second
    )
    db.add(exec3)
    executions.append(exec3)

    # Successful execution 3 (task_2, 4 hours ago)
    exec4 = TaskExecution(
        id='exec_4',
        taskId='task_2',
        status='completed',
        startedAt=now - timedelta(hours=4),
        completedAt=now - timedelta(hours=4, minutes=-2),
        output='Research completed',
        duration=2000  # 2 seconds
    )
    db.add(exec4)
    executions.append(exec4)

    # Last 7 days (but not last 24h) - older executions
    # Successful execution from 3 days ago
    exec5 = TaskExecution(
        id='exec_5',
        taskId='task_1',
        status='completed',
        startedAt=now - timedelta(days=3),
        completedAt=now - timedelta(days=3, minutes=-5),
        output='Backup completed',
        duration=5000
    )
    db.add(exec5)
    executions.append(exec5)

    # Failed execution from 5 days ago
    exec6 = TaskExecution(
        id='exec_6',
        taskId='task_2',
        status='failed',
        startedAt=now - timedelta(days=5),
        completedAt=now - timedelta(days=5, minutes=-1),
        output='Error: Network issue',
        duration=1000
    )
    db.add(exec6)
    executions.append(exec6)

    # Very old execution (8 days ago, outside 7-day window)
    exec7 = TaskExecution(
        id='exec_7',
        taskId='task_1',
        status='completed',
        startedAt=now - timedelta(days=8),
        completedAt=now - timedelta(days=8, minutes=-5),
        output='Old backup',
        duration=5000
    )
    db.add(exec7)
    executions.append(exec7)

    db.commit()
    return executions


class TestDailyDigestQueries:
    """Test database queries for daily digest email."""

    def test_counts_total_tasks_in_last_24_hours(self, db, sample_tasks, sample_executions):
        """Test that daily digest counts all executions in last 24 hours."""
        result = get_daily_digest_data(db, datetime.now())

        # Should count 4 executions from last 24h
        assert result['total_tasks'] == 4

    def test_counts_successful_tasks_in_last_24_hours(self, db, sample_tasks, sample_executions):
        """Test that daily digest counts successful executions."""
        result = get_daily_digest_data(db, datetime.now())

        # Should count 3 successful executions from last 24h
        assert result['successful'] == 3

    def test_counts_failed_tasks_in_last_24_hours(self, db, sample_tasks, sample_executions):
        """Test that daily digest counts failed executions."""
        result = get_daily_digest_data(db, datetime.now())

        # Should count 1 failed execution from last 24h
        assert result['failed'] == 1

    def test_calculates_success_rate(self, db, sample_tasks, sample_executions):
        """Test that daily digest calculates correct success rate."""
        result = get_daily_digest_data(db, datetime.now())

        # 3 successful out of 4 total = 75%
        assert result['success_rate'] == 75

    def test_success_rate_zero_when_no_executions(self, db, sample_tasks):
        """Test that success rate is 0 when no executions exist."""
        # No executions fixture loaded
        result = get_daily_digest_data(db, datetime.now())

        assert result['total_tasks'] == 0
        assert result['successful'] == 0
        assert result['failed'] == 0
        assert result['success_rate'] == 0

    def test_gets_upcoming_tasks(self, db, sample_tasks, sample_executions):
        """Test that daily digest gets next 5 upcoming tasks."""
        result = get_daily_digest_data(db, datetime.now())

        # Should return 2 upcoming tasks (only enabled tasks)
        assert len(result['upcoming_tasks']) == 2

        # Should be sorted by nextRun (earliest first)
        assert result['upcoming_tasks'][0]['name'] == 'Daily Backup'
        assert result['upcoming_tasks'][1]['name'] == 'Research Summary'

        # Should have 'time' key for template
        assert 'time' in result['upcoming_tasks'][0]

    def test_upcoming_tasks_excludes_disabled(self, db, sample_tasks, sample_executions):
        """Test that upcoming tasks excludes disabled tasks."""
        result = get_daily_digest_data(db, datetime.now())

        # Should not include task_3 (disabled)
        task_names = [t['name'] for t in result['upcoming_tasks']]
        assert 'Disabled Task' not in task_names

    def test_handles_empty_database(self, db):
        """Test that query handles empty database gracefully."""
        result = get_daily_digest_data(db, datetime.now())

        assert result['total_tasks'] == 0
        assert result['successful'] == 0
        assert result['failed'] == 0
        assert result['success_rate'] == 0
        assert result['upcoming_tasks'] == []


class TestWeeklySummaryQueries:
    """Test database queries for weekly summary email."""

    def test_counts_total_executions_in_last_7_days(self, db, sample_tasks, sample_executions):
        """Test that weekly summary counts all executions in last 7 days."""
        result = get_weekly_summary_data(db, datetime.now() - timedelta(days=6))

        # Should count 6 executions from last 7 days (excludes 8-day-old execution)
        assert result['total_executions'] == 6

    def test_counts_successful_executions_in_last_7_days(self, db, sample_tasks, sample_executions):
        """Test that weekly summary counts successful executions."""
        result = get_weekly_summary_data(db, datetime.now() - timedelta(days=6))

        # Should count 4 successful executions from last 7 days
        assert result['success_count'] == 4

    def test_counts_failed_executions_in_last_7_days(self, db, sample_tasks, sample_executions):
        """Test that weekly summary counts failed executions."""
        result = get_weekly_summary_data(db, datetime.now() - timedelta(days=6))

        # Should count 2 failed executions from last 7 days
        assert result['failure_count'] == 2

    def test_identifies_top_failing_tasks(self, db, sample_tasks, sample_executions):
        """Test that weekly summary identifies tasks with most failures."""
        result = get_weekly_summary_data(db, datetime.now() - timedelta(days=6))

        # Should return up to 3 tasks with failures
        assert len(result['top_failures']) <= 3

        # Tasks should be sorted by failure count (descending)
        if len(result['top_failures']) > 0:
            # task_1 has 1 failure, task_2 has 1 failure in last 7 days
            assert result['top_failures'][0]['task'] in ['Daily Backup', 'Research Summary']
            assert result['top_failures'][0]['count'] >= 1

    def test_calculates_average_execution_duration(self, db, sample_tasks, sample_executions):
        """Test that weekly summary calculates average execution duration."""
        result = get_weekly_summary_data(db, datetime.now() - timedelta(days=6))

        # Average of (5000, 3000, 1000, 2000, 5000, 1000) = 2833ms
        assert 2800 <= result['avg_duration_ms'] <= 2900

    def test_handles_zero_duration(self, db, sample_tasks):
        """Test that average duration is 0 when no executions exist."""
        result = get_weekly_summary_data(db, datetime.now() - timedelta(days=6))

        assert result['avg_duration_ms'] == 0

    def test_handles_empty_database(self, db):
        """Test that query handles empty database gracefully."""
        result = get_weekly_summary_data(db, datetime.now() - timedelta(days=6))

        assert result['total_executions'] == 0
        assert result['success_count'] == 0
        assert result['failure_count'] == 0
        assert result['top_failures'] == []
        assert result['avg_duration_ms'] == 0
