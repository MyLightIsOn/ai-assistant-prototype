# Deployment Guide

## Prerequisites

- Mac Mini with macOS configured
- Tailscale installed and running
- Docker installed (for ntfy.sh)
- Node.js 18+ and Python 3.11+ installed
- Claude Code CLI installed and authenticated
- PM2 installed globally: `npm install -g pm2`

## Pre-Deployment Checklist

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] ntfy.sh server running and tested
- [ ] Tailscale connection verified
- [ ] Claude Code CLI authenticated

## Production Build

### 1. Build Frontend

```bash
npm run build
```

This creates an optimized production build in `frontend/.next/`.

### 2. Verify Python Dependencies

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Database Migrations

```bash
npm run prisma:migrate
```

## Deployment with PM2

### Start All Services

```bash
pm2 start ecosystem.config.js
```

This starts three services:
- `ai-assistant-web` - Next.js server (port 3000)
- `ai-assistant-backend` - FastAPI server (port 8000)
- `ai-assistant-scheduler` - APScheduler daemon

### Monitor Services

```bash
# View status
pm2 status

# View logs
pm2 logs

# Monitor resources
pm2 monit
```

### Managing Services

```bash
# Restart all
pm2 restart all

# Restart specific service
pm2 restart ai-assistant-web

# Stop all
pm2 stop all

# Delete all
pm2 delete all
```

### Auto-Start on Boot

```bash
# Generate startup script
pm2 startup

# Save current process list
pm2 save
```

Follow the instructions PM2 provides to enable auto-start.

## Environment Variables

Ensure production environment variables are set:

**Frontend** (`frontend/.env.local`):
```bash
DATABASE_URL="file:../ai-assistant.db"
NEXTAUTH_URL="http://your-tailscale-hostname:3000"
NEXTAUTH_SECRET="<secure-random-string>"
PYTHON_BACKEND_URL="http://localhost:8000"
```

**Backend** (`backend/.env`):
```bash
DATABASE_URL="file:../ai-assistant.db"
NTFY_URL="http://localhost:8080/ai-notifications"
NTFY_USERNAME="your-username-ai"
NTFY_PASSWORD="<secure-password>"
AI_WORKSPACE="./ai-workspace"
```

## Database Backup

The system includes automated daily backups at 3 AM. Manual backup:

```bash
# Backup database
cp ai-assistant.db backups/ai-assistant_$(date +%Y%m%d_%H%M%S).db

# Restore from backup
cp backups/ai-assistant_TIMESTAMP.db ai-assistant.db
```

## Monitoring

### Check Service Status

```bash
pm2 status
```

### View Logs

```bash
# All services
pm2 logs

# Specific service
pm2 logs ai-assistant-backend

# Last N lines
pm2 logs --lines 100
```

### System Resource Usage

```bash
pm2 monit
```

## Updating the Application

### Standard Update

```bash
# Pull latest changes
git pull origin main

# Install new dependencies
npm install
cd backend && pip install -r requirements.txt && cd ..

# Run migrations if needed
npm run prisma:migrate

# Rebuild frontend
npm run build

# Restart services
pm2 restart all
```

### Database Schema Updates

```bash
# Backup database first!
cp ai-assistant.db backups/pre-migration_$(date +%Y%m%d).db

# Run migrations
npm run prisma:migrate

# Update SQLAlchemy models if needed
# Edit backend/models.py manually

# Restart backend services
pm2 restart ai-assistant-backend
pm2 restart ai-assistant-scheduler
```

## Rollback Procedure

If something goes wrong:

```bash
# Stop services
pm2 stop all

# Restore database from backup
cp backups/ai-assistant_TIMESTAMP.db ai-assistant.db

# Checkout previous version
git checkout <previous-commit>

# Reinstall dependencies
npm install
cd backend && pip install -r requirements.txt && cd ..

# Rebuild
npm run build

# Restart services
pm2 restart all
```

## Security Considerations

- Access only via Tailscale (no public exposure)
- Regularly update dependencies
- Monitor logs for unusual activity
- Keep database backups
- Rotate ntfy passwords periodically

## Troubleshooting

### Service Won't Start

```bash
# Check PM2 logs
pm2 logs <service-name> --err

# Check process details
pm2 show <service-name>

# Try manual start to see errors
cd frontend && npm start  # For frontend
cd backend && python main.py  # For backend
```

### Database Lock Issues

```bash
# Check for stale connections
lsof ai-assistant.db

# Restart all services
pm2 restart all
```

### Port Conflicts

```bash
# Check what's using port
lsof -i :3000
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

## Performance Tuning

TODO: Add performance optimization tips

## Maintenance Tasks

### Weekly

- Review logs for errors
- Check disk space
- Verify backups are running

### Monthly

- Update dependencies
- Review and rotate logs
- Test backup restoration

## Resources

- [PM2 Documentation](https://pm2.keymetrics.io/docs/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
