"""
Email templates for task notifications and digests.

This module provides functions to render HTML and plain text email templates
for various notification types.
"""

from typing import Dict, Tuple


def render_task_completion_email(task_data: Dict) -> Tuple[str, str]:
    """
    Render task completion email (HTML and plain text).

    Args:
        task_data: Dictionary with task info (name, duration, output, etc.)

    Returns:
        Tuple of (html_body, text_body)
    """
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #10b981;">✅ Task Complete: {task_data['name']}</h2>
        <p><strong>Status:</strong> Completed</p>
        <p><strong>Duration:</strong> {task_data['duration']}</p>
        <p><strong>Description:</strong> {task_data.get('description', 'N/A')}</p>

        <h3>Output Summary</h3>
        <pre style="background: #f3f4f6; padding: 10px; border-radius: 5px;">{task_data.get('output_summary', 'No output')}</pre>

        {f'<p><a href="{task_data["drive_link"]}" style="color: #3b82f6;">View full logs in Drive</a></p>' if task_data.get('drive_link') else ''}

        {f'<p><strong>Next Run:</strong> {task_data["next_run"]}</p>' if task_data.get('next_run') else ''}

        <hr style="margin-top: 20px; border: none; border-top: 1px solid #e5e7eb;">
        <p style="color: #6b7280; font-size: 12px;">
            AI Assistant - Automated Task Notification
        </p>
    </body>
    </html>
    """

    text = f"""
✅ Task Complete: {task_data['name']}

Status: Completed
Duration: {task_data['duration']}
Description: {task_data.get('description', 'N/A')}

Output Summary:
{task_data.get('output_summary', 'No output')}

{f"View full logs: {task_data['drive_link']}" if task_data.get('drive_link') else ''}

{f"Next Run: {task_data['next_run']}" if task_data.get('next_run') else ''}

---
AI Assistant - Automated Task Notification
    """

    return html.strip(), text.strip()


def render_task_failure_email(task_data: Dict) -> Tuple[str, str]:
    """
    Render task failure email (HTML and plain text).

    Args:
        task_data: Dictionary with task info (name, error, retry history, etc.)

    Returns:
        Tuple of (html_body, text_body)
    """
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #ef4444;">❌ Task Failed: {task_data['name']}</h2>
        <p><strong>Status:</strong> Failed (after retries)</p>
        <p><strong>Description:</strong> {task_data.get('description', 'N/A')}</p>

        <h3>Error Details</h3>
        <pre style="background: #fef2f2; padding: 10px; border-radius: 5px; color: #991b1b;">{task_data.get('error_message', 'Unknown error')}</pre>

        <p><strong>Retry History:</strong> {task_data.get('retry_history', 'No retries')}</p>

        <h3>Troubleshooting Tips</h3>
        <ul>
            <li>Check task configuration and arguments</li>
            <li>Review error logs for details</li>
            <li>Verify external dependencies are accessible</li>
        </ul>

        <hr style="margin-top: 20px; border: none; border-top: 1px solid #e5e7eb;">
        <p style="color: #6b7280; font-size: 12px;">
            AI Assistant - Automated Task Notification
        </p>
    </body>
    </html>
    """

    text = f"""
❌ Task Failed: {task_data['name']}

Status: Failed (after retries)
Description: {task_data.get('description', 'N/A')}

Error Details:
{task_data.get('error_message', 'Unknown error')}

Retry History: {task_data.get('retry_history', 'No retries')}

Troubleshooting Tips:
- Check task configuration and arguments
- Review error logs for details
- Verify external dependencies are accessible

---
AI Assistant - Automated Task Notification
    """

    return html.strip(), text.strip()


def render_daily_digest_email(digest_data: Dict) -> Tuple[str, str]:
    """
    Render daily digest email (HTML and plain text).

    Args:
        digest_data: Dictionary with daily statistics

    Returns:
        Tuple of (html_body, text_body)
    """
    upcoming_html = ''.join([
        f'<li>{task["name"]} at {task["time"]}</li>'
        for task in digest_data.get('upcoming_tasks', [])
    ])

    upcoming_text = '\n'.join([
        f"  - {task['name']} at {task['time']}"
        for task in digest_data.get('upcoming_tasks', [])
    ])

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #3b82f6;">📊 AI Assistant Daily Summary - {digest_data['date']}</h2>

        <h3>Today's Activity</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #f3f4f6;">
                <td style="padding: 8px;">Total Tasks</td>
                <td style="padding: 8px; text-align: right;"><strong>{digest_data['total_tasks']}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px;">Successful</td>
                <td style="padding: 8px; text-align: right; color: #10b981;"><strong>{digest_data['successful']}</strong></td>
            </tr>
            <tr style="background: #f3f4f6;">
                <td style="padding: 8px;">Failed</td>
                <td style="padding: 8px; text-align: right; color: #ef4444;"><strong>{digest_data['failed']}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px;">Success Rate</td>
                <td style="padding: 8px; text-align: right;"><strong>{digest_data['success_rate']}%</strong></td>
            </tr>
        </table>

        <h3>Upcoming Tasks</h3>
        <ul>
            {upcoming_html}
        </ul>

        <hr style="margin-top: 20px; border: none; border-top: 1px solid #e5e7eb;">
        <p style="color: #6b7280; font-size: 12px;">
            AI Assistant - Daily Digest
        </p>
    </body>
    </html>
    """

    text = f"""
📊 AI Assistant Daily Summary - {digest_data['date']}

Today's Activity:
  Total Tasks: {digest_data['total_tasks']}
  Successful: {digest_data['successful']}
  Failed: {digest_data['failed']}
  Success Rate: {digest_data['success_rate']}%

Upcoming Tasks:
{upcoming_text}

---
AI Assistant - Daily Digest
    """

    return html.strip(), text.strip()


def render_weekly_summary_email(summary_data: Dict) -> Tuple[str, str]:
    """
    Render weekly summary email (HTML and plain text).

    Args:
        summary_data: Dictionary with weekly statistics

    Returns:
        Tuple of (html_body, text_body)
    """
    failures_html = ''.join([
        f'<li>{failure["task"]} ({failure["count"]} times)</li>'
        for failure in summary_data.get('top_failures', [])
    ])

    failures_text = '\n'.join([
        f"  - {failure['task']} ({failure['count']} times)"
        for failure in summary_data.get('top_failures', [])
    ])

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #8b5cf6;">📈 AI Assistant Weekly Report</h2>
        <p><strong>Week:</strong> {summary_data['week_start']} to {summary_data['week_end']}</p>

        <h3>Weekly Statistics</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #f3f4f6;">
                <td style="padding: 8px;">Total Executions</td>
                <td style="padding: 8px; text-align: right;"><strong>{summary_data['total_executions']}</strong></td>
            </tr>
            <tr>
                <td style="padding: 8px;">Successful</td>
                <td style="padding: 8px; text-align: right; color: #10b981;"><strong>{summary_data['success_count']}</strong></td>
            </tr>
            <tr style="background: #f3f4f6;">
                <td style="padding: 8px;">Failed</td>
                <td style="padding: 8px; text-align: right; color: #ef4444;"><strong>{summary_data['failure_count']}</strong></td>
            </tr>
        </table>

        <h3>Top Failures</h3>
        <ul>
            {failures_html}
        </ul>

        {f'<p><a href="{summary_data["report_link"]}" style="color: #3b82f6;">View detailed report in Drive</a></p>' if summary_data.get('report_link') else ''}

        <hr style="margin-top: 20px; border: none; border-top: 1px solid #e5e7eb;">
        <p style="color: #6b7280; font-size: 12px;">
            AI Assistant - Weekly Summary
        </p>
    </body>
    </html>
    """

    text = f"""
📈 AI Assistant Weekly Report
Week: {summary_data['week_start']} to {summary_data['week_end']}

Weekly Statistics:
  Total Executions: {summary_data['total_executions']}
  Successful: {summary_data['success_count']}
  Failed: {summary_data['failure_count']}

Top Failures:
{failures_text}

{f"View detailed report: {summary_data['report_link']}" if summary_data.get('report_link') else ''}

---
AI Assistant - Weekly Summary
    """

    return html.strip(), text.strip()
