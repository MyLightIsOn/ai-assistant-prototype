"""
ntfy.sh notification client for AI Assistant.

Sends push notifications via self-hosted ntfy.sh server.
Integrates with ActivityLog for audit trail.
"""

import os
import json
import logging
from typing import Optional
from datetime import datetime, timezone

import requests
from sqlalchemy.orm import Session

from database import get_db
from models import ActivityLog
from logger import get_logger

# Configure logging
logger = get_logger()


class NotificationError(Exception):
    """Raised when notification sending fails."""
    pass


class NotificationConfig:
    """Configuration for ntfy.sh notification client.

    Loads settings from environment variables:
    - NTFY_URL: Full URL to ntfy topic (required)
    - NTFY_USERNAME: Basic auth username (optional)
    - NTFY_PASSWORD: Basic auth password (optional)
    """

    def __init__(self):
        self.url = os.getenv('NTFY_URL')
        if not self.url:
            raise ValueError("NTFY_URL environment variable is required")

        self.username = os.getenv('NTFY_USERNAME')
        self.password = os.getenv('NTFY_PASSWORD')


def send_notification(
    title: str,
    message: str,
    priority: str = 'default',
    tags: Optional[str] = None
) -> bool:
    """Send a notification via ntfy.sh server.

    Args:
        title: Notification title (shown in bold)
        message: Notification message body
        priority: Priority level (min, low, default, high, max, urgent)
        tags: Comma-separated list of tags (e.g., 'warning,ai,task')

    Returns:
        True if notification sent successfully, False otherwise

    Logs all notification attempts to ActivityLog table.
    """
    try:
        # Load configuration
        config = NotificationConfig()

        # Prepare headers
        headers = {
            'X-Title': title,
        }

        if priority:
            headers['X-Priority'] = priority

        if tags:
            headers['X-Tags'] = tags

        # Prepare authentication
        auth = None
        if config.username and config.password:
            auth = (config.username, config.password)

        # Send notification
        response = requests.post(
            config.url,
            data=message,
            headers=headers,
            auth=auth,
            timeout=10
        )

        # Check response
        response.raise_for_status()

        # Log success to database
        log_notification_to_db(
            type='notification_sent',
            message=f'Notification sent: {title}',
            metadata={
                'title': title,
                'priority': priority,
                'tags': tags,
                'status': 'success'
            }
        )

        logger.info(f"Notification sent successfully: {title}")
        return True

    except requests.ConnectionError as e:
        logger.error(f"Connection error sending notification: {e}")
        log_notification_to_db(
            type='notification_error',
            message=f'Failed to send notification: {title} - Connection error',
            metadata={
                'title': title,
                'error': str(e),
                'status': 'failed'
            }
        )
        return False

    except requests.Timeout as e:
        logger.error(f"Timeout sending notification: {e}")
        log_notification_to_db(
            type='notification_error',
            message=f'Failed to send notification: {title} - Timeout',
            metadata={
                'title': title,
                'error': str(e),
                'status': 'failed'
            }
        )
        return False

    except requests.HTTPError as e:
        logger.error(f"HTTP error sending notification: {e}")
        log_notification_to_db(
            type='notification_error',
            message=f'Failed to send notification: {title} - HTTP error',
            metadata={
                'title': title,
                'error': str(e),
                'status': 'failed'
            }
        )
        return False

    except Exception as e:
        logger.error(f"Unexpected error sending notification: {e}")
        log_notification_to_db(
            type='notification_error',
            message=f'Failed to send notification: {title} - Unexpected error',
            metadata={
                'title': title,
                'error': str(e),
                'status': 'failed'
            }
        )
        return False


def log_notification_to_db(
    type: str,
    message: str,
    metadata: Optional[dict] = None
) -> None:
    """Log notification event to ActivityLog table.

    Args:
        type: Log type (notification_sent, notification_error)
        message: Human-readable log message
        metadata: Additional structured data (will be JSON-encoded)
    """
    db = None
    try:
        # Get database session
        db = next(get_db())

        # Create log entry
        log_entry = ActivityLog(
            id=f"log_{datetime.now(timezone.utc).timestamp()}_{os.urandom(4).hex()}",
            type=type,
            message=message,
            metadata_=json.dumps(metadata) if metadata else None,
            createdAt=datetime.now(timezone.utc)
        )

        db.add(log_entry)
        db.commit()

    except Exception as e:
        logger.error(f"Failed to log notification to database: {e}")
        # Don't fail notification on logging error
    finally:
        if db:
            db.close()
