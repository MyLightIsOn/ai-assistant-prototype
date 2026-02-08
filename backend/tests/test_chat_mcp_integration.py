import pytest
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from chat_executor import execute_chat_message
from models import ChatMessage, User
from database import SessionLocal


@pytest.mark.asyncio
async def test_chat_executor_creates_mcp_config():
    """Test that chat executor creates MCP configuration file."""
    db = SessionLocal()

    try:
        user = db.query(User).first()

        # Create user message requesting task creation
        user_msg = ChatMessage(
            userId=user.id,
            role="user",
            content="Create a task called 'Test Task' that runs tomorrow at 2pm"
        )
        db.add(user_msg)
        db.commit()
        db.refresh(user_msg)

        # Mock subprocess to capture arguments
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate = AsyncMock(return_value=(b"Task created successfully", b""))
            mock_subprocess.return_value = mock_process

            # Execute
            await execute_chat_message(
                user_id=user.id,
                user_message_id=user_msg.id,
                user_message_content=user_msg.content
            )

            # Check that subprocess was called with --mcp-config
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0]  # positional args

            assert "claude" in call_args, "Should call claude command"
            assert "--mcp-config" in call_args, "Should include --mcp-config parameter"

            # Find the config file path in args
            config_idx = call_args.index("--mcp-config")
            config_path = call_args[config_idx + 1]

            # Verify config file was created
            assert Path(config_path).exists(), "MCP config file should be created"

            # Verify config content
            with open(config_path) as f:
                config = json.load(f)

            assert "mcpServers" in config, "Config should have mcpServers"
            assert "task-management" in config["mcpServers"], "Should include task-management server"

            server_config = config["mcpServers"]["task-management"]
            assert server_config["command"] == "python3", "Should use python3 command"
            assert "mcp_task_server.py" in server_config["args"][0], "Should point to MCP server script"

    finally:
        db.query(ChatMessage).filter_by(userId=user.id).delete()
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_mcp_server_script_exists():
    """Test that mcp_task_server.py exists and is executable."""
    server_path = Path(__file__).parent.parent / "mcp_task_server.py"

    assert server_path.exists(), "MCP task server script should exist"
    assert server_path.stat().st_mode & 0o111, "MCP task server should be executable"
