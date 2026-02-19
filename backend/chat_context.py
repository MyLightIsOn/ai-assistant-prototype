"""
Chat Context Builder.

Assembles smart context for Claude Code subprocess execution.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from models import ChatMessage, ChatAttachment


class ChatContextBuilder:
    """Build context for chat message execution."""

    def __init__(self, db: Session):
        self.db = db

    def build_context(
        self,
        user_id: str,
        current_message: str,
        attachments: List[ChatAttachment] = None
    ) -> List[Dict[str, Any]]:
        """
        Build smart context for Claude Code subprocess.

        Returns list of messages in Claude API format:
        [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
        ]
        """
        messages = []

        # 1. System prompt
        messages.append({
            "role": "system",
            "content": self._build_system_prompt()
        })

        # 2. Get last 10 messages
        recent_messages = self._get_recent_messages(user_id, limit=10)

        # 3. Get task operation messages from last 50
        task_messages = self._get_task_operation_messages(user_id, limit=50)

        # 4. Merge and deduplicate
        all_messages = self._merge_deduplicate(recent_messages, task_messages)

        # 5. Sort by timestamp
        all_messages.sort(key=lambda m: m.createdAt)

        # 6. Convert to Claude format
        for msg in all_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 7. Add current message
        current_content = current_message

        # Add file attachments if present
        if attachments:
            attachment_text = "\n\n[Attachments]:\n"
            for att in attachments:
                attachment_text += f"- {att.fileName} ({att.fileType}, {att.fileSize} bytes): {att.filePath}\n"
            current_content += attachment_text

        messages.append({
            "role": "user",
            "content": current_content
        })

        return messages

    def _build_system_prompt(self) -> str:
        """Build system prompt with tools and capabilities."""
        import pytz
        pst = pytz.timezone("America/Los_Angeles")
        now_pst = datetime.now(pst)

        return """You are a personal AI assistant. You help the user with:
- General questions and conversation
- Creating, updating, and managing scheduled tasks
- Executing tasks on demand
- Analyzing files and logs
- Providing coding assistance

## Task Management via REST API

You can manage tasks using the Bash tool with curl. The backend API is at http://localhost:8000.

**List tasks:**
curl -s http://localhost:8000/api/tasks

**Create a task:**
curl -s -X POST http://localhost:8000/api/tasks -H "Content-Type: application/json" -d '{{"name": "Task Name", "schedule": "0 9 * * *", "command": "claude", "args": "Task description prompt", "priority": "default", "enabled": true}}'

**Get task details:**
curl -s http://localhost:8000/api/tasks/TASK_ID

**Update a task:**
curl -s -X PUT http://localhost:8000/api/tasks/TASK_ID -H "Content-Type: application/json" -d '{{"enabled": false}}'

**Delete a task:**
curl -s -X DELETE http://localhost:8000/api/tasks/TASK_ID

**Execute a task now:**
curl -s -X POST http://localhost:8000/api/tasks/TASK_ID/execute

**Get execution history:**
curl -s http://localhost:8000/api/tasks/TASK_ID/executions

**List available templates:**
curl -s http://localhost:8000/api/templates

**Create task from template:**
curl -s -X POST http://localhost:8000/api/tasks/from-template -H "Content-Type: application/json" -d '{{"template_id": "dev-fix", "schedule": "0 9 * * 1-5", "parameters": {{"repo": "owner/repo"}}}}'

## Scheduling Rules

- The scheduler uses America/Los_Angeles (Pacific Time) timezone.
- Current time: {current_time_pst} ({current_time_utc})
- Cron format: "minute hour day month day_of_week" (all in Pacific Time)
- Examples:
  - "6:30 PM today" → "{example_min} {example_hour} {today_day} {today_month} *"
  - "9:00 AM daily" → "0 9 * * *"
  - "Every Monday at 3 PM" → "0 15 * * 1"
- For one-time tasks, use specific day and month fields (not wildcards).
- For recurring tasks, use wildcards (*) for day/month as appropriate.
- ALWAYS use 24-hour format for the hour field (e.g., 6:30 PM = hour 18, minute 30).

## Task Types

**Email tasks:**
- command: "send-email", args: --to <email> --subject "<subject>" --body "<body>"

**Claude AI tasks (development work, research, analysis):**
- command: "claude"
- args: plain text description of the work (NOT CLI flags)
- Example args: "Look at the GitHub issues for https://github.com/org/repo using the gh CLI. Pick one issue that is an easy fix, implement the fix, and open a PR."

## Task Templates

Templates provide rich, pre-built prompts for common workflows. ALWAYS prefer creating from template when one matches.

- **"dev-fix"** — Fix GitHub issues, work on backlogs, auto-fix bugs. Parameters: repo (required), issues, filter, max_issues, branch_prefix.
- **"ai-news"** — Daily AI news research and email reports. Parameters: recipient_email (required), topics, max_items_per_topic.
- **"custom-research"** — Research ANY topic across configurable sources and send an HTML email report. Parameters: topic (required), sources (optional, default: news,papers,repos,blogs,social), recipient_email (optional, default: thelawrencemoore@gmail.com), max_items_per_source (optional, default: 5).
  - Valid sources: news, papers, repos, blogs, social (comma-separated)
  - Use this when the user asks to "research X", "look into X", "find out about X and email me", etc.
  - To run IMMEDIATELY (one-time, not scheduled): create with a specific one-time cron for a time a few minutes in the future, then immediately call execute_task.

Examples:
- "schedule a dev fix on my-org/my-repo for 9am weekdays" → POST /api/tasks/from-template with template_id="dev-fix", schedule="0 9 * * 1-5", parameters={{"repo": "my-org/my-repo"}}
- "fix issues 42 and 57 at 3pm today" → POST /api/tasks/from-template with template_id="dev-fix", schedule="0 15 {today_day} {today_month} *", parameters={{"repo": "my-org/my-repo", "issues": "42,57"}}
- "research prompt engineering and email me" → create_task_from_template with template_id="custom-research", schedule="0 9 {today_day} {today_month} *", parameters={{"topic": "prompt engineering"}}, then immediately execute_task
- "research quantum computing papers only" → same but parameters={{"topic": "quantum computing", "sources": "papers"}}
- "every Monday research AI safety news and blogs" → schedule="0 9 * * 1", parameters={{"topic": "AI safety", "sources": "news,blogs"}}

## Guidelines

- When the user asks to schedule something, use the task API (prefer templates when applicable).
- When the user asks about their tasks, list them.
- Always confirm task operations with natural language. State the exact Pacific Time when a task will run.
- Be concise, helpful, and transparent about what actions you're taking.
- Always use -s (silent) flag with curl to suppress progress bars.""".format(
            current_time_pst=now_pst.strftime("%Y-%m-%d %I:%M %p %Z"),
            current_time_utc=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            example_min=now_pst.strftime("%-M") if now_pst.minute > 0 else "30",
            example_hour="18",
            today_day=now_pst.strftime("%-d"),
            today_month=now_pst.strftime("%-m"),
        )

    def _get_recent_messages(self, user_id: str, limit: int) -> List[ChatMessage]:
        """Get most recent messages."""
        return self.db.query(ChatMessage)\
            .filter_by(userId=user_id)\
            .order_by(ChatMessage.createdAt.desc())\
            .limit(limit)\
            .all()

    def _get_task_operation_messages(self, user_id: str, limit: int) -> List[ChatMessage]:
        """Get messages where AI used task management tools."""
        # Query messages with metadata containing tool_calls
        messages = self.db.query(ChatMessage)\
            .filter_by(userId=user_id, role="assistant")\
            .order_by(ChatMessage.createdAt.desc())\
            .limit(limit)\
            .all()

        # Filter to only messages with tool calls
        tool_messages = []
        for msg in messages:
            if msg.message_metadata and isinstance(msg.message_metadata, dict):
                if "tool_calls" in msg.message_metadata:
                    tool_messages.append(msg)

        return tool_messages

    def _merge_deduplicate(self, list1: List[ChatMessage], list2: List[ChatMessage]) -> List[ChatMessage]:
        """Merge two lists and remove duplicates."""
        seen_ids = set()
        merged = []

        for msg in list1 + list2:
            if msg.id not in seen_ids:
                seen_ids.add(msg.id)
                merged.append(msg)

        return merged
