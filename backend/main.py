"""
FastAPI backend for AI Assistant.

Main application with WebSocket support for real-time communication.
"""

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Request, BackgroundTasks, Depends
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sqlalchemy import text
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from models import Base, Task, TaskExecution, DigestSettings, DigestSettingsUpdate, DigestSettingsResponse
from logger import get_logger
from scheduler import TaskScheduler, setup_digest_jobs
from google_calendar import get_calendar_sync
from digest_queries import get_success_rate, get_execution_trends
from gmail_sender import get_gmail_sender
import base64

# Initialize logger
logger = get_logger()

# Create database tables
Base.metadata.create_all(bind=engine)

# Create task scheduler instance (will be started in lifespan)
task_scheduler = TaskScheduler(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown logic."""
    # Startup
    logger.info("Starting AI Assistant Backend")
    task_scheduler.start()
    task_scheduler.sync_tasks()
    logger.info("Scheduler started and tasks synchronized")

    yield

    # Shutdown
    logger.info("Shutting down AI Assistant Backend")
    task_scheduler.shutdown(wait=True)
    logger.info("Scheduler shutdown complete")


# Create FastAPI application with lifespan handler
app = FastAPI(
    title="AI Assistant Backend",
    description="Python FastAPI backend for AI Assistant with WebSocket support",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific WebSocket connection."""
        await websocket.send_json(message)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Connection might be closed, will be removed on next interaction
                logger.warning(
                    "Error broadcasting to client",
                    extra={"metadata": {"error": str(e), "message_type": message.get("type")}}
                )


# Create connection manager instance
manager = ConnectionManager()


class TaskIdRequest(BaseModel):
    """Request model for task ID operations."""
    taskId: str


class ManualExecuteRequest(BaseModel):
    """Request model for manual task execution."""
    taskId: str


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "message": "AI Assistant Backend API",
        "version": "0.1.0",
        "websocket": "/ws",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    # Check database connection
    db_status = "connected"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    # Check scheduler status
    scheduler_status = "running" if task_scheduler.scheduler.running else "stopped"

    # Return degraded status if database is not connected
    status = "healthy" if db_status == "connected" and scheduler_status == "running" else "degraded"

    return {
        "status": status,
        "service": "ai-assistant-backend",
        "database": db_status,
        "scheduler": scheduler_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_db():
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request):
    """Dependency to get current authenticated user (placeholder)."""
    # For now, return first user (will integrate with NextAuth later)
    db = SessionLocal()
    try:
        from models import User
        user = db.query(User).first()
        if not user:
            raise HTTPException(status_code=401, detail="No user found")
        return {"id": user.id, "email": user.email}
    finally:
        db.close()


@app.get("/api/stats/success-rate")
async def get_success_rate_endpoint(
    days: int = Query(default=7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get task success rate for specified time period.

    Args:
        days: Number of days to calculate success rate for (1-365, default: 7)
        db: Database session dependency

    Returns:
        JSON object with success rate statistics:
        {
            "success_rate": 85.5,
            "total_executions": 100,
            "successful": 85,
            "failed": 15,
            "period_days": 7
        }
    """
    try:
        result = get_success_rate(db, days)
        return result
    except Exception as e:
        logger.error(
            "Error calculating success rate",
            extra={"metadata": {"error": str(e), "days": days}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to calculate success rate: {str(e)}")


@app.get("/api/stats/execution-trends")
async def get_execution_trends_endpoint(
    days: int = Query(default=7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get daily execution trend data for charts.

    Args:
        days: Number of days to query (1-30, default: 7)
        db: Database session dependency

    Returns:
        JSON array with daily execution statistics:
        [
            {
                "date": "2026-02-01",
                "successful": 10,
                "failed": 2,
                "total": 12
            },
            ...
        ]
    """
    try:
        result = get_execution_trends(db, days)
        return result
    except Exception as e:
        logger.error(
            "Error fetching execution trends",
            extra={"metadata": {"error": str(e), "days": days}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch execution trends: {str(e)}")


@app.get("/api/logs")
async def get_logs(limit: int = Query(default=100, ge=1, le=1000)):
    """
    Get recent log entries from the structured JSON log file.

    Args:
        limit: Maximum number of log entries to return (1-1000, default: 100)

    Returns:
        JSON object with logs array containing parsed log entries
    """
    # Get log file path
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent
    log_file_path = project_root / "ai-workspace" / "logs" / "ai_assistant.log"

    logs = []

    try:
        if log_file_path.exists():
            # Read log file
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Parse JSON log entries (most recent first)
            for line in reversed(lines):
                if len(logs) >= limit:
                    break

                line = line.strip()
                if not line:
                    continue

                try:
                    log_entry = json.loads(line)
                    logs.append(log_entry)
                except json.JSONDecodeError:
                    # Skip invalid JSON lines
                    continue

    except Exception as e:
        logger.error(
            "Error reading log file",
            extra={"metadata": {"error": str(e), "log_file": str(log_file_path)}}
        )

    return {"logs": logs}


@app.post("/api/scheduler/sync")
async def sync_scheduler(db: Session = Depends(get_db)):
    """
    Manually trigger scheduler to sync all tasks from database.

    This endpoint loads all enabled tasks from the database and updates
    the APScheduler job queue. Useful after creating or modifying tasks
    to avoid waiting for automatic sync.

    Returns:
        Success status with count of tasks loaded
    """
    try:
        # Get count of enabled tasks before sync
        enabled_count = db.query(Task).filter_by(enabled=True).count()

        # Sync all tasks with scheduler
        task_scheduler.sync_tasks()

        logger.info(
            "Scheduler synced via API",
            extra={"metadata": {"tasks_loaded": enabled_count}}
        )

        # Broadcast sync event to WebSocket clients
        await manager.broadcast({
            "type": "scheduler_sync",
            "data": {"tasks_loaded": enabled_count},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {
            "message": "Scheduler synced",
            "tasks_loaded": enabled_count
        }

    except Exception as e:
        logger.error(
            "Error syncing scheduler",
            extra={"metadata": {"error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to sync scheduler: {str(e)}")


@app.post("/api/scheduler/remove")
async def remove_from_scheduler(request: TaskIdRequest):
    """
    Remove a task from APScheduler.

    Args:
        request: Task ID to remove

    Returns:
        Success status
    """
    try:
        # Remove job from scheduler
        job = task_scheduler.scheduler.get_job(request.taskId)
        if job:
            task_scheduler.scheduler.remove_job(request.taskId)
            logger.info(
                f"Removed job {request.taskId} from scheduler",
                extra={"metadata": {"task_id": request.taskId}}
            )

            # Broadcast removal event
            await manager.broadcast({
                "type": "task_removed",
                "data": {"task_id": request.taskId},
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        return {"success": True, "removed": request.taskId}

    except Exception as e:
        logger.error(
            "Error removing task from scheduler",
            extra={"metadata": {"error": str(e), "task_id": request.taskId}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to remove task: {str(e)}")


@app.post("/api/tasks/execute")
async def execute_task_manually(request: ManualExecuteRequest):
    """
    Manually trigger a task execution (run now) - body-based endpoint.

    Args:
        request: Task ID to execute

    Returns:
        Success status and execution ID
    """
    import asyncio
    from executor import execute_task

    try:
        # Verify task exists
        db = SessionLocal()
        try:
            task = db.query(Task).filter_by(id=request.taskId).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Execute task asynchronously
            async def run_task():
                nonlocal db
                try:
                    output, exit_code = await execute_task(
                        request.taskId,
                        db,
                        broadcast_callback=manager.broadcast
                    )
                    return {"output": output, "exit_code": exit_code}
                finally:
                    db.close()

            result = await run_task()

            logger.info(
                f"Manual execution of task {request.taskId} completed",
                extra={"metadata": {"exit_code": result["exit_code"]}}
            )

            return {
                "success": True,
                "task_id": request.taskId,
                "exit_code": result["exit_code"]
            }

        except HTTPException:
            db.close()
            raise

    except Exception as e:
        logger.error(
            "Error executing task manually",
            extra={"metadata": {"error": str(e), "task_id": request.taskId}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@app.post("/api/tasks/{task_id}/execute")
async def execute_task_by_id(task_id: str):
    """
    Manually trigger a task execution (run now) - RESTful path-based endpoint.

    Args:
        task_id: Task ID from URL path

    Returns:
        Success status and execution ID
    """
    import asyncio
    from executor import execute_task

    try:
        # Verify task exists
        db = SessionLocal()
        try:
            task = db.query(Task).filter_by(id=task_id).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            # Execute task asynchronously
            async def run_task():
                nonlocal db
                try:
                    output, exit_code = await execute_task(
                        task_id,
                        db,
                        broadcast_callback=manager.broadcast
                    )
                    return {"output": output, "exit_code": exit_code}
                finally:
                    db.close()

            result = await run_task()

            logger.info(
                f"Manual execution of task {task_id} completed",
                extra={"metadata": {"exit_code": result["exit_code"]}}
            )

            return {
                "success": True,
                "task_id": task_id,
                "exit_code": result["exit_code"]
            }

        except HTTPException:
            db.close()
            raise

    except Exception as e:
        logger.error(
            "Error executing task manually",
            extra={"metadata": {"error": str(e), "task_id": task_id}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to execute task: {str(e)}")


@app.post("/api/tasks/{task_id}/validate")
async def validate_task_schedule(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Validate that task scheduling is correct and reasonable.

    Returns warnings if:
    - Task scheduled > 1 year in future
    - Task has never executed but should have by now
    - Calendar event missing
    """
    task = db.query(Task).filter_by(id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    warnings = []

    # Check if scheduled too far in future
    if task.nextRun:
        one_year_from_now = datetime.now(timezone.utc) + timedelta(days=365)
        if task.nextRun > one_year_from_now:
            warnings.append({
                "type": "far_future",
                "message": f"Task scheduled {task.nextRun}, over 1 year away",
                "severity": "high"
            })

    # Check if task should have run by now but hasn't
    if task.nextRun and task.nextRun < datetime.now(timezone.utc) and not task.lastRun:
        warnings.append({
            "type": "missed_execution",
            "message": f"Task was scheduled for {task.nextRun} but never executed",
            "severity": "critical"
        })

    # Check if calendar event exists
    if not task.task_metadata or not task.task_metadata.get('calendarEventId'):
        warnings.append({
            "type": "missing_calendar",
            "message": "Task not synced to Google Calendar",
            "severity": "low"
        })

    # Check execution history
    exec_count = db.query(TaskExecution).filter_by(taskId=task_id).count()
    if task.enabled and task.lastRun is None and exec_count == 0:
        warnings.append({
            "type": "never_executed",
            "message": "Task is enabled but has never executed",
            "severity": "medium"
        })

    return {
        "task_id": task_id,
        "valid": len(warnings) == 0,
        "warnings": warnings,
        "task": {
            "name": task.name,
            "enabled": task.enabled,
            "schedule": task.schedule,
            "nextRun": task.nextRun.isoformat() if task.nextRun else None,
            "lastRun": task.lastRun.isoformat() if task.lastRun else None,
            "execution_count": exec_count
        }
    }


def get_task_from_db(task_id: str) -> Optional[Task]:
    """
    Get task from database by ID.

    Args:
        task_id: Task ID to fetch

    Returns:
        Task instance or None if not found
    """
    db = SessionLocal()
    try:
        return db.query(Task).filter_by(id=task_id).first()
    finally:
        db.close()


def update_task_metadata(task_id: str, metadata_updates: dict):
    """
    Update task metadata in database.

    Args:
        task_id: Task ID to update
        metadata_updates: Dictionary of metadata fields to update
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            # Get existing metadata (JSON column handles serialization automatically)
            existing_metadata = task.task_metadata or {}

            # Merge with updates
            existing_metadata.update(metadata_updates)

            # Save back (no need for json.dumps - JSON column handles it)
            task.task_metadata = existing_metadata
            db.commit()
    finally:
        db.close()


@app.post("/api/calendar/sync")
async def sync_task_to_calendar(request: Request):
    """
    Sync task to Google Calendar.

    Request body: {"taskId": "task_123"}
    Response: {"event_id": "event_12345"}
    """
    try:
        data = await request.json()
        task_id = data['taskId']

        # Get task from database
        task = get_task_from_db(task_id)
        if not task:
            logger.error(f"Task {task_id} not found for calendar sync")
            return Response(
                content=json.dumps({"error": "Task not found"}),
                status_code=404
            )

        # Only sync enabled tasks to calendar
        if not task.enabled:
            logger.info(f"Skipping calendar sync for disabled task {task_id}")
            return {"event_id": None, "skipped": True, "reason": "Task disabled"}

        # Sync to Calendar
        calendar_sync = get_calendar_sync()
        event_id = calendar_sync.sync_task_to_calendar(task)

        # Update task metadata with event ID
        update_task_metadata(task_id, {'calendarEventId': event_id})

        logger.info(f"Successfully synced task {task_id} to calendar event {event_id}")

        return {"event_id": event_id}

    except Exception as e:
        logger.error(
            "Calendar sync error",
            extra={"metadata": {"error": str(e), "task_id": task_id if 'task_id' in locals() else None}}
        )
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500
        )


@app.delete("/api/calendar/sync/{task_id}")
async def delete_task_calendar_event(task_id: str):
    """
    Delete Calendar event when task deleted.

    Response: {"status": "deleted"}
    """
    try:
        # Get task from database
        task = get_task_from_db(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found for calendar event deletion")
            return Response(
                content=json.dumps({"error": "Task not found"}),
                status_code=404
            )

        # Check if task has calendar event
        event_id = None
        if task.task_metadata and isinstance(task.task_metadata, dict):
            event_id = task.task_metadata.get('calendarEventId')

        if not event_id:
            logger.info(f"No calendar event found for task {task_id}, nothing to delete")
            return {"status": "no_event", "message": "Task has no associated calendar event"}

        # Delete Calendar event
        calendar_sync = get_calendar_sync()
        calendar_sync.delete_calendar_event(task)

        logger.info(f"Successfully deleted calendar event {event_id} for task {task_id}")

        return {"status": "deleted", "event_id": event_id}

    except Exception as e:
        logger.error(
            "Calendar delete error",
            extra={"metadata": {"error": str(e), "task_id": task_id}}
        )
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500
        )


def create_task_in_db(task_data: dict) -> Task:
    """
    Create task in database.

    Args:
        task_data: Task data dict

    Returns:
        Created Task instance
    """
    db = SessionLocal()
    try:
        task = Task(**task_data)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
    finally:
        db.close()


def update_task_in_db(task_id: str, task_data: dict):
    """
    Update task in database.

    Args:
        task_id: Task ID to update
        task_data: Task data dict
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            for key, value in task_data.items():
                setattr(task, key, value)
            db.commit()
    finally:
        db.close()


def delete_task_in_db(task_id: str):
    """
    Delete task from database.

    Args:
        task_id: Task ID to delete
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter_by(id=task_id).first()
        if task:
            db.delete(task)
            db.commit()
    finally:
        db.close()


def _verify_pubsub_request(request: Request) -> bool:
    """
    Verify request is from Google Pub/Sub.

    Implements security verification for Pub/Sub push messages:
    1. Verifies required Pub/Sub headers are present
    2. Optionally verifies secret token (if PUBSUB_VERIFICATION_TOKEN is set)
    3. Validates message structure

    Returns:
        bool: True if request appears to be from Pub/Sub, False otherwise
    """
    # Check for standard Pub/Sub push headers
    has_pubsub_headers = (
        'X-Goog-Resource-State' in request.headers or
        'X-Goog-Channel-ID' in request.headers or
        'X-Goog-Message-Number' in request.headers
    )

    if not has_pubsub_headers:
        logger.warning("Missing Pub/Sub headers")
        return False

    # Optional: Verify secret token if configured
    # To use: Set PUBSUB_VERIFICATION_TOKEN in .env and configure it in
    # the Pub/Sub push subscription attributes
    verification_token = os.getenv('PUBSUB_VERIFICATION_TOKEN')
    if verification_token:
        # Check token in query parameter (recommended by Google)
        token_param = request.query_params.get('token')
        if token_param != verification_token:
            logger.warning("Invalid Pub/Sub verification token")
            return False

    return True


def _get_priority_from_color(color_id: Optional[str]) -> str:
    """Map Calendar color to task priority."""
    color_to_priority = {
        '1': 'low',
        '10': 'default',
        '6': 'high',
        '11': 'urgent'
    }
    return color_to_priority.get(color_id, 'default')


def _update_event_extended_props(event_id: str, props: dict):
    """Update Calendar event extended properties."""
    try:
        calendar_sync = get_calendar_sync()
        event = calendar_sync.get_event(event_id)

        if not event:
            return

        # Merge new props with existing
        extended_props = event.get('extendedProperties', {})
        private_props = extended_props.get('private', {})
        private_props.update(props)
        extended_props['private'] = private_props

        # Update event
        calendar_sync.service.events().update(
            calendarId=calendar_sync.calendar_id,
            eventId=event_id,
            body={'extendedProperties': extended_props}
        ).execute()

    except Exception as e:
        logger.error(f"Error updating event extended props: {e}")


@app.post("/api/google/calendar/webhook")
async def calendar_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Calendar change notifications from Pub/Sub.

    Google Pub/Sub sends push notifications when Calendar events change.
    This endpoint verifies the message and processes it asynchronously.
    """
    try:
        # Verify Pub/Sub signature
        if not _verify_pubsub_request(request):
            logger.warning("Invalid Pub/Sub request signature")
            return Response(status_code=401)

        # Parse Pub/Sub message
        body = await request.json()

        # Handle subscription verification (Pub/Sub health check)
        if 'message' not in body:
            return Response(status_code=200)

        message_data = base64.b64decode(body['message']['data'])
        calendar_notification = json.loads(message_data)

        # Process asynchronously (return 200 quickly per Pub/Sub requirements)
        background_tasks.add_task(process_calendar_change, calendar_notification)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Calendar webhook error: {e}")
        return Response(status_code=500)


async def process_calendar_change(notification: dict):
    """
    Process Calendar event change and sync to database.

    Args:
        notification: Pub/Sub notification data
    """
    try:
        # Fetch the actual event from Calendar API
        resource_id = notification.get('resourceId')
        if not resource_id:
            logger.warning("No resourceId in notification")
            return

        calendar_sync = get_calendar_sync()
        event = calendar_sync.get_event(resource_id)

        if not event:
            logger.warning(f"Event {resource_id} not found")
            return

        # Check if this is our own event (prevent loops)
        extended_props = event.get('extendedProperties', {}).get('private', {})
        if extended_props.get('source') == 'ai-assistant':
            logger.info(f"Ignoring own event {event['id']}")
            return  # Ignore our own synced events

        # Determine change type and update DB
        if event['status'] == 'confirmed':
            await create_or_update_task_from_event(event)
        elif event['status'] == 'cancelled':
            await delete_task_from_event(event)

    except Exception as e:
        logger.error(f"Error processing calendar change: {e}")


async def create_or_update_task_from_event(event: dict):
    """Create or update task from Calendar event."""
    try:
        # Extract task data from event
        task_data = {
            'name': event['summary'],
            'description': event.get('description', ''),
            'schedule': '0 0 * * *',  # TODO: Convert event to cron
            'priority': _get_priority_from_color(event.get('colorId')),
            'enabled': True,
            'notifyOn': 'completion,error'
        }

        # Check if task already exists (by checking extended properties)
        extended_props = event.get('extendedProperties', {}).get('private', {})
        task_id = extended_props.get('taskId')

        if task_id:
            # Update existing task
            update_task_in_db(task_id, task_data)
            logger.info(f"Updated task {task_id} from Calendar event")
        else:
            # Create new task
            task = create_task_in_db(task_data)
            logger.info(f"Created task {task.id} from Calendar event")

            # Update Calendar event with taskId to prevent future duplicates
            _update_event_extended_props(event['id'], {'taskId': task.id})

    except Exception as e:
        logger.error(f"Error creating/updating task from event: {e}")


async def delete_task_from_event(event: dict):
    """Delete task when Calendar event deleted."""
    try:
        extended_props = event.get('extendedProperties', {}).get('private', {})
        task_id = extended_props.get('taskId')

        if task_id:
            delete_task_in_db(task_id)
            logger.info(f"Deleted task {task_id} from Calendar event deletion")

    except Exception as e:
        logger.error(f"Error deleting task from event: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time communication.

    Messages format:
    {
        "type": "message_type",
        "data": {...},
        "timestamp": "ISO-8601"
    }

    Message types:
    - connected: Sent when client connects
    - pong: Response to ping
    - terminal_output: Terminal output stream
    - task_status: Task status update
    - notification: Push notification
    - activity_log: Activity log entry
    """
    await manager.connect(websocket)

    try:
        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connected",
                "data": {
                    "message": "Connected to AI Assistant Backend",
                    "client_count": len(manager.active_connections)
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            websocket
        )

        # Handle incoming messages
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle ping/pong heartbeat
            if data.get("type") == "ping":
                await manager.send_personal_message(
                    {
                        "type": "pong",
                        "data": {},
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    websocket
                )
            else:
                # Echo other messages for now (will be expanded later)
                await manager.send_personal_message(
                    {
                        "type": "echo",
                        "data": data,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        # Log error and disconnect
        logger.error(
            "WebSocket error",
            extra={"metadata": {"error": str(e), "error_type": type(e).__name__}}
        )
        manager.disconnect(websocket)
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


# ============================================================================
# Digest Settings Endpoints
# ============================================================================

@app.get("/api/settings/digest", response_model=DigestSettingsResponse)
async def get_digest_settings(db: Session = Depends(get_db)):
    """
    Get current digest email settings.

    Returns:
        DigestSettings object with current configuration
    """
    try:
        settings = db.query(DigestSettings).first()
        if not settings:
            raise HTTPException(status_code=404, detail="Digest settings not found. Run scheduler sync first.")
        return settings
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error retrieving digest settings",
            extra={"metadata": {"error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve settings: {str(e)}")


@app.put("/api/settings/digest", response_model=DigestSettingsResponse)
async def update_digest_settings(
    settings_update: DigestSettingsUpdate,
    db: Session = Depends(get_db)
):
    """
    Update digest email settings and reschedule jobs.

    Args:
        settings_update: Updated settings fields

    Returns:
        Updated DigestSettings object
    """
    try:
        settings = db.query(DigestSettings).first()
        if not settings:
            raise HTTPException(status_code=404, detail="Digest settings not found")

        # Update fields
        update_data = settings_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

        settings.updatedAt = int(datetime.now(timezone.utc).timestamp() * 1000)
        db.commit()
        db.refresh(settings)

        # Reschedule jobs with new settings
        setup_digest_jobs(task_scheduler.scheduler, db)

        logger.info(
            "Digest settings updated",
            extra={"metadata": {"updated_fields": list(update_data.keys())}}
        )

        return settings
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            "Error updating digest settings",
            extra={"metadata": {"error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@app.post("/api/settings/digest/test")
async def send_test_digest(
    digest_type: str = Query(..., pattern="^(daily|weekly)$"),
    db: Session = Depends(get_db)
):
    """
    Send test digest email immediately.

    Args:
        digest_type: Type of digest to send (daily or weekly)

    Returns:
        Status message
    """
    try:
        settings = db.query(DigestSettings).first()
        if not settings:
            raise HTTPException(status_code=404, detail="Digest settings not found")

        sender = get_gmail_sender()

        if digest_type == "daily":
            message_id = sender.send_daily_digest(db, settings.recipientEmail)
            logger.info(
                "Test daily digest sent",
                extra={"metadata": {"recipient": settings.recipientEmail, "message_id": message_id}}
            )
            return {
                "status": "sent",
                "type": "daily",
                "recipient": settings.recipientEmail,
                "message_id": message_id
            }
        else:
            message_id = sender.send_weekly_summary(db, settings.recipientEmail)
            logger.info(
                "Test weekly summary sent",
                extra={"metadata": {"recipient": settings.recipientEmail, "message_id": message_id}}
            )
            return {
                "status": "sent",
                "type": "weekly",
                "recipient": settings.recipientEmail,
                "message_id": message_id
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error sending test digest",
            extra={"metadata": {"error": str(e), "digest_type": digest_type}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to send test digest: {str(e)}")


# ============================================================================
# Chat Endpoints
# ============================================================================

from chat_executor import execute_chat_message
from models import ChatMessage as ChatMessageModel, ChatAttachment as ChatAttachmentModel


class ChatSendRequest(BaseModel):
    """Request model for sending chat message."""
    content: str = Field(..., min_length=1, max_length=50000, description="Message content (1-50000 characters)")
    attachments: list[str] = Field(default_factory=list, max_length=10, description="List of attachment IDs (max 10)")


@app.post("/api/chat/send")
async def send_chat_message(
    request: ChatSendRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send chat message and execute via Claude Code.

    Returns message ID and WebSocket URL for streaming.
    """
    try:
        # Create user message
        user_msg = ChatMessageModel(
            userId=user["id"],
            role="user",
            content=request.content,
            messageType="text"
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Link attachments
        for attachment_id in request.attachments:
            attachment = db.query(ChatAttachmentModel).filter_by(id=attachment_id).first()
            if attachment:
                attachment.messageId = user_msg.id
        db.commit()

        # Trigger async execution
        background_tasks.add_task(
            execute_chat_message,
            user_id=user["id"],
            user_message_id=user_msg.id,
            user_message_content=request.content
        )

        return {
            "messageId": user_msg.id,
            "wsUrl": f"/ws?user_id={user['id']}"
        }

    except Exception as e:
        logger.error(
            "Error sending chat message",
            extra={"metadata": {"error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


class ChatExecuteRequest(BaseModel):
    """Request model for triggering chat execution (message already created)."""
    userId: str = Field(..., description="User ID who sent the message")
    userMessageId: str = Field(..., description="ID of the user message to respond to")
    content: str = Field(..., min_length=1, max_length=50000, description="Message content")


@app.post("/api/chat/execute")
async def execute_chat_message_endpoint(
    request: ChatExecuteRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger AI execution for an existing chat message.

    This endpoint is called by the frontend after it has already created
    the user message in the database. It triggers Claude Code execution
    without creating a duplicate message.

    Returns immediately while execution happens in background.
    """
    try:
        from chat_executor import execute_chat_message

        # Trigger async execution
        background_tasks.add_task(
            execute_chat_message,
            user_id=request.userId,
            user_message_id=request.userMessageId,
            user_message_content=request.content,
            broadcast_callback=manager.broadcast
        )

        logger.info(
            f"Triggered chat execution for message {request.userMessageId}",
            extra={"metadata": {"user_id": request.userId, "message_id": request.userMessageId}}
        )

        return {
            "status": "executing",
            "messageId": request.userMessageId,
            "wsUrl": f"/ws?user_id={request.userId}"
        }

    except Exception as e:
        logger.error(
            "Error triggering chat execution",
            extra={"metadata": {"error": str(e), "message_id": request.userMessageId}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to trigger execution: {str(e)}")


@app.get("/api/chat/messages")
async def get_chat_messages(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get chat message history for current user.

    Returns messages in reverse chronological order (newest first).
    """
    try:
        messages = db.query(ChatMessageModel)\
            .filter_by(userId=user["id"])\
            .order_by(ChatMessageModel.createdAt.desc())\
            .offset(offset)\
            .limit(limit)\
            .all()

        # Convert to dict and reverse to chronological order
        message_dicts = []
        for msg in reversed(messages):
            message_dicts.append({
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "messageType": msg.messageType,
                "metadata": msg.message_metadata,
                "createdAt": int(msg.createdAt.timestamp() * 1000) if isinstance(msg.createdAt, datetime) else msg.createdAt,
                "attachments": [
                    {
                        "id": att.id,
                        "fileName": att.fileName,
                        "filePath": att.filePath,
                        "fileType": att.fileType,
                        "fileSize": att.fileSize
                    }
                    for att in msg.attachments
                ]
            })

        return {
            "messages": message_dicts,
            "total": db.query(ChatMessageModel).filter_by(userId=user["id"]).count()
        }

    except Exception as e:
        logger.error(
            "Error fetching chat messages",
            extra={"metadata": {"error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")


@app.delete("/api/chat/clear")
async def clear_chat_context(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Clear chat conversation context (delete all messages).
    """
    try:
        deleted_count = db.query(ChatMessageModel)\
            .filter_by(userId=user["id"])\
            .delete()

        db.commit()

        logger.info(
            f"Cleared chat context for user {user['id']}",
            extra={"metadata": {"deleted_count": deleted_count}}
        )

        return {
            "success": True,
            "deleted_count": deleted_count
        }

    except Exception as e:
        logger.error(
            "Error clearing chat context",
            extra={"metadata": {"error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to clear context: {str(e)}")