# Development Guide

## Prerequisites

Before starting development, ensure you have:
- **Mac Mini** with macOS
- **Tailscale** installed and configured
- **Docker** (for self-hosted ntfy.sh)
- **Node.js** 18+ and npm
- **Python** 3.11+
- **Claude Code CLI** installed and authenticated
  ```bash
  npm install -g @anthropic-ai/claude-code
  claude login
  ```

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ai-assistant-prototype.git
cd ai-assistant-prototype
```

### 2. Install Frontend Dependencies

```bash
npm install
```

### 3. Setup Python Environment

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 4. Configure Environment Variables

**Frontend** (`frontend/.env.local`):
```bash
DATABASE_URL="file:../ai-assistant.db"
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="$(openssl rand -base64 32)"
PYTHON_BACKEND_URL="http://localhost:8000"
```

**Backend** (`backend/.env`):
```bash
DATABASE_URL="file:../ai-assistant.db"
NTFY_URL="http://localhost:8080/ai-notifications"
NTFY_USERNAME="your-username-ai"
NTFY_PASSWORD="your-secure-password"
AI_WORKSPACE="./ai-workspace"
```

### 5. Setup Database

```bash
# Generate Prisma client
npm run prisma:generate

# Run migrations
npm run prisma:migrate
```

### 6. Create AI Workspace Directory

```bash
mkdir -p ai-workspace/{memory,logs,output,temp,dev}
```

## Running Development Servers

### Start All Services (Recommended)

```bash
npm run dev:all
```

This starts:
- Frontend (Next.js) on port 3000
- Python backend (FastAPI) on port 8000
- Task scheduler daemon

### Start Services Individually

**Terminal 1 - Frontend:**
```bash
npm run dev
```

**Terminal 2 - Backend API:**
```bash
npm run dev:backend
```

**Terminal 3 - Task Scheduler:**
```bash
npm run dev:scheduler
```

## Database Management

### Prisma Studio (Database GUI)

```bash
npm run prisma:studio
```

Opens at http://localhost:5555

### Create Migration

```bash
npm run prisma:migrate
```

### Reset Database (Development Only!)

```bash
npx prisma migrate reset -w frontend
```

⚠️ This deletes all data!

## Development Workflow

### Making Changes

1. Create feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make changes, commit using conventional commits:
   ```bash
   git add .
   git commit -m "feat(frontend): add task scheduling UI"
   ```

3. Push and create PR:
   ```bash
   git push origin feature/your-feature-name
   ```

### Database Schema Changes

When modifying the Prisma schema:

1. Edit `frontend/prisma/schema.prisma`
2. Generate new migration:
   ```bash
   npm run prisma:migrate
   ```
3. Update SQLAlchemy models in `backend/models.py` to match
4. Test thoroughly - both ORMs must stay in sync!

## Testing

### Frontend Tests

TODO: Add testing framework and examples

### Backend Tests

TODO: Add pytest examples

## Troubleshooting

### Port Already in Use

```bash
# Check what's using the port
lsof -i :3000  # or :8000

# Kill the process
kill -9 <PID>
```

### Prisma Client Out of Sync

```bash
npm run prisma:generate
```

### Python Virtual Environment Issues

```bash
cd backend
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database Connection Issues

- Ensure DATABASE_URL in both .env files points to the same database
- Check that ai-assistant.db exists in project root
- Verify file permissions

## VS Code / WebStorm Setup

TODO: Add recommended extensions and settings

## Useful Commands

```bash
# View logs
npm run logs

# Format code
npm run format

# Type check
npm run type-check

# Lint
npm run lint

# Build production
npm run build
```

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [Claude Code Documentation](https://claude.ai/code)
