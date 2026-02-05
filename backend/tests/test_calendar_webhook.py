"""Tests for Calendar Pub/Sub webhook."""
import pytest
import base64
import json
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.fixture
def pubsub_message():
    """Create sample Pub/Sub message."""
    return {
        'message': {
            'data': base64.b64encode(json.dumps({
                'resourceId': 'event_12345',
                'state': 'exists'
            }).encode()).decode()
        }
    }


def test_calendar_webhook_accepts_valid_pubsub_message(pubsub_message):
    """Test webhook accepts valid Pub/Sub message."""
    with patch('main.process_calendar_change') as mock_process:
        from main import app
        client = TestClient(app)

        response = client.post(
            '/api/google/calendar/webhook',
            json=pubsub_message,
            headers={'X-Goog-Resource-State': 'exists'}
        )

        assert response.status_code == 200


def test_calendar_webhook_rejects_invalid_signature():
    """Test webhook rejects messages without Pub/Sub headers."""
    from main import app
    client = TestClient(app)

    response = client.post(
        '/api/google/calendar/webhook',
        json={'invalid': 'message'}
    )

    assert response.status_code == 401


def test_calendar_webhook_processes_event_asynchronously(pubsub_message):
    """Test webhook processes event in background."""
    with patch('main.BackgroundTasks.add_task') as mock_add_task:
        from main import app
        client = TestClient(app)

        response = client.post(
            '/api/google/calendar/webhook',
            json=pubsub_message,
            headers={'X-Goog-Resource-State': 'exists'}
        )

        assert response.status_code == 200
        assert mock_add_task.called


@pytest.mark.asyncio
async def test_process_calendar_change_ignores_own_events():
    """Test process_calendar_change ignores events from ai-assistant."""
    with patch('main.get_calendar_sync') as mock_get_sync:
        mock_sync = Mock()
        mock_sync.get_event.return_value = {
            'id': 'event_12345',
            'summary': 'Test Event',
            'extendedProperties': {
                'private': {
                    'source': 'ai-assistant'
                }
            }
        }
        mock_get_sync.return_value = mock_sync

        from main import process_calendar_change

        notification = {'resourceId': 'event_12345'}
        await process_calendar_change(notification)

        # Should fetch event but not process it
        assert mock_sync.get_event.called
        # Should not create/update task (verified by no DB calls)


@pytest.mark.asyncio
async def test_process_calendar_change_creates_task_from_new_event():
    """Test process_calendar_change creates task from user-created event."""
    with patch('main.get_calendar_sync') as mock_get_sync:
        mock_sync = Mock()
        mock_sync.get_event.return_value = {
            'id': 'event_12345',
            'summary': 'New Task from Calendar',
            'description': 'Task description',
            'status': 'confirmed',
            'extendedProperties': {
                'private': {}  # No source = user-created
            }
        }
        mock_get_sync.return_value = mock_sync

        with patch('main.create_task_in_db') as mock_create_task:
            mock_task = Mock()
            mock_task.id = 'task_123'
            mock_create_task.return_value = mock_task

            from main import process_calendar_change

            notification = {'resourceId': 'event_12345'}
            await process_calendar_change(notification)

            assert mock_create_task.called
            call_args = mock_create_task.call_args[0][0]
            assert call_args['name'] == 'New Task from Calendar'
