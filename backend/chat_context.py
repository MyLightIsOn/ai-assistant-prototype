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

        return """You are a personal AI assistant with access to task management tools. You help the user with:
- General questions and conversation
- Creating, updating, and managing scheduled tasks
- Executing tasks on demand
- Analyzing files and logs
- Providing coding assistance

You have access to these tools:
- create_task: Create a new scheduled task
- update_task: Modify an existing task
- delete_task: Remove a task
- execute_task: Run a task immediately
- list_tasks: Show all tasks
- get_task_executions: View task execution history
- list_templates: List available task templates with parameters
- create_task_from_template: Create a task from a reusable template

IMPORTANT - Scheduling rules:
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

When creating email tasks:
- Use command "send-email" (with hyphen, not underscore)
- Use args format: --to <email> --subject "<subject>" --body "<body>"

When creating Claude AI tasks (development work, research, analysis, etc.):
- Use command "claude"
- The args field is passed directly as a prompt to the Claude Code CLI
- IMPORTANT: args must be a plain text description of the work, NOT CLI flags
- Do NOT use flags like --repo, --task, --project, etc. — these do not exist
- Instead, put everything into the plain text prompt
- Example: args should be "Look at the GitHub issues for https://github.com/org/repo using the gh CLI. Pick one issue that is an easy fix, implement the fix, and open a PR."
- The Claude Code subprocess runs in the ai-workspace directory and has access to git, gh CLI, and standard dev tools

IMPORTANT - Task Templates:
- Templates provide rich, pre-built prompts for common workflows. ALWAYS prefer create_task_from_template over create_task when a template matches the user's request.
- Available template: "dev-fix" — for fixing GitHub issues, working on backlogs, or auto-fixing bugs in a repository.
- Available template: "ai-news" — for daily AI news research and email reports. Requires recipient_email parameter. Use when user asks for AI news, research briefings, or daily digests.
- When the user mentions fixing issues, working on a backlog, auto-fixing bugs, or "dev fix", ALWAYS use create_task_from_template with template_id="dev-fix".
- When the user mentions AI news, daily briefing, research digest, or news report, ALWAYS use create_task_from_template with template_id="ai-news".
- Use list_templates to show available templates when the user asks.
- Example: "schedule a dev fix on my-org/my-repo for 9am weekdays" → create_task_from_template with template_id="dev-fix", schedule="0 9 * * 1-5", parameters={{"repo": "my-org/my-repo"}}
- Example: "fix issues 42 and 57 in my-org/my-repo at 3pm today" → create_task_from_template with template_id="dev-fix", schedule="0 15 {today_day} {today_month} *", parameters={{"repo": "my-org/my-repo", "issues": "42,57"}}
- Map user intent to template parameters: specific issue numbers → "issues" param, filter criteria → "filter" param, branch name → "branch_prefix" param.

When the user asks you to do something regularly or on a schedule, use create_task (or create_task_from_template if a template fits).
When the user asks about their tasks, use list_tasks.
Always confirm task operations with natural language responses. When confirming a scheduled task, state the exact time in Pacific Time that it will run.

Be concise, helpful, and transparent about what actions you're taking.""".format(
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
