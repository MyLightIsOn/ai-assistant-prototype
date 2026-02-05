# ntfy.sh Self-Hosted Setup Guide

## Overview

This guide covers setting up a self-hosted ntfy server on your Mac Mini for secure, private notifications from your AI assistant.

## Why Self-Host?

- **Complete privacy** - Messages never leave your network
- **No external dependencies** - Works even if ntfy.sh is down
- **Full control** - Configure authentication, retention, limits
- **Local network speed** - Instant delivery

## Prerequisites

- Mac Mini with SSH access
- Docker installed (or you can run it natively)
- Basic understanding of networking/ports

## Installation Methods

### Option 1: Docker (Recommended)

#### Step 1: Create Docker Compose File

```yaml
# docker-compose.yml
version: "3.7"

services:
  ntfy:
    image: binwiederhier/ntfy:latest
    container_name: ntfy
    command:
      - serve
    ports:
      - "8080:80"  # Change 8080 to your preferred port
    volumes:
      - ./ntfy-cache:/var/cache/ntfy
      - ./ntfy-config:/etc/ntfy
    environment:
      - TZ=America/Los_Angeles  # Your timezone
    restart: unless-stopped
```

#### Step 2: Create Config File

```yaml
# ntfy-config/server.yml
base-url: "http://your-mac-mini-ip:8080"

# Authentication (optional but recommended)
auth-default-access: "deny-all"
auth-file: "/etc/ntfy/user.db"

# Message retention
cache-duration: "12h"
cache-file: "/var/cache/ntfy/cache.db"

# Rate limiting
visitor-request-limit-burst: 100
visitor-request-limit-replenish: "10s"

# Logging
log-level: info
```

#### Step 3: Start the Service

```bash
# SSH into your Mac Mini
ssh your-mac-mini

# Create directories
mkdir -p ~/ntfy/{ntfy-cache,ntfy-config}

# Create the config file (use the YAML above)
nano ~/ntfy/ntfy-config/server.yml

# Create docker-compose.yml (use the YAML above)
nano ~/ntfy/docker-compose.yml

# Start ntfy
cd ~/ntfy
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Option 2: Native Binary (Alternative)

```bash
# Install ntfy
brew install ntfy

# Create config directory
mkdir -p ~/.config/ntfy

# Create config file
nano ~/.config/ntfy/server.yml
# (Use the server.yml content from above)

# Run as a service with launchd
# Create ~/Library/LaunchAgents/sh.ntfy.server.plist
```

## Setting Up Authentication (Recommended)

```bash
# Create a user for your AI assistant
docker exec -it ntfy ntfy user add your-username-ai
# You'll be prompted to create a password

# Create a user for yourself (for mobile app)
docker exec -it ntfy ntfy user add your-username
# Set a password

# Grant permissions to specific topics
docker exec -it ntfy ntfy access your-username-ai ai-notifications rw
docker exec -it ntfy ntfy access your-username ai-notifications rw
```

## Testing Your Setup

### From Command Line

```bash
# Simple message
curl -u your-username-ai:your-password \
  -d "Test notification from AI!" \
  http://your-mac-mini-ip:8080/ai-notifications

# With title and priority
curl -u your-username-ai:your-password \
  -H "Title: Test Alert" \
  -H "Priority: high" \
  -H "Tags: robot" \
  -d "AI assistant is online and ready!" \
  http://your-mac-mini-ip:8080/ai-notifications
```

### From Python (for your AI)

```python
import requests

def send_notification(title, message, priority="default", tags=None):
    """Send notification to self-hosted ntfy"""
    url = "http://your-mac-mini-ip:8080/ai-notifications"
    headers = {
        "Title": title,
        "Priority": priority,
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    
    response = requests.post(
        url,
        data=message,
        headers=headers,
        auth=("your-username-ai", "your-password")
    )
    return response.status_code == 200

# Usage
send_notification(
    "Task Complete",
    "Research on AI agents finished. Found 23 relevant articles.",
    priority="default",
    tags=["white_check_mark", "robot"]
)
```

## Mobile App Setup

1. **Install ntfy app** (iOS/Android)
2. **Add your server:**
    - Tap "+" to add subscription
    - Server URL: `http://your-mac-mini-ip:8080`
    - Topic: `ai-notifications`
    - Username: `your-username`
    - Password: `your-password`
3. **Enable notifications** in phone settings

## Security Considerations

### Network Access

**Option A: Local network only (Most Secure)**
- Only accessible from your home network
- No external access needed
- Use VPN when away from home

**Option B: Port forwarding with authentication**
- Forward port 8080 on your router
- Use strong passwords
- Consider adding HTTPS with reverse proxy (nginx/Caddy)

**Option C: Tailscale/Wireguard (Recommended)**
- Access your Mac Mini via VPN
- No port forwarding needed
- Encrypted tunnel

### HTTPS Setup (Optional but Recommended)

If you want HTTPS (especially for mobile access):

```bash
# Using Caddy (simplest)
brew install caddy

# Caddyfile
your-domain.com {
    reverse_proxy localhost:8080
}

# Start Caddy (handles HTTPS automatically with Let's Encrypt)
caddy run
```

## Firewall Configuration

```bash
# If you have a firewall, allow the port
sudo pfctl -e
# Or configure via System Preferences > Security & Privacy
```

## Environment Variables for AI

Store these in your AI's config:

```bash
# .env file
NTFY_URL=http://your-mac-mini-ip:8080/ai-notifications
NTFY_USERNAME=your-username-ai
NTFY_PASSWORD=your-secure-password
```

## Advanced Features

### Action Buttons

Send notifications with clickable actions:

```bash
curl -u your-username-ai:password \
  -H "Title: Deployment Ready" \
  -H "Actions: view, Open Dashboard, http://localhost:3000; http, Deploy, http://your-server/deploy, method=POST" \
  -d "App is ready to deploy" \
  http://your-mac-mini-ip:8080/ai-notifications
```

### Attachments

Send files with notifications:

```bash
curl -u your-username-ai:password \
  -H "Title: Report Ready" \
  -T report.pdf \
  http://your-mac-mini-ip:8080/ai-notifications
```

### Priority Levels

- `min` - No sound/vibration
- `low` - Subtle notification
- `default` - Normal notification
- `high` - Louder/more prominent
- `urgent` - Critical, bypass Do Not Disturb

## Monitoring & Maintenance

```bash
# View logs
docker-compose logs -f ntfy

# Check disk usage
du -sh ~/ntfy/ntfy-cache/

# Backup (important!)
tar -czf ntfy-backup-$(date +%Y%m%d).tar.gz ~/ntfy/

# Update ntfy
docker-compose pull
docker-compose up -d
```

## Troubleshooting

### Can't connect from phone
- Check firewall settings
- Verify IP address
- Ensure port 8080 is accessible
- Try from Mac Mini first: `curl http://localhost:8080`

### Notifications not appearing
- Check app permissions on phone
- Verify authentication credentials
- Check ntfy logs for errors
- Test with simple curl command first

### Docker container won't start
```bash
docker-compose logs ntfy
# Check for port conflicts
lsof -i :8080
```

## Next Steps

1. Set up ntfy server on Mac Mini
2. Test from command line
3. Install mobile app and connect
4. Integrate with AI assistant
5. Create notification templates for different event types

## Resources

- [Official ntfy docs](https://docs.ntfy.sh/)
- [ntfy GitHub](https://github.com/binwiederhier/ntfy)
- [Docker Hub](https://hub.docker.com/r/binwiederhier/ntfy)
