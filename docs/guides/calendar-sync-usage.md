# Calendar Sync - Usage Guide

This guide explains the bi-directional sync between database tasks and Google Calendar.

## Architecture

**Hybrid Sync:**
- **DB → Calendar:** Immediate (event-driven via API routes)
- **Calendar → DB:** Real-time (event-driven via Pub/Sub webhooks)
- **Loop Prevention:** Extended properties (`source: 'ai-assistant'`)

## Setup

### 1. Configure Environment Variables

Add to `backend/.env`:

```bash
GOOGLE_CALENDAR_ID=primary
GOOGLE_PROJECT_ID=ai-assistant-123456
GOOGLE_PUBSUB_TOPIC=calendar-notifications
WEBHOOK_BASE_URL=https://your-tailscale-hostname:8000
```

### 2. Setup Google Cloud Pub/Sub

See `docs/GOOGLE_WORKSPACE_SETUP.md` for complete setup instructions.

**Quick steps:**

1. Create Pub/Sub topic: `calendar-notifications`
2. Create push subscription pointing to: `{WEBHOOK_BASE_URL}/api/google/calendar/webhook`
3. Enable Calendar API in Google Cloud Console

### 3. Setup Calendar Watch

Calendar watch is automatically registered on backend startup, but you can also trigger manually:

```python
from google_calendar import get_calendar_sync

calendar_sync = get_calendar_sync()
calendar_sync.setup_watch()
```

Watch expires after 7 days and auto-renews.

### 4. Verify HTTPS

Pub/Sub requires HTTPS endpoints:

**Development:**
```bash
# Use ngrok
ngrok http 8000

# Update Pub/Sub subscription with ngrok URL
# Update WEBHOOK_BASE_URL in .env
```

**Production:**
- Configure Tailscale HTTPS
- Or use Caddy reverse proxy

## How It Works

### DB → Calendar Sync

When you create/update/delete a task via the web UI:

1. Frontend API route calls backend `/api/calendar/sync`
2. Backend creates/updates/deletes Calendar event
3. Event includes extended properties:
   ```json
   {
     "extendedProperties": {
       "private": {
         "taskId": "task_123",
         "source": "ai-assistant"
       }
     }
   }
   ```

**Color Coding:**
- Low priority: Lavender (color 1)
- Default: Green (color 10)
- High priority: Orange (color 6)
- Urgent: Red (color 11)

### Calendar → DB Sync

When you create/update/delete an event in Google Calendar:

1. Google sends Pub/Sub notification to webhook
2. Webhook fetches event from Calendar API
3. Checks `source` property (if `ai-assistant`, ignores to prevent loop)
4. Creates/updates/deletes task in database

**Loop Prevention:**

```python
# Before processing Calendar event
if event.get('extendedProperties', {}).get('private', {}).get('source') == 'ai-assistant':
    return  # Ignore our own events
```

## Usage

### Create Task (Auto-syncs to Calendar)

```bash
# Via web UI
curl -X POST http://localhost:3000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Backup",
    "schedule": "0 3 * * *",
    "priority": "high"
  }'
```

→ Creates Calendar event at next scheduled run time with orange color

### Update Task (Auto-syncs to Calendar)

```bash
curl -X PUT http://localhost:3000/api/tasks/task_123 \
  -H "Content-Type: application/json" \
  -d '{
    "priority": "urgent"
  }'
```

→ Updates Calendar event color to red

### Delete Task (Auto-removes from Calendar)

```bash
curl -X DELETE http://localhost:3000/api/tasks/task_123
```

→ Removes Calendar event

### Create Event in Calendar (Auto-creates Task)

1. Open Google Calendar
2. Create new event: "Data Sync"
3. Set time, add description

→ Task created in database with same name and schedule

## Troubleshooting

### Events not appearing in Calendar

Check logs:
```bash
tail -f logs/backend.log | grep calendar
```

Verify Calendar sync endpoint:
```bash
curl -X POST http://localhost:8000/api/calendar/sync \
  -H "Content-Type: application/json" \
  -d '{"taskId": "task_123"}'
```

### Calendar changes not creating tasks

1. Verify Pub/Sub subscription is active
2. Check webhook endpoint is accessible (HTTPS required)
3. Review Pub/Sub delivery attempts in Google Cloud Console
4. Check webhook logs for errors

### Sync loops (duplicate events)

Verify extended properties are set correctly:

```python
from google_calendar import get_calendar_sync

sync = get_calendar_sync()
event = sync.get_event('event_id')
print(event['extendedProperties'])
# Should include: {'private': {'source': 'ai-assistant'}}
```

### Calendar watch expired

Watch auto-renews, but can manually renew:

```python
from google_calendar import get_calendar_sync

sync = get_calendar_sync()
sync.setup_watch()
```

## Testing

### Unit Tests

```bash
cd backend
pytest tests/test_google_calendar.py -v
pytest tests/test_calendar_webhook.py -v
```

### Integration Test (Manual)

1. Create task in web UI
2. Check Google Calendar for new event
3. Verify event color matches priority
4. Update task priority, verify color changes
5. Create event in Calendar
6. Check database for new task
7. Delete event in Calendar
8. Verify task deleted from database

### Webhook Test

```bash
# Send test Pub/Sub message
curl -X POST http://localhost:8000/api/google/calendar/webhook \
  -H "X-Goog-Resource-State: exists" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "data": "eyJyZXNvdXJjZUlkIjogImV2ZW50XzEyMzQ1In0="
    }
  }'
```

## Known Limitations

- Calendar watch expires every 7 days (auto-renews)
- Pub/Sub requires HTTPS (use ngrok for dev)
- Complex cron → Calendar recurrence conversion not implemented (creates individual events)
- Timezone hardcoded to America/Los_Angeles (TODO: make configurable)

## Future Enhancements

- [ ] Support recurring Calendar events → cron conversion
- [ ] Configurable timezone
- [ ] Multiple calendar sync
- [ ] Calendar sharing with multiple users
- [ ] Sync task completion status to Calendar
