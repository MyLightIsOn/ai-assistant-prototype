# Database Backup System

Automated SQLite database backup system with Google Drive integration and intelligent rotation policy.

## Features

- **Automated Daily Backups**: Runs at 3:00 AM daily via APScheduler
- **Intelligent Rotation**: Keeps 7 daily, 4 weekly, and 12 monthly backups
- **Google Drive Upload**: Optional cloud backup for disaster recovery
- **Database Optimization**: Runs VACUUM before backup to reduce file size
- **Notifications**: Sends ntfy.sh notifications on success/failure
- **Manual Triggers**: CLI tool for on-demand backups

## Architecture

### Backup Strategy

The backup system uses a multi-tiered retention policy:

1. **Daily Backups**: Last 7 days (full granularity)
2. **Weekly Backups**: Last 4 weeks (one backup per week)
3. **Monthly Backups**: Last 12 months (one backup per month)

This provides excellent recent history while limiting long-term storage growth.

### Components

#### `BackupConfig`
Loads configuration from environment variables:
- `DATABASE_URL`: SQLite database path
- `BACKUP_DIR`: Directory for backups (default: `ai-workspace/backups/database`)
- `AI_WORKSPACE`: Workspace root directory

#### `BackupManager`
Manages backup operations:
- Creates timestamped backups
- Lists existing backups
- Rotates old backups according to retention policy

#### `BackupRotationPolicy`
Implements the rotation strategy:
- Analyzes backup ages
- Determines which backups to keep/delete
- Ensures retention targets are met

#### `run_backup_task()`
Main entry point for automated backups:
1. Creates database backup with VACUUM
2. Uploads to Google Drive
3. Rotates old backups
4. Sends notification

## Setup

### 1. Environment Variables

Add to `backend/.env`:

```bash
# Database (already configured)
DATABASE_URL=sqlite:///../ai-assistant.db

# Optional: Custom backup directory
BACKUP_DIR=/path/to/backups

# AI Workspace (already configured)
AI_WORKSPACE=../ai-workspace

# Google Drive (for cloud backups)
GOOGLE_APPLICATION_CREDENTIALS=google_user_credentials.json
```

### 2. Google Drive Integration (Optional)

To enable cloud backups:

```bash
cd backend
python google_auth_setup.py
```

This will:
- Open browser for Google OAuth
- Save credentials to `google_user_credentials.json`
- Enable automated Drive uploads

### 3. Scheduler Integration

The backup task is automatically registered with APScheduler. To enable:

```python
# In your scheduler initialization (e.g., main.py or scheduler.py)
from backup import schedule_backup_task

# Add to scheduler startup
scheduler = TaskScheduler(engine)
scheduler.start()

# Schedule the backup task
schedule_backup_task(scheduler.scheduler)
```

## Usage

### Automated Backups

Once configured, backups run automatically at 3:00 AM daily.

Monitor backup status via:
- ntfy.sh notifications (success/failure)
- ActivityLog table (detailed execution logs)
- Backup directory (timestamped backup files)

### Manual Backups

#### Full Backup (with Drive upload)
```bash
cd backend
python manual_backup.py
```

#### Local Backup Only
```bash
python manual_backup.py --no-drive
```

#### Fast Backup (skip VACUUM)
```bash
python manual_backup.py --no-vacuum
```

### Programmatic Usage

```python
from backup import BackupManager, BackupConfig, upload_backup_to_drive

# Create backup manager
config = BackupConfig()
manager = BackupManager(config)

# Create local backup
backup_path = manager.create_backup(vacuum=True)
print(f"Backup created: {backup_path}")

# Upload to Drive
drive_file = upload_backup_to_drive(backup_path)
print(f"Drive link: {drive_file['webViewLink']}")

# Rotate old backups
deleted = manager.rotate_backups()
print(f"Deleted {len(deleted)} old backups")
```

## Backup File Format

Backup files are named with timestamps:
```
backup-YYYY-MM-DD-HHMMSS.db
```

Example:
```
backup-2026-02-04-030000.db  (Created on Feb 4, 2026 at 3:00 AM)
```

## Rotation Policy Details

### How It Works

The rotation policy categorizes backups into three tiers based on age:

**Recent (< 7 days)**
- Keeps all backups (daily granularity)
- Maximum: 7 backups

**Medium (7-28 days)**
- Keeps one backup per week
- Maximum: 4 backups

**Old (> 28 days)**
- Keeps one backup per month
- Maximum: 12 backups

### Example Timeline

Assuming today is March 1, 2026:

| Date Range | Retention | Example Backups Kept |
|---|---|---|
| Feb 23 - Mar 1 | Daily | Feb 23, 24, 25, 26, 27, 28, Mar 1 |
| Feb 2 - Feb 22 | Weekly | Feb 2, Feb 9, Feb 16 |
| Mar 2025 - Jan 2026 | Monthly | Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec, Jan |

Total backups: ~20-25 files

## Monitoring

### Notifications

Success notification includes:
- Backup filename
- File size
- Local path
- Google Drive link (if uploaded)
- Number of rotated backups

Error notification includes:
- Error message
- Failure timestamp

### Logs

All backup operations are logged to:
1. **Application logs**: Via `logger.py` (console + file)
2. **ActivityLog table**: Database records for audit trail
3. **Notification history**: Sent notifications tracked in DB

### Health Checks

Verify backup system health:

```bash
# Check last backup
ls -lth /path/to/backups | head -n 5

# Check backup count
ls -1 /path/to/backups | wc -l

# Test manual backup
python manual_backup.py --no-drive

# Verify Google Drive integration
python test_google_apis.py
```

## Disaster Recovery

### Restore from Local Backup

```bash
# Stop application
pm2 stop ai-assistant-backend

# Backup current database (just in case)
cp ai-assistant.db ai-assistant.db.before-restore

# Restore from backup
cp ai-workspace/backups/database/backup-YYYY-MM-DD-HHMMSS.db ai-assistant.db

# Restart application
pm2 start ai-assistant-backend
```

### Restore from Google Drive

1. Download backup from Drive:
   - Visit Google Drive in browser
   - Navigate to "AI Assistant Backups" folder
   - Download desired backup file

2. Follow "Restore from Local Backup" steps above

## Troubleshooting

### Backup Not Running

Check:
1. Scheduler is running: `pm2 status ai-assistant-scheduler`
2. Task is registered: Check scheduler logs
3. Environment variables: Verify `DATABASE_URL` is set

### Drive Upload Fails

Check:
1. Credentials exist: `ls -l google_user_credentials.json`
2. Credentials valid: `python test_google_apis.py`
3. Re-authenticate: `python google_auth_setup.py`

### Disk Space Issues

If backups consume too much space:

1. Adjust retention policy:
   ```python
   # In backup.py
   policy = BackupRotationPolicy(
       daily_keep=5,    # Reduce from 7
       weekly_keep=3,   # Reduce from 4
       monthly_keep=6   # Reduce from 12
   )
   ```

2. Run manual rotation:
   ```python
   from backup import BackupManager
   manager = BackupManager()
   deleted = manager.rotate_backups()
   ```

3. Clean old backups:
   ```bash
   # Delete backups older than 90 days
   find ai-workspace/backups/database -name "backup-*.db" -mtime +90 -delete
   ```

## Testing

Run comprehensive test suite:

```bash
cd backend
python -m pytest tests/test_backup.py -v
```

Test coverage includes:
- Configuration loading
- Backup creation with VACUUM
- Rotation policy logic
- Google Drive upload
- Error handling
- Notification integration

## Performance

### Backup Duration

Typical backup times (estimated):

| Database Size | VACUUM | Copy | Upload | Total |
|---|---|---|---|---|
| 10 MB | ~1s | <1s | ~2s | ~3s |
| 100 MB | ~5s | ~1s | ~10s | ~16s |
| 1 GB | ~30s | ~3s | ~60s | ~93s |

### Optimization Tips

1. **Skip VACUUM for frequent backups**:
   - VACUUM is expensive but compacts database
   - Run with VACUUM nightly, without for hourly

2. **Use local backups only**:
   - Skip Drive upload for faster backups
   - Manually upload weekly backups to Drive

3. **Adjust rotation policy**:
   - Fewer retained backups = faster rotation
   - Consider needs vs. storage costs

## Security Considerations

### Local Backups

- Stored in `ai-workspace/backups/database`
- Same permissions as main database
- Excluded from git (via `.gitignore`)

### Google Drive

- Encrypted in transit (HTTPS)
- Stored in user's personal Drive account
- Access controlled via OAuth 2.0
- Credentials stored locally in `google_user_credentials.json`

### Best Practices

1. **Protect credentials**:
   - Never commit `google_user_credentials.json`
   - Keep `.env` file secure

2. **Encrypt backups** (optional):
   ```bash
   # Encrypt backup before upload
   gpg --encrypt backup-YYYY-MM-DD-HHMMSS.db
   ```

3. **Test restores regularly**:
   - Verify backups are valid
   - Practice recovery procedures

## Future Enhancements

Potential improvements:

1. **Compression**: gzip backups to save space
2. **Encryption**: Encrypt backups at rest
3. **Multiple destinations**: S3, Dropbox, etc.
4. **Incremental backups**: Only backup changes
5. **Point-in-time recovery**: WAL mode + streaming backups
6. **Backup verification**: Automatic restore testing

## Support

For issues or questions:
1. Check logs: `pm2 logs ai-assistant-scheduler`
2. Review ActivityLog table
3. Test manually: `python manual_backup.py`
4. Re-run tests: `pytest tests/test_backup.py`
