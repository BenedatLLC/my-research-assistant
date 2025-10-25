"""Tests for logging configuration module."""

import logging
import tempfile
from pathlib import Path

import pytest

from my_research_assistant.logging_config import (
    FileFormatter,
    TerminalFormatter,
    configure_logging,
    redact_api_key,
)


class TestRedactApiKey:
    """Tests for API key redaction function."""

    def test_redact_openai_key(self):
        """Test redaction of OpenAI API key."""
        text = "Error with key sk-U10C2abc123xyz0yZg"
        result = redact_api_key(text)
        assert "sk-U10C2a*************0yZg" in result
        assert "bc123xyz" not in result

    def test_redact_openai_key_in_error_message(self):
        """Test redaction in full error message."""
        text = (
            "Error code: 401 - {'error': {'message': 'Incorrect API key provided: "
            "sk-U10C2abc123xyz0yZg. You can find your API key at "
            "https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error'}}"
        )
        result = redact_api_key(text)
        assert "sk-U10C2a*************0yZg" in result
        assert "bc123xyz" not in result

    def test_redact_multiple_keys(self):
        """Test redaction of multiple API keys in same text."""
        text = "Key1: sk-abc123def456ghi789 Key2: sk-xyz987uvw654rst321"
        result = redact_api_key(text)
        # Both keys should be redacted (middle parts hidden)
        assert "def456" not in result
        assert "uvw654" not in result
        # Should show sk- prefix + 6 chars for each key
        assert "sk-abc123" in result
        assert "sk-xyz987" in result
        # Should show last 4 chars
        assert "i789" in result
        assert "t321" in result

    def test_no_redaction_when_no_key(self):
        """Test that normal text is not modified."""
        text = "This is a normal error message without any API keys"
        result = redact_api_key(text)
        assert result == text

    def test_redact_generic_api_key(self):
        """Test redaction of generic API key (20+ alphanumeric chars)."""
        text = "Google API key: AIzaSyAbC123dEf456GhI789jKl012MnO3456"
        result = redact_api_key(text)
        # Should redact if it has both letters and numbers
        assert "AIzaSy*************3456" in result or "AbC123" not in result

    def test_no_redaction_for_short_strings(self):
        """Test that short alphanumeric strings are not redacted."""
        text = "Version 123abc is available"
        result = redact_api_key(text)
        assert result == text

    def test_preserve_non_key_long_numbers(self):
        """Test that long number-only strings are not redacted."""
        text = "Transaction ID: 123456789012345678901234"
        result = redact_api_key(text)
        # Pure numbers shouldn't be redacted
        assert "123456789012345678901234" in result


class TestTerminalFormatter:
    """Tests for terminal log formatter."""

    def test_format_info_message(self):
        """Test formatting INFO level message."""
        formatter = TerminalFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert result == "I Test message"

    def test_format_error_message(self):
        """Test formatting ERROR level message."""
        formatter = TerminalFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error occurred",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert result == "E Error occurred"

    def test_format_warning_message(self):
        """Test formatting WARNING level message."""
        formatter = TerminalFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert result == "W Warning message"

    def test_format_debug_message(self):
        """Test formatting DEBUG level message."""
        formatter = TerminalFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Debug info",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert result == "D Debug info"

    def test_format_redacts_api_keys(self):
        """Test that formatter redacts API keys."""
        formatter = TerminalFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error with key sk-U10C2abc123xyz0yZg",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "sk-U10C2a*************0yZg" in result
        assert "bc123xyz" not in result


class TestFileFormatter:
    """Tests for file log formatter."""

    def test_format_includes_timestamp(self):
        """Test that file format includes ISO timestamp."""
        formatter = FileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        # Should have ISO timestamp format (contains 'T' separator)
        assert 'T' in result
        assert "INFO Test message" in result

    def test_format_includes_level(self):
        """Test that file format includes log level."""
        formatter = FileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "ERROR Error message" in result

    def test_format_redacts_api_keys(self):
        """Test that file formatter redacts API keys."""
        formatter = FileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error with key sk-U10C2abc123xyz0yZg",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "sk-U10C2a*************0yZg" in result
        assert "bc123xyz" not in result


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_with_no_arguments(self):
        """Test configuration with no logging enabled."""
        configure_logging()
        root_logger = logging.getLogger()
        # Should have no handlers (or only default ones that were there before)
        assert len(root_logger.handlers) == 0
        # Root logger level should be very high to prevent lastResort handler
        assert root_logger.level > logging.CRITICAL

    def test_configure_with_loglevel(self):
        """Test configuration with console logging."""
        configure_logging(loglevel="INFO")
        root_logger = logging.getLogger()
        # Should have exactly one handler (console)
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.Handler)
        # Root logger should be set to DEBUG to capture all levels
        assert root_logger.level == logging.DEBUG

    def test_configure_with_logfile(self):
        """Test configuration with file logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "test.log"
            configure_logging(logfile=str(logfile))
            root_logger = logging.getLogger()
            # Should have exactly one handler (file)
            assert len(root_logger.handlers) == 1
            assert isinstance(root_logger.handlers[0], logging.FileHandler)
            # Log file should exist
            assert logfile.exists()
            # Root logger should be set to DEBUG to capture all levels
            assert root_logger.level == logging.DEBUG

    def test_configure_with_both(self):
        """Test configuration with both console and file logging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "test.log"
            configure_logging(loglevel="DEBUG", logfile=str(logfile))
            root_logger = logging.getLogger()
            # Should have two handlers
            assert len(root_logger.handlers) == 2

    def test_invalid_loglevel_raises_error(self):
        """Test that invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid log level"):
            configure_logging(loglevel="INVALID")

    def test_logfile_creates_directory(self):
        """Test that log file creation creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "subdir" / "test.log"
            configure_logging(logfile=str(logfile))
            # Directory and file should be created
            assert logfile.parent.exists()
            assert logfile.exists()

    def test_session_delimiter_written(self):
        """Test that session delimiter is written to log file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "test.log"
            configure_logging(logfile=str(logfile))
            content = logfile.read_text()
            assert "Session started:" in content
            assert "=" * 80 in content

    def test_multiple_sessions_appended(self):
        """Test that multiple sessions are appended to same file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logfile = Path(tmpdir) / "test.log"

            # First session
            configure_logging(logfile=str(logfile))
            logger = logging.getLogger("test")
            logger.info("First session message")

            # Second session
            configure_logging(logfile=str(logfile))
            logger.info("Second session message")

            content = logfile.read_text()
            # Should have two session delimiters
            assert content.count("Session started:") == 2
            # Should have both messages
            assert "First session message" in content
            assert "Second session message" in content

    def test_loglevel_case_insensitive(self):
        """Test that log level is case insensitive."""
        configure_logging(loglevel="info")
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 1

        configure_logging(loglevel="DEBUG")
        assert len(root_logger.handlers) == 1

    def test_llama_index_logging_suppressed(self):
        """Test that LlamaIndex logging is set to WARNING."""
        configure_logging(loglevel="DEBUG")
        llama_logger = logging.getLogger('llama_index')
        assert llama_logger.level == logging.WARNING

    def test_openai_logging_suppressed(self):
        """Test that OpenAI logging is set to WARNING."""
        configure_logging(loglevel="DEBUG")
        openai_logger = logging.getLogger('openai')
        assert openai_logger.level == logging.WARNING
