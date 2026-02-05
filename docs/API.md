# API Documentation

## Base URLs

- **Frontend API Routes**: `http://localhost:3000/api`
- **Python Backend**: `http://localhost:8000`
- **WebSocket**: `ws://localhost:8000/ws`

## Authentication

All API routes (except `/api/auth/*`) require valid session authentication via NextAuth.js.

**Session Cookie**: `next-auth.session-token`

### Authentication Endpoints

#### POST `/api/auth/signin`
Login with credentials.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password"
}
```

**Response:**
```json
{
  "user": {
    "id": "cuid",
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

#### POST `/api/auth/signout`
Logout and invalidate session.

## Task Management

### GET `/api/tasks`
Get all tasks for the authenticated user.

**Response:**
```json
{
  "tasks": [
    {
      "id": "cuid",
      "name": "Daily Backup",
      "description": "Backup database",
      "command": "backup_database",
      "args": "{}",
      "schedule": "0 3 * * *",
      "enabled": true,
      "priority": "default",
      "notifyOn": "completion,error",
      "lastRun": "2026-02-01T03:00:00Z",
      "nextRun": "2026-02-02T03:00:00Z",
      "createdAt": "2026-01-01T00:00:00Z"
    }
  ]
}
```

### POST `/api/tasks`
Create a new task.

**Request:**
```json
{
  "name": "Weekly Report",
  "description": "Generate weekly summary",
  "command": "generate_report",
  "args": "{\"format\": \"pdf\"}",
  "schedule": "0 9 * * 1",
  "priority": "default",
  "notifyOn": "completion"
}
```

**Response:**
```json
{
  "task": {
    "id": "cuid",
    ...
  }
}
```

### GET `/api/tasks/[id]`
Get a specific task by ID.

### PUT `/api/tasks/[id]`
Update a task.

**Request:**
```json
{
  "name": "Updated Name",
  "enabled": false,
  "schedule": "0 10 * * *"
}
```

### DELETE `/api/tasks/[id]`
Delete a task.

## Activity Logs

### GET `/api/logs`
Get recent activity logs.

**Query Parameters:**
- `limit` (optional): Number of logs to return (default: 100)
- `offset` (optional): Offset for pagination
- `type` (optional): Filter by log type

**Response:**
```json
{
  "logs": [
    {
      "id": "cuid",
      "type": "task_complete",
      "message": "Task 'Daily Backup' completed successfully",
      "metadata": "{\"duration\": 1234}",
      "createdAt": "2026-02-01T03:00:15Z",
      "executionId": "cuid"
    }
  ],
  "total": 150
}
```

## WebSocket Connection

### Connection

Connect to `ws://localhost:8000/ws` with session authentication.

**Connection Headers:**
```
Cookie: next-auth.session-token=<token>
```

### Message Types

All WebSocket messages follow this format:

```typescript
type WebSocketMessage = {
  type: string;
  data: any;
  timestamp: string;
}
```

#### Outgoing (Client → Server)

**Ping**
```json
{
  "type": "ping"
}
```

#### Incoming (Server → Client)

**Terminal Output**
```json
{
  "type": "terminal_output",
  "data": {
    "task_id": "cuid",
    "execution_id": "cuid",
    "output": "Task started...\n",
    "stream": "stdout"
  },
  "timestamp": "2026-02-01T03:00:05Z"
}
```

**Task Status Update**
```json
{
  "type": "task_status",
  "data": {
    "task_id": "cuid",
    "execution_id": "cuid",
    "status": "running",
    "progress": 50
  },
  "timestamp": "2026-02-01T03:00:10Z"
}
```

**Notification**
```json
{
  "type": "notification",
  "data": {
    "title": "Task Complete",
    "message": "Daily backup finished successfully",
    "priority": "default",
    "tags": ["check_mark"]
  },
  "timestamp": "2026-02-01T03:00:15Z"
}
```

**Activity Log**
```json
{
  "type": "activity_log",
  "data": {
    "id": "cuid",
    "type": "task_complete",
    "message": "Task completed",
    "executionId": "cuid"
  },
  "timestamp": "2026-02-01T03:00:15Z"
}
```

**Pong**
```json
{
  "type": "pong",
  "timestamp": "2026-02-01T03:00:00Z"
}
```

## Python Backend Endpoints

### POST `/execute-task`
Manually trigger a task execution.

**Request:**
```json
{
  "task_id": "cuid"
}
```

**Response:**
```json
{
  "execution_id": "cuid",
  "status": "started"
}
```

### GET `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "scheduler": "running",
    "claude_code": "available"
  }
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

**Common Error Codes:**
- `UNAUTHORIZED` (401): Invalid or missing session
- `FORBIDDEN` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `VALIDATION_ERROR` (422): Invalid request data
- `INTERNAL_ERROR` (500): Server error

## Rate Limiting

TODO: Define rate limiting policies

## Webhooks

TODO: Define webhook system for external integrations

## Versioning

API version: `v1`

Currently no versioning prefix required. Future versions will use `/api/v2/...` format.
