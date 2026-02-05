Architecture Documentation
Prerequisites

The following must be configured before running this application:
- Mac Mini with macOS
- Tailscale installed and configured for secure network access
- Docker (for self-hosted ntfy.sh notification server)
- Node.js 18+ and npm
- Python 3.11+
- Claude Code CLI installed and authenticated (npm install -g @anthropic-ai/claude-code)
- Gmail account for AI assistant (e.g., your-ai-assistant@gmail.com)
- Google Cloud project with APIs enabled:
  - Google Calendar API
  - Google Drive API
  - Gmail API
  - Cloud Pub/Sub API

Repository Structure
This project uses a monorepo approach, with all components (frontend, backend, documentation) in a single repository. This simplifies development, deployment, and version control.

See Project Structure Documentation for detailed directory layout.

Tech Stack
Frontend
Framework: Next.js 14+ (App Router)
UI Library: React 18+
Styling: Tailwind CSS
PWA: next-pwa for offline support and mobile installation
Real-time: WebSocket connection for live updates
State Management: Zustand for client state, React Query for server state
UI Components: shadcn/ui (Radix UI primitives with Tailwind)
Authentication: NextAuth.js (session-based, 30-day sessions)
Backend
API: Python FastAPI for AI integration and task execution
AI Integration: Claude Code CLI as subprocess (uses user's subscription)
Task Scheduler: APScheduler daemon with retry logic
Database: SQLite (simple, file-based, perfect for single-user)
ORM:
  - Frontend: Prisma (TypeScript client, schema source of truth)
  - Backend: SQLAlchemy (Python, manually synced with Prisma schema)
Real-time: Python FastAPI WebSocket for streaming terminal output and events
Infrastructure
Hosting: Mac Mini (self-hosted)
Network: Tailscale for secure access
Notifications: Self-hosted ntfy.sh (instant alerts) + Gmail (detailed reports)
Process Manager: PM2 for keeping services running
Event Bus: Google Cloud Pub/Sub (Calendar webhooks, Drive notifications)
Google Workspace:
  - Gmail: AI's dedicated account for sending reports
  - Google Calendar: Task visualization and manual triggers
  - Google Drive: Long-term log archival and file storage
  - Google Docs/Sheets: Formatted reports and data analysis
System Architecture
┌─────────────────────────────────────────────────────────┐
│                    User (Phone/Desktop)                  │
│                  via Tailscale + PWA                     │
└───────────────────────┬─────────────────────────────────┘
│
│ HTTPS
▼
┌─────────────────────────────────────────────────────────┐
│              Next.js Application (Port 3000)             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Frontend (React + Tailwind)                     │   │
│  │  - Dashboard UI                                  │   │
│  │  - Chat Interface                                │   │
│  │  - Task Management                               │   │
│  │  - Terminal Viewer                               │   │
│  │  - PWA Manifest + Service Worker                 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  API Routes                                      │   │
│  │  - /api/auth/* (NextAuth)                       │   │
│  │  - /api/tasks/* (CRUD operations)               │   │
│  │  - /api/logs (activity feed)                    │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Prisma ORM → SQLite Database                   │   │
│  │  - User (auth)                                   │   │
│  │  - Task (scheduled tasks)                       │   │
│  │  - ActivityLog (history)                        │   │
│  │  - Notification (sent messages)                 │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────┘
│
│ IPC / HTTP
▼
┌─────────────────────────────────────────────────────────┐
│         Python AI Backend (Port 8000)                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  FastAPI Service                                 │   │
│  │  - Claude Code Integration                       │   │
│  │  - MCP Server Management                         │   │
│  │  - Task Execution Engine                         │   │
│  │  - Terminal Output Streaming                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Task Scheduler Daemon (APScheduler)             │   │
│  │  - Reads tasks from SQLite via SQLAlchemy       │   │
│  │  - Cron-style scheduling with persistence       │   │
│  │  - Executes Claude Code subprocess               │   │
│  │  - Retry logic: 3 attempts, exponential backoff │   │
│  │  - Sends ntfy notifications on final failure    │   │
│  │  - Streams output via WebSocket                  │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────┘
│
│
▼
┌─────────────────────────────────────────────────────────┐
│                  AI Workspace                            │
│  /ai-workspace/                                          │
│  ├── memory/         (Persistent context)               │
│  ├── logs/           (Execution logs)                   │
│  ├── output/         (Generated files)                  │
│  └── temp/           (Temporary work)                   │
└─────────────────────────────────────────────────────────┘
Database Schema (Prisma)
// schema.prisma

datasource db {
provider = "sqlite"
url      = env("DATABASE_URL")  // Points to project root: file:../ai-assistant.db
}

generator client {
provider = "prisma-client-js"
}

model User {
id            String    @id @default(cuid())
email         String    @unique
name          String?
passwordHash  String    // Hashed with bcrypt
createdAt     DateTime  @default(now())
updatedAt     DateTime  @updatedAt
sessions      Session[]
tasks         Task[]
}

model Session {
id           String   @id @default(cuid())
sessionToken String   @unique
userId       String
expires      DateTime
user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model Task {
id          String    @id @default(cuid())
userId      String
name        String
description String?
command     String    // e.g., "research", "backup", "analyze"
args        String    // JSON string of arguments
schedule    String    // Cron format: "0 8 * * *"
enabled     Boolean   @default(true)
priority    String    @default("default") // "low", "default", "high", "urgent"
notifyOn    String    @default("completion,error") // Comma-separated
createdAt   DateTime  @default(now())
updatedAt   DateTime  @updatedAt
lastRun     DateTime?
nextRun     DateTime?
user        User      @relation(fields: [userId], references: [id], onDelete: Cascade)
executions  TaskExecution[]
}

model TaskExecution {
id          String    @id @default(cuid())
taskId      String
status      String    // "running", "completed", "failed"
startedAt   DateTime  @default(now())
completedAt DateTime?
output      String?   // Terminal output or error message
duration    Int?      // Milliseconds
task        Task      @relation(fields: [taskId], references: [id], onDelete: Cascade)
logs        ActivityLog[]
}

model ActivityLog {
id          String    @id @default(cuid())
executionId String?
type        String    // "task_start", "task_complete", "notification_sent", "error"
message     String
metadata    String?   // JSON string for additional context
createdAt   DateTime  @default(now())
execution   TaskExecution? @relation(fields: [executionId], references: [id])
}

model Notification {
id          String    @id @default(cuid())
title       String
message     String
priority    String    @default("default")
tags        String?   // Comma-separated
sentAt      DateTime  @default(now())
delivered   Boolean   @default(true)
readAt      DateTime?
}

model AiMemory {
id          String    @id @default(cuid())
key         String    @unique // e.g., "last_research_topic", "user_preferences"
value       String    // JSON string
category    String?   // "preference", "context", "fact"
createdAt   DateTime  @default(now())
updatedAt   DateTime  @updatedAt
}
Component Structure
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx
│   │   └── layout.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx           # Main dashboard layout with nav
│   │   ├── page.tsx             # Dashboard home
│   │   ├── tasks/
│   │   │   ├── page.tsx         # Task list view
│   │   │   ├── [id]/
│   │   │   │   └── page.tsx     # Task detail/edit
│   │   │   └── new/
│   │   │       └── page.tsx     # Create new task
│   │   ├── chat/
│   │   │   └── page.tsx         # Chat interface
│   │   ├── terminal/
│   │   │   └── page.tsx         # Live terminal view
│   │   ├── activity/
│   │   │   └── page.tsx         # Activity log
│   │   └── settings/
│   │       └── page.tsx         # User settings
│   ├── api/
│   │   ├── auth/
│   │   │   └── [...nextauth]/
│   │   │       └── route.ts     # NextAuth config
│   │   ├── tasks/
│   │   │   ├── route.ts         # GET, POST tasks
│   │   │   └── [id]/
│   │   │       └── route.ts     # GET, PUT, DELETE task
│   │   └── logs/
│   │       └── route.ts         # GET activity logs
│   ├── layout.tsx               # Root layout
│   ├── globals.css              # Tailwind imports
│   └── manifest.json            # PWA manifest
├── components/
│   ├── ui/                      # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── dashboard/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   ├── TaskCard.tsx
│   │   ├── ActivityFeed.tsx
│   │   └── StatsOverview.tsx
│   ├── chat/
│   │   ├── ChatInterface.tsx
│   │   ├── MessageBubble.tsx
│   │   └── ChatInput.tsx
│   ├── terminal/
│   │   ├── TerminalView.tsx
│   │   └── TerminalLine.tsx
│   └── tasks/
│       ├── TaskList.tsx
│       ├── TaskForm.tsx
│       ├── ScheduleInput.tsx    # Cron builder with natural language
│       └── TaskStatusBadge.tsx
├── lib/
│   ├── prisma.ts                # Prisma client singleton
│   ├── auth.ts                  # NextAuth config
│   ├── websocket.ts             # WebSocket client
│   └── utils.ts                 # Utility functions
├── hooks/
│   ├── useWebSocket.ts
│   ├── useTasks.ts
│   ├── useActivityLog.ts
│   └── useAuth.ts
└── types/
├── task.ts
├── activity.ts
└── api.ts
Python Backend Structure
backend/
├── main.py                      # FastAPI app with WebSocket endpoint
├── scheduler.py                 # APScheduler daemon
├── claude_interface.py          # Claude Code subprocess integration
├── ntfy_client.py               # ntfy notification sender
├── models.py                    # SQLAlchemy models + Pydantic schemas
├── database.py                  # SQLAlchemy session management
└── requirements.txt             # APScheduler, SQLAlchemy, FastAPI, etc.
Authentication Flow
User Registration/Login

NextAuth.js with Credentials provider
Password hashed with bcrypt
JWT stored in HTTP-only cookie
Since it's self-hosted, simple username/password is fine
Session Management

Sessions stored in SQLite via Prisma
30-day session expiry (configurable)
Automatic refresh on activity
API Protection

All API routes check for valid session
Middleware validates JWT on each request
Real-time Communication
WebSocket Connection
Established on dashboard load
Used for:
Live terminal output streaming
Task status updates
Activity log updates
Notification delivery
Flow:
User opens dashboard
→ WebSocket connects to /api/ws
→ Server authenticates via session
→ Server sends initial state
→ Bidirectional updates begin
→ Frontend sends: chat messages, commands
→ Backend sends: terminal output, status updates, logs
PWA Configuration
// next.config.js
const withPWA = require('next-pwa')({
dest: 'public',
register: true,
skipWaiting: true,
disable: process.env.NODE_ENV === 'development'
})

module.exports = withPWA({
// Next.js config
})
// public/manifest.json
{
"name": "AI Assistant",
"short_name": "AI Assistant",
"description": "Personal AI Assistant Dashboard",
"start_url": "/",
"display": "standalone",
"background_color": "#000000",
"theme_color": "#000000",
"icons": [
{
"src": "/icons/icon-192x192.png",
"sizes": "192x192",
"type": "image/png"
},
{
"src": "/icons/icon-512x512.png",
"sizes": "512x512",
"type": "image/png"
}
]
}
Deployment & Process Management
PM2 Configuration
// ecosystem.config.js
const path = require('path');

module.exports = {
apps: [
{
name: 'ai-assistant-web',
script: 'npm',
args: 'start',
cwd: path.join(__dirname, 'frontend'),
env: {
NODE_ENV: 'production',
PORT: 3000
}
},
{
name: 'ai-assistant-backend',
script: 'python',
args: 'main.py',
cwd: path.join(__dirname, 'backend'),
interpreter: path.join(__dirname, 'backend/venv/bin/python'),
env: {
PYTHONUNBUFFERED: '1'
}
},
{
name: 'ai-assistant-scheduler',
script: 'python',
args: 'scheduler.py',
cwd: path.join(__dirname, 'backend'),
interpreter: path.join(__dirname, 'backend/venv/bin/python'),
env: {
PYTHONUNBUFFERED: '1'
}
}
]
}
Commands
# Start all services
pm2 start ecosystem.config.js

# Monitor services
pm2 monit

# View logs
pm2 logs

# Restart services
pm2 restart all

# Set to start on boot
pm2 startup
pm2 save
Environment Variables
# frontend/.env.local (Next.js)
DATABASE_URL="file:../ai-assistant.db"  # Project root
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="generate-with-openssl-rand-base64-32"
PYTHON_BACKEND_URL="http://localhost:8000"

# backend/.env (Python)
DATABASE_URL="file:../ai-assistant.db"  # Project root (same file)
NTFY_URL="http://localhost:8080/ai-notifications"
NTFY_USERNAME="your-username-ai"
NTFY_PASSWORD="your-secure-password"
AI_WORKSPACE="./ai-workspace"  # Relative to project root
Security Considerations
Authentication

Strong password requirements
Rate limiting on login attempts
Session timeout after inactivity
API Security

All routes require authentication
Input validation with Zod
SQL injection protection via Prisma
XSS protection via React
Network Security

Accessed only via Tailscale
No public port exposure
HTTPS via Tailscale HTTPS
AI Safety

AI "Desktop" Model:
  - AI operates in ai-workspace/ directory with full freedom
  - External access only via MCP servers and APIs (logged and mediated)
  - Convention-based boundaries (transparent, inspectable)
  - Entire ai-workspace/ is .gitignored
  - AI can create separate git repos in ai-workspace/dev/
Claude Code Integration:
  - Spawns as subprocess using user's subscription
  - Inherits MCP server config from ~/.claude/
  - No API keys stored in this app
  - Terminal output streamed via WebSocket
Unattended Operation:
  - Safe for scheduled tasks (AI workspace is bounded)
  - All operations logged in structured JSON format
  - Retry logic prevents false alarm notifications
Performance Considerations
Database

SQLite is single-user, perfect for this use case
Indexes on frequently queried fields
Regular VACUUM to optimize
Real-time Updates

WebSocket connection pool
Debounce terminal output updates
Pagination for long lists
Caching

React Query for API responses
Service Worker for offline support
Static asset caching
Mobile Considerations (PWA)
Responsive Design

Mobile-first Tailwind breakpoints
Touch-friendly UI elements
Swipe gestures for navigation
Offline Support

Service Worker caches UI
Queue actions when offline
Sync when connection restored
Performance

Lazy load components
Optimize bundle size
Progressive image loading
Key Architecture Decisions
Task Scheduling (APScheduler)

SQLite job store for persistence across restarts
Cron-style scheduling syntax
Retry Logic:
  - 3 attempts per failed task
  - Exponential backoff: 1min, 5min, 15min
  - Notify user only after final failure
  - All attempts logged to ActivityLog
Logging Strategy

Format: Structured JSON logs
Rotation: Daily (midnight)
Retention: 30 days of history
Location: ai-workspace/logs/
Contents: Task executions, API calls, errors, Claude Code output
UI Integration: Recent logs (24h) exposed via /api/logs
Terminal Output Streaming

Method: Chunk-based via WebSocket
Buffer: 1KB chunks or 500ms timeout (whichever comes first)
Priority: Efficiency over real-time feel
Connection: Python FastAPI WebSocket at ws://localhost:8000/ws
Message Types:
  - terminal_output: Claude Code subprocess output
  - task_status: Task state changes
  - notification: System notifications
  - activity_log: New activity log entries
Session Management

Duration: 30 days absolute expiry
Inactivity: No timeout (long-lived sessions)
Rationale: Single-user private network, convenience over strict security
Storage: Database-backed (Session table)
Frontend State Management

Client State: Zustand (lightweight, TypeScript-friendly)
Server State: React Query / TanStack Query (caching, refetching)
UI Components: shadcn/ui (copy-paste, built on Radix UI)
Database Architecture

Schema Source: Prisma (frontend/prisma/schema.prisma)
Migrations: Managed by Prisma CLI
Frontend ORM: Prisma Client (TypeScript, auto-generated)
Backend ORM: SQLAlchemy (Python, manually synced with schema)
Location: Project root (ai-assistant.db)
Backup: Daily automated task at 3 AM
WebSocket Architecture

Server: Python FastAPI (not Next.js)
Endpoint: ws://localhost:8000/ws
Authentication: Verify session token on connection
Broadcasting: Server pushes updates to connected clients
Use Cases: Terminal streaming, task updates, real-time logs
Google Workspace Integration

Hybrid Architecture: Database as Source of Truth
  - Tasks stored in SQLite with full metadata
  - APScheduler executes recurring cron-based tasks
  - Google Calendar mirrors tasks for visualization
  - Manual Calendar events trigger via Pub/Sub webhooks
  - Bi-directional sync: UI → DB → Calendar, Calendar → Pub/Sub → DB

Google Cloud Pub/Sub (Central Event Bus)
  - Receives push notifications from Google Calendar
  - Webhook endpoint: /api/google/calendar/webhook
  - Authenticates Pub/Sub messages
  - Triggers task execution for manual Calendar events
  - Future: Drive change notifications, Gmail push

Gmail Integration (AI's Account)
  - Dedicated Gmail: your-ai-assistant@gmail.com
  - **Outbound (Sending):**
    - Task completion summaries
    - Daily/weekly digests
    - Error reports with logs
    - On-demand reports via chat
    - Backup notification channel (redundancy with ntfy)
  - **Inbound (Manual Reading Only):**
    - Read access to AI's inbox (manual trigger only)
    - User gets normal Gmail notifications on phone
    - User explicitly tells AI which emails to read/process
    - On-demand email processing via chat or UI commands
    - Examples:
      - User: "Read the email from John about the invoice"
      - User: "Process that receipt email I just forwarded"
      - User: "Summarize the article email from this morning"
    - Attachment processing when instructed
    - Email parsing and data extraction on command
    - **No automatic monitoring** - AI only reads when told
  - **Use Cases:**
    - Forward invoice → AI extracts data, logs to spreadsheet
    - Forward article → AI summarizes, saves to Drive
    - Forward meeting notes → AI creates calendar events
    - Email commands: "Create task: Research topic X, daily at 9am"
    - Attachment processing: PDFs, images, data files → Drive

Google Calendar Integration
  - Purpose: Visual UI + manual task triggers
  - Sync Direction: Bi-directional
    - DB tasks → Calendar events (for visibility)
    - Calendar events → Pub/Sub → DB tasks (manual scheduling)
  - Event Metadata:
    - Description: Task details and command
    - Color: Priority level (low=blue, default=green, high=orange, urgent=red)
    - Reminders: Configured per task
  - Recurring Tasks: Cron expressions in DB, shown as recurring events in Calendar
  - Shared Calendar: AI calendar shared with user's personal Google account

Google Drive Integration
  - Purpose: Long-term storage and archival
  - Folder Structure:
    ```
    AI Assistant Drive/
    ├── logs/
    │   └── YYYY/MM/
    │       └── daily-logs.json
    ├── reports/
    │   ├── weekly-summaries/
    │   └── task-reports/
    ├── research/
    │   └── [topic]/findings.md
    └── artifacts/
        └── [generated files]
    ```
  - Archive Strategy:
    - Logs older than 30 days moved from local to Drive
    - Task outputs and generated files
    - AI research and findings
    - Formatted reports (Docs/Sheets)
  - Sharing: User has view/edit access to all folders

Google Docs/Sheets Integration
  - AI creates formatted documents for reports
  - Sheets for data analysis and visualization
  - Better presentation than plain text
  - Collaborative editing if needed

Authentication & Permissions
  - AI Service Account: Dedicated Gmail account
  - Google Cloud Project: AI-managed project
  - API Credentials: Service account JSON key
  - Permissions:
    - Calendar: Full access to AI's calendar
    - Drive: Full access to AI's drive
    - Gmail: Send-only (no reading user's email)
  - User Access: Shared calendars and Drive folders

Python Libraries
  - google-auth, google-auth-oauthlib, google-auth-httplib2
  - google-api-python-client
  - google-cloud-pubsub

Development Workflow
# Frontend development
cd frontend
npm run dev

# Backend development
cd backend
python main.py

# Database migrations
npx prisma migrate dev

# Type generation
npx prisma generate
Testing Strategy
Frontend

Jest + React Testing Library
Playwright for E2E tests
Component visual regression
Backend

pytest for Python
Integration tests for API
Mock Claude Code for testing
Security

OWASP dependency check
Regular security audits
Penetration testing
Future Enhancements (Phase 2+)
Multi-Agent Orchestration (Phase 2 Priority):
  - Main AI coordinates specialized sub-agents for complex tasks
  - User flow: Task → AI suggests agents → User configures → Parallel execution → Synthesis
  - Communication: Shared workspace files (ai-workspace/tasks/task-id/)
  - Roles: Hybrid library (predefined + user-custom)
  - Examples: Security Reviewer, Test Writer, Documentation Specialist, Research Agent
  - Architecture: Multiple Claude Code subprocesses, main AI mediates

Voice Interface: Add speech-to-text for mobile
Multi-user Support: If you want to share with family
Plugin System: Custom task types and integrations
Analytics Dashboard: Task success rates, AI usage stats, cost tracking
Mobile App: Native iOS/Android wrapper
AI Model Selection: Switch between Claude models (Sonnet, Opus, Haiku)
Integration Hub: Connect more services via MCP and APIs
Documentation Structure
docs/
├── ARCHITECTURE.md          # This file
├── NTFY_SETUP.md           # ntfy configuration
├── API.md                  # API documentation
├── DEVELOPMENT.md          # Dev setup guide
├── DEPLOYMENT.md           # Production deployment
└── USER_GUIDE.md           # End-user documentation