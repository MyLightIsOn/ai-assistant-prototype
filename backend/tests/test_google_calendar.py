"""Tests for Google Calendar sync service."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from google_calendar import CalendarSync, get_calendar_sync


@pytest.fixture
def mock_calendar_service():
    """Mock Calendar API service."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def calendar_sync(mock_calendar_service):
    """Create CalendarSync instance with mocked service."""
    with patch('google_calendar.CalendarSync._get_calendar_service', return_value=mock_calendar_service):
        return CalendarSync()


@pytest.fixture
def sample_task():
    """Create sample task for testing."""
    task = Mock()
    task.id = 'task_123'
    task.name = 'Daily Backup'
    task.description = 'Backup database to Drive'
    task.command = 'backup'
    task.args = '{}'
    task.priority = 'default'
    task.nextRun = datetime(2026, 2, 5, 3, 0, 0)
    task.schedule = '0 3 * * *'
    task.metadata = '{}'
    return task


def test_sync_task_creates_calendar_event(calendar_sync, mock_calendar_service, sample_task):
    """Test sync_task_to_calendar creates new event."""
    mock_calendar_service.events().insert().execute.return_value = {
        'id': 'event_12345'
    }

    event_id = calendar_sync.sync_task_to_calendar(sample_task)

    assert event_id == 'event_12345'
    assert mock_calendar_service.events().insert.called

    # Verify event structure
    call_args = mock_calendar_service.events().insert.call_args
    event_data = call_args[1]['body']

    assert event_data['summary'] == 'Daily Backup'
    assert 'Backup database' in event_data['description']
    assert event_data['extendedProperties']['private']['taskId'] == 'task_123'
    assert event_data['extendedProperties']['private']['source'] == 'ai-assistant'


def test_sync_task_updates_existing_event(calendar_sync, mock_calendar_service, sample_task):
    """Test sync_task_to_calendar updates existing event."""
    # Task already has calendar event ID
    sample_task.task_metadata = {'calendarEventId': 'event_12345'}

    mock_calendar_service.events().update().execute.return_value = {
        'id': 'event_12345'
    }

    event_id = calendar_sync.sync_task_to_calendar(sample_task)

    assert event_id == 'event_12345'
    assert mock_calendar_service.events().update.called
    assert not mock_calendar_service.events().insert.called


def test_sync_task_sets_color_by_priority(calendar_sync, mock_calendar_service, sample_task):
    """Test event color matches task priority."""
    test_cases = [
        ('low', '1'),      # Lavender
        ('default', '10'), # Green
        ('high', '6'),     # Orange
        ('urgent', '11')   # Red
    ]

    for priority, expected_color in test_cases:
        sample_task.priority = priority

        mock_calendar_service.events().insert().execute.return_value = {
            'id': f'event_{priority}'
        }

        calendar_sync.sync_task_to_calendar(sample_task)

        call_args = mock_calendar_service.events().insert.call_args
        event_data = call_args[1]['body']
        assert event_data['colorId'] == expected_color


def test_delete_calendar_event(calendar_sync, mock_calendar_service, sample_task):
    """Test delete_calendar_event removes event."""
    import json
    sample_task.task_metadata = {'calendarEventId': 'event_12345'}

    calendar_sync.delete_calendar_event(sample_task)

    assert mock_calendar_service.events().delete.called
    call_args = mock_calendar_service.events().delete.call_args
    assert call_args[1]['eventId'] == 'event_12345'


def test_get_event_retrieves_from_api(calendar_sync, mock_calendar_service):
    """Test get_event fetches event from Calendar API."""
    mock_calendar_service.events().get().execute.return_value = {
        'id': 'event_12345',
        'summary': 'Test Event'
    }

    event = calendar_sync.get_event('event_12345')

    assert event['id'] == 'event_12345'
    assert event['summary'] == 'Test Event'


def test_singleton_pattern(mock_calendar_service):
    """Test get_calendar_sync returns same instance."""
    with patch('google_calendar.CalendarSync._get_calendar_service', return_value=mock_calendar_service):
        sync1 = get_calendar_sync()
        sync2 = get_calendar_sync()

        assert sync1 is sync2


def test_handles_calendar_api_errors(calendar_sync, mock_calendar_service, sample_task):
    """Test proper error handling for Calendar API failures."""
    from googleapiclient.errors import HttpError

    mock_calendar_service.events().insert().execute.side_effect = HttpError(
        resp=Mock(status=500),
        content=b'Server error'
    )

    with pytest.raises(Exception) as exc_info:
        calendar_sync.sync_task_to_calendar(sample_task)

    assert 'Calendar API error' in str(exc_info.value)
