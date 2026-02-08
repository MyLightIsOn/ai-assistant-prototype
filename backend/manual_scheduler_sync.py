#!/usr/bin/env python3
"""
Manually trigger scheduler sync.
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from scheduler import TaskScheduler
from models import Task

def main():
    print("Creating scheduler instance...")
    scheduler = TaskScheduler(engine)

    print("Starting scheduler...")
    scheduler.start()

    # Inspect tasks before sync
    print("\nInspecting tasks in database...")
    db = SessionLocal()
    try:
        tasks = db.query(Task).filter_by(enabled=True).all()
        for task in tasks:
            is_one_time = scheduler._is_one_time_task(task)
            print(f"  Task {task.id}:")
            print(f"    Name: {task.name}")
            print(f"    Schedule: {task.schedule}")
            print(f"    Next Run: {task.nextRun}")
            print(f"    Is One-Time: {is_one_time}")
    finally:
        db.close()

    print("\nSyncing tasks from database...")
    scheduler.sync_tasks()

    print("✅ Scheduler sync complete!")

    # List jobs
    jobs = scheduler.scheduler.get_jobs()
    print(f"\n{len(jobs)} jobs scheduled:")
    for job in jobs:
        print(f"  - {job.id}: {job.name}")
        print(f"    Trigger: {type(job.trigger).__name__}")
        print(f"    Next run: {job.next_run_time}")

    print("\nScheduler will continue running in the main backend process.")
    return 0

if __name__ == '__main__':
    sys.exit(main())
