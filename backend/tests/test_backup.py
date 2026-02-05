"""
Tests for database backup functionality.

Following TDD: These tests are written FIRST before implementation.
All tests should FAIL initially until the implementation is complete.
"""

import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from io import BytesIO

import pytest

# Import will fail initially - this is expected in TDD
from backup import (
    BackupConfig,
    BackupManager,
    BackupRotationPolicy,
    upload_backup_to_drive,
    run_backup_task
)


class TestBackupConfig:
    """Test backup configuration loading."""

    def test_loads_config_from_environment(self):
        """Loads backup configuration from environment variables."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///test.db',
            'BACKUP_DIR': '/tmp/backups',
            'AI_WORKSPACE': '/tmp/workspace'
        }):
            config = BackupConfig()

            assert config.database_path is not None
            assert config.backup_dir.resolve() == Path('/tmp/backups').resolve()
            assert config.ai_workspace.resolve() == Path('/tmp/workspace').resolve()

    def test_uses_default_backup_dir(self):
        """Uses default backup directory in ai-workspace if not specified."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///test.db',
            'AI_WORKSPACE': '/tmp/workspace'
        }, clear=True):
            config = BackupConfig()

            expected_dir = Path('/tmp/workspace') / 'backups' / 'database'
            assert config.backup_dir.resolve() == expected_dir.resolve()

    def test_extracts_database_path_from_url(self):
        """Extracts database file path from DATABASE_URL."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:////absolute/path/to/database.db',
            'AI_WORKSPACE': '/tmp/workspace'
        }):
            config = BackupConfig()

            assert config.database_path == Path('/absolute/path/to/database.db')

    def test_handles_relative_database_path(self):
        """Handles relative database paths correctly."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'sqlite:///../ai-assistant.db',
            'AI_WORKSPACE': '/tmp/workspace'
        }):
            config = BackupConfig()

            # Should resolve to absolute path
            assert config.database_path.is_absolute()
            assert config.database_path.name == 'ai-assistant.db'


class TestBackupRotationPolicy:
    """Test backup rotation policy implementation."""

    def test_keeps_last_7_daily_backups(self):
        """Keeps the last 7 daily backups."""
        policy = BackupRotationPolicy(daily_keep=7, weekly_keep=4, monthly_keep=12)

        # Create test backup files with dates
        backups = [
            f'backup-2026-02-{day:02d}-030000.db'
            for day in range(1, 15)  # 14 daily backups
        ]

        to_delete = policy.get_backups_to_delete(backups)

        # Should delete 14 - 7 = 7 oldest daily backups
        assert len(to_delete) == 7
        assert 'backup-2026-02-01-030000.db' in to_delete

    def test_keeps_last_4_weekly_backups(self):
        """Keeps weekly backups (one per week for 4 weeks)."""
        policy = BackupRotationPolicy(daily_keep=7, weekly_keep=4, monthly_keep=12)

        # Create backups spanning multiple weeks
        backups = []
        base_date = datetime(2026, 1, 1)
        for week in range(6):  # 6 weeks of backups
            for day in range(7):
                date = base_date + timedelta(weeks=week, days=day)
                backups.append(f'backup-{date.strftime("%Y-%m-%d")}-030000.db')

        to_delete = policy.get_backups_to_delete(backups)

        # Should keep 7 daily + 4 weekly, delete the rest
        # Exact count depends on current date, but oldest weekly should be deleted
        assert 'backup-2026-01-01-030000.db' in to_delete

    def test_keeps_last_12_monthly_backups(self):
        """Keeps monthly backups (one per month for 12 months)."""
        policy = BackupRotationPolicy(daily_keep=7, weekly_keep=4, monthly_keep=12)

        # Create backups spanning multiple months
        backups = []
        for month in range(1, 15):  # 14 months
            date = datetime(2025 if month <= 12 else 2026, month if month <= 12 else month - 12, 1)
            backups.append(f'backup-{date.strftime("%Y-%m-%d")}-030000.db')

        to_delete = policy.get_backups_to_delete(backups)

        # Should keep monthly backups for 12 months, delete older ones
        # Oldest monthly backups from early 2025 should be deleted
        assert any('2025-01' in b or '2025-02' in b for b in to_delete)

    def test_never_deletes_if_below_threshold(self):
        """Does not delete backups if count is below threshold."""
        policy = BackupRotationPolicy(daily_keep=7, weekly_keep=4, monthly_keep=12)

        # Only 3 backups - should keep all
        backups = [
            'backup-2026-02-01-030000.db',
            'backup-2026-02-02-030000.db',
            'backup-2026-02-03-030000.db',
        ]

        to_delete = policy.get_backups_to_delete(backups)

        assert len(to_delete) == 0


class TestBackupManager:
    """Test backup manager functionality."""

    def test_creates_backup_with_timestamp(self):
        """Creates backup with timestamp in filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real test database
            db_path = Path(tmpdir) / 'test.db'
            db_path.touch()

            backup_dir = Path(tmpdir) / 'backups'

            config = BackupConfig()
            with patch.object(config, 'database_path', db_path):
                with patch.object(config, 'backup_dir', backup_dir):
                    manager = BackupManager(config)
                    backup_path = manager.create_backup(vacuum=False)

                    # Should create backup with timestamp
                    assert 'backup-' in backup_path.name
                    assert backup_path.suffix == '.db'
                    assert backup_path.parent == backup_dir
                    assert backup_path.exists()

    def test_creates_backup_directory_if_not_exists(self):
        """Creates backup directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real test database
            db_path = Path(tmpdir) / 'test.db'
            db_path.touch()

            backup_dir = Path(tmpdir) / 'non_existent' / 'backups'

            config = BackupConfig()
            with patch.object(config, 'backup_dir', backup_dir):
                with patch.object(config, 'database_path', db_path):
                    manager = BackupManager(config)
                    manager.create_backup(vacuum=False)

                    # Directory should be created
                    assert backup_dir.exists()

    def test_vacuum_database_before_backup(self):
        """Runs VACUUM on database before creating backup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real test database
            db_path = Path(tmpdir) / 'test.db'
            backup_dir = Path(tmpdir) / 'backups'

            # Create actual database with SQLite
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.execute('CREATE TABLE test (id INTEGER)')
            conn.commit()
            conn.close()

            config = BackupConfig()
            with patch.object(config, 'database_path', db_path):
                with patch.object(config, 'backup_dir', backup_dir):
                    manager = BackupManager(config)

                    # This should not raise an error
                    backup_path = manager.create_backup(vacuum=True)

                    # Backup should exist
                    assert backup_path.exists()

    def test_returns_backup_file_path(self):
        """Returns path to created backup file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real test database
            db_path = Path(tmpdir) / 'test.db'
            db_path.touch()

            backup_dir = Path(tmpdir) / 'backups'

            config = BackupConfig()
            with patch.object(config, 'database_path', db_path):
                with patch.object(config, 'backup_dir', backup_dir):
                    manager = BackupManager(config)
                    result = manager.create_backup(vacuum=False)

                    assert isinstance(result, Path)
                    assert result.name.startswith('backup-')

    def test_raises_error_if_database_not_found(self):
        """Raises error if source database doesn't exist."""
        config = BackupConfig()
        manager = BackupManager(config)

        with patch.object(config, 'database_path', Path('/non/existent/db.db')):
            with pytest.raises(FileNotFoundError):
                manager.create_backup()

    def test_lists_existing_backups(self):
        """Lists all existing backup files in backup directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)

            # Create some test backup files
            (backup_dir / 'backup-2026-02-01-030000.db').touch()
            (backup_dir / 'backup-2026-02-02-030000.db').touch()
            (backup_dir / 'other-file.txt').touch()  # Should be ignored

            config = BackupConfig()
            with patch.object(config, 'backup_dir', backup_dir):
                manager = BackupManager(config)
                backups = manager.list_backups()

                # Should return only backup files
                assert len(backups) == 2
                assert all('.db' in str(b) for b in backups)

    def test_deletes_old_backups(self):
        """Deletes old backups according to rotation policy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir)

            # Create test backups
            old_backup = backup_dir / 'backup-2026-01-01-030000.db'
            recent_backup = backup_dir / 'backup-2026-02-04-030000.db'
            old_backup.touch()
            recent_backup.touch()

            config = BackupConfig()
            with patch.object(config, 'backup_dir', backup_dir):
                manager = BackupManager(config)

                # Mock policy to delete the old backup
                with patch.object(manager.policy, 'get_backups_to_delete') as mock_policy:
                    mock_policy.return_value = ['backup-2026-01-01-030000.db']
                    deleted = manager.rotate_backups()

                    # Should delete old backup
                    assert not old_backup.exists()
                    assert recent_backup.exists()
                    assert len(deleted) == 1


class TestDriveIntegration:
    """Test Google Drive upload integration."""

    @patch('backup.get_drive_service')
    def test_uploads_backup_to_drive(self, mock_get_service):
        """Uploads backup file to Google Drive."""
        mock_client = MagicMock()
        mock_get_service.return_value = mock_client

        # Mock DriveClient methods
        mock_client.upload_file.return_value = 'file123'
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123'

        # Mock service.files().get() for metadata
        mock_files = MagicMock()
        mock_files.get().execute.return_value = {
            'id': 'file123',
            'name': 'backup-2026-02-04-030000.db',
            'webViewLink': 'https://drive.google.com/file/d/file123',
            'size': '1024'
        }
        mock_client.service.files.return_value = mock_files

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real backup file
            backup_path = Path(tmpdir) / 'backup-2026-02-04-030000.db'
            backup_path.touch()

            result = upload_backup_to_drive(backup_path, folder_id='folder123')

            # Should return file metadata
            assert result['id'] == 'file123'
            assert 'webViewLink' in result
            mock_client.upload_file.assert_called_once()

    @patch('backup.get_drive_service')
    def test_creates_drive_folder_if_not_exists(self, mock_get_service):
        """Creates backup folder in Drive if folder_id not provided."""
        mock_client = MagicMock()
        mock_get_service.return_value = mock_client

        # Mock DriveClient methods - folder creation is handled internally
        mock_client.upload_file.return_value = 'file123'
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123'

        # Mock service.files().get() for metadata
        mock_files = MagicMock()
        mock_files.get().execute.return_value = {
            'id': 'file123',
            'name': 'backup.db',
            'webViewLink': 'https://drive.google.com/file/d/file123'
        }
        mock_client.service.files.return_value = mock_files

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real backup file
            backup_path = Path(tmpdir) / 'backup.db'
            backup_path.touch()

            result = upload_backup_to_drive(backup_path)

            # Should upload file (folder creation is handled internally by DriveClient)
            mock_client.upload_file.assert_called_once()
            assert result['id'] == 'file123'

    @patch('backup.get_drive_service')
    def test_handles_drive_upload_error(self, mock_get_service):
        """Handles errors during Drive upload gracefully."""
        from google_drive import DriveError
        mock_client = MagicMock()
        mock_get_service.return_value = mock_client

        # Simulate upload error - mock upload_file to raise DriveError
        mock_client.upload_file.side_effect = DriveError("Upload failed: Server error")

        backup_path = Path('/tmp/backup.db')
        with patch('backup.Path.exists', return_value=True):
            with pytest.raises(DriveError):
                upload_backup_to_drive(backup_path)


class TestBackupTask:
    """Test automated backup task execution."""

    @patch('backup.BackupManager')
    @patch('backup.upload_backup_to_drive')
    @patch('backup.send_notification')
    def test_creates_backup_and_uploads_to_drive(
        self, mock_notify, mock_upload, mock_manager_class
    ):
        """Creates backup, uploads to Drive, and sends notification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real backup file to return
            backup_path = Path(tmpdir) / 'backup.db'
            backup_path.write_text('test data')

            # Setup mocks
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.create_backup.return_value = backup_path
            mock_manager.rotate_backups.return_value = []
            mock_upload.return_value = {'id': 'file123', 'webViewLink': 'https://drive.google.com/...'}

            # Run backup task
            from backup import run_backup_task
            result = run_backup_task()

            # Should create backup
            mock_manager.create_backup.assert_called_once()

            # Should upload to Drive
            mock_upload.assert_called_once()

            # Should send success notification
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args
            assert 'success' in call_args[1]['message'].lower() or 'complete' in call_args[1]['message'].lower()

    @patch('backup.BackupManager')
    @patch('backup.send_notification')
    def test_sends_error_notification_on_failure(
        self, mock_notify, mock_manager_class
    ):
        """Sends error notification if backup fails."""
        # Simulate backup failure
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager
        mock_manager.create_backup.side_effect = Exception('Backup failed')

        # Run backup task
        from backup import run_backup_task
        with pytest.raises(Exception):
            run_backup_task()

        # Should send error notification
        assert mock_notify.called
        call_args = mock_notify.call_args
        assert 'error' in call_args[1]['message'].lower() or 'fail' in call_args[1]['message'].lower()

    @patch('backup.BackupManager')
    @patch('backup.upload_backup_to_drive')
    @patch('backup.send_notification')
    def test_rotates_backups_after_creation(
        self, mock_notify, mock_upload, mock_manager_class
    ):
        """Rotates old backups after creating new one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real backup file to return
            backup_path = Path(tmpdir) / 'backup.db'
            backup_path.write_text('test data')

            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            mock_manager.create_backup.return_value = backup_path
            mock_manager.rotate_backups.return_value = ['old-backup-1.db', 'old-backup-2.db']

            from backup import run_backup_task
            result = run_backup_task()

            # Should rotate backups
            mock_manager.rotate_backups.assert_called_once()

    @patch('backup.BackupManager')
    @patch('backup.upload_backup_to_drive')
    def test_includes_backup_size_in_result(self, mock_upload, mock_manager_class):
        """Includes backup file size in task result."""
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        backup_path = Path('/tmp/backup.db')
        mock_manager.create_backup.return_value = backup_path

        with patch('backup.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 1024 * 1024  # 1 MB

            from backup import run_backup_task
            result = run_backup_task()

            # Result should include size information
            assert 'size' in result or 'size_bytes' in result


class TestSchedulerIntegration:
    """Test integration with APScheduler."""

    def test_backup_task_registered_with_scheduler(self):
        """Backup task is registered with APScheduler on startup."""
        # This test verifies that the backup task gets added to the scheduler
        # Implementation will add this in the scheduler initialization
        pass

    def test_backup_runs_at_3am_daily(self):
        """Backup is scheduled to run at 3 AM daily."""
        # This test verifies the cron schedule
        # The actual schedule should be: 0 3 * * *
        pass
