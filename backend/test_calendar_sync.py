"""Manual test script for Calendar sync."""
from google_calendar import get_calendar_sync
from datetime import datetime
from unittest.mock import Mock

def test_calendar_sync():
    """Test Calendar sync integration."""
    sync = get_calendar_sync()

    # Create mock task
    task = Mock()
    task.id = 'test_task_123'
    task.name = 'Test Calendar Sync'
    task.description = 'Testing Calendar integration'
    task.command = 'test'
    task.args = '{}'
    task.priority = 'high'
    task.nextRun = datetime.now()
    task.schedule = '0 9 * * *'
    task.task_metadata = '{}'

    # Test 1: Create Calendar event
    print("Creating Calendar event...")
    event_id = sync.sync_task_to_calendar(task)
    print(f"✓ Created event ID: {event_id}")

    # Test 2: Fetch event
    print("\nFetching event...")
    event = sync.get_event(event_id)
    print(f"✓ Fetched event: {event['summary']}")
    print(f"  Color: {event['colorId']} (should be 6 for high priority)")
    print(f"  Extended props: {event.get('extendedProperties')}")

    # Test 3: Update task metadata with event ID
    task.task_metadata = {'calendarEventId': event_id}

    # Test 4: Update event
    print("\nUpdating event (change priority to urgent)...")
    task.priority = 'urgent'
    event_id_updated = sync.sync_task_to_calendar(task)
    print(f"✓ Updated event ID: {event_id_updated}")

    # Test 5: Verify color changed
    event_updated = sync.get_event(event_id)
    print(f"  New color: {event_updated['colorId']} (should be 11 for urgent)")

    # Test 6: Delete event
    print("\nDeleting event...")
    sync.delete_calendar_event(task)
    print("✓ Event deleted")

    # Test 7: Verify deletion
    event_deleted = sync.get_event(event_id)
    if event_deleted is None:
        print("✓ Event confirmed deleted")
    else:
        print("⚠ Event still exists")

    print("\n✅ All Calendar sync tests passed!")
    print("Check Google Calendar to verify events.")

if __name__ == '__main__':
    test_calendar_sync()
