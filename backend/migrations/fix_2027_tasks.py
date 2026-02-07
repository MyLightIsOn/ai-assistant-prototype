#!/usr/bin/env python3
"""
Fix tasks scheduled for 2027 that should be 2026.

This migration finds tasks with:
- nextRun in 2027
- Created before Feb 7, 2026 (day after max intended run)
- One-time tasks (specific day/month in schedule)

And updates them to 2026.

Usage:
    python3 backend/migrations/fix_2027_tasks.py
"""

import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import SessionLocal
from models import Task


def is_one_time_task(schedule: str) -> bool:
    """Check if task is one-time based on cron schedule."""
    parts = schedule.split()
    if len(parts) != 5:
        return False

    # Cron format: minute hour day month day_of_week
    day = parts[2]
    month = parts[3]

    # If both day and month are specific (not wildcards), it's one-time
    return day != '*' and month != '*'


def fix_2027_tasks():
    """Fix tasks scheduled for 2027 that should be 2026."""
    db = SessionLocal()

    try:
        print("=" * 70)
        print("  Database Migration: Fix 2027 Task Scheduling")
        print("=" * 70)
        print()

        # Find tasks scheduled in 2027 created before end of Feb 2026
        cutoff = datetime(2026, 3, 1)
        tasks = db.query(Task).filter(
            Task.nextRun >= datetime(2027, 1, 1),
            Task.nextRun < datetime(2028, 1, 1),
            Task.createdAt < cutoff
        ).all()

        if not tasks:
            print("✓ No tasks found scheduled for 2027")
            print("  Database is already correct.")
            return 0

        print(f"Found {len(tasks)} task(s) scheduled for 2027:")
        print()

        fixed_count = 0
        skipped_count = 0

        for task in tasks:
            # Check if one-time task
            if is_one_time_task(task.schedule):
                old_date = task.nextRun
                # Update year from 2027 to 2026
                task.nextRun = task.nextRun.replace(year=2026)
                fixed_count += 1

                print(f"  ✓ Fixed task: {task.name}")
                print(f"    ID: {task.id}")
                print(f"    Schedule: {task.schedule}")
                print(f"    Old nextRun: {old_date}")
                print(f"    New nextRun: {task.nextRun}")
                print()
            else:
                print(f"  ⊘ Skipped (recurring task): {task.name}")
                print(f"    ID: {task.id}")
                print(f"    Schedule: {task.schedule}")
                print(f"    nextRun: {task.nextRun}")
                print()
                skipped_count += 1

        if fixed_count > 0:
            # Commit changes
            db.commit()
            print("=" * 70)
            print(f"✅ Migration Complete: Fixed {fixed_count} task(s)")
            if skipped_count > 0:
                print(f"   Skipped {skipped_count} recurring task(s) (intentionally in 2027)")
            print("=" * 70)
            print()
            print("Next steps:")
            print("  1. Restart the backend: python3 backend/main.py")
            print("  2. Run scheduler sync: python3 backend/manual_scheduler_sync.py")
            print("  3. Verify tasks now show 2026 dates")
            print()
            return 0
        else:
            print("=" * 70)
            print(f"ℹ️  No one-time tasks found to fix")
            if skipped_count > 0:
                print(f"   Found {skipped_count} recurring task(s) in 2027 (this is normal)")
            print("=" * 70)
            return 0

    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        db.close()


if __name__ == '__main__':
    sys.exit(fix_2027_tasks())
