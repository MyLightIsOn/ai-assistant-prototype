"""
FastAPI backend for AI Assistant.

Main application with WebSocket support for real-time communication.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Dict, Any
import json
from database import SessionLocal, engine
from models import Base

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
            except Exception:
                # Connection might be closed, will be removed on next interaction
                pass


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
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception:
        db_status = "disconnected"

    return {
        "status": "healthy",
        "service": "ai-assistant-backend",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


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
                "timestamp": datetime.utcnow().isoformat()
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
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    websocket
                )
            else:
                # Echo other messages for now (will be expanded later)
                await manager.send_personal_message(
                    {
                        "type": "echo",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        # Log error and disconnect
        manager.disconnect(websocket)
        raise


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
