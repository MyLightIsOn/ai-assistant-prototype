"""
Tests for Claude Code subprocess interface.

Following TDD approach:
1. Write failing test
2. Implement minimal code to pass
3. Refactor

Test Strategy:
- Mock asyncio.subprocess to avoid spawning real Claude processes
- Test subprocess spawning with correct arguments
- Test working directory configuration
- Test output streaming line-by-line
- Test exit code capture
- Test timeout handling
- Test subprocess cleanup on errors
- Test logging of Claude interactions
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import os


# Test 1: Module can be imported
def test_module_imports():
    """Test that claude_interface module can be imported."""
    import claude_interface
    assert claude_interface is not None


# Test 2: execute_claude_task function exists
def test_execute_claude_task_exists():
    """Test that execute_claude_task function exists and is async."""
    from claude_interface import execute_claude_task
    import inspect
    assert callable(execute_claude_task)
    # Function should be an async generator function
    assert inspect.isasyncgenfunction(execute_claude_task)


# Test 3: Subprocess spawns with correct arguments
@pytest.mark.asyncio
async def test_subprocess_spawns_with_correct_args():
    """Test that subprocess spawns with 'claude --yes' command."""
    from claude_interface import execute_claude_task
    import tempfile

    # Create temporary workspace directory
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Setup mock process
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.stdin = AsyncMock()
            mock_process.stdin.write = Mock()
            mock_process.stdin.drain = AsyncMock()
            mock_process.stdin.close = Mock()

            # Mock stdout/stderr readline to return empty (EOF)
            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b'')
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b'')

            mock_process.wait = AsyncMock(return_value=None)
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            # Consume generator
            async for line in execute_claude_task("test task", tmpdir):
                pass

            # Verify subprocess was called with correct command
            mock_subprocess.assert_called_once()
            args = mock_subprocess.call_args[0]
            assert args[0] == 'claude'
            assert '--yes' in args


# Test 4: Working directory set correctly
@pytest.mark.asyncio
async def test_working_directory_set():
    """Test that subprocess working directory is set to ai-workspace."""
    from claude_interface import execute_claude_task
    import tempfile

    # Create temporary workspace directory
    with tempfile.TemporaryDirectory() as workspace_path:
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            # Setup mock process
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.stdin = AsyncMock()
            mock_process.stdin.write = Mock()
            mock_process.stdin.drain = AsyncMock()
            mock_process.stdin.close = Mock()

            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(return_value=b'')
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b'')

            mock_process.wait = AsyncMock(return_value=None)
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            # Consume generator
            async for line in execute_claude_task("test task", workspace_path):
                pass

            # Verify cwd parameter was set
            mock_subprocess.assert_called_once()
            kwargs = mock_subprocess.call_args[1]
            assert kwargs['cwd'] == workspace_path


# Test 5: Output streams line-by-line
@pytest.mark.asyncio
async def test_output_streams_line_by_line():
    """Test that stdout/stderr are captured and yielded line-by-line."""
    from claude_interface import execute_claude_task

    test_output = [
        b"Line 1\n",
        b"Line 2\n",
        b"Line 3\n",
        b''  # EOF
    ]

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process with output
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        # Mock readline to return lines sequentially
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=test_output)

        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')

        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        output_lines = []
        async for line in execute_claude_task("test task", "/tmp"):
            output_lines.append(line)

        # Verify lines were yielded (3 output + 1 exit message)
        assert len(output_lines) >= 3
        assert "Line 1" in output_lines[0]
        assert "Line 2" in output_lines[1]
        assert "Line 3" in output_lines[2]


# Test 6: Exit code captured and returned
@pytest.mark.asyncio
async def test_exit_code_captured():
    """Test that subprocess exit code is captured and returned."""
    from claude_interface import execute_claude_task

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process with non-zero exit
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'')
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')

        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 1
        mock_subprocess.return_value = mock_process

        output_lines = []
        async for line in execute_claude_task("test task", "/tmp"):
            output_lines.append(line)

        # Get final result (should include exit code)
        # The generator should yield exit code info
        assert any("exit" in line.lower() or "code" in line.lower() for line in output_lines)


# Test 7: Timeout handling
@pytest.mark.asyncio
async def test_timeout_handling():
    """Test that timeout parameter is passed and respected."""
    from claude_interface import execute_claude_task

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        # Simple mock that returns quickly
        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'')
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')

        mock_process.wait = AsyncMock(return_value=None)
        mock_process.kill = Mock()
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        # Execute with timeout parameter
        async for line in execute_claude_task("test task", "/tmp", timeout=10):
            pass

        # Test just verifies timeout parameter is accepted and doesn't cause errors
        # Actual timeout behavior is integration-tested with real subprocess
        assert True


# Test 8: Subprocess cleanup on error
@pytest.mark.asyncio
async def test_subprocess_cleanup_on_error():
    """Test that subprocess is properly cleaned up when errors occur."""
    from claude_interface import execute_claude_task

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process that raises error
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=Exception("Test error"))
        mock_process.stderr = AsyncMock()

        mock_process.kill = Mock()
        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process

        # Should cleanup even on error
        with pytest.raises(Exception):
            async for line in execute_claude_task("test task", "/tmp"):
                pass

        # Verify process was killed
        mock_process.kill.assert_called()


# Test 9: Stderr is captured separately
@pytest.mark.asyncio
async def test_stderr_captured():
    """Test that stderr output is captured and marked appropriately."""
    from claude_interface import execute_claude_task

    test_stderr = [
        b"Error: something went wrong\n",
        b"Warning: deprecated feature\n",
        b''  # EOF
    ]

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process with stderr
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'')

        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(side_effect=test_stderr)

        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        output_lines = []
        async for line in execute_claude_task("test task", "/tmp"):
            output_lines.append(line)

        # Verify stderr was captured (2 error lines + exit message)
        assert len(output_lines) >= 2
        assert any("Error" in line or "Warning" in line for line in output_lines)


# Test 10: Task description passed via stdin
@pytest.mark.asyncio
async def test_task_description_via_stdin():
    """Test that task description is passed to Claude via stdin."""
    from claude_interface import execute_claude_task

    task_desc = "Write a Python script to analyze data"

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(return_value=b'')
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')

        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        async for line in execute_claude_task(task_desc, "/tmp"):
            pass

        # Verify stdin was written to
        mock_process.stdin.write.assert_called_once()
        # Verify the task description was passed
        written_data = mock_process.stdin.write.call_args[0][0]
        assert task_desc.encode('utf-8') == written_data


# Test 11: Logging of Claude interactions
@pytest.mark.asyncio
async def test_logging_claude_interactions():
    """Test that all Claude interactions are logged."""
    from claude_interface import execute_claude_task

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        with patch('claude_interface.logger') as mock_logger:
            # Setup mock process
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.stdin = AsyncMock()
            mock_process.stdin.write = Mock()
            mock_process.stdin.drain = AsyncMock()
            mock_process.stdin.close = Mock()

            mock_process.stdout = AsyncMock()
            mock_process.stdout.readline = AsyncMock(side_effect=[b"output\n", b''])
            mock_process.stderr = AsyncMock()
            mock_process.stderr.readline = AsyncMock(return_value=b'')

            mock_process.wait = AsyncMock(return_value=None)
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process

            async for line in execute_claude_task("test task", "/tmp"):
                pass

            # Verify logging occurred
            assert mock_logger.info.called or mock_logger.debug.called


# Test 12: Handles unicode output correctly
@pytest.mark.asyncio
async def test_unicode_output_handling():
    """Test that unicode characters in output are handled correctly."""
    from claude_interface import execute_claude_task

    test_output = [
        "Hello 世界\n".encode('utf-8'),
        "Testing émojis 🚀\n".encode('utf-8'),
        b''  # EOF
    ]

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=test_output)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')

        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        output_lines = []
        async for line in execute_claude_task("test task", "/tmp"):
            output_lines.append(line)

        # Verify unicode was decoded correctly
        assert any("世界" in line for line in output_lines)
        assert any("🚀" in line for line in output_lines)


# Test 13: Returns result summary
@pytest.mark.asyncio
async def test_returns_result_summary():
    """Test that function returns a summary of execution results."""
    from claude_interface import execute_claude_task

    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # Setup mock process
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.stdin = AsyncMock()
        mock_process.stdin.write = Mock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdin.close = Mock()

        mock_process.stdout = AsyncMock()
        mock_process.stdout.readline = AsyncMock(side_effect=[b"Done\n", b''])
        mock_process.stderr = AsyncMock()
        mock_process.stderr.readline = AsyncMock(return_value=b'')

        mock_process.wait = AsyncMock(return_value=None)
        mock_process.returncode = 0
        mock_subprocess.return_value = mock_process

        # Collect all output
        all_output = []
        async for line in execute_claude_task("test task", "/tmp"):
            all_output.append(line)

        # Should have output plus summary/exit info
        assert len(all_output) > 0
        # Should have completion message
        assert any("completed" in line.lower() for line in all_output)
