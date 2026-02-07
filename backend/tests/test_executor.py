"""Tests for task executor with Gmail integration."""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timezone


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def mock_task():
    """Create a mock task."""
    task = Mock(spec=['id', 'name', 'description', 'notifyOn', 'command', 'args', 'lastRun', 'nextRun'])
    task.id = 'task_123'
    task.name = 'Test Task'
    task.description = 'Test description'
    task.notifyOn = 'completion,error'
    task.command = 'test'
    task.args = '{}'
    task.lastRun = None
    task.nextRun = None
    return task


@pytest.fixture
def mock_execution():
    """Create a mock execution."""
    execution = Mock(spec=['id', 'status', 'duration', 'output', 'completedAt', 'startedAt'])
    execution.id = 'exec_456'
    execution.status = 'completed'
    execution.duration = 1200
    execution.output = 'Task completed successfully'
    execution.completedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
    execution.startedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
    return execution


@pytest.mark.asyncio
async def test_executor_sends_completion_email_when_configured(mock_db, mock_task, mock_execution):
    """Test executor sends email on task completion when notifyOn includes completion."""
    from executor import execute_task

    # Mock database query
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_task

    with patch('executor.get_gmail_sender') as mock_get_sender, \
         patch('executor.execute_claude_task') as mock_claude, \
         patch('executor.TaskExecution') as mock_exec_class, \
         patch('executor.send_notification') as mock_ntfy:

        # Setup mocks
        mock_sender = Mock()
        mock_sender.send_task_completion_email.return_value = 'msg_12345'
        mock_get_sender.return_value = mock_sender

        # Mock Claude execution
        async def mock_lines():
            yield "Task output line 1"
            yield "Task output line 2"
            yield "exit code: 0"

        mock_claude.return_value = mock_lines()

        # Mock execution object
        mock_exec_class.return_value = mock_execution

        # Execute task
        await execute_task('task_123', mock_db)

        # Verify email was sent
        assert mock_sender.send_task_completion_email.called
        call_args = mock_sender.send_task_completion_email.call_args
        assert call_args[0][0].id == mock_task.id


@pytest.mark.asyncio
async def test_executor_sends_failure_email_when_configured(mock_db, mock_task):
    """Test executor sends email on task failure when notifyOn includes error."""
    from executor import execute_task

    # Mock database query
    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_task

    # Create failed execution
    failed_execution = Mock(spec=['id', 'status', 'duration', 'output', 'completedAt', 'startedAt'])
    failed_execution.id = 'exec_456'
    failed_execution.status = 'failed'
    failed_execution.duration = 1200
    failed_execution.output = 'Error: Task failed'
    failed_execution.completedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
    failed_execution.startedAt = int(datetime.now(timezone.utc).timestamp() * 1000)

    with patch('executor.get_gmail_sender') as mock_get_sender, \
         patch('executor.execute_claude_task') as mock_claude, \
         patch('executor.TaskExecution') as mock_exec_class, \
         patch('executor.send_notification') as mock_ntfy:

        # Setup mocks
        mock_sender = Mock()
        mock_sender.send_task_failure_email.return_value = 'msg_12345'
        mock_get_sender.return_value = mock_sender

        # Mock Claude execution to fail
        async def mock_lines():
            raise Exception("Task execution failed")

        mock_claude.return_value = mock_lines()

        # Mock execution object
        mock_exec_class.return_value = failed_execution

        # Execute task (should fail)
        try:
            await execute_task('task_123', mock_db)
        except Exception:
            pass  # Expected to fail

        # Verify failure email was sent
        assert mock_sender.send_task_failure_email.called


@pytest.mark.asyncio
async def test_executor_skips_email_when_not_configured(mock_db):
    """Test executor does not send email when notifyOn excludes event."""
    from executor import execute_task

    # Create task with no notifications
    task = Mock(spec=['id', 'name', 'description', 'notifyOn', 'command', 'args', 'lastRun', 'nextRun'])
    task.id = 'task_123'
    task.name = 'Test Task'
    task.description = 'Test description'
    task.notifyOn = ''  # No notifications
    task.command = 'test'
    task.args = '{}'
    task.lastRun = None
    task.nextRun = None

    # Mock database query
    mock_db.query.return_value.filter_by.return_value.first.return_value = task

    execution = Mock(spec=['id', 'status', 'duration', 'output', 'completedAt', 'startedAt'])
    execution.id = 'exec_456'
    execution.status = 'completed'
    execution.duration = 1200
    execution.output = 'Task completed successfully'
    execution.completedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
    execution.startedAt = int(datetime.now(timezone.utc).timestamp() * 1000)

    with patch('executor.get_gmail_sender') as mock_get_sender, \
         patch('executor.execute_claude_task') as mock_claude, \
         patch('executor.TaskExecution') as mock_exec_class, \
         patch('executor.send_notification') as mock_ntfy:

        # Setup mocks
        mock_sender = Mock()
        mock_get_sender.return_value = mock_sender

        # Mock Claude execution
        async def mock_lines():
            yield "Task output line 1"
            yield "exit code: 0"

        mock_claude.return_value = mock_lines()

        # Mock execution object
        mock_exec_class.return_value = execution

        # Execute task
        await execute_task('task_123', mock_db)

        # Verify no email was sent
        assert not mock_sender.send_task_completion_email.called
