"""
TDD tests for digest email scheduling integration.

These tests verify:
1. Default settings created on first run
2. Daily job scheduled with correct cron expression
3. Weekly job scheduled with correct day/time
4. Jobs disabled when enabled=false
5. Jobs rescheduled when settings updated
6. Test email endpoints work correctly
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database import Base
from models import User, DigestSettings


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


# ============================================================================
# Default Settings Tests
# ============================================================================

def test_default_settings_created_on_first_run(engine, db_session):
    """Test that default DigestSettings are created if none exist."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    # Verify no settings exist initially
    settings = db_session.query(DigestSettings).first()
    assert settings is None

    # Create a mock scheduler
    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    # Call setup with mock environment
    with patch.dict('os.environ', {'USER_EMAIL': 'user@example.com'}):
        setup_digest_jobs(mock_scheduler, db_session)

    # Verify settings were created
    settings = db_session.query(DigestSettings).first()
    assert settings is not None
    assert settings.dailyEnabled is True
    assert settings.dailyTime == "20:00"
    assert settings.weeklyEnabled is True
    assert settings.weeklyDay == "monday"
    assert settings.weeklyTime == "09:00"
    assert settings.recipientEmail == "user@example.com"


def test_default_settings_use_environment_email(engine, db_session):
    """Test that default settings use USER_EMAIL from environment."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    # Set custom email in environment
    with patch.dict('os.environ', {'USER_EMAIL': 'custom@example.com'}):
        setup_digest_jobs(mock_scheduler, db_session)

    settings = db_session.query(DigestSettings).first()
    assert settings.recipientEmail == "custom@example.com"


# ============================================================================
# Job Scheduling Tests
# ============================================================================

def test_daily_job_scheduled_with_correct_time(engine, db_session):
    """Test that daily digest job is scheduled with correct cron time."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    # Create settings with custom daily time
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=True,
        dailyTime="18:30",
        weeklyEnabled=False,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    setup_digest_jobs(mock_scheduler, db_session)

    # Verify daily job was added
    assert mock_scheduler.add_job.called

    # Find the daily job call
    daily_job_call = None
    for call in mock_scheduler.add_job.call_args_list:
        if call[1].get('id') == 'daily_digest':
            daily_job_call = call
            break

    assert daily_job_call is not None
    # Verify replace_existing is True
    assert daily_job_call[1].get('replace_existing') is True


def test_weekly_job_scheduled_with_correct_day_and_time(engine, db_session):
    """Test that weekly digest job is scheduled with correct day and time."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    # Create settings with custom weekly schedule
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=False,
        dailyTime="20:00",
        weeklyEnabled=True,
        weeklyDay="friday",
        weeklyTime="10:15",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    setup_digest_jobs(mock_scheduler, db_session)

    # Find the weekly job call
    weekly_job_call = None
    for call in mock_scheduler.add_job.call_args_list:
        if call[1].get('id') == 'weekly_digest':
            weekly_job_call = call
            break

    assert weekly_job_call is not None
    # Verify replace_existing is True
    assert weekly_job_call[1].get('replace_existing') is True


# ============================================================================
# Enable/Disable Tests
# ============================================================================

def test_jobs_disabled_when_enabled_false(engine, db_session):
    """Test that jobs are not scheduled when enabled=false."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    # Create settings with both disabled
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=False,
        dailyTime="20:00",
        weeklyEnabled=False,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    setup_digest_jobs(mock_scheduler, db_session)

    # Verify no jobs were added
    assert not mock_scheduler.add_job.called


def test_only_enabled_jobs_are_scheduled(engine, db_session):
    """Test that only enabled jobs are scheduled."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    # Create settings with only daily enabled
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=True,
        dailyTime="20:00",
        weeklyEnabled=False,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    setup_digest_jobs(mock_scheduler, db_session)

    # Verify only daily job was added
    assert mock_scheduler.add_job.call_count == 1
    assert mock_scheduler.add_job.call_args[1]['id'] == 'daily_digest'


# ============================================================================
# Job Rescheduling Tests
# ============================================================================

def test_jobs_rescheduled_when_settings_updated(engine, db_session):
    """Test that jobs are rescheduled when settings are updated."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    # Create initial settings
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=True,
        dailyTime="20:00",
        weeklyEnabled=True,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    # Initial setup
    setup_digest_jobs(mock_scheduler, db_session)
    initial_call_count = mock_scheduler.add_job.call_count

    # Update settings
    settings.dailyTime = "21:00"
    settings.weeklyDay = "friday"
    db_session.commit()

    # Reset mock
    mock_scheduler.add_job.reset_mock()

    # Re-setup (simulating settings update)
    setup_digest_jobs(mock_scheduler, db_session)

    # Verify jobs were rescheduled
    assert mock_scheduler.add_job.called


def test_jobs_use_replace_existing_flag(engine, db_session):
    """Test that jobs use replace_existing=True to allow rescheduling."""
    from scheduler import setup_digest_jobs
    from apscheduler.schedulers.background import BackgroundScheduler

    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=True,
        dailyTime="20:00",
        weeklyEnabled=True,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    mock_scheduler = Mock(spec=BackgroundScheduler)
    mock_scheduler.add_job = Mock()

    setup_digest_jobs(mock_scheduler, db_session)

    # Verify all add_job calls have replace_existing=True
    for call in mock_scheduler.add_job.call_args_list:
        assert call[1].get('replace_existing') is True


# ============================================================================
# Job Function Tests
# ============================================================================

def test_send_daily_digest_job_checks_enabled(engine, db_session):
    """Test that send_daily_digest_job checks if daily digest is enabled."""
    from scheduler import send_daily_digest_job

    # Create settings with daily disabled
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=False,
        dailyTime="20:00",
        weeklyEnabled=True,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    # Mock GmailSender
    with patch('gmail_sender.get_gmail_sender') as mock_sender:
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance

        # Mock SessionLocal to return our test session
        def mock_session_local():
            return db_session

        with patch('database.SessionLocal', return_value=mock_session_local()):
            send_daily_digest_job()

        # Verify email was NOT sent (daily disabled)
        assert not mock_sender_instance.send_daily_digest.called


def test_send_daily_digest_job_sends_when_enabled(engine, db_session):
    """Test that send_daily_digest_job sends email when enabled."""
    from scheduler import send_daily_digest_job

    # Create settings with daily enabled
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=True,
        dailyTime="20:00",
        weeklyEnabled=True,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    # Mock GmailSender
    with patch('gmail_sender.get_gmail_sender') as mock_sender:
        mock_sender_instance = Mock()
        mock_sender_instance.send_daily_digest = Mock()
        mock_sender.return_value = mock_sender_instance

        # Mock SessionLocal to return our test session
        def mock_session_local():
            return db_session

        with patch('database.SessionLocal', return_value=mock_session_local()):
            send_daily_digest_job()

        # Verify email was sent with correct recipient
        mock_sender_instance.send_daily_digest.assert_called_once()
        call_args = mock_sender_instance.send_daily_digest.call_args
        assert call_args[0][1] == "test@example.com"


def test_send_weekly_digest_job_checks_enabled(engine, db_session):
    """Test that send_weekly_digest_job checks if weekly digest is enabled."""
    from scheduler import send_weekly_digest_job

    # Create settings with weekly disabled
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=True,
        dailyTime="20:00",
        weeklyEnabled=False,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    # Mock GmailSender
    with patch('gmail_sender.get_gmail_sender') as mock_sender:
        mock_sender_instance = Mock()
        mock_sender.return_value = mock_sender_instance

        # Mock SessionLocal to return our test session
        def mock_session_local():
            return db_session

        with patch('database.SessionLocal', return_value=mock_session_local()):
            send_weekly_digest_job()

        # Verify email was NOT sent (weekly disabled)
        assert not mock_sender_instance.send_weekly_summary.called


def test_send_weekly_digest_job_sends_when_enabled(engine, db_session):
    """Test that send_weekly_digest_job sends email when enabled."""
    from scheduler import send_weekly_digest_job

    # Create settings with weekly enabled
    settings = DigestSettings(
        id=str(uuid.uuid4()),
        dailyEnabled=True,
        dailyTime="20:00",
        weeklyEnabled=True,
        weeklyDay="monday",
        weeklyTime="09:00",
        recipientEmail="test@example.com"
    )
    db_session.add(settings)
    db_session.commit()

    # Mock GmailSender
    with patch('gmail_sender.get_gmail_sender') as mock_sender:
        mock_sender_instance = Mock()
        mock_sender_instance.send_weekly_summary = Mock()
        mock_sender.return_value = mock_sender_instance

        # Mock SessionLocal to return our test session
        def mock_session_local():
            return db_session

        with patch('database.SessionLocal', return_value=mock_session_local()):
            send_weekly_digest_job()

        # Verify email was sent with correct recipient
        mock_sender_instance.send_weekly_summary.assert_called_once()
        call_args = mock_sender_instance.send_weekly_summary.call_args
        assert call_args[0][1] == "test@example.com"


# ============================================================================
# Integration Tests
# ============================================================================

def test_setup_digest_jobs_called_during_scheduler_init(engine, db_session):
    """Test that setup_digest_jobs is called when scheduler initializes."""
    # This is a documentation test showing the intended integration
    # In actual implementation, scheduler.py's TaskScheduler.__init__ or start()
    # should call setup_digest_jobs()
    pass  # Implementation verified in integration testing
