"""Logging configuration for the research assistant chatbot.

This module provides centralized logging setup with support for:
- Console logging via Rich library for terminal output
- File logging with ISO timestamps
- API key redaction for sensitive information
- LlamaIndex logging suppression
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


def redact_api_key(text: str) -> str:
    """Redact API keys in text, showing "sk-" + first 6 chars and last 4 characters.

    Handles various API key formats:
    - OpenAI keys (sk-...)
    - Google API keys (various formats)

    Args:
        text: Text potentially containing API keys

    Returns:
        Text with API keys redacted

    Examples:
        >>> redact_api_key("Error with key sk-U10C2abc123xyz0yZg")
        'Error with key sk-U10C2a*************0yZg'
    """
    # Pattern for OpenAI-style keys (sk- followed by 40+ chars)
    # Show "sk-" + first 6 chars of key + redaction + last 4 chars
    pattern = r'(sk-[A-Za-z0-9]{6})([A-Za-z0-9]+)([A-Za-z0-9]{4})'
    text = re.sub(pattern, r'\1*************\3', text)

    # Pattern for other API keys (long alphanumeric strings, at least 20 chars)
    # Only redact if it looks like a key (has mix of letters and numbers)
    pattern = r'\b([A-Za-z0-9]{6})([A-Za-z0-9]{10,})([A-Za-z0-9]{4})\b'
    def replace_if_mixed(match):
        full = match.group(0)
        # Only redact if string has both letters and numbers
        if re.search(r'[A-Za-z]', full) and re.search(r'[0-9]', full):
            return f"{match.group(1)}{'*' * 13}{match.group(3)}"
        return full

    text = re.sub(pattern, replace_if_mixed, text)

    return text


class TerminalFormatter(logging.Formatter):
    """Log formatter for terminal output: level char + message (no timestamp)."""

    LEVEL_CHARS = {
        'DEBUG': 'D',
        'INFO': 'I',
        'WARNING': 'W',
        'ERROR': 'E',
        'CRITICAL': 'E',
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for terminal output.

        Args:
            record: Log record to format

        Returns:
            Formatted log message
        """
        level_char = self.LEVEL_CHARS.get(record.levelname, '?')
        message = super().format(record)

        # Redact API keys
        message = redact_api_key(message)

        return f"{level_char} {message}"


class FileFormatter(logging.Formatter):
    """Log formatter for file output: ISO timestamp + level + message."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for file output.

        Args:
            record: Log record to format

        Returns:
            Formatted log message with ISO timestamp
        """
        # Get ISO formatted timestamp
        timestamp = datetime.fromtimestamp(record.created).isoformat()

        # Format the message
        message = super().format(record)

        # Redact API keys
        message = redact_api_key(message)

        return f"{timestamp} {record.levelname} {message}"


def _write_session_delimiter(logfile: str) -> None:
    """Write session start marker to log file.

    Args:
        logfile: Path to log file
    """
    delimiter = f"\n{'=' * 80}\n"
    delimiter += f"Session started: {datetime.now().isoformat()}\n"
    delimiter += f"{'=' * 80}\n"

    with open(logfile, 'a') as f:
        f.write(delimiter)


def _create_console_handler(loglevel: str) -> RichHandler:
    """Create Rich-based console handler for terminal logging.

    Args:
        loglevel: Log level (ERROR, WARNING, INFO, DEBUG)

    Returns:
        Configured RichHandler
    """
    console = Console(stderr=True)
    handler = RichHandler(
        console=console,
        show_time=False,
        show_level=False,
        show_path=False,
        markup=False,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
    )
    handler.setLevel(getattr(logging, loglevel.upper()))
    handler.setFormatter(TerminalFormatter())

    return handler


def _create_file_handler(logfile: str) -> logging.FileHandler:
    """Create file handler for logging to file.

    Args:
        logfile: Path to log file

    Returns:
        Configured FileHandler
    """
    # Ensure directory exists
    logfile_path = Path(logfile)
    logfile_path.parent.mkdir(parents=True, exist_ok=True)

    # Write session delimiter
    _write_session_delimiter(logfile)

    handler = logging.FileHandler(logfile, mode='a')
    handler.setLevel(logging.DEBUG)  # File gets all levels
    handler.setFormatter(FileFormatter())

    return handler


def configure_logging(loglevel: Optional[str] = None, logfile: Optional[str] = None) -> None:
    """Configure logging for the research assistant.

    Args:
        loglevel: Terminal log level (ERROR, WARNING, INFO, DEBUG). If None, no terminal logging.
        logfile: Path to log file. If None, no file logging.

    Raises:
        ValueError: If loglevel is not a valid log level
    """
    # Validate loglevel
    if loglevel is not None:
        loglevel_upper = loglevel.upper()
        if loglevel_upper not in ('ERROR', 'WARNING', 'INFO', 'DEBUG'):
            raise ValueError(f"Invalid log level: {loglevel}")

    # Get root logger
    root_logger = logging.getLogger()

    # Remove existing handlers
    root_logger.handlers.clear()

    # Determine if we're adding any handlers
    adding_handlers = (loglevel is not None) or (logfile is not None)

    if adding_handlers:
        # Set root logger to capture all levels, handlers will filter
        root_logger.setLevel(logging.DEBUG)
    else:
        # No handlers being added - disable logging by setting very high level
        # This prevents Python's lastResort handler from printing to stderr
        root_logger.setLevel(logging.CRITICAL + 1)

    # Add console handler if loglevel specified
    if loglevel is not None:
        console_handler = _create_console_handler(loglevel)
        root_logger.addHandler(console_handler)

    # Add file handler if logfile specified
    if logfile is not None:
        file_handler = _create_file_handler(logfile)
        root_logger.addHandler(file_handler)

    # Suppress LlamaIndex verbose logging
    logging.getLogger('llama_index').setLevel(logging.WARNING)

    # Also suppress some other verbose loggers
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
