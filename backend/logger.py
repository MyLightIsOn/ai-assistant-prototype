"""
Structured JSON logging system for AI Assistant backend.

Provides:
- JSON log formatting with structured fields
- Daily log rotation at midnight
- 30-day log retention
- Automatic log directory creation
- Structured context fields: task_id, execution_id, metadata
"""

import json
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any


class JSONLogFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON.

    Includes structured fields:
    - timestamp: ISO 8601 format
    - level: Log level name (INFO, ERROR, etc.)
    - message: Log message
    - task_id: Optional task identifier
    - execution_id: Optional execution identifier
    - metadata: Optional additional context dict
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: LogRecord to format

        Returns:
            JSON string with structured log data
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "task_id": getattr(record, "task_id", None),
            "execution_id": getattr(record, "execution_id", None),
            "metadata": getattr(record, "metadata", None) or {}
        }

        return json.dumps(log_data)


def setup_logger(
    log_dir: Optional[str] = None,
    logger_name: str = "ai_assistant",
    level: int = logging.INFO
) -> logging.Logger:
    """
    Set up and configure a logger with JSON formatting and daily rotation.

    Args:
        log_dir: Directory for log files. Defaults to ai-workspace/logs
        logger_name: Name for the logger instance
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    # Default to ai-workspace/logs if not specified
    if log_dir is None:
        # Get project root (parent of backend directory)
        backend_dir = Path(__file__).parent
        project_root = backend_dir.parent
        log_dir = str(project_root / "ai-workspace" / "logs")

    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create TimedRotatingFileHandler
    log_file = os.path.join(log_dir, f"{logger_name}.log")
    handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )

    # Set JSON formatter
    formatter = JSONLogFormatter()
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def get_logger() -> logging.Logger:
    """
    Get the default configured logger for the AI Assistant backend.

    This is a convenience function that returns a pre-configured logger
    instance using the default settings (ai-workspace/logs directory).

    Returns:
        Configured logger instance
    """
    return setup_logger()
