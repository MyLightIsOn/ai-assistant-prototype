"""
Tests for structured JSON logging system.

Following TDD: These tests are written FIRST and should FAIL until implementation is complete.
"""

import json
import logging
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest


class TestJSONLogFormatter:
    """Test JSON log formatting."""

    def test_formats_log_as_json(self):
        """JSON formatter should output valid JSON."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        parsed = json.loads(output)  # Should not raise

        assert isinstance(parsed, dict)

    def test_includes_timestamp(self):
        """Log entry should include ISO 8601 timestamp."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "timestamp" in parsed
        # Should be valid ISO 8601 format
        datetime.fromisoformat(parsed["timestamp"].replace("Z", "+00:00"))

    def test_includes_level(self):
        """Log entry should include log level."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "level" in parsed
        assert parsed["level"] == "WARNING"

    def test_includes_message(self):
        """Log entry should include message."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message with content",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "message" in parsed
        assert parsed["message"] == "Test message with content"

    def test_includes_task_id_from_extra(self):
        """Log entry should include task_id from extra fields."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.task_id = "task-123"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "task_id" in parsed
        assert parsed["task_id"] == "task-123"

    def test_includes_execution_id_from_extra(self):
        """Log entry should include execution_id from extra fields."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.execution_id = "exec-456"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "execution_id" in parsed
        assert parsed["execution_id"] == "exec-456"

    def test_includes_metadata_from_extra(self):
        """Log entry should include metadata dict from extra fields."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.metadata = {"user": "test@example.com", "action": "login"}

        output = formatter.format(record)
        parsed = json.loads(output)

        assert "metadata" in parsed
        assert parsed["metadata"]["user"] == "test@example.com"
        assert parsed["metadata"]["action"] == "login"

    def test_handles_missing_optional_fields(self):
        """Log entry should handle missing optional fields (task_id, execution_id, metadata)."""
        from logger import JSONLogFormatter

        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        output = formatter.format(record)
        parsed = json.loads(output)

        # Should have None or null for optional fields
        assert parsed.get("task_id") is None
        assert parsed.get("execution_id") is None
        assert parsed.get("metadata") is None or parsed.get("metadata") == {}


class TestLoggerSetup:
    """Test logger configuration and setup."""

    def test_setup_logger_creates_handler(self):
        """setup_logger should create and configure a logger."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir, logger_name="test_logger")

            assert isinstance(logger, logging.Logger)
            assert logger.name == "test_logger"
            assert len(logger.handlers) > 0

    def test_creates_log_directory_if_missing(self):
        """setup_logger should create log directory if it doesn't exist."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "nested", "logs")
            assert not os.path.exists(log_dir)

            setup_logger(log_dir=log_dir)

            assert os.path.exists(log_dir)
            assert os.path.isdir(log_dir)

    def test_log_file_created_in_correct_location(self):
        """Logger should create log file in specified directory."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)
            logger.info("Test log message")

            # Should create a log file
            log_files = list(Path(tmpdir).glob("*.log"))
            assert len(log_files) > 0

    def test_log_level_set_correctly(self):
        """Logger should respect specified log level."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir, level=logging.WARNING)

            assert logger.level == logging.WARNING


class TestLogRotation:
    """Test daily log rotation functionality."""

    def test_uses_timed_rotating_handler(self):
        """Logger should use TimedRotatingFileHandler for daily rotation."""
        from logger import setup_logger
        from logging.handlers import TimedRotatingFileHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)

            # Should have at least one TimedRotatingFileHandler
            rotating_handlers = [
                h for h in logger.handlers
                if isinstance(h, TimedRotatingFileHandler)
            ]
            assert len(rotating_handlers) > 0

    def test_rotation_configured_for_midnight(self):
        """TimedRotatingFileHandler should rotate at midnight."""
        from logger import setup_logger
        from logging.handlers import TimedRotatingFileHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)

            rotating_handler = next(
                h for h in logger.handlers
                if isinstance(h, TimedRotatingFileHandler)
            )

            # 'midnight' rotation (stored as uppercase by handler)
            # interval is stored as seconds (86400 = 24 hours for daily)
            assert rotating_handler.when == 'MIDNIGHT'
            assert rotating_handler.interval == 86400

    def test_backup_count_set_to_30(self):
        """TimedRotatingFileHandler should keep 30 days of logs."""
        from logger import setup_logger
        from logging.handlers import TimedRotatingFileHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)

            rotating_handler = next(
                h for h in logger.handlers
                if isinstance(h, TimedRotatingFileHandler)
            )

            assert rotating_handler.backupCount == 30


class TestStructuredLogging:
    """Test structured logging with context fields."""

    def test_log_with_task_id(self):
        """Should log with task_id in structured format."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)
            logger.info("Task started", extra={"task_id": "task-789"})

            # Read log file
            log_files = list(Path(tmpdir).glob("*.log"))
            with open(log_files[0]) as f:
                log_line = f.readline()

            parsed = json.loads(log_line)
            assert parsed["task_id"] == "task-789"
            assert parsed["message"] == "Task started"

    def test_log_with_execution_id(self):
        """Should log with execution_id in structured format."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)
            logger.info("Execution started", extra={"execution_id": "exec-999"})

            # Read log file
            log_files = list(Path(tmpdir).glob("*.log"))
            with open(log_files[0]) as f:
                log_line = f.readline()

            parsed = json.loads(log_line)
            assert parsed["execution_id"] == "exec-999"

    def test_log_with_metadata(self):
        """Should log with metadata dict in structured format."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)
            metadata = {"endpoint": "/api/tasks", "status_code": 200}
            logger.info("API request", extra={"metadata": metadata})

            # Read log file
            log_files = list(Path(tmpdir).glob("*.log"))
            with open(log_files[0]) as f:
                log_line = f.readline()

            parsed = json.loads(log_line)
            assert parsed["metadata"]["endpoint"] == "/api/tasks"
            assert parsed["metadata"]["status_code"] == 200

    def test_log_with_all_fields(self):
        """Should log with all structured fields."""
        from logger import setup_logger

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logger(log_dir=tmpdir)
            logger.error(
                "Task execution failed",
                extra={
                    "task_id": "task-abc",
                    "execution_id": "exec-xyz",
                    "metadata": {"error": "timeout", "duration_ms": 30000}
                }
            )

            # Read log file
            log_files = list(Path(tmpdir).glob("*.log"))
            with open(log_files[0]) as f:
                log_line = f.readline()

            parsed = json.loads(log_line)
            assert parsed["level"] == "ERROR"
            assert parsed["message"] == "Task execution failed"
            assert parsed["task_id"] == "task-abc"
            assert parsed["execution_id"] == "exec-xyz"
            assert parsed["metadata"]["error"] == "timeout"
            assert parsed["metadata"]["duration_ms"] == 30000


class TestDefaultLoggerFunction:
    """Test get_logger() helper function."""

    def test_get_logger_returns_configured_logger(self):
        """get_logger() should return pre-configured logger."""
        from logger import get_logger

        logger = get_logger()

        assert isinstance(logger, logging.Logger)
        assert len(logger.handlers) > 0

    def test_get_logger_uses_ai_workspace_logs_directory(self):
        """get_logger() should default to ai-workspace/logs directory."""
        from logger import get_logger

        logger = get_logger()

        # Check that handlers point to ai-workspace/logs
        from logging.handlers import TimedRotatingFileHandler
        rotating_handlers = [
            h for h in logger.handlers
            if isinstance(h, TimedRotatingFileHandler)
        ]

        if rotating_handlers:
            handler = rotating_handlers[0]
            assert "ai-workspace/logs" in handler.baseFilename
