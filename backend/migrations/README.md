# Database Migrations

## migrate_timestamps_to_integer.py

**Purpose:** Convert timestamp columns from TEXT/DATETIME to INTEGER (Unix milliseconds) for Prisma compatibility.

**Usage:**
```bash
cd backend/migrations
python migrate_timestamps_to_integer.py
```

**What it does:**
1. Creates backup: `ai-assistant.db.backup-YYYYMMDD-HHMMSS`
2. Converts all timestamp columns to INTEGER format
3. Preserves data by parsing TEXT timestamps to Unix milliseconds
4. Commits changes or rolls back on error

**Affected tables:**
- User (createdAt, updatedAt)
- Session (expires)
- Task (createdAt, updatedAt, lastRun, nextRun)
- TaskExecution (startedAt, completedAt)
- ActivityLog (createdAt)
- Notification (sentAt, readAt)
- AiMemory (createdAt, updatedAt)
- DigestSettings (createdAt, updatedAt)

**Rollback:**
```bash
cp ai-assistant.db.backup-YYYYMMDD-HHMMSS ai-assistant.db
```

**IMPORTANT:** Run this ONCE after deploying the model changes. Do not run on production without testing on a copy first.
