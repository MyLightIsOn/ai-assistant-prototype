import pytest
from unittest.mock import patch, AsyncMock
from chat_executor import execute_chat_message
from database import SessionLocal
from models import ChatMessage, User


@pytest.mark.asyncio
async def test_execute_chat_message_creates_response():
    """Test that chat executor creates assistant response with streaming."""
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

        # Mock the subprocess to match actual implementation:
        # - process.stdout.read(chunk_size) - returns chunks then EOF
        # - process.stderr.read() - returns stderr data
        # - process.wait() - returns exit code
        # - process.returncode - checked during streaming

        mock_response = b"Hello! How can I help you today?"

        # Mock stdout stream that returns data in chunks
        mock_stdout = AsyncMock()
        mock_stdout.read = AsyncMock(side_effect=[
            mock_response,  # First read returns data
            b""  # Second read returns EOF (empty bytes)
        ])

        # Mock stderr stream
        mock_stderr = AsyncMock()
        mock_stderr.read = AsyncMock(return_value=b"")

        # Mock process
        mock_process = AsyncMock()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.returncode = None  # Initially None, then set to 0
        mock_process.wait = AsyncMock(return_value=0)

        with patch('chat_executor.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_subprocess.return_value = mock_process

            # Execute
            assistant_msg_id = await execute_chat_message(
                user_id=user.id,
                user_message_id=user_msg.id,
                user_message_content=user_msg.content
            )

            # Verify assistant response was created
            assistant_msg = db.query(ChatMessage).filter_by(id=assistant_msg_id).first()
            assert assistant_msg is not None
            assert assistant_msg.role == "assistant"
            assert assistant_msg.content == mock_response.decode('utf-8')
            assert "Hello" in assistant_msg.content

            # Verify subprocess was called correctly
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args
            assert call_args[0][0] == "claude"  # First arg is 'claude'
            assert call_args[0][1] == user_msg.content  # Second arg is message content

    finally:
        db.query(ChatMessage).filter_by(userId=user.id).delete()
        db.commit()
        db.close()
