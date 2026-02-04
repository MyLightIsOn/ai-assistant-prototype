"""
FastAPI backend for AI Assistant.

Main application with WebSocket support for real-time communication.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

from database import SessionLocal, engine
from models import Base
from logger import get_logger

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

    # Return degraded status if database is not connected
    status = "healthy" if db_status == "connected" else "degraded"

    return {
        "status": status,
        "service": "ai-assistant-backend",
        "database": db_status,
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
