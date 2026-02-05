"""
Google Drive integration for AI Assistant.

Provides log archival and file storage functionality using Google Drive API.
Integrates with ActivityLog for audit trail.

Features:
- OAuth 2.0 authentication using user credentials
- Automatic log archival (files older than 30 days)
- Organized folder structure: AI Assistant Drive/logs/YYYY/MM/
- File upload/download utilities
- Drive link generation for task outputs
"""

import os
import json
import logging
import mimetypes
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError

from logger import get_logger

# Configure logging
logger = get_logger()


class DriveError(Exception):
    """Raised when Google Drive operations fail."""
    pass


class DriveConfig:
    """Configuration for Google Drive client.

    Loads OAuth credentials from google_user_credentials.json file.
    This file is created by running google_auth_setup.py.
    """

    def __init__(self, credentials_file: str = 'google_user_credentials.json'):
        """Initialize Drive configuration.

        Args:
            credentials_file: Path to OAuth credentials file

        Raises:
            DriveError: If credentials file is not found
        """
        # Resolve path relative to backend directory
        if not os.path.isabs(credentials_file):
            backend_dir = Path(__file__).parent
            credentials_file = str(backend_dir / credentials_file)

        self.credentials_file = credentials_file

        if not os.path.exists(self.credentials_file):
            raise DriveError(
                f"Credentials file not found: {self.credentials_file}\n"
                "Run google_auth_setup.py to create credentials."
            )


class DriveClient:
    """Google Drive API client for file operations.

    Handles authentication, folder management, and file upload/download.
    """

    SCOPES = ['https://www.googleapis.com/auth/drive']

    def __init__(self, credentials_file: str = 'google_user_credentials.json'):
        """Initialize Drive client with OAuth credentials.

        Args:
            credentials_file: Path to OAuth credentials file

        Raises:
            DriveError: If authentication fails
        """
        config = DriveConfig(credentials_file)
        self.service = self._authenticate(config.credentials_file)

    def _authenticate(self, credentials_file: str):
        """Authenticate with Google Drive API.

        Args:
            credentials_file: Path to OAuth credentials file

        Returns:
            Authenticated Drive API service

        Raises:
            DriveError: If authentication fails
        """
        try:
            # Load credentials from file
            creds = Credentials.from_authorized_user_file(
                credentials_file,
                self.SCOPES
            )

            # Refresh token if expired
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Save refreshed credentials
                    with open(credentials_file, 'w') as token:
                        token.write(creds.to_json())
                else:
                    raise DriveError(
                        "Invalid credentials. Please run google_auth_setup.py to re-authenticate."
                    )

            # Build Drive API service
            service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive client initialized successfully")
            return service

        except Exception as e:
            logger.error(f"Failed to authenticate with Google Drive: {e}")
            raise DriveError(f"Authentication failed: {e}")

    def _find_or_create_folder(
        self,
        folder_name: str,
        parent_id: Optional[str] = None
    ) -> str:
        """Find existing folder or create new one.

        Args:
            folder_name: Name of the folder
            parent_id: Parent folder ID (None for root)

        Returns:
            Folder ID

        Raises:
            DriveError: If folder operation fails
        """
        try:
            # Search for existing folder
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()

            files = results.get('files', [])

            # Return existing folder if found
            if files:
                folder_id = files[0]['id']
                logger.info(f"Found existing folder: {folder_name} (ID: {folder_id})")
                return folder_id

            # Create new folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                folder_metadata['parents'] = [parent_id]

            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()

            folder_id = folder['id']
            logger.info(f"Created new folder: {folder_name} (ID: {folder_id})")
            return folder_id

        except HttpError as e:
            logger.error(f"Failed to find or create folder '{folder_name}': {e}")
            raise DriveError(f"Folder operation failed: {e}")

    def _create_folder_path(self, folder_path: str) -> str:
        """Create nested folder structure from path.

        Args:
            folder_path: Folder path (e.g., 'AI Assistant Drive/logs/2026/02')

        Returns:
            Final folder ID

        Raises:
            DriveError: If folder creation fails
        """
        parts = folder_path.split('/')
        parent_id = None

        for part in parts:
            if part:  # Skip empty parts
                parent_id = self._find_or_create_folder(part, parent_id)

        return parent_id

    def upload_file(
        self,
        file_path: str,
        folder_path: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> str:
        """Upload a file to Google Drive.

        Args:
            file_path: Local file path to upload
            folder_path: Destination folder path in Drive (e.g., 'AI Assistant Drive/logs/2026/02')
            mime_type: MIME type (auto-detected if None)

        Returns:
            File ID of uploaded file

        Raises:
            DriveError: If upload fails
        """
        try:
            if not os.path.exists(file_path):
                raise DriveError(f"File not found: {file_path}")

            # Get file name
            file_name = os.path.basename(file_path)

            # Detect MIME type if not provided
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'

            # Create folder structure if specified
            parent_id = None
            if folder_path:
                parent_id = self._create_folder_path(folder_path)

            # Prepare file metadata
            file_metadata = {'name': file_name}
            if parent_id:
                file_metadata['parents'] = [parent_id]

            # Upload file
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()

            file_id = file['id']
            logger.info(f"Uploaded file: {file_name} (ID: {file_id})")
            return file_id

        except HttpError as e:
            logger.error(f"Failed to upload file '{file_path}': {e}")
            raise DriveError(f"Upload failed: {e}")

    def download_file(self, file_id: str, destination_path: str) -> None:
        """Download a file from Google Drive.

        Args:
            file_id: Drive file ID
            destination_path: Local path to save file

        Raises:
            DriveError: If download fails
        """
        try:
            request = self.service.files().get_media(fileId=file_id)

            with open(destination_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            logger.info(f"Downloaded file: {file_id} to {destination_path}")

        except Exception as e:
            logger.error(f"Failed to download file '{file_id}': {e}")
            raise DriveError(f"Failed to download file: {e}")

    def get_file_link(
        self,
        file_id: str,
        make_public: bool = False
    ) -> str:
        """Get shareable link for a file.

        Args:
            file_id: Drive file ID
            make_public: If True, set file to 'anyone with link can view'

        Returns:
            Web view link for the file

        Raises:
            DriveError: If operation fails
        """
        try:
            # Make file public if requested
            if make_public:
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                self.service.permissions().create(
                    fileId=file_id,
                    body=permission
                ).execute()
                logger.info(f"Set file {file_id} to public (anyone with link)")

            # Get file metadata with link
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()

            link = file.get('webViewLink')
            logger.info(f"Retrieved link for file {file_id}")
            return link

        except HttpError as e:
            logger.error(f"Failed to get link for file '{file_id}': {e}")
            raise DriveError(f"Failed to get file link: {e}")


# ============================================================================
# Public API Functions
# ============================================================================

def upload_file(
    file_path: str,
    folder_path: Optional[str] = None,
    mime_type: Optional[str] = None
) -> str:
    """Upload a file to Google Drive.

    Args:
        file_path: Local file path to upload
        folder_path: Destination folder path (e.g., 'AI Assistant Drive/logs/2026/02')
        mime_type: MIME type (auto-detected if None)

    Returns:
        File ID of uploaded file

    Raises:
        DriveError: If upload fails

    Example:
        >>> file_id = upload_file('/path/to/log.json', folder_path='AI Assistant Drive/logs/2026/02')
    """
    if not os.path.exists(file_path):
        raise DriveError(f"File not found: {file_path}")

    client = DriveClient()
    return client.upload_file(file_path, folder_path, mime_type)


def download_file(file_id: str, destination_path: str) -> None:
    """Download a file from Google Drive.

    Args:
        file_id: Drive file ID
        destination_path: Local path to save file

    Raises:
        DriveError: If download fails

    Example:
        >>> download_file('abc123', '/path/to/save/file.json')
    """
    client = DriveClient()
    client.download_file(file_id, destination_path)


def get_drive_link(file_id: str, make_public: bool = False) -> str:
    """Get shareable link for a Drive file.

    Args:
        file_id: Drive file ID
        make_public: If True, set file to 'anyone with link can view'

    Returns:
        Web view link for the file

    Raises:
        DriveError: If operation fails

    Example:
        >>> link = get_drive_link('abc123', make_public=True)
        >>> print(f"View file: {link}")
    """
    client = DriveClient()
    return client.get_file_link(file_id, make_public)


def archive_old_logs(
    log_dir: Optional[str] = None,
    days_threshold: int = 30
) -> List[Dict[str, Any]]:
    """Archive log files older than threshold to Google Drive.

    Moves log files older than days_threshold to Google Drive organized by
    year and month. Deletes local files after successful upload.

    Args:
        log_dir: Directory containing log files (defaults to ai-workspace/logs)
        days_threshold: Age threshold in days (default: 30)

    Returns:
        List of archived file information dicts with keys:
            - filename: Original file name
            - file_id: Drive file ID
            - link: Drive web view link
            - archived_at: ISO timestamp

    Raises:
        DriveError: If archival fails

    Example:
        >>> archived = archive_old_logs()
        >>> for file_info in archived:
        ...     print(f"Archived {file_info['filename']} to {file_info['link']}")
    """
    # Default to ai-workspace/logs if not specified
    if log_dir is None:
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent
        log_dir = str(project_root / "ai-workspace" / "logs")

    if not os.path.exists(log_dir):
        raise DriveError(f"Log directory not found: {log_dir}")

    client = DriveClient()
    archived_files = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

    logger.info(f"Starting log archival from {log_dir} (threshold: {days_threshold} days)")

    # Scan log directory for old files
    for filename in os.listdir(log_dir):
        file_path = os.path.join(log_dir, filename)

        # Skip directories and current log file
        if not os.path.isfile(file_path) or filename.endswith('.log'):
            continue

        # Check if file is a rotated log file
        if not filename.startswith('ai_assistant.log.'):
            continue

        # Check file age
        file_mtime = datetime.fromtimestamp(
            os.path.getmtime(file_path),
            tz=timezone.utc
        )

        if file_mtime > cutoff_date:
            logger.info(f"Skipping recent file: {filename} (modified: {file_mtime.date()})")
            continue

        try:
            # Extract date from filename (format: ai_assistant.log.YYYY-MM-DD)
            date_part = filename.replace('ai_assistant.log.', '')
            file_date = datetime.strptime(date_part, '%Y-%m-%d')

            # Create folder path: AI Assistant Drive/logs/YYYY/MM
            folder_path = f"AI Assistant Drive/logs/{file_date.year}/{file_date.month:02d}"

            # Upload file to Drive
            logger.info(f"Archiving {filename} to {folder_path}")
            file_id = client.upload_file(file_path, folder_path)

            # Get shareable link
            link = client.get_file_link(file_id, make_public=False)

            # Record archived file
            archived_files.append({
                'filename': filename,
                'file_id': file_id,
                'link': link,
                'archived_at': datetime.now(timezone.utc).isoformat()
            })

            # Delete local file after successful upload
            os.remove(file_path)
            logger.info(f"Deleted local file: {filename}")

        except Exception as e:
            logger.error(f"Failed to archive {filename}: {e}")
            # Continue with other files even if one fails

    logger.info(f"Log archival complete. Archived {len(archived_files)} files.")
    return archived_files
