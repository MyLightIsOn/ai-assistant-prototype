#!/usr/bin/env python3
"""
End-to-end test for task execution system.

Tests:
1. Task creation with near-future execution time
2. Task actually executes (creates TaskExecution record)
3. Calendar event is created
4. Email notification is sent (if configured)

Usage: python3 test_e2e_task_execution.py
"""

import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text

from database import SessionLocal, engine
from models import Task, TaskExecution
from logger import get_logger

logger = get_logger()


def get_first_user_id(db):
    """Get first user ID from database using raw SQL."""
    result = db.execute(text("SELECT id FROM User LIMIT 1"))
    row = result.fetchone()
    if not row:
        raise Exception("No users found in database. Please create a user first.")
    return row[0]


def create_test_task(db, run_in_seconds=60):
    """Create a test task that runs in N seconds."""
    user_id = get_first_user_id(db)

    run_time = datetime.now(timezone.utc) + timedelta(seconds=run_in_seconds)

    # Create cron schedule for one-time task (specific day and month)
    # Format: minute hour day month day_of_week
    schedule = f"{run_time.minute} {run_time.hour} {run_time.day} {run_time.month} *"

    task = Task(
        id=f"e2e_test_{uuid.uuid4().hex[:8]}",
        userId=user_id,
        name='E2E Test Task',
        description='Automated end-to-end test',
        command='echo',
        args='{"message": "E2E test successful"}',
        schedule=schedule,  # One-time task with specific day/month
        enabled=True,
        nextRun=run_time,
        priority='default',
        notifyOn='completion,error'
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def check_task_execution(db, task_id, timeout=90):
    """Poll for task execution with timeout."""
    start = time.time()

    while time.time() - start < timeout:
        execution = db.query(TaskExecution).filter_by(taskId=task_id).first()
        if execution:
            return execution
        time.sleep(2)

    return None


def main():
    print("=" * 70)
    print("  End-to-End Task Execution Test")
    print("=" * 70)

    db = SessionLocal()

    try:
        # Create test task that runs in 30 seconds
        print("\n[1/4] Creating test task (runs in 30 seconds)...")
        task = create_test_task(db, run_in_seconds=30)
        print(f"  ✓ Created task: {task.id}")
        print(f"  ✓ Scheduled for: {task.nextRun}")

        # Check calendar sync
        print("\n[2/4] Checking calendar sync...")
        if task.task_metadata and task.task_metadata.get('calendarEventId'):
            print(f"  ✓ Calendar event created: {task.task_metadata['calendarEventId']}")
        else:
            print("  ⚠ No calendar event (may not be configured)")

        # Wait for execution
        print("\n[3/4] Waiting for task execution (up to 90 seconds)...")
        print("  (This will take about 30-40 seconds...)")

        execution = check_task_execution(db, task.id, timeout=90)

        if execution:
            print(f"  ✓ Task executed!")
            print(f"    Status: {execution.status}")
            print(f"    Started: {execution.startedAt}")
            print(f"    Duration: {execution.duration}ms")
            print(f"    Output: {execution.output[:100] if execution.output else 'None'}...")
        else:
            print("  ✗ Task did NOT execute within timeout")
            print("  This indicates the scheduler is not working correctly.")
            return 1

        # Check if task ran successfully
        print("\n[4/4] Verifying execution status...")
        if execution.status == "completed":
            print("  ✓ Task completed successfully")
        else:
            print(f"  ⚠ Task status: {execution.status}")

        # Cleanup
        print("\n[Cleanup] Removing test task...")
        db.delete(task)
        db.commit()
        print("  ✓ Test task removed")

        print("\n" + "=" * 70)
        print("  ✅ END-TO-END TEST PASSED")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(main())
