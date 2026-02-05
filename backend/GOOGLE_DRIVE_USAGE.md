# Google Drive Integration Usage Guide

## Overview

The Google Drive integration provides log archival and file storage functionality for the AI Assistant backend. It uses OAuth 2.0 authentication and organizes files in a structured folder hierarchy.

## Features

- **Automatic Log Archival**: Archive logs older than 30 days to Google Drive
- **Organized Storage**: Files stored in `AI Assistant Drive/logs/YYYY/MM/` structure
- **File Operations**: Upload, download, and share files via Drive API
- **OAuth Authentication**: Secure authentication using user credentials
- **Integration Ready**: Works seamlessly with task execution and notification systems

## Authentication Setup

### Prerequisites

1. Google Cloud Project with Drive API enabled
2. OAuth 2.0 client credentials downloaded as `google_oauth_client.json`
3. User credentials file `google_user_credentials.json` (created by `google_auth_setup.py`)

### Initial Setup

Run the authentication setup script once:

```bash
cd backend
source venv/bin/activate
python google_auth_setup.py
```

This will:
1. Open a browser for OAuth authorization
2. Save credentials to `google_user_credentials.json`
3. Verify access to Google Drive API

## API Usage

### Upload a File

Upload any file to Google Drive with optional folder structure:

```python
from google_drive import upload_file

# Upload to root
file_id = upload_file('/path/to/file.json')

# Upload to specific folder path
file_id = upload_file(
    '/path/to/log.json',
    folder_path='AI Assistant Drive/logs/2026/02'
)

# Specify MIME type (auto-detected if not provided)
file_id = upload_file(
    '/path/to/data.txt',
    folder_path='AI Assistant Drive/output',
    mime_type='text/plain'
)
```

### Download a File

Download a file from Google Drive by file ID:

```python
from google_drive import download_file

download_file('abc123xyz', '/local/path/file.json')
```

### Get Shareable Link

Generate a shareable link for a file:

```python
from google_drive import get_drive_link

# Get link (file remains private)
link = get_drive_link('abc123xyz')

# Get link and make file publicly viewable
link = get_drive_link('abc123xyz', make_public=True)
```

### Archive Old Logs

Automatically archive log files older than 30 days:

```python
from google_drive import archive_old_logs

# Archive from default location (ai-workspace/logs)
archived = archive_old_logs()

# Archive from custom location
archived = archive_old_logs(
    log_dir='/custom/log/directory',
    days_threshold=60  # Archive logs older than 60 days
)

# Process archived files
for file_info in archived:
    print(f"Archived: {file_info['filename']}")
    print(f"Drive Link: {file_info['link']}")
    print(f"File ID: {file_info['file_id']}")
```

## Advanced Usage

### Direct Client Access

For more control, use the `DriveClient` class directly:

```python
from google_drive import DriveClient

# Initialize client
client = DriveClient()

# Upload with custom options
file_id = client.upload_file(
    file_path='/path/to/file.pdf',
    folder_path='AI Assistant Drive/documents',
    mime_type='application/pdf'
)

# Download file
client.download_file(file_id, '/local/destination.pdf')

# Get shareable link
link = client.get_file_link(file_id, make_public=True)
```

### Folder Management

The client automatically creates nested folder structures:

```python
# This creates: AI Assistant Drive > logs > 2026 > 02
client.upload_file(
    '/path/to/log.json',
    folder_path='AI Assistant Drive/logs/2026/02'
)

# Folders are reused if they already exist
client.upload_file(
    '/path/to/another-log.json',
    folder_path='AI Assistant Drive/logs/2026/02'  # Uses existing folders
)
```

## Integration with Task System

### Attach Drive Links to Task Outputs

```python
from google_drive import upload_file, get_drive_link

# Generate report
report_path = '/ai-workspace/output/report.pdf'
generate_report(report_path)

# Upload to Drive
file_id = upload_file(
    report_path,
    folder_path='AI Assistant Drive/reports'
)

# Get shareable link
link = get_drive_link(file_id, make_public=True)

# Include in task completion notification
send_notification(
    title='Report Complete',
    message=f'View report: {link}',
    priority='high'
)
```

### Scheduled Log Archival

Add to `scheduler.py` for automated log cleanup:

```python
from google_drive import archive_old_logs

def archive_logs_job():
    """Daily job to archive old logs to Google Drive."""
    try:
        archived = archive_old_logs()
        if archived:
            logger.info(f"Archived {len(archived)} log files to Google Drive")
            # Optional: Send notification
            send_notification(
                title='Log Archival Complete',
                message=f'Archived {len(archived)} files to Google Drive',
                priority='low'
            )
    except Exception as e:
        logger.error(f"Log archival failed: {e}")

# Schedule daily at 2 AM
scheduler.add_job(
    archive_logs_job,
    'cron',
    hour=2,
    minute=0,
    id='archive_logs'
)
```

## Error Handling

All operations raise `DriveError` on failure:

```python
from google_drive import upload_file, DriveError

try:
    file_id = upload_file('/path/to/file.json')
except DriveError as e:
    logger.error(f"Upload failed: {e}")
    # Handle error (retry, notify user, etc.)
```

Common error scenarios:
- **Authentication failed**: Re-run `google_auth_setup.py`
- **File not found**: Check file path before upload
- **Network timeout**: Implement retry logic
- **Quota exceeded**: Check Google Drive storage quota

## Folder Structure

The default organization for automated log archival:

```
Google Drive
└── AI Assistant Drive/
    └── logs/
        ├── 2026/
        │   ├── 01/
        │   │   ├── ai_assistant.log.2026-01-01
        │   │   ├── ai_assistant.log.2026-01-02
        │   │   └── ...
        │   ├── 02/
        │   │   └── ...
        │   └── ...
        └── 2027/
            └── ...
```

You can use any custom folder structure for manual uploads.

## Security Notes

1. **OAuth Credentials**: Keep `google_user_credentials.json` secure (excluded in `.gitignore`)
2. **File Permissions**: Files are private by default unless `make_public=True`
3. **Shared Links**: Public links allow anyone with the URL to view (not edit)
4. **Token Refresh**: Tokens automatically refresh when expired
5. **Audit Trail**: All operations logged to `ActivityLog` table

## Testing

Run the test suite:

```bash
cd backend
source venv/bin/activate
python -m pytest tests/test_google_drive.py -v
```

## Integration Points

### With Existing Backend Components

1. **Logger Integration**: Uses `logger.py` for structured logging
2. **Database Integration**: Can log to `ActivityLog` table via `models.py`
3. **Notification System**: Works with `ntfy_client.py` for upload notifications
4. **Task Scheduler**: Integrates with `scheduler.py` for automated archival

### Example: Complete Task Workflow

```python
from google_drive import upload_file, get_drive_link
from ntfy_client import send_notification
from logger import get_logger

logger = get_logger()

def task_with_drive_output(task_id: str):
    """Execute task and upload output to Drive."""
    try:
        # Execute task
        output_path = f'/ai-workspace/output/task_{task_id}_output.json'
        execute_task(output_path)

        # Upload to Drive
        logger.info(f"Uploading task output to Google Drive")
        file_id = upload_file(
            output_path,
            folder_path=f'AI Assistant Drive/tasks/{task_id}'
        )

        # Get shareable link
        link = get_drive_link(file_id, make_public=False)

        # Notify user
        send_notification(
            title=f'Task {task_id} Complete',
            message=f'View output: {link}',
            priority='default',
            tags='task,complete'
        )

        logger.info(f"Task {task_id} completed successfully")
        return {'status': 'success', 'drive_link': link}

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        send_notification(
            title=f'Task {task_id} Failed',
            message=str(e),
            priority='high',
            tags='task,error'
        )
        return {'status': 'error', 'message': str(e)}
```

## Troubleshooting

### Authentication Issues

If you see authentication errors:

```bash
# Re-run authentication setup
python google_auth_setup.py

# Verify credentials file exists
ls -la google_user_credentials.json
```

### Rate Limiting

Google Drive API has rate limits. Implement exponential backoff:

```python
import time
from google_drive import upload_file, DriveError

def upload_with_retry(file_path, max_retries=3):
    """Upload with exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return upload_file(file_path)
        except DriveError as e:
            if 'rate limit' in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
            else:
                raise
```

### Storage Quota

Check available storage before large uploads:

```python
from google_drive import DriveClient

client = DriveClient()
# Use Drive API to check quota
about = client.service.about().get(fields='storageQuota').execute()
quota = about.get('storageQuota', {})
print(f"Used: {quota.get('usage')} / Limit: {quota.get('limit')}")
```

## Best Practices

1. **Batch Operations**: Upload multiple files in sequence, not parallel (rate limits)
2. **Error Logging**: Always log Drive operations for debugging
3. **Cleanup**: Delete local files only after successful upload confirmation
4. **Monitoring**: Track archived files count in daily reports
5. **Testing**: Use test folder paths during development
6. **Documentation**: Update task descriptions with Drive link patterns

## Future Enhancements

Potential improvements for future development:

- [ ] Batch upload API for multiple files
- [ ] Resume interrupted uploads (Drive API supports resumable uploads)
- [ ] Archive compression before upload (gzip logs)
- [ ] Folder sharing with specific users
- [ ] Drive webhook notifications for file changes
- [ ] Integration with Google Calendar for archival schedule
- [ ] Automatic cleanup of Drive storage (delete very old logs)
- [ ] Migration tool from Drive back to local storage
