"""
Tests for Google Drive integration module.

Following TDD: These tests are written FIRST before implementation.
All tests should FAIL initially until the implementation is complete.
"""

import os
import json
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Import will succeed - this is expected in TDD
from google_drive import (
    DriveClient,
    DriveConfig,
    DriveError,
    upload_file,
    download_file,
    archive_old_logs,
    get_drive_link
)


class TestDriveConfig:
    """Test configuration loading for Google Drive client."""

    def test_loads_credentials_from_file(self):
        """Loads OAuth credentials from google_user_credentials.json."""
        with patch('os.path.exists', return_value=True):
            config = DriveConfig()

            # Should resolve to absolute path in backend directory
            assert config.credentials_file.endswith('google_user_credentials.json')

    def test_raises_error_when_credentials_missing(self):
        """Raises error if credentials file does not exist."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(DriveError, match="Credentials file not found"):
                DriveConfig()

    def test_uses_custom_credentials_path(self):
        """Allows custom credentials file path."""
        with patch('os.path.exists', return_value=True):
            config = DriveConfig(credentials_file='/custom/path/creds.json')

            assert config.credentials_file == '/custom/path/creds.json'


class TestDriveClient:
    """Test Google Drive client initialization and authentication."""

    @patch('google_drive.build')
    @patch('google_drive.Credentials.from_authorized_user_file')
    def test_initializes_with_valid_credentials(self, mock_creds, mock_build):
        """Initializes Drive API client with valid OAuth credentials."""
        mock_creds_obj = Mock()
        mock_creds_obj.valid = True
        mock_creds.return_value = mock_creds_obj

        mock_service = Mock()
        mock_build.return_value = mock_service

        client = DriveClient()

        assert client.service == mock_service
        mock_build.assert_called_once_with('drive', 'v3', credentials=mock_creds_obj)

    @patch('google_drive.build')
    @patch('google_drive.Credentials.from_authorized_user_file')
    @patch('builtins.open', create=True)
    def test_refreshes_expired_credentials(self, mock_open, mock_creds, mock_build):
        """Refreshes OAuth token if expired but has refresh token."""
        mock_creds_obj = Mock()
        mock_creds_obj.valid = False
        mock_creds_obj.expired = True
        mock_creds_obj.refresh_token = 'test-refresh-token'
        mock_creds_obj.to_json.return_value = '{"token": "new-token"}'
        mock_creds.return_value = mock_creds_obj

        mock_service = Mock()
        mock_build.return_value = mock_service

        client = DriveClient()

        # Should refresh credentials
        mock_creds_obj.refresh.assert_called_once()

    @patch('google_drive.Credentials.from_authorized_user_file')
    def test_raises_error_when_credentials_invalid(self, mock_creds):
        """Raises error when credentials are invalid and cannot be refreshed."""
        mock_creds_obj = Mock()
        mock_creds_obj.valid = False
        mock_creds_obj.expired = True
        mock_creds_obj.refresh_token = None
        mock_creds.return_value = mock_creds_obj

        with pytest.raises(DriveError, match="Invalid credentials"):
            DriveClient()


class TestUploadFile:
    """Test file upload functionality."""

    @patch('google_drive.DriveClient')
    @patch('os.path.exists', return_value=True)
    def test_uploads_file_to_drive(self, mock_exists, mock_client_class):
        """Uploads a local file to Google Drive."""
        mock_client = Mock()
        mock_client.upload_file.return_value = 'file123'
        mock_client_class.return_value = mock_client

        file_id = upload_file('/path/to/file.json', folder_path='AI Assistant Drive/logs/2026/02')

        assert file_id == 'file123'
        mock_client.upload_file.assert_called_once_with(
            '/path/to/file.json',
            'AI Assistant Drive/logs/2026/02',
            None
        )

    @patch('google_drive.DriveClient')
    @patch('os.path.exists', return_value=True)
    def test_creates_folder_structure_if_not_exists(self, mock_exists, mock_client_class):
        """Creates nested folder structure if it doesn't exist."""
        mock_client = Mock()
        mock_client._create_folder_path.return_value = 'folder123'
        mock_client.upload_file.return_value = 'file123'
        mock_client_class.return_value = mock_client

        upload_file('/path/to/file.json', folder_path='AI Assistant Drive/logs/2026')

        # Should call upload_file on the client
        mock_client.upload_file.assert_called_once()

    @patch('google_drive.DriveClient')
    def test_raises_error_when_file_not_found(self, mock_client_class):
        """Raises error when trying to upload non-existent file."""
        with pytest.raises(DriveError, match="File not found"):
            upload_file('/nonexistent/file.json')

    @patch('google_drive.DriveClient')
    @patch('os.path.exists', return_value=True)
    def test_uploads_with_mime_type_detection(self, mock_exists, mock_client_class):
        """Detects MIME type automatically based on file extension."""
        mock_client = Mock()
        mock_client.upload_file.return_value = 'file123'
        mock_client_class.return_value = mock_client

        upload_file('/path/to/file.json')

        # Should be called with client's upload_file method
        mock_client.upload_file.assert_called_once()


class TestDownloadFile:
    """Test file download functionality."""

    @patch('google_drive.DriveClient')
    def test_downloads_file_by_id(self, mock_client_class):
        """Downloads a file from Drive by file ID."""
        mock_client = Mock()
        mock_client.download_file.return_value = None
        mock_client_class.return_value = mock_client

        download_file('file123', '/local/path/file.json')

        # Should call download_file on the client
        mock_client.download_file.assert_called_once_with('file123', '/local/path/file.json')

    @patch('google_drive.DriveClient')
    def test_raises_error_when_file_id_invalid(self, mock_client_class):
        """Raises error when file ID is invalid."""
        mock_client = Mock()
        mock_client.download_file.side_effect = DriveError("Failed to download file: File not found")
        mock_client_class.return_value = mock_client

        with pytest.raises(DriveError, match="Failed to download"):
            download_file('invalid-id', '/local/path/file.json')


class TestArchiveOldLogs:
    """Test log archival functionality."""

    @patch('google_drive.DriveClient')
    @patch('os.remove')
    @patch('os.listdir')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    @patch('os.path.getmtime')
    def test_archives_logs_older_than_30_days(self, mock_getmtime, mock_isfile, mock_exists, mock_listdir, mock_remove, mock_client_class):
        """Moves log files older than 30 days to Google Drive."""
        # Mock log files
        now = datetime.now(timezone.utc).timestamp()
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()

        mock_listdir.return_value = ['ai_assistant.log.2026-01-01', 'ai_assistant.log.2026-02-03', 'ai_assistant.log']

        # First file is old, second is recent, third is current log
        mock_getmtime.side_effect = [old_date, now]

        mock_client = Mock()
        mock_client.upload_file.return_value = 'file123'
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123'
        mock_client_class.return_value = mock_client

        archived = archive_old_logs('/path/to/logs')

        # Should archive only the old file
        assert len(archived) == 1
        assert 'ai_assistant.log.2026-01-01' in archived[0]['filename']
        mock_client.upload_file.assert_called_once()

    @patch('google_drive.DriveClient')
    @patch('os.remove')
    @patch('os.listdir')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    @patch('os.path.getmtime')
    def test_deletes_local_logs_after_upload(self, mock_getmtime, mock_isfile, mock_exists, mock_listdir, mock_remove, mock_client_class):
        """Deletes local log files after successful upload to Drive."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()

        mock_listdir.return_value = ['ai_assistant.log.2026-01-01']
        mock_getmtime.return_value = old_date

        mock_client = Mock()
        mock_client.upload_file.return_value = 'file123'
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123'
        mock_client_class.return_value = mock_client

        archive_old_logs('/path/to/logs')

        # Should delete the file after upload
        mock_remove.assert_called_once()

    @patch('google_drive.DriveClient')
    @patch('os.remove')
    @patch('os.listdir')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    @patch('os.path.getmtime')
    def test_organizes_logs_by_year_month(self, mock_getmtime, mock_isfile, mock_exists, mock_listdir, mock_remove, mock_client_class):
        """Organizes archived logs in Drive by year and month folders."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()

        mock_listdir.return_value = ['ai_assistant.log.2026-01-15']
        mock_getmtime.return_value = old_date

        mock_client = Mock()
        mock_client.upload_file.return_value = 'file123'
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123'
        mock_client_class.return_value = mock_client

        archive_old_logs('/path/to/logs')

        # Should upload to year/month folder structure
        call_args = mock_client.upload_file.call_args
        folder_path = call_args[0][1]  # Second argument
        assert '2026' in folder_path
        assert '01' in folder_path

    @patch('google_drive.DriveClient')
    @patch('os.remove')
    @patch('os.listdir')
    @patch('os.path.exists', return_value=True)
    @patch('os.path.isfile', return_value=True)
    @patch('os.path.getmtime')
    def test_continues_on_upload_failure(self, mock_getmtime, mock_isfile, mock_exists, mock_listdir, mock_remove, mock_client_class):
        """Continues archiving other files if one upload fails."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=31)).timestamp()

        mock_listdir.return_value = ['ai_assistant.log.2026-01-01', 'ai_assistant.log.2026-01-02']
        mock_getmtime.return_value = old_date

        mock_client = Mock()
        # First upload fails, second succeeds
        mock_client.upload_file.side_effect = [Exception("Upload failed"), 'file123']
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123'
        mock_client_class.return_value = mock_client

        archived = archive_old_logs('/path/to/logs')

        # Should archive the second file despite first failure
        assert len(archived) == 1
        # Should not delete files that failed to upload
        mock_remove.assert_called_once()


class TestGetDriveLink:
    """Test Drive link generation."""

    @patch('google_drive.DriveClient')
    def test_returns_web_view_link(self, mock_client_class):
        """Returns shareable web view link for a file."""
        mock_client = Mock()
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123/view'
        mock_client_class.return_value = mock_client

        link = get_drive_link('file123')

        assert link == 'https://drive.google.com/file/d/file123/view'
        mock_client.get_file_link.assert_called_once_with('file123', False)

    @patch('google_drive.DriveClient')
    def test_makes_file_viewable_by_link(self, mock_client_class):
        """Sets file permissions to 'anyone with link can view'."""
        mock_client = Mock()
        mock_client.get_file_link.return_value = 'https://drive.google.com/file/d/file123/view'
        mock_client_class.return_value = mock_client

        get_drive_link('file123', make_public=True)

        # Should create permission for anyone with link
        mock_client.get_file_link.assert_called_once_with('file123', True)


class TestDriveClientHelpers:
    """Test helper methods of DriveClient."""

    @patch('google_drive.DriveClient.__init__', return_value=None)
    def test_finds_or_creates_folder(self, mock_init):
        """Finds existing folder or creates new one."""
        client = DriveClient.__new__(DriveClient)
        client.service = Mock()

        # Mock folder search - folder exists
        mock_search = Mock()
        mock_search.execute.return_value = {'files': [{'id': 'folder123'}]}
        client.service.files.return_value.list.return_value = mock_search

        folder_id = client._find_or_create_folder('TestFolder', parent_id=None)

        assert folder_id == 'folder123'

    @patch('google_drive.DriveClient.__init__', return_value=None)
    def test_creates_folder_when_not_found(self, mock_init):
        """Creates new folder when it doesn't exist."""
        client = DriveClient.__new__(DriveClient)
        client.service = Mock()

        # Mock folder search - no results
        mock_search = Mock()
        mock_search.execute.return_value = {'files': []}
        client.service.files.return_value.list.return_value = mock_search

        # Mock folder creation
        mock_create = Mock()
        mock_create.execute.return_value = {'id': 'new-folder123'}
        client.service.files.return_value.create.return_value = mock_create

        folder_id = client._find_or_create_folder('NewFolder', parent_id=None)

        assert folder_id == 'new-folder123'
        client.service.files.return_value.create.assert_called()

    @patch('google_drive.DriveClient.__init__', return_value=None)
    def test_creates_nested_folder_path(self, mock_init):
        """Creates nested folder structure from path string."""
        client = DriveClient.__new__(DriveClient)
        client.service = Mock()

        # Mock folder searches and creations
        mock_search = Mock()
        mock_search.execute.return_value = {'files': []}
        client.service.files.return_value.list.return_value = mock_search

        mock_create = Mock()
        # Return different IDs for each folder creation
        mock_create.execute.side_effect = [
            {'id': 'folder1'},
            {'id': 'folder2'},
            {'id': 'folder3'}
        ]
        client.service.files.return_value.create.return_value = mock_create

        folder_id = client._create_folder_path('AI Assistant Drive/logs/2026')

        # Should create all three folders
        assert client.service.files.return_value.create.call_count == 3
