# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL: Documentation Policy

**NEVER commit the `docs/` directory to git:**
- This repository is PUBLIC
- The `docs/` directory contains detailed architecture and implementation plans
- These details must remain private until the system is verified and production-ready
- The `docs/` directory is intentionally excluded in `.gitignore` and must stay that way
- Only commit documentation when explicitly approved by the user

## Project Overview

This is a personal AI assistant system that combines Claude Code with selective MCP integrations in a controlled environment.

**Current Status:** Phase 1 complete. Phase 2 backend infrastructure complete (PR #51 pending review).

**Core Philosophy:**
- Simplicity over feature complexity
- Security through minimal attack surface
- Full user transparency and control
- Self-hosted on Mac Mini with no external dependencies

## Repository Structure

This is a **monorepo** containing:
- `frontend/` - Next.js 14+ (App Router) + React + Tailwind CSS
- `backend/` - Python FastAPI + Task Scheduler service (Phase 2 complete)
- `ai-workspace/` - AI's working directory for memory, logs, and outputs
- `docs/` - Comprehensive architecture and setup documentation (**NEVER commit to git**)

## Key Architecture Decisions

### Communication Strategy
- **Instant notifications:** Self-hosted ntfy.sh (instant, private, mobile-friendly)
- **Detailed reports:** Gmail (AI's dedicated account sends formatted emails)
- **Task visualization:** Google Calendar (shared calendar for task schedule)
- **Long-term storage:** Google Drive (logs, reports, generated files)
- **Event bus:** Google Cloud Pub/Sub (Calendar webhooks, future integrations)
- Workflow: Task completes → ntfy notification → Detailed email report → Logs archived to Drive

### Tech Stack Rationale
- **Frontend:** Next.js App Router with PWA support, Zustand for state management, shadcn/ui components
- **Backend:** Python FastAPI for API layer, APScheduler for task scheduling, SQLAlchemy ORM
- **Database:** SQLite (single-user system, simplicity over scale)
  - Frontend: Prisma client (TypeScript, generated from schema)
  - Backend: SQLAlchemy models (Python, manually synced with Prisma schema)
  - Schema source of truth: Prisma (`frontend/prisma/schema.prisma`)
- **Real-time:** Python FastAPI WebSocket for live terminal output and status updates
- **AI Integration:** Claude Code CLI as subprocess (uses user's subscription, no API key needed)
- **Infrastructure:** PM2 for process management, Tailscale for secure access (prerequisite)

### Data Flow
1. Next.js frontend (Port 3000) serves UI, user authentication, and database API routes
2. Python backend (Port 8000) manages Claude Code subprocess, WebSocket streaming, and task execution
3. APScheduler daemon runs cron-style recurring tasks with retry logic (3 attempts, exponential backoff)
4. SQLite database (project root) stores tasks, execution history, and AI memory
5. AI Workspace (`ai-workspace/`) is the AI's "desktop" - full freedom within, external access via MCP servers
6. WebSocket connection streams terminal output, task status, and real-time updates from Python backend
7. Claude Code subprocess inherits MCP server configuration from user's `~/.claude/` settings

## Development Commands (Once Implemented)

### Setup
```bash
# Install all dependencies
npm install

# Setup Python environment
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Database setup
npm run prisma:generate
npm run prisma:migrate
```

### Development
```bash
# Start all services
npm run dev:all

# Or individually:
npm run dev              # Frontend (port 3000)
npm run dev:backend      # Python API (port 8000)
npm run dev:scheduler    # Task scheduler
```

### Database
```bash
npm run prisma:studio    # Open database GUI
npm run prisma:migrate   # Create migration
npx prisma migrate reset -w frontend  # Reset DB (dev only)
```

### Production
```bash
npm run build            # Build frontend
pm2 start ecosystem.config.js  # Start all services
pm2 logs                 # View logs
```

## Database Schema (Prisma)

The SQLite database uses Prisma ORM with these core models:
- `User` - Authentication (single user, expandable)
- `Task` - Scheduled tasks with cron-style timing
- `TaskExecution` - Execution history and results
- `ActivityLog` - System event tracking
- `Notification` - Sent notification history
- `AiMemory` - Persistent context storage

Schema location: `frontend/prisma/schema.prisma` (when created)

## AI Workspace Structure

The AI operates within its "desktop" directory (`ai-workspace/`):
- `memory/` - Persistent context and conversation history
- `logs/` - Structured JSON execution logs (daily rotation, 30-day retention)
- `output/` - Generated files and artifacts
- `temp/` - Temporary working files
- `dev/` - AI's project workspace (can contain separate git repos)

**Security Model:**
- **Inside ai-workspace/:** AI has full freedom to create, modify, delete
- **Outside ai-workspace/:** AI must use MCP servers (filesystem, git, web) or Python APIs
- **Convention-based boundaries:** Claude Code subprocess starts in ai-workspace/ directory
- **Version control:** Entire ai-workspace/ is .gitignored; AI can init separate repos in dev/

This provides safe, transparent boundaries for unattended AI operations while maintaining flexibility.

## Authentication & Security

- NextAuth.js for session-based authentication (30-day sessions, no inactivity timeout)
- Passwords hashed with bcrypt
- All API routes require valid session
- Network access exclusively via Tailscale VPN (prerequisite - must be configured)
- No public port exposure
- AI workspace uses convention-based boundaries (transparency over enforcement)
- Structured JSON logging with 30-day retention for audit trail
- Automated daily database backups

## Development Workflow

### Git Strategy
- `main` - Production-ready code
- `feature/*` - Feature branches
- Conventional Commits format: `feat(frontend): description`

### Component Organization
- **Pages:** `frontend/app/` (App Router structure)
- **Components:** `frontend/components/` (reusable UI)
- **API Routes:** `frontend/app/api/` (Next.js API)
- **Python Services:** `backend/*.py` (separate files per concern)

### Environment Variables
Frontend (`.env.local`):
- `DATABASE_URL`, `NEXTAUTH_URL`, `NEXTAUTH_SECRET`, `PYTHON_BACKEND_URL`

Backend (`.env`):
- `DATABASE_URL`, `NTFY_URL`, `NTFY_USERNAME`, `NTFY_PASSWORD`, `AI_WORKSPACE`

## PM2 Process Management

Production services run via PM2 (`ecosystem.config.js`):
- `ai-assistant-web` - Next.js server (port 3000)
- `ai-assistant-backend` - FastAPI service (port 8000)
- `ai-assistant-scheduler` - Task scheduler daemon

## Integration: ntfy.sh Self-Hosted

Notification server setup (see `docs/NTFY_SETUP.md`):
- Docker-based deployment on Mac Mini
- Authentication with separate AI and user accounts
- Python client for sending notifications
- Mobile app subscription for instant alerts

## Design Principles

When implementing features:

1. **Avoid Over-Engineering**
   - Keep solutions simple and focused
   - Don't add features beyond what's requested
   - Single-user system doesn't need multi-tenant complexity

2. **Transparency First**
   - User should always see what AI is doing
   - Terminal output visible in real-time
   - All tasks and executions logged

3. **Security Through Simplicity**
   - Minimal credentials and external dependencies
   - Explicit file permissions and boundaries
   - Safe for unattended scheduled operations

4. **User Control**
   - Manual approval for sensitive operations
   - Configurable notification thresholds
   - Easy access to AI memory and task queue

## Key Technical Decisions

**Task Scheduling:**
- APScheduler with SQLite job store for persistence
- Retry logic: 3 attempts with exponential backoff (1min, 5min, 15min)
- Notify user only after all retries exhausted

**Logging:**
- Structured JSON logs with daily rotation
- 30-day retention, exposed in UI for recent logs
- All task executions, API calls, and errors logged

**Terminal Streaming:**
- Chunk-based (1KB or 500ms timeout)
- Efficiency over real-time feel
- WebSocket auto-updates UI without refresh

**State Management:**
- Zustand for client state
- React Query for server state/caching
- shadcn/ui for UI components

**Multi-Agent Orchestration (Phase 2):**
- Main AI coordinates specialized sub-agents
- Shared workspace files for communication
- Parallel execution, hybrid role library (predefined + custom)
- Future enhancement after core app is stable

## Documentation

Comprehensive docs in `docs/`:
- `ARCHITECTURE.md` - Detailed system design and component structure
- `PROJECT_STRUCTURE.md` - Monorepo layout and development workflow
- `NTFY_SETUP.md` - Self-hosted notification server setup
- `DEVELOPMENT.md` - Development setup guide
- `DEPLOYMENT.md` - Production deployment guide
- `API.md` - API endpoints and WebSocket message types

Keep documentation synchronized when making architectural changes.

## Current State

**Status:** Planning and documentation phase complete. Implementation has not started.

The repository currently contains:
- Complete architectural documentation
- Detailed technical specifications
- Project structure planning
- Setup guides for infrastructure (ntfy.sh)

**Next Steps:**
1. Create `frontend/` directory with Next.js setup
2. Create `backend/` directory with Python services
3. Implement Prisma schema and database
4. Build core UI components
5. Integrate Claude Code execution
6. Implement task scheduling system
7. Add ntfy.sh notification integration
