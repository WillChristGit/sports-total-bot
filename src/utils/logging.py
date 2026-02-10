"""
Structured logging configuration for SportsTotalBot
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in {'name', 'msg', 'args', 'levelname', 'levelno',
                           'pathname', 'filename', 'module', 'exc_info',
                           'exc_text', 'stack_info', 'lineno', 'funcName',
                           'created', 'msecs', 'relativeCreated', 'thread',
                           'threadName', 'processName', 'process', 'message',
                           'asctime'}:
                log_data[key] = value

        return json.dumps(log_data)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter with better formatting"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def __init__(self, fmt: str = None, use_colors: bool = True):
        super().__init__(fmt)
        self.use_colors = use_colors and self._supports_color()

    def _supports_color(self) -> bool:
        """Check if terminal supports colors"""
        # Check if we're in a TTY
        if not hasattr(sys.stdout, 'isatty'):
            return False
        if not sys.stdout.isatty():
            return False

        # Check NO_COLOR environment variable
        if os.getenv('NO_COLOR'):
            return False

        return True

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            level_color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{level_color}{record.levelname}{self.RESET}"
            # Add color to message for ERROR and CRITICAL
            if record.levelno >= logging.ERROR:
                record.msg = f"{level_color}{record.msg}{self.RESET}"

        return super().format(record)


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: str = "logs",
    json_output: bool = False,
    include_timestamp: bool = True
) -> logging.Logger:
    """
    Set up logging for the application

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name (default: sportstotalbot.log)
        log_dir: Directory for log files (default: logs/)
        json_output: Use JSON formatting for machine-readable logs
        include_timestamp: Include timestamp in console output

    Returns:
        The root logger
    """
    # Create log directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if json_output:
        console_formatter = JSONFormatter()
    else:
        timestamp_format = '%(asctime)s ' if include_timestamp else ''
        console_format = f'{timestamp_format}[%(levelname)-8s] %(name)s: %(message)s'
        console_formatter = ColoredFormatter(console_format)

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler
    log_file_name = log_file or "sportstotalbot.log"
    log_file_path = Path(log_dir) / log_file_name

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(numeric_level)

    if json_output:
        file_formatter = JSONFormatter()
    else:
        file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        file_formatter = logging.Formatter(file_format)

    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name"""
    return logging.getLogger(name)
