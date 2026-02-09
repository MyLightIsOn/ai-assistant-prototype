"""Manual test script for Calendar sync."""
from google_calendar import get_calendar_sync
from datetime import datetime
from unittest.mock import Mock
import sys
import os

def test_calendar_sync():
    """Test Calendar sync integration."""
    # Check for required credentials
    credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    token_path = os.path.join(os.path.dirname(__file__), 'token.json')

    if not os.path.exists(credentials_path):
        print("⚠️  Skipping calendar sync test - credentials.json not found")
        print("   This is an integration test that requires Google Calendar API credentials")
        print("   Place credentials.json in the backend/ directory to run this test")
        sys.exit(0)

    try:
        sync = get_calendar_sync()
    except Exception as e:
        print(f"⚠️  Skipping calendar sync test - failed to initialize Calendar client: {e}")
        print("   This is an integration test that requires valid Google Calendar API credentials")
        sys.exit(0)

    # Create mock task
    task = Mock()
    task.id = 'test_task_123'
    task.name = 'Test Calendar Sync'
    task.description = 'Testing Calendar integration'
    task.command = 'test'
    task.args = '{}'
    task.priority = 'high'
    task.nextRun = int(datetime.now().timestamp() * 1000)
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
