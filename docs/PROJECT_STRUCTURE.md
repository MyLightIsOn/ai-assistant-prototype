# Project Structure

Comprehensive guide to the AI Assistant monorepo layout, development workflow, and architectural organization.

---

## Table of Contents

1. [Repository Overview](#repository-overview)
2. [Directory Structure](#directory-structure)
3. [Frontend Organization](#frontend-organization)
4. [Backend Organization](#backend-organization)
5. [AI Workspace](#ai-workspace)
6. [Development Workflow](#development-workflow)
7. [File Conventions](#file-conventions)
8. [Testing Structure](#testing-structure)

---

## Repository Overview

This is a **monorepo** containing both frontend and backend services in a single repository. This approach simplifies development, testing, and deployment while maintaining clear separation of concerns.

### Why Monorepo?

- **Single source of truth** - All code in one place
- **Atomic commits** - Frontend and backend changes together
- **Shared tooling** - Consistent linting, testing, CI/CD
- **Simplified deployment** - Build and deploy from one repo
- **Better collaboration** - No cross-repo PRs or version mismatches

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Frontend** | Next.js 14+ (App Router) | Web UI and PWA |
| **Backend** | Python FastAPI | REST API and WebSocket server |
| **Database** | SQLite | Shared data store |
| **Frontend ORM** | Prisma | TypeScript database client |
| **Backend ORM** | SQLAlchemy | Python database models |
| **Scheduler** | APScheduler | Cron-style task execution |
| **Process Manager** | PM2 | Production service orchestration |

---

## Directory Structure

```
ai-assistant-prototype/
├── frontend/                   # Next.js application
│   ├── app/                   # Next.js App Router pages
│   │   ├── api/              # API routes (auth, data)
│   │   ├── chat/             # Chat interface page
│   │   ├── dashboard/        # Dashboard page
│   │   ├── tasks/            # Task management pages
│   │   └── layout.tsx        # Root layout with auth
│   ├── components/           # React components
│   │   ├── ui/              # shadcn/ui components
│   │   ├── chat/            # Chat-specific components
│   │   ├── tasks/           # Task-specific components
│   │   └── layout/          # Layout components
│   ├── lib/                 # Utility libraries
│   │   ├── api.ts          # API client functions
│   │   ├── websocket.ts    # WebSocket client
│   │   └── utils.ts        # Helper functions
│   ├── prisma/             # Prisma ORM
│   │   ├── schema.prisma   # Database schema (source of truth)
│   │   └── migrations/     # Database migrations (.gitignored)
│   ├── public/             # Static assets
│   ├── styles/             # Global CSS
│   ├── next.config.js      # Next.js configuration
│   ├── package.json        # Frontend dependencies
│   └── tsconfig.json       # TypeScript configuration
│
├── backend/                    # Python FastAPI service
│   ├── main.py                # FastAPI app and routes
│   ├── scheduler.py           # APScheduler daemon
│   ├── chat_executor_cli.py   # Chat execution (CLI subprocess)
│   ├── chat_context.py        # Chat system prompt builder
│   ├── claude_interface.py    # Claude CLI subprocess wrapper
│   ├── task_tools.py          # Task CRUD tool handlers
│   ├── calendar_sync.py       # Google Calendar integration
│   ├── email_service.py       # Gmail notification service
│   ├── models.py              # SQLAlchemy ORM models
│   ├── database.py            # Database connection setup
│   ├── logger.py              # Logging configuration
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Environment variables (.gitignored)
│   └── venv/                  # Python virtual environment (.gitignored)
│
├── ai-workspace/              # AI's working directory (.gitignored)
│   ├── memory/               # Persistent context and history
│   ├── tasks/                # Multi-agent task workspaces
│   │   └── {execution_id}/  # Per-execution isolated workspace
│   │       ├── task.json
│   │       ├── shared/
│   │       ├── agents/
│   │       └── final_result.json
│   ├── logs/                 # JSON execution logs (30-day retention)
│   ├── dev/                  # AI project workspace (can contain git repos)
│   ├── output/               # Generated files and artifacts
│   └── temp/                 # Temporary working files
│
├── docs/                      # Documentation
│   ├── PROJECT_STRUCTURE.md  # This file (public)
│   ├── USER_GUIDE_CHAT.md    # Chat user guide (public)
│   └── do_not_commit/        # Private planning docs (.gitignored)
│       ├── plans/
│       └── code-reviews/
│
├── ai-assistant.db            # SQLite database (.gitignored)
├── .gitignore                # Git ignore rules
├── CLAUDE.md                 # Claude Code instructions
├── README.md                 # Project overview
└── ecosystem.config.js       # PM2 process configuration
```

---

## Frontend Organization

### App Router Structure

The frontend uses Next.js 14+ App Router with file-based routing:

```
frontend/app/
├── layout.tsx              # Root layout (auth, providers)
├── page.tsx               # Home page (/)
├── api/                   # Backend API routes
│   ├── auth/
│   │   └── [...nextauth]/route.ts  # NextAuth.js endpoints
│   ├── tasks/
│   │   ├── route.ts       # GET/POST /api/tasks
│   │   └── [id]/route.ts  # GET/PUT/DELETE /api/tasks/:id
│   └── chat/
│       └── messages/route.ts  # Chat message history
├── chat/
│   ├── page.tsx           # Chat interface (/chat)
│   └── layout.tsx         # Chat-specific layout
├── dashboard/
│   └── page.tsx           # Main dashboard (/dashboard)
└── tasks/
    ├── page.tsx           # Task list (/tasks)
    ├── [id]/
    │   └── page.tsx       # Task detail (/tasks/:id)
    └── new/
        └── page.tsx       # Create task (/tasks/new)
```

### Component Organization

```
frontend/components/
├── ui/                    # shadcn/ui primitives
│   ├── button.tsx
│   ├── card.tsx
│   ├── dialog.tsx
│   └── ...
├── chat/
│   ├── ChatInterface.tsx      # Main chat container
│   ├── MessageList.tsx        # Message display
│   ├── MessageInput.tsx       # Input field
│   └── ConnectionStatus.tsx   # WebSocket status
├── tasks/
│   ├── TaskList.tsx           # Task table
│   ├── TaskCard.tsx           # Task card view
│   ├── TaskForm.tsx           # Create/edit form
│   └── ExecutionHistory.tsx   # Execution log viewer
└── layout/
    ├── Header.tsx             # App header
    ├── Sidebar.tsx            # Navigation sidebar
    └── Footer.tsx             # App footer
```

### State Management

- **Zustand** for global client state (user preferences, UI state)
- **React Context** for auth session
- **React Query** (optional) for server state caching
- **Native hooks** (useState, useEffect) for component-local state

### Styling

- **Tailwind CSS** for utility-first styling
- **CSS Modules** for component-scoped styles (when needed)
- **shadcn/ui** for pre-built accessible components
- **Dark mode** support via Tailwind dark: prefix

---

## Backend Organization

### Main Application (main.py)

The FastAPI application in `main.py` contains:

- **REST API routes** for task CRUD operations
- **WebSocket endpoint** for real-time chat and updates
- **Google Calendar webhook** for bidirectional sync
- **Health check endpoint** for monitoring
- **CORS configuration** for frontend access

### Service Modules

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `scheduler.py` | Task execution daemon | APScheduler with SQLite job store |
| `chat_executor_cli.py` | Chat message handling | Spawns Claude CLI subprocess |
| `chat_context.py` | System prompt builder | Builds conversation context |
| `claude_interface.py` | Claude CLI wrapper | Subprocess management for tasks |
| `task_tools.py` | Task operations | CRUD handlers for REST API |
| `calendar_sync.py` | Calendar integration | Event ↔ task sync |
| `email_service.py` | Email notifications | Gmail API client |
| `models.py` | Database models | SQLAlchemy ORM definitions |
| `database.py` | DB connection | Session management |
| `logger.py` | Logging config | Structured JSON logging |

### Database Schema

The database uses **dual ORM support**:

- **Prisma** (frontend) - TypeScript client, schema source of truth
- **SQLAlchemy** (backend) - Python models, manually synced

**Core Models:**

```python
User             # Authentication and user management
Task             # Scheduled tasks with cron timing
TaskExecution    # Execution history and results
ChatMessage      # Chat conversation history
ActivityLog      # System event tracking
Notification     # Notification delivery history
AiMemory         # Persistent AI context
```

**Schema Source of Truth:** `frontend/prisma/schema.prisma`

When modifying schema:
1. Update Prisma schema
2. Run `npx prisma migrate dev`
3. Manually sync SQLAlchemy models in `backend/models.py`

### Environment Variables

Backend configuration via `.env` file:

```bash
# Database
DATABASE_URL=sqlite:///../ai-assistant.db

# FastAPI
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Anthropic (not used by CLI - subscription only)
ANTHROPIC_API_KEY=sk-ant-...

# Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=google_user_credentials.json
GOOGLE_PROJECT_ID=...
GOOGLE_AI_EMAIL=...
GOOGLE_CALENDAR_ID=primary

# Gmail
GMAIL_USER_EMAIL=...
GMAIL_RECIPIENT_EMAIL=...

# Notifications
NTFY_URL=http://localhost:8080/ai-notifications
NTFY_USERNAME=...
NTFY_PASSWORD=...

# Workspace
AI_WORKSPACE=../ai-workspace

# Timezone
USER_TIMEZONE=America/Los_Angeles
```

---

## AI Workspace

The AI workspace (`ai-workspace/`) is the AI's isolated working directory where it has full freedom to create, modify, and delete files.

### Workspace Philosophy

- **Inside ai-workspace/**: AI has complete control (convention-based boundary)
- **Outside ai-workspace/**: AI uses REST APIs or MCP servers
- **Transparency**: All operations logged and visible to user
- **Safety**: Workspace entirely .gitignored - no accidental commits

### Directory Purpose

```
ai-workspace/
├── memory/                 # Long-term context storage
│   ├── conversations/     # Chat history context
│   ├── learnings/         # Accumulated knowledge
│   └── preferences/       # User preferences
│
├── tasks/                 # Multi-agent execution workspaces
│   └── exec_12345/       # Isolated per-execution directory
│       ├── task.json     # Task configuration
│       ├── shared/       # Context shared between agents
│       │   └── context.json
│       ├── agents/       # Per-agent outputs
│       │   ├── research/
│       │   ├── execute/
│       │   └── review/
│       └── final_result.json
│
├── logs/                  # Structured JSON logs
│   ├── 2026-02-12.json   # Daily rotation
│   └── 2026-02-11.json   # 30-day retention
│
├── dev/                   # AI's project workspace
│   ├── project-a/        # Can contain separate git repos
│   └── project-b/
│
├── output/                # Generated artifacts
│   ├── reports/
│   ├── exports/
│   └── generated-code/
│
└── temp/                  # Ephemeral files
    └── scratch/
```

### Multi-Agent Task Workspace

When a task uses multi-agent orchestration, the system creates an isolated workspace:

```
ai-workspace/tasks/{execution_id}/
├── task.json                      # Original task config
├── shared/
│   └── context.json              # Accumulates agent outputs
├── agents/
│   ├── research/
│   │   ├── instructions.md       # Agent mission
│   │   ├── output.json          # Structured output
│   │   ├── output.md            # Narrative output
│   │   └── status.json          # Execution status
│   ├── execute/
│   │   └── ...
│   └── review/
│       └── ...
└── final_result.json             # Synthesis (if enabled)
```

**Agent Handoff:**
1. Agent reads `shared/context.json` for prior agent outputs
2. Agent executes its role
3. Agent writes results to `agents/{name}/output.json`
4. System updates `shared/context.json` with agent's contribution
5. Next agent starts with full context

---

## Development Workflow

### Initial Setup

```bash
# Clone repository
git clone https://github.com/MyLightIsOn/ai-assistant-prototype.git
cd ai-assistant-prototype

# Install frontend dependencies
cd frontend
npm install
npm run prisma:generate

# Install backend dependencies
cd ../backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Setup database
cd ../frontend
npx prisma migrate dev

# Create .env files
cp backend/.env.example backend/.env
# Edit backend/.env with your credentials
```

### Development Commands

#### Frontend

```bash
cd frontend
npm run dev              # Start dev server (port 3000)
npm run build            # Production build
npm run start            # Start production server
npm run lint             # Run ESLint
npm run prisma:studio    # Open Prisma Studio (DB GUI)
npm run prisma:migrate   # Create new migration
```

#### Backend

```bash
cd backend
source venv/bin/activate
python main.py           # Start FastAPI server (port 8000)
python scheduler.py      # Start task scheduler daemon
python -m pytest         # Run tests
```

#### Database

```bash
# Generate Prisma client (after schema changes)
npx prisma generate -w frontend

# Create migration
npx prisma migrate dev -w frontend --name description

# Reset database (DEV ONLY - destroys all data!)
npx prisma migrate reset -w frontend

# View database
npx prisma studio -w frontend
```

### Git Workflow

**Branch Naming:**
- `feat/feature-name` - New features
- `fix/bug-description` - Bug fixes
- `docs/update-description` - Documentation
- `refactor/component-name` - Code refactoring
- `test/test-description` - Test additions

**Commit Messages:**
Follow Conventional Commits format:

```
feat(backend): implement calendar to cron conversion
fix(chat): prevent duplicate message sends
docs(readme): update installation instructions
refactor(tasks): extract task form validation
test(api): add task creation endpoint tests
```

**PR Workflow:**
1. Create feature branch: `git checkout -b feat/feature-name`
2. Make changes and commit with conventional commit messages
3. Push branch: `git push -u origin feat/feature-name`
4. Create PR on GitHub
5. Request review (or merge if solo project)
6. Squash and merge to main
7. Delete feature branch

### Running Services

**Development (manual):**

```bash
# Terminal 1: Frontend
cd frontend && npm run dev

# Terminal 2: Backend
cd backend && source venv/bin/activate && python main.py

# Terminal 3: Scheduler (optional)
cd backend && source venv/bin/activate && python scheduler.py
```

**Production (PM2):**

```bash
# Start all services
pm2 start ecosystem.config.js

# View status
pm2 status

# View logs
pm2 logs

# Restart service
pm2 restart ai-assistant-web

# Stop all
pm2 stop all
```

---

## File Conventions

### Naming

- **React Components**: PascalCase (`TaskCard.tsx`)
- **Utility files**: camelCase (`apiClient.ts`)
- **Python modules**: snake_case (`task_tools.py`)
- **API routes**: kebab-case directories (`app/api/task-history/`)
- **Test files**: `*.test.ts` or `test_*.py`

### TypeScript

```typescript
// Prefer named exports
export function formatDate(date: Date): string { }

// Use interfaces for objects
interface Task {
  id: string;
  name: string;
  schedule: string;
}

// Use type for unions/primitives
type Status = 'pending' | 'running' | 'completed';

// Add JSDoc for public APIs
/**
 * Creates a new task with the given parameters.
 * @param name - Task name
 * @param schedule - Cron schedule string
 * @returns Created task object
 */
export async function createTask(name: string, schedule: string): Promise<Task>
```

### Python

```python
# Type hints for function signatures
from typing import Optional, List, Dict

def create_task(
    name: str,
    schedule: str,
    priority: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new scheduled task.

    Args:
        name: Task name
        schedule: Cron schedule string (e.g., "0 9 * * *")
        priority: Optional priority level (low/medium/high)

    Returns:
        Dictionary with task details
    """
    pass

# Docstrings for modules
"""
Task management utilities.

This module provides functions for creating, updating, and deleting
scheduled tasks in the AI assistant system.
"""
```

### File Headers

**TypeScript/JavaScript:**
```typescript
/**
 * Task management API client
 *
 * Provides functions for interacting with the backend task API,
 * including CRUD operations and execution history.
 */
```

**Python:**
```python
"""
Task execution scheduler.

APScheduler-based daemon for executing scheduled tasks with retry logic,
error handling, and notification integration.
"""
```

---

## Testing Structure

### Frontend Tests

```
frontend/
├── __tests__/
│   ├── components/
│   │   ├── TaskCard.test.tsx
│   │   └── ChatInterface.test.tsx
│   ├── lib/
│   │   ├── apiClient.test.ts
│   │   └── utils.test.ts
│   └── integration/
│       └── taskWorkflow.test.tsx
└── jest.config.js
```

**Test Command:**
```bash
npm test                 # Run all tests
npm test -- --watch     # Watch mode
npm test -- TaskCard    # Run specific test
```

### Backend Tests

```
backend/
├── tests/
│   ├── test_task_tools.py
│   ├── test_calendar_sync.py
│   ├── test_chat_executor.py
│   └── fixtures/
│       └── test_data.json
└── pytest.ini
```

**Test Command:**
```bash
pytest                           # Run all tests
pytest tests/test_task_tools.py # Run specific file
pytest -v                        # Verbose output
pytest --cov                     # With coverage
```

### Integration Tests

End-to-end tests using Playwright (when implemented):

```
tests/e2e/
├── chat.spec.ts              # Chat interface flows
├── tasks.spec.ts             # Task management flows
└── auth.spec.ts              # Authentication flows
```

---

## Production Deployment

### PM2 Configuration

The `ecosystem.config.js` file defines production services:

```javascript
module.exports = {
  apps: [
    {
      name: 'ai-assistant-web',
      script: 'npm',
      args: 'start',
      cwd: './frontend',
      env: {
        NODE_ENV: 'production',
        PORT: 3000
      }
    },
    {
      name: 'ai-assistant-backend',
      script: 'venv/bin/python',
      args: 'main.py',
      cwd: './backend',
      env: {
        PYTHON_ENV: 'production'
      }
    },
    {
      name: 'ai-assistant-scheduler',
      script: 'venv/bin/python',
      args: 'scheduler.py',
      cwd: './backend',
      autorestart: true,
      max_restarts: 10
    }
  ]
};
```

### Deployment Steps

```bash
# Pull latest code
git pull origin main

# Update frontend
cd frontend
npm install
npm run build

# Update backend
cd ../backend
source venv/bin/activate
pip install -r requirements.txt

# Run migrations (if any)
cd ../frontend
npx prisma migrate deploy

# Restart services
pm2 restart all

# Verify
pm2 status
pm2 logs --lines 50
```

### Health Checks

```bash
# Frontend
curl http://localhost:3000

# Backend
curl http://localhost:8000/health

# Database
sqlite3 ai-assistant.db "SELECT COUNT(*) FROM Task;"
```

---

## Additional Resources

- **API Documentation**: See CLAUDE.md for detailed API routes
- **User Guides**: See `docs/USER_GUIDE_CHAT.md` for chat interface
- **Architecture Details**: See CLAUDE.md for design decisions
- **Contributing**: Follow Git workflow and commit conventions above

---

## Version Information

**Last Updated:** February 12, 2026
**Document Version:** 1.0
**Project Phase:** Phase 2 Complete

**Maintainer:** Lawrence Moore
**Repository:** https://github.com/MyLightIsOn/ai-assistant-prototype
