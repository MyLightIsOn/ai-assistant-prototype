"""Tests for email templates."""
import pytest
from datetime import datetime
from email_templates import (
    render_task_completion_email,
    render_task_failure_email,
    render_daily_digest_email,
    render_weekly_summary_email
)


def test_render_task_completion_email():
    """Test task completion email template."""
    task_data = {
        'name': 'Daily Backup',
        'description': 'Backup database to Drive',
        'status': 'completed',
        'duration': '1.2s',
        'output_summary': 'Backup created successfully',
        'drive_link': 'https://drive.google.com/file/d/abc123',
        'next_run': '2026-02-05 03:00:00'
    }

    html, text = render_task_completion_email(task_data)

    assert '✅' in html
    assert 'Daily Backup' in html
    assert '1.2s' in html
    assert 'drive.google.com' in html
    assert 'Daily Backup' in text


def test_render_task_failure_email():
    """Test task failure email template."""
    task_data = {
        'name': 'Data Sync',
        'description': 'Sync data from API',
        'error_message': 'Connection timeout',
        'retry_history': '3 attempts (1min, 5min, 15min)',
        'error_logs': 'Full stack trace here...'
    }

    html, text = render_task_failure_email(task_data)

    assert '❌' in html
    assert 'Data Sync' in html
    assert 'Connection timeout' in html
    assert '3 attempts' in html
    assert 'Data Sync' in text


def test_render_daily_digest_email():
    """Test daily digest email template."""
    digest_data = {
        'date': '2026-02-04',
        'total_tasks': 5,
        'successful': 4,
        'failed': 1,
        'success_rate': 80,
        'upcoming_tasks': [
            {'name': 'Morning Backup', 'time': '03:00'},
            {'name': 'Data Sync', 'time': '08:00'}
        ]
    }

    html, text = render_daily_digest_email(digest_data)

    assert '📊' in html
    assert '2026-02-04' in html
    assert '80%' in html
    assert 'Morning Backup' in html


def test_render_weekly_summary_email():
    """Test weekly summary email template."""
    summary_data = {
        'week_start': '2026-02-03',
        'week_end': '2026-02-09',
        'total_executions': 35,
        'success_count': 32,
        'failure_count': 3,
        'top_failures': [
            {'task': 'API Sync', 'count': 2},
            {'task': 'Email Check', 'count': 1}
        ],
        'report_link': 'https://drive.google.com/file/d/xyz789'
    }

    html, text = render_weekly_summary_email(summary_data)

    assert '📈' in html
    assert 'Week' in html
    assert '35' in html
    assert 'API Sync' in html
