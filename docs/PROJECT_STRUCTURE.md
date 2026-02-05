# Project Structure

## Monorepo Architecture

This project uses a monorepo structure to keep all components together, making development, deployment, and version control simpler.

## Directory Layout

```
ai-assistant-prototype/
├── frontend/                    # Next.js application
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/            # Authentication pages
│   │   ├── (dashboard)/       # Main dashboard pages
│   │   ├── api/               # API routes
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/            # React components
│   │   ├── ui/               # shadcn/ui components
│   │   ├── dashboard/        # Dashboard-specific components
│   │   ├── chat/             # Chat interface components
│   │   ├── terminal/         # Terminal viewer components
│   │   └── tasks/            # Task management components
│   ├── lib/                  # Utility libraries
│   │   ├── prisma.ts        # Prisma client
│   │   ├── auth.ts          # NextAuth config
│   │   └── utils.ts
│   ├── hooks/                # Custom React hooks
│   ├── types/                # TypeScript types
│   ├── public/               # Static assets
│   │   ├── icons/           # PWA icons
│   │   └── manifest.json    # PWA manifest
│   ├── prisma/              # Database schema
│   │   └── schema.prisma
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── backend/                     # Python services
│   ├── main.py                 # FastAPI application with WebSocket
│   ├── scheduler.py            # APScheduler daemon
│   ├── claude_interface.py     # Claude Code subprocess integration
│   ├── ntfy_client.py          # Notification client
│   ├── database.py             # SQLAlchemy session management
│   ├── models.py               # SQLAlchemy models + Pydantic schemas
│   ├── requirements.txt        # Python dependencies
│   └── .env.example            # Environment template
│
├── ai-workspace/                # AI's working directory
│   ├── memory/                 # Persistent context
│   ├── logs/                   # Execution logs
│   ├── output/                 # Generated files
│   └── temp/                   # Temporary work
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md         # System architecture
│   ├── NTFY_SETUP.md          # ntfy.sh configuration
│   ├── PROJECT_STRUCTURE.md    # This file
│   ├── DEVELOPMENT.md          # Development guide
│   ├── DEPLOYMENT.md           # Deployment guide
│   └── API.md                  # API documentation
│
├── scripts/                     # Utility scripts
│   ├── setup.sh               # Initial setup script
│   ├── dev.sh                 # Start dev environment
│   └── deploy.sh              # Deployment script
│
├── .github/                     # GitHub configuration
│   └── workflows/             # CI/CD workflows
│
├── package.json                 # Root package.json (workspaces)
├── ecosystem.config.js          # PM2 configuration
├── .gitignore
├── README.md
└── LICENSE
```

## Workspace Configuration

The root `package.json` uses npm workspaces to manage both frontend and backend:

```json
{
  "name": "ai-assistant-prototype",
  "version": "1.0.0",
  "private": true,
  "workspaces": [
    "frontend"
  ],
  "scripts": {
    "dev": "npm run dev -w frontend",
    "dev:backend": "cd backend && python main.py",
    "dev:scheduler": "cd backend && python scheduler.py",
    "dev:all": "concurrently \"npm run dev\" \"npm run dev:backend\" \"npm run dev:scheduler\"",
    "build": "npm run build -w frontend",
    "start": "npm run start -w frontend",
    "prisma:generate": "npm run prisma:generate -w frontend",
    "prisma:migrate": "npm run prisma:migrate -w frontend",
    "prisma:studio": "npm run prisma:studio -w frontend",
    "lint": "npm run lint -w frontend",
    "type-check": "npm run type-check -w frontend"
  },
  "devDependencies": {
    "concurrently": "^8.2.2"
  }
}
```

## Why Monorepo?

### Advantages

1. **Single Source of Truth**
    - One repo to clone, one place for issues
    - Shared documentation
    - Unified version control

2. **Simplified Development**
    - No need to sync schemas across repos
    - Easier to test full-stack changes
    - Single PR for related frontend/backend changes

3. **Shared Configuration**
    - Prisma schema lives in one place
    - Environment variables can be referenced
    - TypeScript types can be shared

4. **Better Portfolio Presentation**
    - One impressive repo vs multiple partial ones
    - Complete system visible in one place
    - Easier for others to understand and run

5. **Deployment Simplicity**
    - PM2 can reference all services from one config
    - Single git pull updates everything
    - Easier to keep versions in sync

### Trade-offs

1. **Mixed Languages**
    - Python and TypeScript in same repo
    - Different tooling requirements
    - Solved with good documentation

2. **Repo Size**
    - Slightly larger than split repos
    - Not significant for this project size

## Development Workflow

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-assistant-prototype.git
cd ai-assistant-prototype

# Install frontend dependencies
npm install

# Install backend dependencies
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
cd ..

# Set up environment variables
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env

# Generate Prisma client
npm run prisma:generate

# Run database migrations
npm run prisma:migrate
```

### Daily Development

```bash
# Start all services in development mode
npm run dev:all

# Or start individually:
# Terminal 1: Frontend
npm run dev

# Terminal 2: Backend API
npm run dev:backend

# Terminal 3: Task Scheduler
npm run dev:scheduler
```

### Database Management

```bash
# Create a new migration
npm run prisma:migrate

# Open Prisma Studio (database GUI)
npm run prisma:studio

# Reset database (dev only!)
npx prisma migrate reset -w frontend
```

## Git Workflow

### Branch Strategy

Simple trunk-based development:
- `main` - Production-ready code, always deployable
- `feature/*` - Feature branches (merge to main when complete)
- `fix/*` - Bug fix branches (merge to main when complete)

### Commit Convention

Follow Conventional Commits:

```
feat(frontend): add task scheduling UI
fix(backend): resolve scheduler memory leak
docs: update architecture documentation
chore(deps): update dependencies
```

### Example Workflow

```bash
# Create feature branch
git checkout -b feature/task-scheduler

# Make changes to both frontend and backend
# Commit related changes together
git add frontend/app/tasks/page.tsx backend/scheduler.py
git commit -m "feat: add task scheduling functionality"

# Push and create PR
git push origin feature/task-scheduler
```

## File Organization Principles

### Frontend Structure

- **Pages**: Located in `frontend/app/` using App Router
- **Components**: Reusable UI components in `frontend/components/`
- **Utilities**: Shared logic in `frontend/lib/`
- **Types**: TypeScript definitions in `frontend/types/`
- **Styles**: Tailwind in components, globals in `globals.css`

### Backend Structure

- **Entry Point**: `main.py` for FastAPI server
- **Services**: Separate files for distinct functionality
- **Models**: Pydantic models for validation
- **Database**: Prisma Python client wrapper

### Shared Resources

- **Database Schema**: `frontend/prisma/schema.prisma`
    - TypeScript types generated for frontend
    - Python client used by backend
- **Documentation**: `docs/` directory
- **Scripts**: `scripts/` for automation

## Environment Variables

### Frontend (.env.local)

```bash
DATABASE_URL="file:../ai-assistant.db"  # Project root
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="generate-with-openssl-rand-base64-32"
PYTHON_BACKEND_URL="http://localhost:8000"
```

### Backend (.env)

```bash
DATABASE_URL="file:../ai-assistant.db"  # Project root (same file as frontend)
NTFY_URL="http://localhost:8080/ai-notifications"
NTFY_USERNAME="your-username-ai"
NTFY_PASSWORD="your-secure-password"
AI_WORKSPACE="./ai-workspace"  # Relative to project root
```

Note: No CLAUDE_API_KEY needed - uses Claude Code CLI with user's subscription.

## Dependency Management

### Frontend

- **Package Manager**: npm (using workspaces)
- **Lock File**: `package-lock.json`
- **Updates**: `npm update` in root or workspace

### Backend

- **Package Manager**: pip
- **Lock File**: `requirements.txt` (consider using `pip-tools`)
- **Virtual Environment**: Recommended for isolation

### Shared Dependencies

- **Prisma**: Schema in frontend, client used by both
- **Types**: Generated from Prisma for TypeScript

## Build & Deploy

### Production Build

```bash
# Build frontend
npm run build

# Backend doesn't need building (Python)
# Just ensure dependencies are installed
```

### Deployment

```bash
# Using PM2 (from root directory)
pm2 start ecosystem.config.js

# Or using provided script
./scripts/deploy.sh
```

## Testing Strategy

### Frontend Tests

```bash
# Unit tests (Jest)
npm test -w frontend

# E2E tests (Playwright)
npm run test:e2e -w frontend
```

### Backend Tests

```bash
# Unit tests (pytest)
cd backend
pytest

# Integration tests
pytest tests/integration/
```

## Documentation Standards

- **Code Comments**: Explain "why", not "what"
- **Function Docs**: JSDoc for TypeScript, docstrings for Python
- **README Files**: Each major directory should have context
- **API Docs**: Keep `docs/API.md` updated
- **Architecture**: Update `docs/ARCHITECTURE.md` for major changes

## Maintenance

### Regular Tasks

- **Dependencies**: Update monthly
- **Database**: Backup regularly
- **Logs**: Rotate and archive
- **Docs**: Keep in sync with code

### Version Bumps

Use semantic versioning (SemVer):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

## Troubleshooting

### Common Issues

**Issue**: Prisma client out of sync
```bash
npm run prisma:generate
```

**Issue**: Port conflicts
```bash
# Check what's using the port
lsof -i :3000  # or :8000
kill -9 <PID>
```

**Issue**: Python virtual environment issues
```bash
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
