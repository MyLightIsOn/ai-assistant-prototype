"""
Gmail Sender for sending task notifications and reports.

This module provides a service to send emails via Gmail API with support
for HTML templates, attachments, and integration with task execution.
"""

import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

from email_templates import (
    render_task_completion_email,
    render_task_failure_email,
    render_daily_digest_email,
    render_weekly_summary_email
)
from digest_queries import get_daily_digest_data, get_weekly_summary_data

# Load environment variables
load_dotenv()

# Constants
CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'google_user_credentials.json')
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SENDER_EMAIL = os.getenv('GMAIL_USER_EMAIL', 'your-ai-assistant@gmail.com')
RECIPIENT_EMAIL = os.getenv('GMAIL_RECIPIENT_EMAIL', 'your-email@gmail.com')


class GmailSenderError(Exception):
    """Custom exception for Gmail sender errors."""
    pass


class GmailSender:
    """
    Gmail sender service for task notifications and reports.

    Uses Gmail API to send HTML/plain text emails with optional attachments.
    Integrates with email templates for consistent formatting.
    """

    def __init__(self):
        """Initialize Gmail sender with authenticated service."""
        self.service = self._get_gmail_service()

    def _get_gmail_service(self):
        """Get authenticated Gmail API service."""
        creds = None

        if os.path.exists(CREDENTIALS_FILE):
            creds = Credentials.from_authorized_user_file(CREDENTIALS_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise GmailSenderError(
                    f"No valid credentials found. Run google_auth_setup.py first."
                )

        return build('gmail', 'v1', credentials=creds)

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[str]] = None
    ) -> str:
        """
        Send email via Gmail API.

        Args:
            to: Recipient email address
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional, extracted from HTML if not provided)
            attachments: List of file paths to attach (optional)

        Returns:
            Gmail message ID

        Raises:
            GmailSenderError: If sending fails
        """
        try:
            # Create multipart message
            message = MIMEMultipart('alternative')
            message['To'] = to
            message['From'] = SENDER_EMAIL
            message['Subject'] = subject

            # Add plain text part
            if body_text:
                part_text = MIMEText(body_text, 'plain')
                message.attach(part_text)

            # Add HTML part
            part_html = MIMEText(body_html, 'html')
            message.attach(part_html)

            # Add attachments if provided
            if attachments:
                for filepath in attachments:
                    if os.path.exists(filepath):
                        self._attach_file(message, filepath)

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send message
            result = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            return result['id']

        except HttpError as e:
            raise GmailSenderError(f"Gmail API error: {e}")
        except Exception as e:
            raise GmailSenderError(f"Failed to send email: {e}")

    def _attach_file(self, message: MIMEMultipart, filepath: str):
        """Attach a file to the email message."""
        with open(filepath, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())

        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={os.path.basename(filepath)}'
        )
        message.attach(part)

    def send_task_completion_email(self, task, execution) -> str:
        """
        Send task completion notification email.

        Args:
            task: Task model instance
            execution: TaskExecution model instance

        Returns:
            Gmail message ID
        """
        # Get recipient email from task metadata or use default
        recipient = RECIPIENT_EMAIL
        if task.task_metadata and isinstance(task.task_metadata, dict):
            recipient = task.task_metadata.get('recipientEmail', RECIPIENT_EMAIL)

        # Prepare task data for template
        task_data = {
            'name': task.name,
            'description': task.description or 'N/A',
            'status': 'completed',
            'duration': f"{execution.duration / 1000:.1f}s" if execution.duration else 'N/A',
            'output_summary': execution.output[:500] if execution.output else 'No output',
            'drive_link': None,  # TODO: Add Drive link if output uploaded
            'next_run': datetime.fromtimestamp(task.nextRun / 1000).strftime('%Y-%m-%d %H:%M:%S') if task.nextRun else None
        }

        # Render template
        html, text = render_task_completion_email(task_data)

        # Send email
        subject = f"✅ Task Complete: {task.name}"
        return self.send_email(
            to=recipient,
            subject=subject,
            body_html=html,
            body_text=text
        )

    def send_task_failure_email(self, task, execution) -> str:
        """
        Send task failure notification email.

        Args:
            task: Task model instance
            execution: TaskExecution model instance

        Returns:
            Gmail message ID
        """
        # Get recipient email from task metadata or use default
        recipient = RECIPIENT_EMAIL
        if task.task_metadata and isinstance(task.task_metadata, dict):
            recipient = task.task_metadata.get('recipientEmail', RECIPIENT_EMAIL)

        # Prepare task data for template
        task_data = {
            'name': task.name,
            'description': task.description or 'N/A',
            'error_message': execution.output or 'Unknown error',
            'retry_history': '3 attempts (1min, 5min, 15min)',  # TODO: Get actual retry history
            'error_logs': execution.output or 'No logs available'
        }

        # Render template
        html, text = render_task_failure_email(task_data)

        # Send email
        subject = f"❌ Task Failed: {task.name}"
        return self.send_email(
            to=recipient,
            subject=subject,
            body_html=html,
            body_text=text
        )

    def send_daily_digest(self, db, recipient_email: str, date: datetime = None) -> str:
        """
        Send daily digest email with task statistics.

        Args:
            db: SQLAlchemy database session
            recipient_email: Email address to send to
            date: Date for the digest (defaults to now)

        Returns:
            Gmail message ID
        """
        if date is None:
            date = datetime.now()

        # Query database for real statistics
        stats = get_daily_digest_data(db, date)

        digest_data = {
            'date': date.strftime('%Y-%m-%d'),
            'total_tasks': stats['total_tasks'],
            'successful': stats['successful'],
            'failed': stats['failed'],
            'success_rate': stats['success_rate'],
            'upcoming_tasks': stats['upcoming_tasks']
        }

        # Render template
        html, text = render_daily_digest_email(digest_data)

        # Send email
        subject = f"📊 AI Assistant Daily Summary - {digest_data['date']}"
        return self.send_email(
            to=recipient_email,
            subject=subject,
            body_html=html,
            body_text=text
        )

    def send_weekly_summary(self, db, recipient_email: str, week_start: datetime = None) -> str:
        """
        Send weekly summary email with task statistics.

        Args:
            db: SQLAlchemy database session
            recipient_email: Email address to send to
            week_start: Start date of the week (defaults to Monday of current week)

        Returns:
            Gmail message ID
        """
        from datetime import timedelta

        if week_start is None:
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        week_end = week_start + timedelta(days=6)

        # Query database for real statistics
        stats = get_weekly_summary_data(db, week_start)

        summary_data = {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'total_executions': stats['total_executions'],
            'success_count': stats['success_count'],
            'failure_count': stats['failure_count'],
            'top_failures': stats['top_failures'],
            'avg_duration_ms': stats['avg_duration_ms'],
            'report_link': None  # TODO: Add Drive report link if needed
        }

        # Render template
        html, text = render_weekly_summary_email(summary_data)

        # Send email
        subject = f"📈 AI Assistant Weekly Report - Week {week_start.strftime('%Y-%m-%d')}"
        return self.send_email(
            to=recipient_email,
            subject=subject,
            body_html=html,
            body_text=text
        )


# Singleton instance
_gmail_sender: Optional[GmailSender] = None


def get_gmail_sender() -> GmailSender:
    """
    Get singleton Gmail sender instance.

    Returns:
        GmailSender instance
    """
    global _gmail_sender
    if _gmail_sender is None:
        _gmail_sender = GmailSender()
    return _gmail_sender
