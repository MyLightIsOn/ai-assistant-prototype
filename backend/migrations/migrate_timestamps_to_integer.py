"""
Migrate timestamp columns from TEXT/DATETIME to INTEGER format.

This script converts existing TEXT-format timestamps to Unix milliseconds (INTEGER)
to ensure Prisma compatibility.

DESTRUCTIVE: Backs up database before migration.
"""

import os
import sys
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DB_PATH = os.getenv('DB_PATH', os.path.join(os.path.dirname(__file__), '../../ai-assistant.db'))


def backup_database():
    """Create backup of database before migration."""
    backup_path = f"{DB_PATH}.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(DB_PATH, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path


def parse_timestamp(value):
    """Parse TEXT timestamp to Unix milliseconds."""
    if isinstance(value, int):
        # Already integer, check if it's in milliseconds
        if value > 10000000000:  # Already milliseconds
            return value
        else:  # Seconds, convert to milliseconds
            return value * 1000

    if isinstance(value, str):
        # Parse ISO format: "2026-02-07 18:09:40.331993"
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1000)
        except:
            print(f"⚠️  Failed to parse timestamp: {value}")
            return None

    return None


def migrate_table(conn, table_name, columns):
    """Migrate timestamp columns in a table."""
    cursor = conn.cursor()

    print(f"\n📊 Migrating table: {table_name}")

    # Get all column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    all_columns = [row[1] for row in cursor.fetchall()]

    # Read all data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    if not rows:
        print(f"  ℹ️  Table is empty, skipping")
        return

    print(f"  Found {len(rows)} records")

    # Create temporary table with INTEGER timestamp columns
    temp_table = f"{table_name}_temp"

    # Get original schema
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    original_schema = cursor.fetchone()[0]

    # Modify schema for temp table (replace DATETIME with INTEGER for timestamp columns)
    temp_schema = original_schema.replace(f'"{table_name}"', f'"{temp_table}"')
    for col in columns:
        # Replace DATETIME with INTEGER for timestamp columns
        temp_schema = temp_schema.replace(f'"{col}" DATETIME', f'"{col}" INTEGER')

    cursor.execute(temp_schema)

    # Convert and insert data
    converted = 0
    failed = 0

    for row in rows:
        row_dict = dict(zip(all_columns, row))

        # Convert timestamp columns
        for col in columns:
            if col in row_dict and row_dict[col] is not None:
                converted_value = parse_timestamp(row_dict[col])
                if converted_value:
                    row_dict[col] = converted_value
                    converted += 1
                else:
                    failed += 1

        # Insert into temp table
        placeholders = ','.join(['?' for _ in all_columns])
        columns_str = ','.join([f'"{col}"' for col in all_columns])
        values = [row_dict[col] for col in all_columns]

        cursor.execute(
            f"INSERT INTO {temp_table} ({columns_str}) VALUES ({placeholders})",
            values
        )

    # Drop original table and rename temp
    cursor.execute(f"DROP TABLE {table_name}")
    cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")

    print(f"  ✅ Converted {converted} timestamps, {failed} failures")


def main():
    """Run migration."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)

    print("=" * 80)
    print("TIMESTAMP MIGRATION: TEXT/DATETIME → INTEGER (Unix milliseconds)")
    print("=" * 80)

    # Backup first
    backup_path = backup_database()

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    try:
        # Migrate each table
        tables_to_migrate = {
            'User': ['createdAt', 'updatedAt'],
            'Session': ['expires'],
            'Task': ['createdAt', 'updatedAt', 'lastRun', 'nextRun'],
            'TaskExecution': ['startedAt', 'completedAt'],
            'ActivityLog': ['createdAt'],
            'Notification': ['sentAt', 'readAt'],
            'AiMemory': ['createdAt', 'updatedAt'],
            'DigestSettings': ['createdAt', 'updatedAt']
        }

        for table, columns in tables_to_migrate.items():
            try:
                migrate_table(conn, table, columns)
            except sqlite3.OperationalError as e:
                if 'no such table' in str(e):
                    print(f"  ℹ️  Table {table} doesn't exist, skipping")
                else:
                    raise

        conn.commit()

        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE")
        print("=" * 80)
        print(f"\nBackup saved: {backup_path}")
        print(f"\nTo rollback: cp {backup_path} {DB_PATH}")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        print(f"\nRestoring backup...")
        shutil.copy2(backup_path, DB_PATH)
        print("✅ Database restored from backup")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
