"""Tests for Gmail sending service."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import base64
from datetime import datetime
from gmail_sender import GmailSender, get_gmail_sender


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail API service."""
    with patch('gmail_sender.os.path.exists', return_value=True), \
         patch('gmail_sender.Credentials.from_authorized_user_file') as mock_creds, \
         patch('gmail_sender.build') as mock_build:

        # Mock valid credentials
        mock_cred = Mock()
        mock_cred.valid = True
        mock_creds.return_value = mock_cred

        # Mock Gmail service
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        yield mock_service


@pytest.fixture
def sender(mock_gmail_service):
    """Create GmailSender instance with mocked service."""
    return GmailSender()


def test_send_email_creates_multipart_message(sender, mock_gmail_service):
    """Test send_email creates proper multipart message."""
    sender.send_email(
        to='user@example.com',
        subject='Test Email',
        body_html='<h1>Hello</h1>',
        body_text='Hello'
    )

    # Verify send was called
    assert mock_gmail_service.users().messages().send.called
    call_args = mock_gmail_service.users().messages().send.call_args

    # Verify message structure
    assert call_args[1]['userId'] == 'me'
    assert 'raw' in call_args[1]['body']


def test_send_email_returns_message_id(sender, mock_gmail_service):
    """Test send_email returns Gmail message ID."""
    mock_gmail_service.users().messages().send().execute.return_value = {
        'id': 'msg_12345'
    }

    message_id = sender.send_email(
        to='user@example.com',
        subject='Test',
        body_html='<p>Test</p>'
    )

    assert message_id == 'msg_12345'


def test_send_email_with_attachments(sender, mock_gmail_service):
    """Test send_email handles attachments."""
    with patch('gmail_sender.os.path.exists', return_value=True):
        with patch('gmail_sender.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b'file content'

            sender.send_email(
                to='user@example.com',
                subject='Test',
                body_html='<p>Test</p>',
                attachments=['test.txt']
            )

    # Verify send was called with attachment
    assert mock_gmail_service.users().messages().send.called


def test_send_task_completion_email(sender, mock_gmail_service):
    """Test send_task_completion_email uses correct template."""
    task = Mock(spec=['id', 'name', 'description', 'notifyOn', 'nextRun', 'task_metadata'])
    task.id = 'task_123'
    task.name = 'Test Task'
    task.description = 'Test description'
    task.notifyOn = 'completion,error'
    task.nextRun = None
    task.task_metadata = None

    execution = Mock(spec=['id', 'status', 'duration', 'output', 'completedAt'])
    execution.id = 'exec_456'
    execution.status = 'completed'
    execution.duration = 1200  # milliseconds
    execution.output = 'Task completed successfully'
    execution.completedAt = '2026-02-04T10:30:00'

    mock_gmail_service.users().messages().send().execute.return_value = {
        'id': 'msg_12345'
    }

    message_id = sender.send_task_completion_email(task, execution)

    assert message_id == 'msg_12345'

    # Verify email was sent with correct parameters
    assert mock_gmail_service.users().messages().send.called
    call_args = mock_gmail_service.users().messages().send.call_args
    assert call_args[1]['userId'] == 'me'
    assert 'raw' in call_args[1]['body']


def test_send_task_completion_email_with_custom_recipient(sender, mock_gmail_service):
    """Test send_task_completion_email uses custom recipient from task metadata."""
    task = Mock(spec=['id', 'name', 'description', 'notifyOn', 'nextRun', 'task_metadata'])
    task.id = 'task_123'
    task.name = 'Test Task'
    task.description = 'Test description'
    task.notifyOn = 'completion,error'
    task.nextRun = None
    task.task_metadata = {'recipientEmail': 'custom@example.com'}

    execution = Mock(spec=['id', 'status', 'duration', 'output', 'completedAt'])
    execution.id = 'exec_456'
    execution.status = 'completed'
    execution.duration = 1200
    execution.output = 'Task completed successfully'
    execution.completedAt = '2026-02-04T10:30:00'

    mock_gmail_service.users().messages().send().execute.return_value = {
        'id': 'msg_12345'
    }

    message_id = sender.send_task_completion_email(task, execution)

    assert message_id == 'msg_12345'

    # Verify email was sent to custom recipient
    call_args = mock_gmail_service.users().messages().send.call_args
    message_raw = call_args[1]['body']['raw']
    import base64
    decoded_message = base64.urlsafe_b64decode(message_raw).decode('utf-8')
    assert 'To: custom@example.com' in decoded_message


def test_send_task_completion_email_falls_back_to_default(sender, mock_gmail_service):
    """Test send_task_completion_email falls back to default recipient when no custom recipient."""
    task = Mock(spec=['id', 'name', 'description', 'notifyOn', 'nextRun', 'task_metadata'])
    task.id = 'task_123'
    task.name = 'Test Task'
    task.description = 'Test description'
    task.notifyOn = 'completion,error'
    task.nextRun = None
    task.task_metadata = None  # No custom recipient

    execution = Mock(spec=['id', 'status', 'duration', 'output', 'completedAt'])
    execution.id = 'exec_456'
    execution.status = 'completed'
    execution.duration = 1200
    execution.output = 'Task completed successfully'
    execution.completedAt = '2026-02-04T10:30:00'

    mock_gmail_service.users().messages().send().execute.return_value = {
        'id': 'msg_12345'
    }

    message_id = sender.send_task_completion_email(task, execution)

    assert message_id == 'msg_12345'

    # Verify email was sent to default recipient (from environment)
    call_args = mock_gmail_service.users().messages().send.call_args
    message_raw = call_args[1]['body']['raw']
    import base64
    decoded_message = base64.urlsafe_b64decode(message_raw).decode('utf-8')
    # Should use RECIPIENT_EMAIL from gmail_sender.py (environment or default)
    from gmail_sender import RECIPIENT_EMAIL
    assert f'To: {RECIPIENT_EMAIL}' in decoded_message


def test_send_task_failure_email_with_custom_recipient(sender, mock_gmail_service):
    """Test send_task_failure_email uses custom recipient from task metadata."""
    task = Mock(spec=['id', 'name', 'description', 'task_metadata'])
    task.id = 'task_123'
    task.name = 'Failed Task'
    task.description = 'Test description'
    task.task_metadata = {'recipientEmail': 'alert@example.com'}

    execution = Mock(spec=['id', 'status', 'output', 'completedAt'])
    execution.id = 'exec_456'
    execution.status = 'failed'
    execution.output = 'Error occurred'
    execution.completedAt = '2026-02-04T10:30:00'

    mock_gmail_service.users().messages().send().execute.return_value = {
        'id': 'msg_12345'
    }

    message_id = sender.send_task_failure_email(task, execution)

    assert message_id == 'msg_12345'

    # Verify email was sent to custom recipient
    call_args = mock_gmail_service.users().messages().send.call_args
    message_raw = call_args[1]['body']['raw']
    import base64
    decoded_message = base64.urlsafe_b64decode(message_raw).decode('utf-8')
    assert 'To: alert@example.com' in decoded_message


def test_send_task_failure_email(sender, mock_gmail_service):
    """Test send_task_failure_email uses correct template."""
    task = Mock(spec=['id', 'name', 'description', 'task_metadata'])
    task.id = 'task_123'
    task.name = 'Failed Task'
    task.description = 'Test description'
    task.task_metadata = None

    execution = Mock(spec=['id', 'status', 'output', 'completedAt'])
    execution.id = 'exec_456'
    execution.status = 'failed'
    execution.output = 'Error: Connection timeout'
    execution.completedAt = '2026-02-04T10:30:00'

    mock_gmail_service.users().messages().send().execute.return_value = {
        'id': 'msg_12345'
    }

    message_id = sender.send_task_failure_email(task, execution)

    assert message_id == 'msg_12345'

    # Verify email was sent with correct parameters
    assert mock_gmail_service.users().messages().send.called
    call_args = mock_gmail_service.users().messages().send.call_args
    assert call_args[1]['userId'] == 'me'
    assert 'raw' in call_args[1]['body']


def test_singleton_pattern(mock_gmail_service):
    """Test get_gmail_sender returns same instance."""
    sender1 = get_gmail_sender()
    sender2 = get_gmail_sender()

    assert sender1 is sender2


def test_handles_gmail_api_errors(sender, mock_gmail_service):
    """Test proper error handling for Gmail API failures."""
    from googleapiclient.errors import HttpError

    mock_gmail_service.users().messages().send().execute.side_effect = HttpError(
        resp=Mock(status=500),
        content=b'Server error'
    )

    with pytest.raises(Exception) as exc_info:
        sender.send_email(
            to='user@example.com',
            subject='Test',
            body_html='<p>Test</p>'
        )

    assert 'Gmail API error' in str(exc_info.value)


def test_send_daily_digest_with_database(sender, mock_gmail_service):
    """Test send_daily_digest queries database and sends email."""
    # Mock database session
    mock_db = Mock()

    # Mock the query results
    with patch('gmail_sender.get_daily_digest_data') as mock_query:
        mock_query.return_value = {
            'total_tasks': 10,
            'successful': 8,
            'failed': 2,
            'success_rate': 80,
            'upcoming_tasks': [
                {'name': 'Task 1', 'time': '2026-02-06 08:00:00', 'description': 'Test', 'priority': 'default'}
            ]
        }

        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'msg_digest_123'
        }

        message_id = sender.send_daily_digest(mock_db, 'test@example.com', datetime.now())

        # Verify query was called with correct parameters
        mock_query.assert_called_once()
        assert mock_query.call_args[0][0] == mock_db

        # Verify email was sent
        assert message_id == 'msg_digest_123'
        assert mock_gmail_service.users().messages().send.called


def test_send_weekly_summary_with_database(sender, mock_gmail_service):
    """Test send_weekly_summary queries database and sends email."""
    # Mock database session
    mock_db = Mock()

    # Mock the query results
    with patch('gmail_sender.get_weekly_summary_data') as mock_query:
        mock_query.return_value = {
            'total_executions': 50,
            'success_count': 45,
            'failure_count': 5,
            'top_failures': [
                {'task': 'Failed Task', 'count': 3}
            ],
            'avg_duration_ms': 2500
        }

        mock_gmail_service.users().messages().send().execute.return_value = {
            'id': 'msg_summary_123'
        }

        message_id = sender.send_weekly_summary(mock_db, 'test@example.com', datetime.now())

        # Verify query was called with correct parameters
        mock_query.assert_called_once()
        assert mock_query.call_args[0][0] == mock_db

        # Verify email was sent
        assert message_id == 'msg_summary_123'
        assert mock_gmail_service.users().messages().send.called
