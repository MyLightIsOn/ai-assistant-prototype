# AI Assistant Prototype

A personal AI assistant that combines Claude Code with selective MCP integrations in a controlled environment.

## Current Status

**Phase 2 Complete** - Core infrastructure fully functional:
- ✅ Task scheduling with one-time and recurring task support
- ✅ Google Calendar bidirectional sync with cron conversion
- ✅ Gmail email notifications on task completion/failure
- ✅ Chat interface with Claude subscription (no API costs)
- ✅ Multi-agent task orchestration
- ✅ End-to-end testing infrastructure

## Overview

This project creates a simplified, secure alternative to tools like OpenClaw, focusing on:
- Running in a controlled SSH environment (Mac Mini)
- Hand-picked MCP servers only
- Minimal attack surface
- Simple, direct communication

## Core Features

### 1. Chat Interface
- Real-time chat with Claude via WebSocket
- Task creation and management through natural language
- Uses Claude subscription (not API) - no per-token costs
- Full conversation history and context

### 2. Task Scheduling & Calendar Integration
- Cron-style scheduling for recurring tasks
- **Bidirectional Google Calendar sync**:
  - Tasks created in chat → synced to Google Calendar
  - Calendar events → automatically converted to scheduled tasks
- Intelligent calendar-to-cron conversion with timezone support
- Example: "Do research on [topic] and give me the latest news at 8 AM daily"

#### Calendar Event Conversion

Google Calendar events are automatically converted to cron schedules:

| Event Type | Example | Cron Output |
|------------|---------|-------------|
| One-time timed | 9 AM on Jan 15 | `0 9 15 1 *` |
| One-time all-day | Jan 15 | `0 0 15 1 *` |
| Daily recurring | Every day at 6 AM | `0 6 * * *` |
| Weekly recurring | Mondays at 3 PM | `0 15 * * 1` |
| Weekly multi-day | Mon/Wed/Fri at 9 AM | `0 9 * * 1,3,5` |
| Monthly recurring | 15th of month at 10 AM | `0 10 15 * *` |
| Yearly recurring | Jan 15 at 10 AM | `0 10 15 1 *` |

All times are converted to Pacific Time (America/Los_Angeles).

### 3. Multi-Agent Task Orchestration
- Coordinate multiple specialized Claude agents for complex tasks
- Sequential execution: Research → Execute → Review
- Custom agent roles for specialized domain expertise
- File-based coordination with transparent workspace
- Optional result synthesis for cohesive deliverables
- Real-time WebSocket broadcasting of agent progress

### 4. Outbound Communication (AI → User)
- **ntfy.sh notifications**: Instant alerts for task completion/errors
- **Gmail**: Automated email reports with detailed results
- **Google Calendar**: Task schedules visible in shared calendar
- **Google Drive**: Long-term log storage (planned)
- Configurable notification thresholds per task

### 5. Dual Interface
- Web UI for user interaction and task management
- Real-time WebSocket terminal view for AI actions
- Chat interface for natural language task creation
- Complete transparency into what the AI is doing

### 6. Persistent Memory/Context
- Dedicated `ai-workspace/` directory for AI operations
- SQLite database for task state, execution history, and AI memory
- Chat conversation history and context
- Enables continuity: "continue working on that project from yesterday"
- User can inspect and modify AI memory as needed

### 7. Task Queue/Status Tracking
- Real-time tracking of task states: pending, running, completed, failed
- Prevents duplicate scheduling
- Execution history with detailed logs and metadata
- Activity log for complete audit trail
- Easy visibility into current workload via UI

### 8. Safe Workspace Boundaries
- Convention-based boundaries: AI has full freedom within `ai-workspace/`
- External access via MCP servers or REST APIs
- Claude Code subprocess isolation
- Safe for unattended scheduled tasks
- Transparent logging of all operations

## Architecture Principles

- **Simplicity**: No social features, multi-platform complexity, or community modules
- **Security**: Minimal credentials, controlled environment, explicit permissions
- **Transparency**: Always visible what the AI is doing
- **Control**: User maintains full oversight and can intervene

## Technical Stack

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **UI**: React 18+ with Tailwind CSS
- **PWA**: next-pwa for mobile installation and offline support
- **Authentication**: NextAuth.js
- **Real-time**: WebSocket for live updates
- **State**: React Context + hooks

### Backend
- **Web API**: Python FastAPI with WebSocket support
- **AI Service**: Claude Code CLI subprocess integration (subscription-based, not API)
- **Task Scheduler**: APScheduler with SQLAlchemy ORM
- **Database**: SQLite shared between frontend (Prisma) and backend (SQLAlchemy)
- **Notifications**: Self-hosted ntfy.sh + Gmail
- **Calendar**: Google Calendar API with Pub/Sub webhooks

### Infrastructure
- **Hosting**: Mac Mini (self-hosted)
- **Network**: Tailscale for secure remote access
- **Process Management**: PM2 for service orchestration

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed technical design.

## AI Workspace Structure

```
/ai-workspace/
  ├── memory/          # Persistent context and conversation history
  ├── tasks/           # Multi-agent task workspaces (per execution)
  │   └── {execution_id}/
  │       ├── task.json       # Task configuration
  │       ├── shared/         # Shared context between agents
  │       ├── agents/         # Per-agent outputs
  │       └── final_result.json
  ├── logs/            # Execution logs (JSON, 30-day retention)
  ├── dev/             # AI's project workspace (can contain git repos)
  ├── output/          # Generated files and artifacts
  └── temp/            # Temporary working files
```

## Communication Strategy

**Multi-channel approach for different notification types:**

1. **ntfy.sh** (Instant notifications)
   - Self-hosted on Mac Mini for complete privacy
   - Mobile and desktop push notifications
   - Task completion, errors, status updates
   - See [NTFY Setup Guide](docs/NTFY_SETUP.md)

2. **Gmail** (Detailed reports)
   - Automated email reports on task completion/failure
   - AI's dedicated Gmail account (hello@hcidesignlab.com)
   - Configurable per-task: notify on completion, error, or both
   - Formatted email body with task details and execution logs

3. **Google Calendar** (Schedule visibility)
   - Bidirectional sync: tasks ↔ calendar events
   - Scheduled tasks appear as calendar events
   - Calendar events auto-create tasks with proper cron schedules
   - Shared calendar for easy visibility

4. **Google Drive** (Planned)
   - Long-term log storage and archival
   - Generated reports and artifacts

**Workflow:**
1. Task scheduled → Appears in Google Calendar
2. Task executes → Real-time WebSocket updates in UI
3. Task completes → ntfy notification + Email report (if configured)
4. Execution logged → Available in UI and database

## Project Structure

This is a **monorepo** containing both the Next.js frontend and Python backend services. Everything lives in one repository for easier development and deployment.

See [Project Structure Documentation](docs/PROJECT_STRUCTURE.md) for detailed layout and development workflow.

```
ai-assistant-prototype/
├── frontend/          # Next.js + React + Tailwind
├── backend/           # Python FastAPI + Scheduler
├── ai-workspace/      # AI's working directory
├── docs/              # Documentation
└── scripts/           # Utility scripts
```

## Database Schema

SQLite database with dual ORM support:
- **Frontend**: Prisma ORM (TypeScript)
- **Backend**: SQLAlchemy ORM (Python)
- **Source of truth**: Prisma schema (`frontend/prisma/schema.prisma`)

Core models:
- `User` - Authentication and user management
- `Task` - Scheduled tasks with cron timing and metadata
- `TaskExecution` - Execution history with status and results
- `ChatMessage` - Chat conversation history
- `ActivityLog` - System event tracking and audit trail
- `Notification` - Notification delivery history
- `AiMemory` - Persistent context storage

## Development

See [CLAUDE.md](CLAUDE.md) for comprehensive development guidelines and architectural decisions.

### Quick Start

```bash
# Frontend
cd frontend
npm install
npm run dev  # Port 3000

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py  # Port 8000
```

### Key Commands

```bash
# Database
npm run prisma:studio    # Open database GUI
npm run prisma:migrate   # Create migration

# Production
pm2 start ecosystem.config.js  # Start all services
pm2 logs                        # View logs
```

## Notes

- This is NOT trying to replicate OpenClaw's full feature set
- Focus on personal use case: one user, controlled environment
- Security through simplicity and explicit boundaries
- Public repository - no hardcoded credentials, use `.env` files
