## ⚠️ CRITICAL: Documentation Policy

**NEVER commit the `docs/` directory to git:**
- This repository is PUBLIC
- The `docs/` directory contains detailed architecture and implementation plans
- These details must remain private until the system is verified and production-ready
- The `docs/` directory is intentionally excluded in `.gitignore` and must stay that way
- Only commit documentation when explicitly approved by the user

---

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

**Multi-Agent Orchestration:**
- Sequential execution of specialized agents (research, execute, review, custom)
- File-based coordination via shared workspace
- Optional result synthesis
- Real-time WebSocket broadcasting of agent progress
- Activity logging for complete audit trail
- Metadata-driven configuration (no database schema changes)
- See detailed documentation below

## Documentation

Comprehensive docs in `docs/`:
- `ARCHITECTURE.md` - Detailed system design and component structure
- `PROJECT_STRUCTURE.md` - Monorepo layout and development workflow
- `NTFY_SETUP.md` - Self-hosted notification server setup
- `DEVELOPMENT.md` - Development setup guide
- `DEPLOYMENT.md` - Production deployment guide
- `API.md` - API endpoints and WebSocket message types

Keep documentation synchronized when making architectural changes.

## Multi-Agent Orchestration

### Overview

Multi-agent orchestration enables a single task to coordinate multiple specialized Claude Code agents working sequentially to accomplish complex objectives. Instead of a single AI agent tackling everything, the task can be split into specialized roles:
- **Research**: Information gathering and context building
- **Execute**: Implementation and code writing
- **Review**: Quality assessment and validation
- **Custom**: User-defined roles with specific instructions

This approach improves quality for complex tasks by leveraging specialization, provides better transparency through per-agent outputs, and creates natural checkpoints in the workflow.

**Key Design Principles:**
- Sequential execution (simple, predictable)
- File-based communication (transparent, debuggable)
- Fail-fast on errors (don't waste compute)
- Optional synthesis (cohesive final result)
- Metadata-driven (zero database schema changes)
- Backward compatible (existing tasks unaffected)

### Metadata Configuration

Tasks opt into multi-agent mode by adding an `agents` object to their `metadata` JSON field:

```json
{
  "name": "Implement User Authentication",
  "description": "Add JWT-based auth to the application",
  "command": "claude",
  "metadata": {
    "agents": {
      "enabled": true,
      "sequence": ["research", "execute", "review"],
      "synthesize": true,
      "roles": {
        "research": {
          "type": "research",
          "instructions": "Research auth best practices and review codebase patterns"
        },
        "execute": {
          "type": "execute",
          "instructions": "Implement JWT auth following research findings"
        },
        "review": {
          "type": "review",
          "instructions": "Review implementation for security and quality"
        }
      }
    }
  }
}
```

**Configuration Fields:**
- `enabled` (boolean): Flag to enable multi-agent mode
- `sequence` (array): Agent execution order (e.g., `["research", "execute", "review"]`)
- `synthesize` (boolean): Auto-combine results after all agents complete
- `roles` (object): Per-agent configuration with type and custom instructions

**Built-in Role Types:**
- `research`: Information gathering and documentation exploration
- `execute`: Code implementation and file creation
- `review`: Quality assessment and validation
- `custom`: Fully user-defined role with custom instructions

**Backward Compatibility:**
Tasks without `metadata.agents` or with `enabled: false` use standard single-agent execution.

### Agent Roles

#### Research Agent

**Purpose:** Gather information, explore documentation, build context for implementation.

**Default Behavior:**
- Explores codebase for existing patterns
- Reviews relevant documentation and best practices
- Identifies technical approaches and dependencies
- Provides comprehensive context for execution

**Output Structure:**
```json
{
  "findings": ["Finding 1", "Finding 2"],
  "documentation_links": ["url1", "url2"],
  "code_patterns": ["pattern1", "pattern2"],
  "recommendations": ["recommendation1", "recommendation2"]
}
```

**Example Custom Instructions:**
```json
{
  "type": "research",
  "instructions": "Investigate GraphQL integration patterns in Next.js. Review our current API architecture and identify best practices for adding GraphQL."
}
```

#### Execute Agent

**Purpose:** Implement the solution based on research findings and task requirements.

**Default Behavior:**
- Reads research findings from shared context
- Implements solution following best practices
- Creates/modifies files as needed
- Documents implementation decisions

**Output Structure:**
```json
{
  "files_created": ["file1.py", "file2.py"],
  "files_modified": ["file3.py"],
  "implementation_summary": "What was built...",
  "key_decisions": ["decision1", "decision2"]
}
```

**Example Custom Instructions:**
```json
{
  "type": "execute",
  "instructions": "Build the GraphQL schema and resolvers based on research findings. Use TDD and follow our existing API patterns."
}
```

#### Review Agent

**Purpose:** Assess quality, identify issues, suggest improvements.

**Default Behavior:**
- Reviews implementation for correctness
- Checks code quality and best practices
- Identifies potential issues
- Provides actionable recommendations

**Output Structure:**
```json
{
  "quality_score": 8.5,
  "issues": [
    {"severity": "high", "description": "Issue 1", "location": "file:line"},
    {"severity": "low", "description": "Issue 2", "location": "file:line"}
  ],
  "recommendations": ["Rec 1", "Rec 2"],
  "positive_observations": ["Good 1", "Good 2"]
}
```

**Example Custom Instructions:**
```json
{
  "type": "review",
  "instructions": "Focus security review on authentication flows. Check for SQL injection, XSS, and authorization issues."
}
```

#### Custom Roles

Define fully custom roles for specialized tasks:

```json
{
  "roles": {
    "security_audit": {
      "type": "custom",
      "instructions": "Perform comprehensive security audit. Check for: SQL injection, XSS, CSRF, authentication/authorization flaws, sensitive data exposure, insecure dependencies. Provide risk ratings and remediation steps."
    },
    "performance_analysis": {
      "type": "custom",
      "instructions": "Analyze application performance. Profile database queries, identify N+1 problems, check caching strategies, review asset optimization. Provide benchmarks and optimization recommendations."
    }
  }
}
```

### Execution Flow

When a task with `metadata.agents.enabled = true` is triggered:

**1. Workspace Creation**
```
ai-workspace/tasks/{execution_id}/
├── task.json                    # Main task description
├── shared/
│   └── context.json            # Shared state (updated by each agent)
├── agents/
│   ├── research/
│   │   ├── instructions.md     # Agent's mission
│   │   ├── output.json         # Structured output
│   │   ├── output.md           # Narrative output (optional)
│   │   └── status.json         # Execution status
│   ├── execute/
│   │   └── ...
│   └── review/
│       └── ...
└── final_result.json           # Synthesis output (if enabled)
```

**2. Sequential Agent Execution**

For each agent in the sequence:
1. Generate agent-specific instructions from template + custom instructions
2. Spawn Claude Code subprocess with agent workspace as working directory
3. Agent reads `shared/context.json` for previous agent outputs
4. Agent executes task and writes outputs to `output.json` and `output.md`
5. Update `shared/context.json` with agent's results
6. Broadcast WebSocket events for real-time UI updates
7. If agent fails after 3 retry attempts, stop execution (fail-fast)

**3. Optional Synthesis**

If `synthesize: true`, spawn final synthesis subprocess:
1. Read all agent outputs from workspace
2. Generate cohesive summary combining all findings
3. Provide actionable conclusions and recommendations
4. Write final result to `final_result.json`

**4. Completion**

Mark execution complete, store metadata in TaskExecution record, send notifications.

**Example Timeline:**
```
[00:00] Task triggered → workspace created
[00:01] Research agent started
[00:15] Research agent completed → context updated
[00:16] Execute agent started
[01:01] Execute agent completed → context updated
[01:02] Review agent started
[01:22] Review agent completed → context updated
[01:23] Synthesis started (if enabled)
[01:33] Synthesis completed → final result ready
[01:34] Task marked complete → notification sent
```

**Retry Logic:**
Each agent has 3 retry attempts with exponential backoff:
- Attempt 1 fails → wait 60 seconds → Attempt 2
- Attempt 2 fails → wait 300 seconds (5 min) → Attempt 3
- Attempt 3 fails → execution fails (fail-fast)

### Workspace Structure

Each multi-agent execution creates an isolated workspace in `ai-workspace/tasks/{execution_id}/`.

**Key Files:**

**task.json** - Original task configuration
```json
{
  "id": "task_123",
  "name": "Implement Feature X",
  "description": "Task description...",
  "metadata": {
    "agents": { /* agent config */ }
  }
}
```

**shared/context.json** - Accumulates agent outputs for handoff
```json
{
  "task_description": "Original task description...",
  "completed_agents": ["research", "execute"],
  "research": {
    "findings": "Research agent discovered...",
    "summary": "Key insights..."
  },
  "execute": {
    "implementation": "Built components X, Y, Z",
    "files_created": ["file1.py", "file2.py"]
  }
}
```

**agents/{agent_name}/status.json** - Per-agent execution status
```json
{
  "status": "completed",
  "started_at": "2026-02-05T10:00:00Z",
  "completed_at": "2026-02-05T10:15:00Z",
  "exit_code": 0,
  "error": null
}
```

**agents/{agent_name}/instructions.md** - Generated agent instructions
```markdown
# Research Agent Instructions

## Role
You are a Research agent. Your job is to gather information...

## Task
{task_description}

## Previous Context
{shared_context from previous agents}

## Your Mission
{custom_instructions or default_research_instructions}

## Output Requirements
- Save findings to output.json (structured data)
- Save narrative to output.md (human-readable summary)
...
```

**final_result.json** - Synthesis output (if enabled)
```json
{
  "summary": "Executive summary of all agent findings...",
  "key_insights": ["insight1", "insight2"],
  "recommendations": ["rec1", "rec2"],
  "next_steps": ["step1", "step2"],
  "agent_contributions": {
    "research": "Summary of research findings...",
    "execute": "Summary of implementation...",
    "review": "Summary of review results..."
  }
}
```

### Real-Time Events

Multi-agent execution broadcasts WebSocket events for live UI updates:

**agent_started**
```json
{
  "type": "agent_started",
  "data": {
    "agent": "research",
    "execution_id": "exec_123",
    "timestamp": "2026-02-05T10:00:00Z"
  }
}
```

**agent_output** (streamed during execution)
```json
{
  "type": "agent_output",
  "data": {
    "agent": "research",
    "line": "Reading documentation...",
    "execution_id": "exec_123",
    "attempt": 1
  }
}
```

**agent_completed**
```json
{
  "type": "agent_completed",
  "data": {
    "agent": "research",
    "execution_id": "exec_123",
    "duration_ms": 15000
  }
}
```

**agent_failed**
```json
{
  "type": "agent_failed",
  "data": {
    "agent": "execute",
    "execution_id": "exec_123",
    "error": "Agent execution timeout after 3 attempts"
  }
}
```

**synthesis_started / synthesis_completed**
```json
{
  "type": "synthesis_started",
  "data": {
    "execution_id": "exec_123"
  }
}
```

**agent_attempt / agent_retry**
```json
{
  "type": "agent_retry",
  "data": {
    "agent": "execute",
    "attempt": 1,
    "next_attempt_in": 60
  }
}
```

### Activity Logging

All agent lifecycle events are logged to the `ActivityLog` database table for audit trail:

**Event Types:**
- `agent_started`: When individual agent begins execution
- `agent_completed`: When individual agent finishes successfully
- `agent_failed`: When individual agent fails after retries
- `synthesis_started`: When final synthesis begins
- `synthesis_completed`: When synthesis finishes

**Example Activity Log Entries:**
```python
# Agent started
{
  "execution_id": "exec_123",
  "type": "agent_started",
  "message": "research agent started",
  "metadata_": {"agent": "research"}
}

# Agent completed
{
  "execution_id": "exec_123",
  "type": "agent_completed",
  "message": "research agent completed successfully",
  "metadata_": {
    "agent": "research",
    "duration_ms": 15000
  }
}

# Agent failed
{
  "execution_id": "exec_123",
  "type": "agent_failed",
  "message": "execute agent failed after 3 attempts",
  "metadata_": {
    "agent": "execute",
    "exit_code": 1,
    "error": "timeout"
  }
}
```

**TaskExecution Metadata:**

Execution results store detailed agent information:

```json
{
  "id": "exec_123",
  "status": "completed",
  "output": "Multi-agent execution completed successfully",
  "metadata_": {
    "execution_mode": "multi_agent",
    "agents_run": ["research", "execute", "review"],
    "agent_results": {
      "research": {"status": "completed", "duration_ms": 15000},
      "execute": {"status": "completed", "duration_ms": 45000},
      "review": {"status": "completed", "duration_ms": 20000}
    },
    "synthesis_duration_ms": 10000,
    "total_agents": 3
  }
}
```

**Failed Execution Metadata:**
```json
{
  "id": "exec_124",
  "status": "failed",
  "output": "Multi-agent execution failed at execute agent",
  "metadata_": {
    "execution_mode": "multi_agent",
    "agents_configured": ["research", "execute", "review"],
    "agents_run": ["research", "execute"],
    "agents_completed": ["research"],
    "failed_agent": "execute",
    "failure_reason": "Agent exceeded retry limit (3 attempts)",
    "partial_workspace": "ai-workspace/tasks/exec_124/"
  }
}
```

### Example Configurations

#### Basic Three-Agent Workflow

Research → Execute → Review with synthesis:

```json
{
  "name": "Add Dark Mode Support",
  "description": "Implement dark mode theme switching",
  "command": "claude",
  "metadata": {
    "agents": {
      "enabled": true,
      "sequence": ["research", "execute", "review"],
      "synthesize": true,
      "roles": {
        "research": {
          "type": "research",
          "instructions": "Research Next.js dark mode implementations and our current theme system"
        },
        "execute": {
          "type": "execute",
          "instructions": "Implement dark mode with theme toggle, persistent storage, and smooth transitions"
        },
        "review": {
          "type": "review",
          "instructions": "Review for accessibility, browser compatibility, and performance"
        }
      }
    }
  }
}
```

#### Custom Security Audit Workflow

Custom roles for specialized security review:

```json
{
  "name": "Quarterly Security Audit",
  "description": "Comprehensive security review of authentication system",
  "command": "claude",
  "metadata": {
    "agents": {
      "enabled": true,
      "sequence": ["code_audit", "dependency_scan", "penetration_test", "report"],
      "synthesize": true,
      "roles": {
        "code_audit": {
          "type": "custom",
          "instructions": "Review auth code for SQL injection, XSS, CSRF, broken authentication, insecure session management. Check password storage, token handling, permission checks."
        },
        "dependency_scan": {
          "type": "custom",
          "instructions": "Scan all dependencies for known vulnerabilities. Check npm audit, Snyk, and CVE databases. Identify outdated packages with security fixes."
        },
        "penetration_test": {
          "type": "custom",
          "instructions": "Attempt common attacks: brute force, credential stuffing, session hijacking, privilege escalation. Document successful exploits."
        },
        "report": {
          "type": "custom",
          "instructions": "Generate executive security report with risk ratings (Critical/High/Medium/Low), CVSS scores, remediation steps, and compliance recommendations."
        }
      }
    }
  }
}
```

#### Research-Only Workflow

No implementation, just comprehensive research and recommendations:

```json
{
  "name": "Database Migration Strategy",
  "description": "Research migrating from SQLite to PostgreSQL",
  "command": "claude",
  "metadata": {
    "agents": {
      "enabled": true,
      "sequence": ["research", "analysis"],
      "synthesize": true,
      "roles": {
        "research": {
          "type": "research",
          "instructions": "Research Prisma migration guides, PostgreSQL setup, schema compatibility, data migration tools, and production migration strategies."
        },
        "analysis": {
          "type": "custom",
          "instructions": "Analyze our current schema for PostgreSQL compatibility. Identify required changes, estimate migration effort, create step-by-step migration plan with rollback strategy."
        }
      }
    }
  }
}
```

**Best Practices:**
- Use 3-5 agents for most workflows (too many increases complexity)
- Provide specific custom instructions for better results
- Enable synthesis for cohesive final deliverables
- Use custom roles for specialized domain expertise
- Keep agent names descriptive for clarity in logs and UI

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
