# Gmail Sending and Calendar Integration - Design Document

**Date:** 2026-02-04
**Author:** Claude Code
**Status:** Approved
**Related Issues:** #46 (Gmail Sending), #44 (Calendar Sync), #47 (Pub/Sub Webhooks)

## Overview

This design covers two parallel implementation tracks:
- **Track 1:** Gmail sending for task notifications and reports (Issue #46)
- **Track 2:** Google Calendar bi-directional sync with Pub/Sub webhooks (Issues #44 + #47)

Both features integrate into the existing backend infrastructure and share common patterns with the existing Google Drive and Gmail reading implementations from PR #53.

## Overall Architecture

Both features integrate into the existing backend infrastructure and share common patterns:

**Gmail Sending (Track 1)** will create a new `backend/gmail_sender.py` module with:
- Core `GmailSender` class for composing and sending emails
- Template rendering system for HTML emails (task completion, failure, digests)
- Integration hooks into the task executor (`backend/executor.py`)
- Utility functions for attachments and Drive link embedding

The sender will check the task's `notifyOn` configuration (e.g., `"completion,error"`) and automatically send appropriate emails after task execution. Daily/weekly digests will be implemented as scheduled tasks themselves.

**Calendar Integration (Track 2)** will create `backend/google_calendar.py` and add a webhook endpoint to FastAPI:
- `CalendarSync` class handles DB → Calendar synchronization
- Event creation/update/deletion triggered by task CRUD operations
- Extended properties store `taskId` and `source: 'ai-assistant'` to prevent sync loops
- Pub/Sub webhook endpoint (`/api/google/calendar/webhook`) processes Calendar → DB events
- Calendar watch setup on backend startup with automatic weekly renewal

Both modules will use the existing Google OAuth credentials setup and follow the singleton pattern established by `google_drive.py` and `gmail_client.py`.

## Track 1: Gmail Sending - Detailed Design

### Module Structure (`backend/gmail_sender.py`)

The `GmailSender` class will handle email composition and delivery:

```python
class GmailSender:
    def __init__(self):
        self.service = self._get_gmail_service()

    def send_email(self, to: str, subject: str, body_html: str,
                   body_text: str = None, attachments: List[str] = None) -> str:
        """Send email with HTML/plain text and optional attachments."""

    def send_task_completion_email(self, task: Task, execution: TaskExecution):
        """Send task completion notification with output summary."""

    def send_task_failure_email(self, task: Task, execution: TaskExecution):
        """Send task failure notification with error details."""

    def send_daily_digest(self, date: datetime):
        """Send daily summary of task executions."""

    def send_weekly_summary(self, week_start: datetime):
        """Send weekly statistics and trends."""
```

### Email Templates

Email templates will be HTML strings with placeholders, stored in `backend/email_templates.py`:

**Task Completion Template:**
- Subject: `✅ Task Complete: {task_name}`
- Status badge, duration, output summary (first 500 chars)
- Drive link to full logs
- Next scheduled run time

**Task Failure Template:**
- Subject: `❌ Task Failed: {task_name}`
- Error message and stack trace
- Retry history (attempt 1/3, 2/3, 3/3)
- Full error logs as attachment
- Troubleshooting suggestions

**Daily Digest Template:**
- Subject: `📊 AI Assistant Daily Summary - {date}`
- Tasks run today with success/failure counts
- Success rate percentage
- Upcoming tasks for tomorrow
- Quick links to dashboard

**Weekly Summary Template:**
- Subject: `📈 AI Assistant Weekly Report - Week {week}`
- Task execution trends (chart/table)
- Top failures and recommendations
- Task performance statistics
- Drive link to detailed report

### Integration with Task Execution

Modify `backend/executor.py` to add email notification hooks:

```python
async def execute_task(task_id: str):
    # Existing execution logic...

    try:
        # Execute task
        result = await _run_task(task)
        execution.status = "completed"

        # Send completion email if configured
        if 'completion' in task.notifyOn:
            gmail_sender.send_task_completion_email(task, execution)

    except Exception as e:
        execution.status = "failed"

        # Send failure email if configured (after all retries)
        if 'error' in task.notifyOn:
            gmail_sender.send_task_failure_email(task, execution)
```

### Future Extensibility

The core `send_email()` method is designed to be reusable for non-task-related emails:
- On-demand reports via chat commands
- System alerts (disk space, service failures)
- Custom user-triggered notifications

This modular design allows future features to use the email service without task integration.

## Track 2: Calendar Sync (DB → Calendar) - Detailed Design

### Module Structure (`backend/google_calendar.py`)

The `CalendarSync` class manages one-way synchronization from database to Google Calendar:

```python
class CalendarSync:
    def __init__(self):
        self.service = self._get_calendar_service()
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')

    def sync_task_to_calendar(self, task: Task) -> str:
        """Create or update Calendar event for task. Returns event_id."""
        event_id = self._get_event_id_from_task(task)
        event_data = self._build_event_from_task(task)

        if event_id:
            # Update existing event
            self.service.events().update(
                calendarId=self.calendar_id,
                eventId=event_id,
                body=event_data
            ).execute()
        else:
            # Create new event
            result = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event_data
            ).execute()
            event_id = result['id']
            # Store event_id in task metadata

        return event_id

    def delete_calendar_event(self, task: Task):
        """Delete Calendar event when task deleted."""

    def get_event(self, event_id: str) -> dict:
        """Fetch event from Calendar API."""
```

### Calendar Event Structure

Events created from tasks will have:

```python
event = {
    'summary': task.name,
    'description': f"{task.description}\n\nCommand: {task.command}\nArgs: {task.args}",
    'start': {
        'dateTime': task.nextRun.isoformat(),
        'timeZone': 'America/Los_Angeles'
    },
    'end': {
        'dateTime': (task.nextRun + timedelta(minutes=15)).isoformat(),
        'timeZone': 'America/Los_Angeles'
    },
    'colorId': get_color_for_priority(task.priority),  # low=1, default=10, high=6, urgent=11
    'reminders': {
        'useDefault': False,
        'overrides': [
            {'method': 'popup', 'minutes': 10}
        ]
    },
    'extendedProperties': {
        'private': {
            'taskId': task.id,
            'source': 'ai-assistant'
        }
    }
}
```

**Priority Color Mapping:**
- Low: `1` (Lavender/Blue)
- Default: `10` (Green)
- High: `6` (Orange)
- Urgent: `11` (Red)

### Integration with Task CRUD

Add Calendar sync calls in Next.js API routes by calling backend:

```typescript
// frontend/app/api/tasks/route.ts (POST)
const task = await prisma.task.create({...});

// Trigger Calendar sync via backend
await fetch(`${PYTHON_BACKEND_URL}/api/calendar/sync`, {
  method: 'POST',
  body: JSON.stringify({ taskId: task.id })
});
```

Backend endpoint in `backend/main.py`:

```python
@app.post("/api/calendar/sync")
async def sync_task(task_id: str):
    task = get_task_from_db(task_id)
    event_id = calendar_sync.sync_task_to_calendar(task)
    update_task_metadata(task_id, {'calendarEventId': event_id})
    return {"event_id": event_id}

@app.delete("/api/calendar/sync/{task_id}")
async def delete_task_event(task_id: str):
    task = get_task_from_db(task_id)
    calendar_sync.delete_calendar_event(task)
    return {"status": "deleted"}
```

### Handling Recurring Tasks

For tasks with cron schedules, create a single recurring Calendar event:

1. Parse cron expression (e.g., `0 8 * * 1-5` = weekdays at 8am)
2. Convert to Calendar recurrence rule (RRULE format)
3. Set event recurrence property

Example:
```python
event['recurrence'] = ['RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR;BYHOUR=8;BYMINUTE=0']
```

Note: For complex cron expressions, use the `croniter` library to calculate next N occurrences and create individual events.

## Track 2: Pub/Sub Webhooks (Calendar → DB) - Detailed Design

### Webhook Endpoint (`backend/main.py`)

Add FastAPI route to handle Calendar change notifications from Google Pub/Sub:

```python
@app.post("/api/google/calendar/webhook")
async def calendar_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Calendar change notifications from Pub/Sub."""

    # Verify Pub/Sub message (check for required headers)
    if not _verify_pubsub_request(request):
        logger.warning("Invalid Pub/Sub request signature")
        return Response(status_code=401)

    # Parse Pub/Sub message
    body = await request.json()
    message_data = base64.b64decode(body['message']['data'])
    calendar_notification = json.loads(message_data)

    # Process asynchronously (return 200 quickly per Pub/Sub requirements)
    background_tasks.add_task(process_calendar_change, calendar_notification)

    return Response(status_code=200)

def _verify_pubsub_request(request: Request) -> bool:
    """Verify request is from Google Pub/Sub."""
    # Check for Pub/Sub headers
    return 'X-Goog-Resource-State' in request.headers or \
           'Authorization' in request.headers
```

### Event Processing (`backend/google_calendar.py`)

```python
async def process_calendar_change(notification: dict):
    """Process Calendar event change and sync to database."""

    # Fetch the actual event from Calendar API
    resource_id = notification.get('resourceId')
    event = calendar_sync.get_event(resource_id)

    if not event:
        logger.warning(f"Event {resource_id} not found")
        return

    # Check if this is our own event (prevent loops)
    extended_props = event.get('extendedProperties', {}).get('private', {})
    if extended_props.get('source') == 'ai-assistant':
        logger.info(f"Ignoring own event {event['id']}")
        return  # Ignore our own synced events

    # Determine change type and update DB
    if event['status'] == 'confirmed':
        await create_or_update_task_from_event(event)
    elif event['status'] == 'cancelled':
        await delete_task_from_event(event)

async def create_or_update_task_from_event(event: dict):
    """Create or update task from Calendar event."""

    # Extract task data from event
    task_data = {
        'name': event['summary'],
        'description': event.get('description', ''),
        'schedule': _convert_event_to_cron(event),
        'priority': _get_priority_from_color(event.get('colorId')),
        'enabled': True,
        'notifyOn': 'completion,error'
    }

    # Check if task already exists (by checking extended properties)
    extended_props = event.get('extendedProperties', {}).get('private', {})
    task_id = extended_props.get('taskId')

    if task_id:
        # Update existing task
        update_task_in_db(task_id, task_data)
    else:
        # Create new task
        task = create_task_in_db(task_data)
        # Update Calendar event with taskId to prevent future duplicates
        _update_event_extended_props(event['id'], {'taskId': task.id})
```

### Calendar Watch Setup

On backend startup, register a Calendar watch:

```python
# backend/main.py startup event
@app.on_event("startup")
async def setup_calendar_watch():
    """Setup Calendar watch on startup."""
    calendar_sync.setup_watch()

# backend/google_calendar.py
def setup_watch(self):
    """Register Calendar watch with Google."""

    watch_request = {
        'id': f'ai-assistant-watch-{int(time.time())}',
        'type': 'web_hook',
        'address': f'https://pubsub.googleapis.com/projects/{PROJECT_ID}/topics/calendar-notifications',
        'params': {
            'ttl': '604800'  # 7 days in seconds
        }
    }

    result = self.service.events().watch(
        calendarId=self.calendar_id,
        body=watch_request
    ).execute()

    # Store watch info for renewal
    self.watch_id = result['id']
    self.watch_expiration = datetime.fromtimestamp(int(result['expiration']) / 1000)

    # Schedule renewal before expiration
    schedule_watch_renewal(self.watch_expiration - timedelta(days=1))
```

### Sync Loop Prevention

Critical safeguard to prevent infinite sync loops:

1. **DB → Calendar:** Add `source: 'ai-assistant'` to extended properties
2. **Calendar → DB:** Check extended properties and ignore if `source == 'ai-assistant'`
3. **Logging:** Log all sync operations for debugging

```python
# Before processing Calendar change
if event.get('extendedProperties', {}).get('private', {}).get('source') == 'ai-assistant':
    logger.info(f"Skipping own event: {event['id']}")
    return
```

## Testing Strategy

### Gmail Sending Tests (`backend/tests/test_gmail_sender.py`)

Following TDD approach from PR #53:

**Unit Tests:**
- Mock Gmail API service with `unittest.mock`
- Test email composition (HTML + plain text multipart)
- Test attachment encoding and inclusion (base64)
- Test template rendering for all email types (completion, failure, digest, weekly)
- Test error handling (API failures, invalid recipients)
- Verify no emails sent when `notifyOn` doesn't include the event type

**Integration Tests:**
- Test integration hooks (verify emails sent after task completion/failure)
- Test Drive link embedding in email body
- Test attachment size limits

**Example Test Structure:**
```python
def test_send_task_completion_email(mock_gmail_service):
    sender = GmailSender()
    task = create_mock_task()
    execution = create_mock_execution(status="completed")

    sender.send_task_completion_email(task, execution)

    assert mock_gmail_service.users().messages().send.called
    sent_message = mock_gmail_service.users().messages().send.call_args[1]['body']
    assert task.name in decode_email_body(sent_message)
```

### Calendar Sync Tests (`backend/tests/test_google_calendar.py`)

**Unit Tests:**
- Mock Calendar API service
- Test event creation with all priority levels (color coding)
- Test event updates when task schedule changes
- Test event deletion when task deleted
- Test cron → Calendar recurrence conversion
- Test loop prevention (ignore events with `source: 'ai-assistant'`)
- Test extended properties storage and retrieval

**Integration Tests:**
- Test full sync flow (create task → verify Calendar event)
- Test metadata storage (calendarEventId in task)
- Test error handling (Calendar API failures)

**Example Test Structure:**
```python
def test_sync_task_to_calendar(mock_calendar_service):
    sync = CalendarSync()
    task = create_mock_task(priority="high")

    event_id = sync.sync_task_to_calendar(task)

    assert event_id is not None
    assert mock_calendar_service.events().insert.called
    event_data = mock_calendar_service.events().insert.call_args[1]['body']
    assert event_data['colorId'] == '6'  # Orange for high priority
    assert event_data['extendedProperties']['private']['source'] == 'ai-assistant'
```

### Pub/Sub Webhook Tests (`backend/tests/test_calendar_webhook.py`)

**Unit Tests:**
- Mock Pub/Sub message format
- Test webhook authentication/verification
- Test event parsing and DB updates
- Test background task processing
- Test sync loop prevention (ignore own events)
- Test error handling for malformed messages

**Integration Tests:**
- Test full webhook flow (simulate Pub/Sub → DB update)
- Test watch setup and renewal
- Test Calendar event → task creation

**Example Test Structure:**
```python
async def test_calendar_webhook_creates_task(test_client, mock_calendar_service):
    pubsub_message = {
        'message': {
            'data': base64.b64encode(json.dumps({
                'resourceId': 'event123'
            }).encode()).decode()
        }
    }

    response = await test_client.post(
        "/api/google/calendar/webhook",
        json=pubsub_message
    )

    assert response.status_code == 200
    # Verify task created in DB
    task = get_task_by_calendar_event_id('event123')
    assert task is not None
```

### Manual Integration Testing

Documented in PR testing instructions:

**Gmail Sending:**
1. Create a task with `notifyOn: "completion"`
2. Trigger the task manually
3. Verify email received with correct template
4. Check Drive link works
5. Verify daily/weekly digest emails

**Calendar Sync:**
1. Create task in web UI
2. Check Google Calendar for new event
3. Verify event color matches task priority
4. Update task schedule, verify Calendar event updates
5. Delete task, verify Calendar event deleted

**Pub/Sub Webhooks:**
1. Create event manually in Google Calendar
2. Verify task appears in database
3. Check extended properties set correctly
4. Verify sync loop prevention (no duplicate events)

## Integration Points

### Task Execution Integration

Modify `backend/executor.py` to add email notification hooks:

```python
async def execute_task(task_id: str):
    task = get_task_from_db(task_id)
    execution = create_execution_record(task_id)

    try:
        # Execute task
        result = await _run_task(task)
        execution.status = "completed"
        execution.output = result
        save_execution(execution)

        # Send completion email if configured
        if 'completion' in task.notifyOn:
            gmail_sender = get_gmail_sender()
            gmail_sender.send_task_completion_email(task, execution)

    except Exception as e:
        execution.status = "failed"
        execution.output = str(e)
        save_execution(execution)

        # Send failure email if configured (after all retries)
        if 'error' in task.notifyOn and execution.retries_exhausted:
            gmail_sender = get_gmail_sender()
            gmail_sender.send_task_failure_email(task, execution)
```

### Task CRUD Integration

**Frontend API Routes:**

```typescript
// frontend/app/api/tasks/route.ts (POST)
export async function POST(request: Request) {
    const data = await request.json();
    const task = await prisma.task.create({ data });

    // Trigger Calendar sync via backend
    try {
        await fetch(`${process.env.PYTHON_BACKEND_URL}/api/calendar/sync`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ taskId: task.id })
        });
    } catch (error) {
        console.error('Calendar sync failed:', error);
        // Non-blocking - task still created
    }

    return NextResponse.json(task);
}

// frontend/app/api/tasks/[id]/route.ts (PUT)
export async function PUT(request: Request, { params }: { params: { id: string } }) {
    const data = await request.json();
    const task = await prisma.task.update({
        where: { id: params.id },
        data
    });

    // Trigger Calendar sync
    await fetch(`${process.env.PYTHON_BACKEND_URL}/api/calendar/sync`, {
        method: 'POST',
        body: JSON.stringify({ taskId: task.id })
    });

    return NextResponse.json(task);
}

// frontend/app/api/tasks/[id]/route.ts (DELETE)
export async function DELETE(request: Request, { params }: { params: { id: string } }) {
    await prisma.task.delete({ where: { id: params.id } });

    // Delete Calendar event
    await fetch(`${process.env.PYTHON_BACKEND_URL}/api/calendar/sync/${params.id}`, {
        method: 'DELETE'
    });

    return new Response(null, { status: 204 });
}
```

**Backend Calendar Sync Endpoints:**

```python
# backend/main.py

@app.post("/api/calendar/sync")
async def sync_task(request: Request):
    """Sync task to Calendar."""
    data = await request.json()
    task_id = data['taskId']

    task = get_task_from_db(task_id)
    calendar_sync = get_calendar_sync()
    event_id = calendar_sync.sync_task_to_calendar(task)

    # Update task metadata with Calendar event ID
    update_task_metadata(task_id, {'calendarEventId': event_id})

    return {"event_id": event_id}

@app.delete("/api/calendar/sync/{task_id}")
async def delete_task_event(task_id: str):
    """Delete Calendar event when task deleted."""
    task = get_task_from_db(task_id)
    calendar_sync = get_calendar_sync()
    calendar_sync.delete_calendar_event(task)
    return {"status": "deleted"}
```

### Scheduled Digest Tasks

Create two new scheduled tasks in the system during initial setup:

**Daily Digest Task:**
```json
{
    "name": "Daily AI Assistant Digest",
    "description": "Send daily summary email",
    "command": "send_digest",
    "args": "{\"type\": \"daily\"}",
    "schedule": "0 20 * * *",
    "enabled": true,
    "priority": "default",
    "notifyOn": "error"
}
```

**Weekly Summary Task:**
```json
{
    "name": "Weekly AI Assistant Summary",
    "description": "Send weekly statistics email",
    "command": "send_digest",
    "args": "{\"type\": \"weekly\"}",
    "schedule": "0 9 * * 1",
    "enabled": true,
    "priority": "default",
    "notifyOn": "error"
}
```

These tasks execute commands that call `gmail_sender.send_daily_digest()` and `send_weekly_summary()` respectively.

## Environment Variables

Add to `backend/.env`:

```bash
# Gmail Sending
GMAIL_USER_EMAIL="your-ai-assistant@gmail.com"
GMAIL_RECIPIENT_EMAIL="your-personal-email@gmail.com"

# Google Calendar
GOOGLE_CALENDAR_ID="primary"

# Google Cloud Pub/Sub
GOOGLE_PROJECT_ID="ai-assistant-123456"
GOOGLE_PUBSUB_TOPIC="calendar-notifications"
GOOGLE_PUBSUB_SUBSCRIPTION="calendar-notifications-sub"

# Webhook URL (for Pub/Sub)
WEBHOOK_BASE_URL="https://your-tailscale-hostname:8000"
```

## HTTPS Requirement for Pub/Sub

Google Pub/Sub requires HTTPS endpoints. Options:

**Development:**
- Use `ngrok`: `ngrok http 8000`
- Update Pub/Sub subscription with ngrok URL
- Temporary solution for testing

**Production:**
- Use Tailscale HTTPS (requires SSL cert configuration)
- Or use Caddy reverse proxy with automatic HTTPS
- Permanent solution for production deployment

## Files to Create/Modify

### New Files

**Backend:**
- `backend/gmail_sender.py` - Gmail sending service
- `backend/email_templates.py` - Email HTML templates
- `backend/google_calendar.py` - Calendar sync service
- `backend/tests/test_gmail_sender.py` - Gmail sender tests
- `backend/tests/test_google_calendar.py` - Calendar sync tests
- `backend/tests/test_calendar_webhook.py` - Webhook tests

**Documentation:**
- `docs/guides/gmail-sending-usage.md` - Gmail sending guide
- `docs/guides/calendar-sync-usage.md` - Calendar sync guide

### Modified Files

**Backend:**
- `backend/main.py` - Add webhook endpoint and Calendar sync endpoints
- `backend/executor.py` - Add email notification hooks
- `backend/.env` - Add new environment variables

**Frontend:**
- `frontend/app/api/tasks/route.ts` - Add Calendar sync on create
- `frontend/app/api/tasks/[id]/route.ts` - Add Calendar sync on update/delete

**Database:**
- Potentially add `calendarEventId` field to Task model metadata (or use existing metadata JSON field)

## Success Criteria

**Gmail Sending:**
- ✅ AI can send emails via Gmail API
- ✅ Email templates are professional and informative
- ✅ Attachments work correctly
- ✅ Emails include Drive links when applicable
- ✅ HTML formatting renders correctly in Gmail
- ✅ Emails sent automatically based on task `notifyOn` configuration
- ✅ Daily and weekly digests send on schedule
- ✅ 90%+ test coverage for gmail_sender.py

**Calendar Integration:**
- ✅ All DB tasks appear in Google Calendar
- ✅ Changes in web UI sync to Calendar instantly
- ✅ Calendar events created by user create tasks in DB
- ✅ Pub/Sub webhook processes Calendar changes
- ✅ No sync conflicts or duplicates (loop prevention works)
- ✅ Color coding matches task priorities
- ✅ Extended properties correctly store task metadata
- ✅ Calendar watch auto-renews before expiration
- ✅ 90%+ test coverage for google_calendar.py

## Implementation Timeline

**Track 1 (Gmail Sending):** Estimated 1-2 days
1. Write tests for gmail_sender.py (TDD)
2. Implement GmailSender class
3. Create email templates
4. Integrate with executor.py
5. Create digest tasks
6. Manual testing with real Gmail

**Track 2 (Calendar + Pub/Sub):** Estimated 2-3 days
1. Write tests for google_calendar.py (TDD)
2. Implement CalendarSync class
3. Add backend sync endpoints
4. Integrate with frontend API routes
5. Implement Pub/Sub webhook endpoint
6. Setup Calendar watch and renewal
7. Manual testing with real Calendar

**Total:** 3-5 days for both tracks (can be parallelized)

## Risks and Mitigations

**Risk:** Sync loops between DB and Calendar
**Mitigation:** Extended properties with `source: 'ai-assistant'` flag, comprehensive logging

**Risk:** Pub/Sub webhook requires HTTPS, may be complex to set up
**Mitigation:** Use ngrok for development, document Tailscale HTTPS setup

**Risk:** Calendar watch expires and isn't renewed
**Mitigation:** Auto-renewal background task, monitor watch status, alert on failure

**Risk:** Email sending fails silently
**Mitigation:** Log all send attempts, retry logic, fallback to ntfy notification

**Risk:** Gmail API rate limits
**Mitigation:** Batch digest emails, respect daily sending limits, implement exponential backoff

## Future Enhancements

- [ ] Rich text email editor for custom reports
- [ ] Email templates stored in database (user-customizable)
- [ ] Multiple Calendar sync (work calendar + personal calendar)
- [ ] Calendar sharing with multiple users
- [ ] Email threading for related task notifications
- [ ] Attachment previews in email (images, PDFs)
- [ ] Calendar event reminders sync to ntfy notifications
- [ ] Two-way sync for task priority (Calendar color → DB priority)

## References

- Issue #46: Gmail sending for reports and notifications
- Issue #44: Google Calendar bi-directional sync
- Issue #47: Google Pub/Sub for Calendar webhooks
- PR #53: Google Drive, Gmail reading implementation
- `docs/GOOGLE_WORKSPACE_SETUP.md`: Google API setup guide
- `docs/ARCHITECTURE.md`: Overall system architecture
