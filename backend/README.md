# AI Assistant Backend

Python backend for the AI Assistant project, providing FastAPI services, Claude Code integration, and task scheduling.

## Tech Stack

- **FastAPI** - Web framework for API endpoints and WebSocket connections
- **SQLAlchemy 2.0** - ORM for database access (mirrors Prisma schema)
- **APScheduler** - Cron-style task scheduling with persistence
- **Python-dotenv** - Environment variable management
- **Uvicorn** - ASGI server
- **pytest** - Testing framework

## Project Structure

```
backend/
├── database.py          # SQLAlchemy session management
├── models.py            # SQLAlchemy models + Pydantic schemas
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not committed)
├── .env.example         # Environment template
└── tests/
    ├── __init__.py
    └── test_models.py   # Model tests
```

## Setup

### 1. Create Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env` and update values:

```bash
cp .env.example .env
```

Edit `.env`:
```bash
DATABASE_URL=sqlite:///../ai-assistant.db
NTFY_URL=http://localhost:8080/ai-notifications
NTFY_USERNAME=ai-assistant
NTFY_PASSWORD=your-secure-password
AI_WORKSPACE=../ai-workspace
```

## Database Models

The SQLAlchemy models **exactly mirror** the Prisma schema in `frontend/prisma/schema.prisma`:

- **User** - User accounts with authentication
- **Session** - NextAuth.js sessions
- **Task** - Scheduled tasks with cron expressions
- **TaskExecution** - Execution history and results
- **ActivityLog** - System event logging
- **Notification** - Sent notification history
- **AiMemory** - Persistent AI context storage

### Important Notes

- **Database Location**: The SQLite database is located at the project root (`../ai-assistant.db`)
- **Schema Sync**: Changes to the Prisma schema must be manually reflected in `models.py`
- **Foreign Keys**: SQLite foreign key constraints are enabled automatically
- **Cascade Deletes**: All relationships properly cascade deletes (User → Tasks → Executions → Logs)

### Special Field Mapping

The `ActivityLog.metadata` database column is mapped to `metadata_` in Python to avoid conflict with SQLAlchemy's reserved `metadata` attribute:

```python
# In database: 'metadata'
# In Python code: 'metadata_'
log = ActivityLog(
    id="log-1",
    type="task_start",
    message="Task started",
    metadata_='{"key": "value"}'  # Note the underscore
)
```

## Testing

Run all tests:

```bash
pytest tests/ -v
```

Run specific test file:

```bash
pytest tests/test_models.py -v
```

Run with coverage:

```bash
pytest tests/ --cov=. --cov-report=html
```

### Test Coverage

Current tests verify:
- ✅ Model creation and field validation
- ✅ Unique constraints (email, session token, memory key)
- ✅ Default values
- ✅ Relationships (User ↔ Task, Task ↔ Execution, etc.)
- ✅ Cascade deletes through entire chain
- ✅ DateTime handling and updates

## Development

### Running the API Server

```bash
# Not yet implemented - coming in future issues
python main.py
```

### Running the Task Scheduler

```bash
# Not yet implemented - coming in future issues
python scheduler.py
```

### Database Inspection

Use SQLite CLI to inspect the database:

```bash
sqlite3 ../ai-assistant.db
.tables
.schema User
.schema Task
.quit
```

## Pydantic Schemas

The `models.py` file includes Pydantic schemas for API validation:

### Task Schemas

- **TaskBase** - Base fields for task creation/updates
- **TaskCreate** - Create new task (includes userId)
- **TaskUpdate** - Partial update (all fields optional)
- **TaskResponse** - API response with timestamps

### Execution Schemas

- **ExecutionBase** - Base execution fields
- **ExecutionCreate** - Create new execution
- **ExecutionUpdate** - Update execution status/results
- **ExecutionResponse** - API response

### Other Schemas

- **ActivityLogResponse** - Activity log entries
- **NotificationCreate/Response** - Notifications
- **AiMemoryCreate/Update/Response** - AI memory CRUD

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite database path | `sqlite:///../ai-assistant.db` |
| `NTFY_URL` | ntfy.sh notification endpoint | `http://localhost:8080/ai-notifications` |
| `NTFY_USERNAME` | ntfy authentication username | `ai-assistant` |
| `NTFY_PASSWORD` | ntfy authentication password | `your-secure-password` |
| `AI_WORKSPACE` | AI workspace directory | `../ai-workspace` |
| `HOST` | API server host | `0.0.0.0` |
| `PORT` | API server port | `8000` |
| `DEBUG` | Enable debug logging | `True` or `False` |

## Next Steps

The following components are planned for future implementation:

1. **main.py** - FastAPI application with WebSocket support
2. **scheduler.py** - APScheduler daemon for recurring tasks
3. **claude_interface.py** - Claude Code subprocess integration
4. **ntfy_client.py** - Notification sender

## Notes

- This backend shares the same SQLite database with the Next.js frontend
- The frontend uses Prisma (TypeScript), the backend uses SQLAlchemy (Python)
- Both ORMs access the same `ai-assistant.db` file at the project root
- The Prisma schema is the source of truth - SQLAlchemy models must be manually synced
