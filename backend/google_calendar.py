"""
Google Calendar integration for task visualization.

This module provides bi-directional sync between database tasks and
Google Calendar events. Prevents sync loops via extended properties.
"""

import os
import json
from typing import Optional, Dict
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google_user_credentials.json')
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
USER_TIMEZONE = os.getenv('USER_TIMEZONE', 'America/Los_Angeles')

# Priority to color mapping
PRIORITY_COLORS = {
    'low': '1',       # Lavender
    'default': '10',  # Green
    'high': '6',      # Orange
    'urgent': '11'    # Red
}


class CalendarSyncError(Exception):
    """Custom exception for Calendar sync errors."""
    pass


class CalendarSync:
    """
    Google Calendar sync service for task visualization.

    Syncs tasks from database to Google Calendar and handles
    Calendar → DB sync via Pub/Sub webhooks.
    """

    def __init__(self):
        """Initialize Calendar sync with authenticated service."""
        self.service = self._get_calendar_service()
        self.calendar_id = CALENDAR_ID

    def _get_calendar_service(self):
        """Get authenticated Calendar API service."""
        creds = None

        if os.path.exists(CREDENTIALS_FILE):
            creds = Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise CalendarSyncError(
                    f"No valid credentials found. Run google_auth_setup.py first."
                )

        return build('calendar', 'v3', credentials=creds)

    def sync_task_to_calendar(self, task) -> str:
        """
        Create or update Calendar event for task.

        Args:
            task: Task model instance

        Returns:
            Calendar event ID

        Raises:
            CalendarSyncError: If sync fails
        """
        try:
            # Get existing event ID from task metadata
            event_id = self._get_event_id_from_task(task)

            # Build event data
            event_data = self._build_event_from_task(task)

            if event_id:
                # Update existing event
                result = self.service.events().update(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                    body=event_data
                ).execute()
            else:
                # Create new event
                result = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event_data
                ).execute()

            return result['id']

        except HttpError as e:
            raise CalendarSyncError(f"Calendar API error: {e}")
        except Exception as e:
            raise CalendarSyncError(f"Failed to sync task to calendar: {e}")

    def delete_calendar_event(self, task):
        """
        Delete Calendar event when task deleted.

        Args:
            task: Task model instance
        """
        try:
            event_id = self._get_event_id_from_task(task)
            if event_id:
                self.service.events().delete(
                    calendarId=self.calendar_id,
                    eventId=event_id
                ).execute()
        except HttpError as e:
            raise CalendarSyncError(f"Calendar API error: {e}")

    def get_event(self, event_id: str) -> Optional[Dict]:
        """
        Fetch event from Calendar API.

        Args:
            event_id: Calendar event ID

        Returns:
            Event dict or None if not found
        """
        try:
            return self.service.events().get(
                calendarId=self.calendar_id,
                eventId=event_id
            ).execute()
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise CalendarSyncError(f"Calendar API error: {e}")

    def _get_event_id_from_task(self, task) -> Optional[str]:
        """Extract Calendar event ID from task metadata."""
        try:
            # JSON column handles deserialization automatically
            metadata = task.task_metadata or {}
            return metadata.get('calendarEventId')
        except AttributeError:
            return None

    def _build_event_from_task(self, task) -> Dict:
        """
        Build Calendar event structure from task.

        Args:
            task: Task model instance

        Returns:
            Event dict for Calendar API
        """
        # Calculate event time (default 15 min duration)
        start_time = task.nextRun or datetime.now()
        end_time = start_time + timedelta(minutes=15)

        # Build event description
        description = f"{task.description or 'No description'}\n\n"
        description += f"Command: {task.command}\n"
        if task.args:
            description += f"Args: {task.args}\n"
        description += f"Schedule: {task.schedule}"

        # Build event
        event = {
            'summary': task.name,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': USER_TIMEZONE
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': USER_TIMEZONE
            },
            'colorId': PRIORITY_COLORS.get(task.priority, '10'),
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 10}
                ]
            },
            'extendedProperties': {
                'private': {
                    'taskId': task.id,
                    'source': 'ai-assistant'  # For loop prevention
                }
            }
        }

        return event


# Singleton instance
_calendar_sync: Optional[CalendarSync] = None


def get_calendar_sync() -> CalendarSync:
    """
    Get singleton Calendar sync instance.

    Returns:
        CalendarSync instance
    """
    global _calendar_sync
    if _calendar_sync is None:
        _calendar_sync = CalendarSync()
    return _calendar_sync
