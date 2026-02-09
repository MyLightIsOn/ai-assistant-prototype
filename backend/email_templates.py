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


def render_ai_news_email(news_data: Dict) -> Tuple[str, str]:
    """
    Render AI news email from evaluator data (fallback when formatter agent fails).

    Args:
        news_data: Dictionary with evaluated news sections (industry, repos, technical, research)

    Returns:
        Tuple of (html_body, text_body)
    """
    from datetime import datetime

    today = datetime.now().strftime("%Y-%m-%d")

    section_config = {
        "industry": {"title": "Industry News", "color": "#3b82f6"},
        "repos": {"title": "Trending Repos", "color": "#10b981"},
        "technical": {"title": "Technical News", "color": "#8b5cf6"},
        "research": {"title": "Research Papers", "color": "#f59e0b"},
    }

    sections_html = ""
    sections_text = ""
    total_items = 0

    for key, config in section_config.items():
        section = news_data.get(key, {})
        items = section.get("items", []) if isinstance(section, dict) else []
        if not items:
            continue

        total_items += len(items)

        items_html = ""
        items_text = ""
        for item in items:
            title = item.get("title", "Untitled")
            url = item.get("url", "#")
            summary = item.get("summary", item.get("description", ""))
            source = item.get("source", item.get("authors", ""))
            confidence = item.get("confidence", "high")

            badge = ""
            if confidence == "medium":
                badge = ' <span style="background:#f59e0b;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;">medium</span>'
            elif confidence == "low":
                badge = ' <span style="background:#ef4444;color:#fff;padding:1px 6px;border-radius:3px;font-size:11px;">low confidence</span>'

            items_html += f"""
            <tr>
                <td style="padding:10px 0;border-bottom:1px solid #eee;">
                    <a href="{url}" style="color:#1a1a2e;font-weight:bold;text-decoration:none;">{title}</a>{badge}<br>
                    <span style="color:#666;font-size:13px;">{source}</span><br>
                    <span style="color:#333;font-size:14px;">{summary}</span>
                </td>
            </tr>"""
            items_text += f"  - {title}\n    {url}\n    {source}\n    {summary}\n\n"

        sections_html += f"""
        <div style="margin-bottom:24px;">
            <h2 style="color:{config['color']};margin:0 0 12px 0;font-size:18px;">{config['title']}</h2>
            <table style="width:100%;">{items_html}</table>
        </div>"""
        sections_text += f"\n{config['title']}\n{'='*40}\n{items_text}"

    quality = news_data.get("quality_report", {})
    quality_html = ""
    if quality:
        quality_html = f"""
        <div style="margin-top:24px;padding:12px;background:#f9fafb;border-radius:6px;font-size:13px;color:#666;">
            Items: {quality.get('items_after_evaluation', total_items)} |
            Duplicates removed: {quality.get('duplicates_removed', 0)} |
            Low confidence: {quality.get('low_confidence_flagged', 0)}
        </div>"""

    html = f"""<html>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#fff;">
    <div style="background:#1a1a2e;padding:24px;text-align:center;">
        <h1 style="color:#fff;margin:0;font-size:22px;">AI Daily News</h1>
        <p style="color:#aaa;margin:8px 0 0 0;font-size:14px;">{today} | {total_items} items</p>
    </div>
    <div style="padding:24px;">
        {sections_html}
        {quality_html}
    </div>
    <div style="padding:16px 24px;background:#f9fafb;text-align:center;font-size:12px;color:#999;">
        Generated by AI Assistant (fallback template)
    </div>
</div>
</body>
</html>"""

    text = f"""AI Daily News - {today}
{'='*40}
{total_items} items
{sections_text}
---
Generated by AI Assistant"""

    return html.strip(), text.strip()
