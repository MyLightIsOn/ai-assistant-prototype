# Gmail Sending - Usage Guide

This guide explains how to use the Gmail sending service for task notifications and reports.

## Setup

### 1. Configure Environment Variables

Add to `backend/.env`:

```bash
GMAIL_USER_EMAIL="your-ai-assistant@gmail.com"
GMAIL_RECIPIENT_EMAIL="your-personal-email@gmail.com"
```

### 2. Verify OAuth Credentials

Ensure Google OAuth is set up:

```bash
cd backend
python google_auth_setup.py
```

This creates `google_user_credentials.json` with Gmail send permission.

### 3. Test Email Sending

```python
from gmail_sender import get_gmail_sender

sender = get_gmail_sender()
sender.send_email(
    to='your-email@gmail.com',
    subject='Test Email',
    body_html='<h1>Hello from AI Assistant!</h1>',
    body_text='Hello from AI Assistant!'
)
```

## Task Notification Configuration

Tasks can automatically send emails based on the `notifyOn` field:

```json
{
    "name": "Daily Backup",
    "notifyOn": "completion,error"
}
```

**Options:**
- `completion` - Send email when task completes successfully
- `error` - Send email when task fails (after all retries)
- `completion,error` - Send email for both events

**Email Types:**

**Completion Email:**
- Subject: ✅ Task Complete: {task_name}
- Includes: Duration, output summary, Drive link, next run time
- Format: HTML with professional styling

**Failure Email:**
- Subject: ❌ Task Failed: {task_name}
- Includes: Error message, retry history, troubleshooting tips
- Format: HTML with error highlighting

## Digest Emails

### Daily Digest

Sent automatically at 8 PM daily (configure as scheduled task):

```json
{
    "name": "Daily AI Assistant Digest",
    "schedule": "0 20 * * *",
    "command": "send_digest",
    "args": "{\"type\": \"daily\"}"
}
```

Includes:
- Total tasks run today
- Success/failure counts
- Success rate percentage
- Upcoming tasks for tomorrow

### Weekly Summary

Sent automatically every Monday at 9 AM (configure as scheduled task):

```json
{
    "name": "Weekly AI Assistant Summary",
    "schedule": "0 9 * * 1",
    "command": "send_digest",
    "args": "{\"type\": \"weekly\"}"
}
```

Includes:
- Total executions for the week
- Success/failure trends
- Top failing tasks
- Link to detailed Drive report

## Manual Email Sending

### Send Custom Email

```python
from gmail_sender import get_gmail_sender

sender = get_gmail_sender()
message_id = sender.send_email(
    to='recipient@example.com',
    subject='Custom Report',
    body_html='<h2>Report</h2><p>Content here...</p>',
    body_text='Report\n\nContent here...',
    attachments=['path/to/report.pdf']
)
```

### Send Task Notification Manually

```python
from gmail_sender import get_gmail_sender
from models import Task, TaskExecution

sender = get_gmail_sender()
task = get_task_by_id('task_123')
execution = get_execution_by_id('exec_456')

# Send completion email
sender.send_task_completion_email(task, execution)

# Send failure email
sender.send_task_failure_email(task, execution)
```

## Troubleshooting

### "No valid credentials found"

Run OAuth setup:
```bash
python google_auth_setup.py
```

### Emails not sending

Check logs:
```bash
tail -f logs/backend.log | grep gmail
```

Verify Gmail API is enabled in Google Cloud Console.

### Rate limiting

Gmail API has daily sending limits:
- Free tier: 100 emails/day
- Workspace: 2000 emails/day

Use digest emails to batch notifications.

## Email Templates

Templates are defined in `backend/email_templates.py`. To customize:

1. Edit template functions
2. Test with `pytest tests/test_email_templates.py`
3. Restart backend to apply changes

Example customization:

```python
def render_task_completion_email(task_data):
    html = f"""
    <html>
    <body>
        <h1>🎉 Success!</h1>
        <p>{task_data['name']} completed in {task_data['duration']}</p>
    </body>
    </html>
    """
    # ... rest of template
```

## Testing

Run tests:

```bash
cd backend
pytest tests/test_gmail_sender.py -v
pytest tests/test_email_templates.py -v
```

Send test email:

```bash
python -c "from gmail_sender import get_gmail_sender; get_gmail_sender().send_email('you@example.com', 'Test', '<p>Test</p>')"
```
