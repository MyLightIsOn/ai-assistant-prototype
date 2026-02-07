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
        createdAt=int(datetime.now().timestamp() * 1000),
        updatedAt=int(datetime.now().timestamp() * 1000)
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
        createdAt=int((datetime.now() - timedelta(days=30)).timestamp() * 1000),
        updatedAt=int(datetime.now().timestamp() * 1000),
        lastRun=int((datetime.now() - timedelta(hours=12)).timestamp() * 1000),
        nextRun=int((datetime.now() + timedelta(hours=12)).timestamp() * 1000)
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
        createdAt=int((datetime.now() - timedelta(days=20)).timestamp() * 1000),
        updatedAt=int(datetime.now().timestamp() * 1000),
        lastRun=int((datetime.now() - timedelta(hours=8)).timestamp() * 1000),
        nextRun=int((datetime.now() + timedelta(hours=16)).timestamp() * 1000)
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
        createdAt=int((datetime.now() - timedelta(days=10)).timestamp() * 1000),
        updatedAt=int(datetime.now().timestamp() * 1000),
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
        startedAt=int((now - timedelta(hours=12)).timestamp() * 1000),
        completedAt=int((now - timedelta(hours=12, minutes=-5)).timestamp() * 1000),
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
        startedAt=int((now - timedelta(hours=8)).timestamp() * 1000),
        completedAt=int((now - timedelta(hours=8, minutes=-3)).timestamp() * 1000),
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
        startedAt=int((now - timedelta(hours=6)).timestamp() * 1000),
        completedAt=int((now - timedelta(hours=6, minutes=-1)).timestamp() * 1000),
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
        startedAt=int((now - timedelta(hours=4)).timestamp() * 1000),
        completedAt=int((now - timedelta(hours=4, minutes=-2)).timestamp() * 1000),
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
        startedAt=int((now - timedelta(days=3)).timestamp() * 1000),
        completedAt=int((now - timedelta(days=3, minutes=-5)).timestamp() * 1000),
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
        startedAt=int((now - timedelta(days=5)).timestamp() * 1000),
        completedAt=int((now - timedelta(days=5, minutes=-1)).timestamp() * 1000),
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
        startedAt=int((now - timedelta(days=8)).timestamp() * 1000),
        completedAt=int((now - timedelta(days=8, minutes=-5)).timestamp() * 1000),
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


class TestSuccessRateQueries:
    """Test database queries for success rate calculation."""

    def test_empty_database_returns_zero_success_rate(self, db):
        """Test that success rate is 0 when no executions exist."""
        from digest_queries import get_success_rate

        result = get_success_rate(db, days=7)

        assert result['success_rate'] == 0.0
        assert result['total_executions'] == 0
        assert result['successful'] == 0
        assert result['failed'] == 0
        assert result['period_days'] == 7

    def test_100_percent_success_rate_all_completed(self, db, sample_tasks):
        """Test that success rate is 100% when all executions completed."""
        from digest_queries import get_success_rate
        now = datetime.now()

        # Create 5 successful executions in last 7 days
        for i in range(5):
            exec = TaskExecution(
                id=f'exec_success_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(days=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=i, minutes=-5)).timestamp() * 1000),
                output='Success',
                duration=5000
            )
            db.add(exec)
        db.commit()

        result = get_success_rate(db, days=7)

        assert result['success_rate'] == 100.0
        assert result['total_executions'] == 5
        assert result['successful'] == 5
        assert result['failed'] == 0

    def test_0_percent_success_rate_all_failed(self, db, sample_tasks):
        """Test that success rate is 0% when all executions failed."""
        from digest_queries import get_success_rate
        now = datetime.now()

        # Create 3 failed executions in last 7 days
        for i in range(3):
            exec = TaskExecution(
                id=f'exec_fail_{i}',
                taskId='task_1',
                status='failed',
                startedAt=int((now - timedelta(days=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=i, minutes=-1)).timestamp() * 1000),
                output='Error',
                duration=1000
            )
            db.add(exec)
        db.commit()

        result = get_success_rate(db, days=7)

        assert result['success_rate'] == 0.0
        assert result['total_executions'] == 3
        assert result['successful'] == 0
        assert result['failed'] == 3

    def test_mixed_results_calculate_correctly(self, db, sample_tasks):
        """Test that success rate calculates correctly with mixed results."""
        from digest_queries import get_success_rate
        now = datetime.now()

        # Create 7 successful and 3 failed executions (70% success rate)
        for i in range(7):
            exec = TaskExecution(
                id=f'exec_success_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(hours=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(hours=i, minutes=-5)).timestamp() * 1000),
                output='Success',
                duration=5000
            )
            db.add(exec)

        for i in range(3):
            exec = TaskExecution(
                id=f'exec_fail_{i}',
                taskId='task_2',
                status='failed',
                startedAt=int((now - timedelta(hours=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(hours=i, minutes=-1)).timestamp() * 1000),
                output='Error',
                duration=1000
            )
            db.add(exec)
        db.commit()

        result = get_success_rate(db, days=7)

        assert result['success_rate'] == 70.0
        assert result['total_executions'] == 10
        assert result['successful'] == 7
        assert result['failed'] == 3

    def test_time_window_filters_correctly(self, db, sample_tasks):
        """Test that time window filters correctly (only last N days)."""
        from digest_queries import get_success_rate
        now = datetime.now()

        # Create 3 executions within last 7 days
        for i in range(3):
            exec = TaskExecution(
                id=f'exec_recent_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(days=i+1)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=i+1, minutes=-5)).timestamp() * 1000),
                output='Success',
                duration=5000
            )
            db.add(exec)

        # Create 2 executions outside 7-day window (8 and 10 days ago)
        for i in [8, 10]:
            exec = TaskExecution(
                id=f'exec_old_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(days=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=i, minutes=-5)).timestamp() * 1000),
                output='Old success',
                duration=5000
            )
            db.add(exec)
        db.commit()

        result = get_success_rate(db, days=7)

        # Should only count the 3 recent executions
        assert result['total_executions'] == 3
        assert result['successful'] == 3
        assert result['failed'] == 0

    def test_division_by_zero_handling(self, db, sample_tasks):
        """Test that function handles division by zero gracefully."""
        from digest_queries import get_success_rate

        # No executions in database
        result = get_success_rate(db, days=7)

        # Should return 0, not raise an exception
        assert result['success_rate'] == 0.0
        assert result['total_executions'] == 0


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


class TestExecutionTrendsQueries:
    """Test database queries for execution trends chart."""

    def test_empty_database_returns_empty_trend_data(self, db):
        """Test that empty database returns 7 days of zero counts."""
        from digest_queries import get_execution_trends

        result = get_execution_trends(db, days=7)

        # Should return 7 days of data
        assert len(result) == 7

        # All days should have zero counts
        for day_data in result:
            assert day_data['successful'] == 0
            assert day_data['failed'] == 0
            assert day_data['total'] == 0
            assert 'date' in day_data

    def test_single_day_with_executions_returns_correct_counts(self, db, sample_tasks):
        """Test that a single day with executions returns correct counts."""
        from digest_queries import get_execution_trends
        now = datetime.now()

        # Create 3 successful and 2 failed executions today
        for i in range(3):
            exec = TaskExecution(
                id=f'exec_success_today_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(hours=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(hours=i, minutes=-5)).timestamp() * 1000),
                output='Success',
                duration=5000
            )
            db.add(exec)

        for i in range(2):
            exec = TaskExecution(
                id=f'exec_fail_today_{i}',
                taskId='task_1',
                status='failed',
                startedAt=int((now - timedelta(hours=i+3)).timestamp() * 1000),
                completedAt=int((now - timedelta(hours=i+3, minutes=-1)).timestamp() * 1000),
                output='Error',
                duration=1000
            )
            db.add(exec)
        db.commit()

        result = get_execution_trends(db, days=7)

        # Find today's data
        today_str = now.strftime('%Y-%m-%d')
        today_data = next((d for d in result if d['date'] == today_str), None)

        assert today_data is not None
        assert today_data['successful'] == 3
        assert today_data['failed'] == 2
        assert today_data['total'] == 5

    def test_multiple_days_aggregate_correctly(self, db, sample_tasks):
        """Test that multiple days aggregate correctly."""
        from digest_queries import get_execution_trends
        now = datetime.now()

        # Create executions across 3 different days
        # Day 0 (today): 2 successful, 1 failed
        for i in range(2):
            exec = TaskExecution(
                id=f'exec_day0_success_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(hours=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(hours=i, minutes=-5)).timestamp() * 1000),
                output='Success',
                duration=5000
            )
            db.add(exec)

        exec = TaskExecution(
            id='exec_day0_fail',
            taskId='task_1',
            status='failed',
            startedAt=int((now - timedelta(hours=2)).timestamp() * 1000),
            completedAt=int((now - timedelta(hours=2, minutes=-1)).timestamp() * 1000),
            output='Error',
            duration=1000
        )
        db.add(exec)

        # Day 2: 1 successful, 0 failed
        exec = TaskExecution(
            id='exec_day2_success',
            taskId='task_1',
            status='completed',
            startedAt=int((now - timedelta(days=2, hours=12)).timestamp() * 1000),
            completedAt=int((now - timedelta(days=2, hours=12, minutes=-5)).timestamp() * 1000),
            output='Success',
            duration=5000
        )
        db.add(exec)

        # Day 4: 0 successful, 2 failed
        for i in range(2):
            exec = TaskExecution(
                id=f'exec_day4_fail_{i}',
                taskId='task_1',
                status='failed',
                startedAt=int((now - timedelta(days=4, hours=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=4, hours=i, minutes=-1)).timestamp() * 1000),
                output='Error',
                duration=1000
            )
            db.add(exec)
        db.commit()

        result = get_execution_trends(db, days=7)

        # Check day 0 (today)
        day0_str = now.strftime('%Y-%m-%d')
        day0_data = next((d for d in result if d['date'] == day0_str), None)
        assert day0_data['successful'] == 2
        assert day0_data['failed'] == 1
        assert day0_data['total'] == 3

        # Check day 2 (use the actual execution time to get correct date)
        day2_execution_time = now - timedelta(days=2, hours=12)
        day2_str = day2_execution_time.strftime('%Y-%m-%d')
        day2_data = next((d for d in result if d['date'] == day2_str), None)
        assert day2_data['successful'] == 1
        assert day2_data['failed'] == 0
        assert day2_data['total'] == 1

        # Check day 4 (use the actual execution time to get correct date)
        day4_execution_time = now - timedelta(days=4, hours=0)
        day4_str = day4_execution_time.strftime('%Y-%m-%d')
        day4_data = next((d for d in result if d['date'] == day4_str), None)
        assert day4_data['successful'] == 0
        assert day4_data['failed'] == 2
        assert day4_data['total'] == 2

    def test_missing_dates_filled_with_zeros(self, db, sample_tasks):
        """Test that missing dates are filled with zero counts."""
        from digest_queries import get_execution_trends
        now = datetime.now()

        # Create execution only on day 0 (today)
        exec = TaskExecution(
            id='exec_today',
            taskId='task_1',
            status='completed',
            startedAt=int(now.timestamp() * 1000),
            completedAt=now + timedelta(minutes=5),
            output='Success',
            duration=5000
        )
        db.add(exec)
        db.commit()

        result = get_execution_trends(db, days=7)

        # Should have 7 days of data
        assert len(result) == 7

        # Find days with no executions (should have zeros)
        yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_data = next((d for d in result if d['date'] == yesterday_str), None)

        assert yesterday_data is not None
        assert yesterday_data['successful'] == 0
        assert yesterday_data['failed'] == 0
        assert yesterday_data['total'] == 0

    def test_date_range_filtering_works(self, db, sample_tasks):
        """Test that date range filtering works (last N days only)."""
        from digest_queries import get_execution_trends
        now = datetime.now()

        # Create executions within 7-day window
        for i in range(5):
            exec = TaskExecution(
                id=f'exec_recent_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(days=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=i, minutes=-5)).timestamp() * 1000),
                output='Success',
                duration=5000
            )
            db.add(exec)

        # Create executions outside 7-day window (8 and 10 days ago)
        for i in [8, 10]:
            exec = TaskExecution(
                id=f'exec_old_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(days=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=i, minutes=-5)).timestamp() * 1000),
                output='Old success',
                duration=5000
            )
            db.add(exec)
        db.commit()

        result = get_execution_trends(db, days=7)

        # Should return exactly 7 days
        assert len(result) == 7

        # All returned dates should be within last 7 days
        dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in result]
        oldest_date = min(dates)
        newest_date = max(dates)

        # Oldest date should be 6 days ago (7 days total including today)
        expected_oldest = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert oldest_date.date() == expected_oldest.date()

        # Newest date should be today
        assert newest_date.date() == now.date()

        # Should not include data from 8 or 10 days ago
        total_count = sum(d['total'] for d in result)
        assert total_count == 5  # Only the 5 recent executions

    def test_dates_returned_in_chronological_order(self, db, sample_tasks):
        """Test that dates are returned in chronological order (oldest first)."""
        from digest_queries import get_execution_trends
        now = datetime.now()

        # Create some executions
        for i in range(3):
            exec = TaskExecution(
                id=f'exec_{i}',
                taskId='task_1',
                status='completed',
                startedAt=int((now - timedelta(days=i)).timestamp() * 1000),
                completedAt=int((now - timedelta(days=i, minutes=-5)).timestamp() * 1000),
                output='Success',
                duration=5000
            )
            db.add(exec)
        db.commit()

        result = get_execution_trends(db, days=7)

        # Convert dates to datetime objects for comparison
        dates = [datetime.strptime(d['date'], '%Y-%m-%d') for d in result]

        # Check that dates are in ascending order (oldest first)
        for i in range(len(dates) - 1):
            assert dates[i] <= dates[i + 1], "Dates should be in chronological order"
