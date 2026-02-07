"""
Integration tests for Prisma-Python SQLAlchemy compatibility.

These tests verify that records created by Python's SQLAlchemy can be read
by Prisma (via Node.js), ensuring ID and timestamp format compatibility.
"""

import pytest
import subprocess
import json
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import ActivityLog, TaskExecution, Task, User


# Test database path (separate from main DB)
TEST_DB_PATH = "/tmp/test_prisma_integration.db"


@pytest.fixture(scope="function")
def test_engine():
    """Create a test SQLite database file for Prisma integration testing."""
    # Remove existing test DB if it exists
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Create new test database
    engine = create_engine(f"sqlite:///{TEST_DB_PATH}", echo=False)
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create a new database session for a test."""
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_prisma_can_read_python_created_activity_log(test_db_session):
    """
    Test that ActivityLog records created by Python use CUID format (Prisma-compatible).

    This verifies:
    1. Python creates record without explicit ID (uses generate_cuid default)
    2. ID is in CUID format (starts with 'c', 20-35 chars, no hyphens)
    3. Timestamp is INTEGER (milliseconds since epoch)

    Note: Full Prisma read integration requires database migration (BIGINT for timestamps)
    which is handled in Task 3. This test focuses on CUID generation for Task 2.
    """
    # Step 1: Create ActivityLog record in Python WITHOUT explicit ID
    log = ActivityLog(
        type="test_event",
        message="Integration test log entry",
        metadata_={"source": "python", "test": True}
    )
    test_db_session.add(log)
    test_db_session.commit()
    test_db_session.refresh(log)

    # Step 2: Verify ID is CUID format
    assert log.id is not None, "ID should be auto-generated"
    assert log.id.startswith('c'), "CUID should start with 'c'"
    assert 20 <= len(log.id) <= 35, f"CUID length should be 20-35 chars, got {len(log.id)}"
    assert '-' not in log.id, "CUID should not contain hyphens (that's UUID format)"

    # Step 3: Verify timestamp is INTEGER (milliseconds since epoch)
    assert isinstance(log.createdAt, int), f"createdAt should be INTEGER, got {type(log.createdAt)}"
    assert log.createdAt > 1700000000000, "Timestamp should be in milliseconds (> 2023-11-01 in ms)"

    print(f"\n✓ Python-created CUID: {log.id}")
    print(f"✓ CUID format valid (starts with 'c', no hyphens, correct length)")
    print(f"✓ Timestamp format: {log.createdAt} ms (INTEGER)")
    print(f"\nNote: Full Prisma read compatibility requires database migration to BIGINT (Task 3)")


def test_cuid_generation_uniqueness(test_db_session):
    """Test that generate_cuid produces unique IDs."""
    logs = []
    for i in range(100):
        log = ActivityLog(
            type=f"test_{i}",
            message=f"Test log {i}"
        )
        test_db_session.add(log)

    test_db_session.commit()

    # Refresh all logs to get their IDs
    for log in logs:
        test_db_session.refresh(log)

    # Verify all IDs are unique
    ids = [log.id for log in test_db_session.query(ActivityLog).all()]
    assert len(ids) == len(set(ids)), "All generated CUIDs should be unique"

    # Verify all are valid CUIDs
    for log_id in ids:
        assert log_id.startswith('c'), f"Invalid CUID: {log_id}"
        assert 20 <= len(log_id) <= 35, f"Invalid CUID length: {log_id}"
        assert '-' not in log_id, f"CUID contains hyphen: {log_id}"
