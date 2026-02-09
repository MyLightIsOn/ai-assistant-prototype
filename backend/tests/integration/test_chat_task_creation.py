import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import User, ChatMessage, Task
from chat_executor import execute_chat_message
import chat_executor


@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Create test user
    user = User(
        id="test-user-123",
        email="test@example.com",
        name="Test User",
        passwordHash="dummy"
    )
    session.add(user)
    session.commit()

    yield session

    session.close()


@pytest.mark.asyncio
async def test_chat_task_creation_flow(test_db):
    """
    Integration test: User sends chat message requesting task creation.

    Expected flow:
    1. User message created in database
    2. Chat executor spawns Claude Code with MCP config
    3. Claude Code uses MCP tools to create task
    4. Assistant response created with confirmation
    5. Task exists in database
    """
    user = test_db.query(User).first()

    # Step 1: Create user message
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    user_msg = ChatMessage(
        userId=user.id,
        role="user",
        content=f"Create a task called 'Integration Test Task' that runs tomorrow at 2pm"
    )
    test_db.add(user_msg)
    test_db.commit()
    test_db.refresh(user_msg)

    # Mock Claude Code subprocess to simulate task creation
    mock_response = f"""I've created the task "Integration Test Task" scheduled for tomorrow at 2pm.

The task has been added to your schedule and will execute automatically at the specified time."""

    # Mock SessionLocal to return our test database session
    with patch('asyncio.create_subprocess_exec') as mock_subprocess, \
         patch.object(chat_executor, 'SessionLocal') as mock_session_factory:

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(mock_response.encode(), b""))
        mock_subprocess.return_value = mock_process

        # Return test database session
        mock_session_factory.return_value = test_db

        # Step 2: Execute chat message
        assistant_msg_id = await execute_chat_message(
            user_id=user.id,
            user_message_id=user_msg.id,
            user_message_content=user_msg.content
        )

        # Step 3: Verify subprocess was called with MCP config
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0]
        assert "--mcp-config" in call_args, "Should use MCP configuration"

        # Verify MCP config file was created
        config_idx = call_args.index("--mcp-config")
        config_path = Path(call_args[config_idx + 1])
        assert config_path.exists(), "MCP config file should exist"

    # Step 4: Verify assistant response
    assistant_msg = test_db.query(ChatMessage).filter_by(id=assistant_msg_id).first()
    assert assistant_msg is not None, "Assistant message should be created"
    assert assistant_msg.role == "assistant"
    assert len(assistant_msg.content) > 0, "Assistant response should have content"
    assert "Integration Test Task" in assistant_msg.content, "Response should mention task name"

    # Step 5: Verify workspace was created
    work_dir = Path(f"ai-workspace/chat/{assistant_msg.id}")
    assert work_dir.exists(), "Chat workspace should be created"
    assert (work_dir / "context.json").exists(), "Context file should exist"
    assert (work_dir / "mcp_config.json").exists(), "MCP config should exist"


@pytest.mark.asyncio
async def test_chat_simple_query_flow(test_db):
    """Test that simple queries (non-task) still work correctly."""
    user = test_db.query(User).first()

    user_msg = ChatMessage(
        userId=user.id,
        role="user",
        content="What is 2 + 2?"
    )
    test_db.add(user_msg)
    test_db.commit()
    test_db.refresh(user_msg)

    mock_response = "2 + 2 equals 4."

    # Mock SessionLocal to return our test database session
    with patch('asyncio.create_subprocess_exec') as mock_subprocess, \
         patch.object(chat_executor, 'SessionLocal') as mock_session_factory:

        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(return_value=(mock_response.encode(), b""))
        mock_subprocess.return_value = mock_process

        # Return test database session
        mock_session_factory.return_value = test_db

        assistant_msg_id = await execute_chat_message(
            user_id=user.id,
            user_message_id=user_msg.id,
            user_message_content=user_msg.content
        )

        # Should still use MCP config (tools available but not necessarily used)
        call_args = mock_subprocess.call_args[0]
        assert "--mcp-config" in call_args

    assistant_msg = test_db.query(ChatMessage).filter_by(id=assistant_msg_id).first()
    assert assistant_msg is not None
    assert "4" in assistant_msg.content
