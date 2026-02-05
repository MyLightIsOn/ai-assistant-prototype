"""
FastAPI backend for AI Assistant.

Main application with WebSocket support for real-time communication.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import SessionLocal, engine
from models import Base, Task
from logger import get_logger
from scheduler import TaskScheduler
from google_calendar import get_calendar_sync

# Initialize logger
logger = get_logger()

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(
    title="AI Assistant Backend",
    description="Python FastAPI backend for AI Assistant with WebSocket support",
    version="0.1.0"
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

# Create task scheduler instance (will be started on app startup)
task_scheduler = TaskScheduler(engine)


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
            db.execute("SELECT 1")
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
async def sync_scheduler(request: TaskIdRequest):
    """
    Sync a specific task or all tasks with APScheduler.

    Args:
        request: Task ID request (optional - if not provided, syncs all tasks)

    Returns:
        Success status and sync details
    """
    try:
        if request.taskId:
            # Verify task exists
            db = SessionLocal()
            try:
                task = db.query(Task).filter_by(id=request.taskId).first()
                if not task:
                    raise HTTPException(status_code=404, detail="Task not found")
            finally:
                db.close()

        # Sync all tasks (scheduler handles individual task updates)
        task_scheduler.sync_tasks()

        logger.info(
            "Scheduler synced via API",
            extra={"metadata": {"task_id": request.taskId if request.taskId else "all"}}
        )

        # Broadcast sync event to WebSocket clients
        await manager.broadcast({
            "type": "scheduler_sync",
            "data": {"task_id": request.taskId if request.taskId else None},
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return {"success": True, "synced": request.taskId if request.taskId else "all"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error syncing scheduler",
            extra={"metadata": {"error": str(e), "task_id": request.taskId if request else None}}
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
    Manually trigger a task execution (run now).

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
            # Parse existing metadata
            if isinstance(task.metadata, str):
                existing_metadata = json.loads(task.metadata) if task.metadata else {}
            else:
                existing_metadata = task.metadata or {}

            # Merge with updates
            existing_metadata.update(metadata_updates)

            # Save back as JSON string
            task.metadata = json.dumps(existing_metadata)
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
            return Response(
                content=json.dumps({"error": "Task not found"}),
                status_code=404
            )

        # Sync to Calendar
        calendar_sync = get_calendar_sync()
        event_id = calendar_sync.sync_task_to_calendar(task)

        # Update task metadata with event ID
        update_task_metadata(task_id, {'calendarEventId': event_id})

        return {"event_id": event_id}

    except Exception as e:
        logger.error(f"Calendar sync error: {e}")
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
            return Response(
                content=json.dumps({"error": "Task not found"}),
                status_code=404
            )

        # Delete Calendar event
        calendar_sync = get_calendar_sync()
        calendar_sync.delete_calendar_event(task)

        return {"status": "deleted"}

    except Exception as e:
        logger.error(f"Calendar delete error: {e}")
        return Response(
            content=json.dumps({"error": str(e)}),
            status_code=500
        )


@app.on_event("startup")
async def startup_event():
    """Application startup - start scheduler and sync tasks."""
    logger.info("Starting AI Assistant Backend")
    task_scheduler.start()
    task_scheduler.sync_tasks()
    logger.info("Scheduler started and tasks synchronized")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown - gracefully stop scheduler."""
    logger.info("Shutting down AI Assistant Backend")
    task_scheduler.shutdown(wait=True)
    logger.info("Scheduler shutdown complete")


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
