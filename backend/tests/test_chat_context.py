import pytest
from datetime import datetime, timezone, timedelta
from chat_context import ChatContextBuilder
from database import SessionLocal
from models import ChatMessage, User


@pytest.mark.asyncio
async def test_build_context_includes_last_10_messages():
    """Test that context includes last 10 messages."""
    db = SessionLocal()

    try:
        user = db.query(User).first()

        # Create 15 messages
        for i in range(15):
            msg = ChatMessage(
                userId=user.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                createdAt=datetime.now(timezone.utc) - timedelta(hours=15-i)
            )
            db.add(msg)
        db.commit()

        # Build context
        builder = ChatContextBuilder(db)
        context = builder.build_context(user.id, "New message")

        # Should have system prompt + last 10 messages + current
        message_count = len([m for m in context if m["role"] != "system"])
        assert message_count >= 10

        # Should include most recent messages
        recent_content = [m["content"] for m in context if m["role"] != "system"]
        assert any("Message 14" in str(c) for c in recent_content)

    finally:
        db.query(ChatMessage).filter_by(userId=user.id).delete()
        db.commit()
        db.close()
