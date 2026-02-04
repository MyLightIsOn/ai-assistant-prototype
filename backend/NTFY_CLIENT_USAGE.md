# ntfy.sh Notification Client Usage

This document demonstrates how to use the `ntfy_client` module to send push notifications.

## Configuration

Set the following environment variables in your `.env` file:

```bash
# Required
NTFY_URL=http://localhost:8080/ai-notifications

# Optional (for authenticated servers)
NTFY_USERNAME=your-username-ai
NTFY_PASSWORD=your-secure-password
```

## Basic Usage

```python
from ntfy_client import send_notification

# Simple notification
result = send_notification(
    title="Task Complete",
    message="Database backup finished successfully"
)

if result:
    print("Notification sent!")
else:
    print("Failed to send notification")
```

## Advanced Usage

### With Priority

Priority levels: `min`, `low`, `default`, `high`, `max`, `urgent`

```python
send_notification(
    title="Critical Error",
    message="Database connection failed",
    priority="urgent"
)
```

### With Tags

Tags appear as icons/badges in the ntfy mobile app:

```python
send_notification(
    title="Task Complete",
    message="Weekly report generated successfully",
    priority="high",
    tags="white_check_mark,ai,report"
)
```

Common tag icons:
- `warning` - Warning triangle
- `rotating_light` - Emergency light
- `white_check_mark` - Success checkmark
- `x` - Error/failure
- `loudspeaker` - Announcement
- `computer` - System notification

### Integration Example

```python
from ntfy_client import send_notification
from models import Task, TaskExecution
from database import get_db

def execute_task(task: Task):
    """Execute a task and send notification on completion."""

    # Run the task
    result = run_task_command(task)

    # Notify based on result
    if result.success:
        send_notification(
            title=f"Task Complete: {task.name}",
            message=f"Task completed in {result.duration}ms",
            priority="default",
            tags="white_check_mark,ai"
        )
    else:
        send_notification(
            title=f"Task Failed: {task.name}",
            message=f"Error: {result.error}",
            priority="high",
            tags="warning,ai"
        )
```

## Activity Logging

All notification sends are automatically logged to the `ActivityLog` database table:

- **Success**: Type `notification_sent` with metadata
- **Failure**: Type `notification_error` with error details

This provides an audit trail of all notification activity.

## Error Handling

The `send_notification` function gracefully handles errors:

- **Connection errors** - Returns `False`, logs error
- **Timeouts** - Returns `False`, logs error
- **HTTP errors** - Returns `False`, logs error
- **Invalid config** - Raises `ValueError` on initialization

The function never raises exceptions during send (only during config loading).

## Testing

The module includes comprehensive tests in `tests/test_ntfy_client.py`:

```bash
# Run ntfy_client tests
cd backend
source venv/bin/activate
pytest tests/test_ntfy_client.py -v
```

All tests use mocks - no actual HTTP requests are made during testing.

## Architecture

```
┌─────────────┐
│   FastAPI   │
│   Backend   │
└──────┬──────┘
       │
       v
┌─────────────┐     HTTP POST      ┌──────────────┐
│ ntfy_client ├───────────────────>│  ntfy.sh     │
│   Module    │                     │   Server     │
└──────┬──────┘                     └──────────────┘
       │                                   │
       v                                   v
┌─────────────┐                     ┌──────────────┐
│ ActivityLog │                     │ Mobile App   │
│  Database   │                     │ (instant)    │
└─────────────┘                     └──────────────┘
```

## Performance

- **Request timeout**: 10 seconds
- **Synchronous**: Sends notification and waits for response
- **Retry logic**: Not implemented (caller responsible for retries)
- **Database logging**: Minimal overhead, non-blocking on failure
