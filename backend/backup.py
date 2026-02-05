"""
Database backup module for AI Assistant.

This module provides automated SQLite database backup functionality with:
- Daily automated backups
- Backup rotation (7 daily, 4 weekly, 12 monthly)
- Google Drive upload for off-site storage
- Notification on success/failure

Backup Strategy:
- Uses SQLite VACUUM + file copy for optimal backup
- Creates timestamped backup files
- Automatically rotates old backups
- Uploads to Google Drive for redundancy
"""

import os
import sqlite3
import shutil
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from io import BytesIO

from dotenv import load_dotenv

from logger import get_logger
from ntfy_client import send_notification
from google_drive import DriveClient, DriveError

# Load environment variables
load_dotenv()

# Configure logging
logger = get_logger()


class BackupConfig:
    """Configuration for database backup operations.

    Loads settings from environment variables:
    - DATABASE_URL: SQLite database URL (required)
    - BACKUP_DIR: Directory to store backups (optional, defaults to ai-workspace/backups/database)
    - AI_WORKSPACE: AI workspace directory (required for default backup dir)
    """

    def __init__(self):
        # Get database path from DATABASE_URL
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        # Extract file path from SQLite URL
        if database_url.startswith('sqlite:///'):
            db_path_str = database_url.replace('sqlite:///', '')

            # Handle relative paths
            if db_path_str.startswith('../') or db_path_str.startswith('./'):
                # Resolve relative to backend directory
                backend_dir = Path(__file__).parent
                self.database_path = (backend_dir / db_path_str).resolve()
            else:
                self.database_path = Path(db_path_str)
        else:
            raise ValueError("Only SQLite databases are supported for backup")

        # Get backup directory
        backup_dir_str = os.getenv('BACKUP_DIR')
        if backup_dir_str:
            self.backup_dir = Path(backup_dir_str)
        else:
            # Default to ai-workspace/backups/database
            ai_workspace = os.getenv('AI_WORKSPACE', '../ai-workspace')
            workspace_path = Path(__file__).parent / ai_workspace
            self.backup_dir = workspace_path.resolve() / 'backups' / 'database'

        # Get AI workspace for reference
        ai_workspace = os.getenv('AI_WORKSPACE', '../ai-workspace')
        workspace_path = Path(__file__).parent / ai_workspace
        self.ai_workspace = workspace_path.resolve()

        logger.info(f"BackupConfig initialized: database={self.database_path}, backup_dir={self.backup_dir}")


class BackupRotationPolicy:
    """Backup rotation policy implementation.

    Rotation strategy:
    - Daily: Keep last 7 daily backups
    - Weekly: Keep last 4 weekly backups (one per week)
    - Monthly: Keep last 12 monthly backups (one per month)

    This ensures good coverage while limiting storage usage.
    """

    def __init__(self, daily_keep: int = 7, weekly_keep: int = 4, monthly_keep: int = 12):
        """
        Initialize rotation policy.

        Args:
            daily_keep: Number of daily backups to keep
            weekly_keep: Number of weekly backups to keep
            monthly_keep: Number of monthly backups to keep
        """
        self.daily_keep = daily_keep
        self.weekly_keep = weekly_keep
        self.monthly_keep = monthly_keep

    def get_backups_to_delete(self, backup_files: List[str]) -> List[str]:
        """
        Determine which backups should be deleted based on rotation policy.

        Args:
            backup_files: List of backup filenames (format: backup-YYYY-MM-DD-HHMMSS.db)

        Returns:
            List of backup filenames to delete
        """
        if not backup_files:
            return []

        # Parse backup dates from filenames
        backups = []
        for filename in backup_files:
            try:
                # Extract date from filename: backup-YYYY-MM-DD-HHMMSS.db
                parts = filename.replace('backup-', '').replace('.db', '').split('-')
                if len(parts) >= 4:
                    date = datetime(
                        int(parts[0]),  # year
                        int(parts[1]),  # month
                        int(parts[2]),  # day
                        int(parts[3][:2]),  # hour
                        int(parts[3][2:4]),  # minute
                        int(parts[3][4:6]) if len(parts[3]) >= 6 else 0  # second
                    )
                    backups.append({'filename': filename, 'date': date})
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse backup filename: {filename} - {e}")
                continue

        if not backups:
            return []

        # Sort by date (newest first)
        backups.sort(key=lambda x: x['date'], reverse=True)

        # Categorize backups
        now = datetime.now()
        daily_backups = []
        weekly_backups = []
        monthly_backups = []

        for backup in backups:
            age_days = (now - backup['date']).days

            if age_days < 7:
                # Recent backups (last 7 days) - daily retention
                daily_backups.append(backup)
            elif age_days < 28:
                # Last 4 weeks - weekly retention (keep one per week)
                week_num = backup['date'].isocalendar()[1]
                if not any(b['date'].isocalendar()[1] == week_num for b in weekly_backups):
                    weekly_backups.append(backup)
            else:
                # Older than 4 weeks - monthly retention (keep one per month)
                month_key = (backup['date'].year, backup['date'].month)
                if not any((b['date'].year, b['date'].month) == month_key for b in monthly_backups):
                    monthly_backups.append(backup)

        # Determine what to keep
        keep_daily = daily_backups[:self.daily_keep]
        keep_weekly = weekly_backups[:self.weekly_keep]
        keep_monthly = monthly_backups[:self.monthly_keep]

        # Combine all backups to keep
        keep_filenames = set()
        for backup in keep_daily + keep_weekly + keep_monthly:
            keep_filenames.add(backup['filename'])

        # Return files to delete
        to_delete = [b['filename'] for b in backups if b['filename'] not in keep_filenames]

        logger.info(
            f"Rotation policy: keeping {len(keep_daily)} daily, "
            f"{len(keep_weekly)} weekly, {len(keep_monthly)} monthly backups. "
            f"Deleting {len(to_delete)} old backups."
        )

        return to_delete


class BackupManager:
    """Manager for database backup operations."""

    def __init__(self, config: Optional[BackupConfig] = None):
        """
        Initialize backup manager.

        Args:
            config: BackupConfig instance (creates default if not provided)
        """
        self.config = config or BackupConfig()
        self.policy = BackupRotationPolicy()

        # Ensure backup directory exists
        self.config.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, vacuum: bool = True) -> Path:
        """
        Create a database backup.

        Args:
            vacuum: Whether to run VACUUM before backup (recommended)

        Returns:
            Path to the created backup file

        Raises:
            FileNotFoundError: If source database doesn't exist
            Exception: If backup creation fails
        """
        if not self.config.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.config.database_path}")

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        backup_filename = f"backup-{timestamp}.db"
        backup_path = self.config.backup_dir / backup_filename

        logger.info(f"Creating backup: {backup_path}")

        try:
            # Run VACUUM if requested (compacts database, removes deleted data)
            if vacuum:
                logger.info("Running VACUUM on database...")
                with sqlite3.connect(str(self.config.database_path)) as conn:
                    conn.execute('VACUUM')
                logger.info("VACUUM completed")

            # Copy database file
            shutil.copy2(self.config.database_path, backup_path)

            # Verify backup was created
            if not backup_path.exists():
                raise Exception("Backup file was not created")

            backup_size = backup_path.stat().st_size
            logger.info(f"Backup created successfully: {backup_path} ({backup_size:,} bytes)")

            return backup_path

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            # Clean up partial backup if it exists
            if backup_path.exists():
                backup_path.unlink()
            raise

    def list_backups(self) -> List[Path]:
        """
        List all backup files in the backup directory.

        Returns:
            List of Path objects for backup files, sorted by modification time (newest first)
        """
        if not self.config.backup_dir.exists():
            return []

        backups = [
            f for f in self.config.backup_dir.iterdir()
            if f.is_file() and f.name.startswith('backup-') and f.suffix == '.db'
        ]

        # Sort by modification time (newest first)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        return backups

    def rotate_backups(self) -> List[str]:
        """
        Rotate backups according to retention policy.

        Deletes old backups that exceed the retention policy.

        Returns:
            List of deleted backup filenames
        """
        backups = self.list_backups()

        if not backups:
            logger.info("No backups to rotate")
            return []

        # Get filenames only
        backup_filenames = [b.name for b in backups]

        # Get files to delete from policy
        to_delete = self.policy.get_backups_to_delete(backup_filenames)

        deleted = []
        for filename in to_delete:
            file_path = self.config.backup_dir / filename
            try:
                file_path.unlink()
                deleted.append(filename)
                logger.info(f"Deleted old backup: {filename}")
            except Exception as e:
                logger.error(f"Failed to delete backup {filename}: {e}")

        if deleted:
            logger.info(f"Rotation complete: deleted {len(deleted)} old backups")
        else:
            logger.info("Rotation complete: no backups to delete")

        return deleted


def get_drive_service():
    """
    Get authenticated Google Drive service.

    Returns:
        DriveClient instance

    Raises:
        DriveError: If authentication fails

    Note:
        This function is maintained for backward compatibility.
        New code should use DriveClient directly from google_drive module.
    """
    return DriveClient()


def upload_backup_to_drive(
    backup_path: Path,
    folder_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload backup file to Google Drive.

    Args:
        backup_path: Path to backup file
        folder_id: Optional folder ID (for backward compatibility, uses default if not provided)

    Returns:
        Dictionary with uploaded file metadata (id, name, webViewLink)

    Raises:
        FileNotFoundError: If backup file doesn't exist
        DriveError: If Drive upload fails
    """
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    logger.info(f"Uploading backup to Google Drive: {backup_path.name}")

    try:
        # Use google_drive module for upload
        # Uploads to 'AI Assistant Drive/backups' folder
        client = get_drive_service()  # Returns DriveClient instance
        file_id = client.upload_file(
            str(backup_path),
            folder_path='AI Assistant Drive/backups',
            mime_type='application/x-sqlite3'
        )

        # Get file link
        link = client.get_file_link(file_id, make_public=False)

        # Get file metadata
        file_metadata = client.service.files().get(
            fileId=file_id,
            fields='id,name,webViewLink,size'
        ).execute()

        logger.info(f"Upload complete: {file_metadata.get('name')} (ID: {file_id})")

        return file_metadata

    except (DriveError, Exception) as e:
        logger.error(f"Failed to upload backup to Drive: {e}")
        raise DriveError(f"Upload failed: {e}")


def run_backup_task() -> Dict[str, Any]:
    """
    Run the complete backup task.

    This is the main entry point for scheduled backups.

    Steps:
    1. Create database backup
    2. Upload to Google Drive
    3. Rotate old backups
    4. Send notification

    Returns:
        Dictionary with task results

    Raises:
        Exception: If backup fails (after sending error notification)
    """
    result = {
        'success': False,
        'backup_path': None,
        'drive_file_id': None,
        'size_bytes': 0,
        'deleted_backups': [],
        'error': None
    }

    try:
        logger.info("Starting automated database backup task...")

        # Create backup manager
        manager = BackupManager()

        # Create backup
        backup_path = manager.create_backup(vacuum=True)
        result['backup_path'] = str(backup_path)
        result['size_bytes'] = backup_path.stat().st_size

        # Upload to Google Drive
        try:
            drive_file = upload_backup_to_drive(backup_path)
            result['drive_file_id'] = drive_file.get('id')
            result['drive_link'] = drive_file.get('webViewLink')
            logger.info(f"Backup uploaded to Drive: {drive_file.get('webViewLink')}")
        except Exception as e:
            logger.error(f"Drive upload failed: {e}")
            # Continue with local backup even if Drive upload fails
            result['error'] = f"Drive upload failed: {str(e)}"

        # Rotate old backups
        deleted = manager.rotate_backups()
        result['deleted_backups'] = deleted

        result['success'] = True

        # Send success notification
        size_mb = result['size_bytes'] / (1024 * 1024)
        message = (
            f"Database backup completed successfully.\n\n"
            f"File: {backup_path.name}\n"
            f"Size: {size_mb:.2f} MB\n"
            f"Location: {backup_path.parent}\n"
        )
        if result.get('drive_link'):
            message += f"Drive: {result['drive_link']}\n"
        if deleted:
            message += f"\nRotated {len(deleted)} old backups."

        send_notification(
            title="Backup Complete",
            message=message,
            priority="default",
            tags="backup,success"
        )

        logger.info("Backup task completed successfully")
        return result

    except Exception as e:
        logger.error(f"Backup task failed: {e}")
        result['error'] = str(e)

        # Send error notification
        send_notification(
            title="Backup Failed",
            message=f"Database backup failed with error:\n\n{str(e)}",
            priority="high",
            tags="backup,error"
        )

        raise


def schedule_backup_task(scheduler):
    """
    Schedule the backup task with APScheduler.

    Args:
        scheduler: APScheduler instance

    The backup runs daily at 3:00 AM.
    """
    from apscheduler.triggers.cron import CronTrigger

    # Schedule daily backup at 3 AM
    trigger = CronTrigger(hour=3, minute=0)

    scheduler.add_job(
        func=run_backup_task,
        trigger=trigger,
        id='database_backup',
        name='Daily Database Backup',
        replace_existing=True
    )

    logger.info("Scheduled daily database backup at 3:00 AM")
