# AI Assistant Prototype

A personal AI assistant that combines Claude Code with selective MCP integrations in a controlled environment.

## Overview

This project aims to create a simplified, secure alternative to tools like OpenClaw, focusing on:
- Running in a controlled SSH environment (Mac Mini)
- Hand-picked MCP servers only
- Minimal attack surface
- Simple, direct communication

## Core Features

### 1. Scheduling
- Ability to schedule tasks (e.g., daily research summaries, periodic checks)
- Cron-like capability for recurring tasks
- Example: "Do research on [topic] and give me the latest news at 8 AM daily"

### 2. Outbound Communication (AI → User)
- **Webhook notifications** for quick updates and alerts (Discord/Telegram/Slack/ntfy.sh)
- **Email** for long-form reports and detailed updates
- Hybrid approach: AI sends webhook notification, user can request full email report
- Examples:
  - Webhook: "Research complete!" → User: "Send me the full report" → Email: Detailed breakdown
  - Webhook: "Error in deployment" → Immediate attention
  - Email: Weekly summary of completed tasks

### 3. Dual Interface
- Simple UI for user interaction
- Terminal view available for monitoring AI actions
- Transparency into what the AI is doing

### 4. Persistent Memory/Context
- Dedicated directory for AI to manage its own memory
- Markdown files or SQLite database for context storage
- Enables continuity: "continue working on that project from yesterday"
- User can inspect and modify AI memory as needed

### 5. Task Queue/Status Tracking
- Simple tracking of task states: running, scheduled, completed
- Prevents duplicate scheduling
- JSON file or simple database for state management
- Easy visibility into current workload

### 6. Configurable Notification Thresholds
- Control when AI interrupts vs. just logs
- Examples:
  - "Only email me on errors or completion"
  - "Log progress but don't notify unless critical"
- Prevents notification fatigue

### 7. Safe Workspace Boundaries
- Explicit directory permissions
- Clear read/write/execute boundaries
- Safe for unattended scheduled tasks
- Similar to Claude Code's project directory concept

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
- **Web**: Next.js API Routes
- **AI Service**: Python + FastAPI for Claude Code integration
- **Task Scheduler**: Python daemon with cron-style scheduling
- **Database**: SQLite + Prisma ORM
- **Notifications**: Self-hosted ntfy.sh

### Infrastructure
- **Hosting**: Mac Mini (self-hosted)
- **Network**: Tailscale for secure remote access
- **Process Management**: PM2 for service orchestration

See [Architecture Documentation](docs/ARCHITECTURE.md) for detailed technical design.

## AI Workspace Structure

```
/ai-workspace/
  ├── memory/          # Persistent context and conversation history
  ├── tasks/           # Task definitions and queue
  ├── logs/            # Execution logs
  ├── config/          # Configuration files
  └── output/          # Task results and artifacts
```

## Communication Strategy

**Primary: Self-hosted ntfy.sh notifications** (instant, private, mobile-friendly)
- Self-hosted on Mac Mini for complete privacy
- No external dependencies or account needed
- See [NTFY Setup Guide](docs/NTFY_SETUP.md) for detailed installation

**Secondary: Email for detailed reports**
- AI sends email as user with `[AI Assistant]` prefix in subject
- Used for long-form content, detailed reports, weekly summaries
- Triggered by user request or automatically for certain task types

**Workflow:**
1. AI completes task → Sends ntfy notification: "Task XYZ complete!"
2. User sees notification on phone/desktop
3. User can request details: "Send me the full report"
4. AI emails comprehensive breakdown

**Advantages:**
- Instant notifications without email delays
- Complete privacy (self-hosted)
- No spam filter issues
- Rich formatting support (titles, priorities, emojis, action buttons)
- User controls detail level

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

1. Define specific MCP servers needed
2. Design task scheduling mechanism
3. Create basic directory structure
4. Implement simple UI/terminal interface
5. Set up email integration
6. Build task queue and status tracking
7. Implement memory/context persistence

## Notes

- This is NOT trying to replicate OpenClaw's full feature set
- Focus on personal use case: one user, controlled environment
- Security through simplicity and explicit boundaries
