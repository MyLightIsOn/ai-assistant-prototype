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
        """Build system prompt with MCP tools and capabilities."""
        return """You are a personal AI assistant with access to task management tools. You help the user with:
- General questions and conversation
- Creating, updating, and managing scheduled tasks
- Executing tasks on demand
- Analyzing files and logs
- Providing coding assistance

You have access to these tools via MCP:
- create_task: Create a new scheduled task
- update_task: Modify an existing task
- delete_task: Remove a task
- execute_task: Run a task immediately
- list_tasks: Show all tasks
- get_task_executions: View task execution history

When the user asks you to do something regularly or on a schedule, use create_task.
When the user asks about their tasks, use list_tasks.
Always confirm task operations with natural language responses.

Current date and time: {current_time}

Be concise, helpful, and transparent about what actions you're taking.""".format(
            current_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
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
