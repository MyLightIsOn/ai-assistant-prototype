import pytest
from unittest.mock import patch, AsyncMock
from chat_executor import execute_chat_message
from database import SessionLocal
from models import ChatMessage, User


@pytest.mark.asyncio
async def test_execute_chat_message_creates_response():
    """Test that chat executor creates assistant response (mocked)."""
    db = SessionLocal()

    try:
        user = db.query(User).first()

        # Create user message
        user_msg = ChatMessage(
            userId=user.id,
            role="user",
            content="Hello, AI!"
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Mock the subprocess call to avoid actually calling Claude Code
        mock_stdout = b"Hello! How can I help you today?"
        mock_stderr = b""

        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Configure mock process
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(mock_stdout, mock_stderr))
            mock_subprocess.return_value = mock_process

            # Execute
            assistant_msg_id = await execute_chat_message(
                user_id=user.id,
                user_message_id=user_msg.id,
                user_message_content=user_msg.content
            )

            # Should create assistant response
            assistant_msg = db.query(ChatMessage).filter_by(id=assistant_msg_id).first()
            assert assistant_msg is not None
            assert assistant_msg.role == "assistant"
            assert len(assistant_msg.content) > 0
            assert "Hello" in assistant_msg.content

    finally:
        db.query(ChatMessage).filter_by(userId=user.id).delete()
        db.commit()
        db.close()
