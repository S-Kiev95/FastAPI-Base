"""
Structured Logging System

Provides JSON-formatted structured logging with:
- Automatic context (timestamp, level, request_id)
- Context manager for enriched logging
- Integration with FastAPI
- Log rotation and file output
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar
from pathlib import Path

from app.config import settings


# Context variable to store request-specific data
log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON

    Output format:
    {
        "timestamp": "2025-12-18T12:00:00.000Z",
        "level": "INFO",
        "logger": "app.services.media",
        "message": "Processing image",
        "request_id": "abc123",
        "user_id": 456,
        "media_id": 789,
        ...any extra fields...
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""

        # Base log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context from ContextVar (request_id, user_id, etc.)
        context = log_context.get()
        if context:
            log_data.update(context)

        # Add extra fields from record
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }

        # Add file location for debugging
        if settings.LOG_LEVEL == "DEBUG":
            log_data["file"] = {
                "path": record.pathname,
                "line": record.lineno,
                "function": record.funcName
            }

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """
    Human-readable formatter for development

    Output format:
    2025-12-18 12:00:00 | INFO | app.services.media | Processing image | request_id=abc123 user_id=456
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as text"""

        # Base format
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        base = f"{timestamp} | {record.levelname:8} | {record.name:30} | {record.getMessage()}"

        # Add context
        context = log_context.get()
        if context:
            context_str = " ".join(f"{k}={v}" for k, v in context.items())
            base += f" | {context_str}"

        # Add extra fields
        if hasattr(record, 'extra_fields'):
            extra_str = " ".join(f"{k}={v}" for k, v in record.extra_fields.items())
            base += f" | {extra_str}"

        # Add exception if present
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


def setup_logging(
    level: str = None,
    log_format: str = None,
    log_file: str = None
):
    """
    Setup logging configuration

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format (json or text)
        log_file: Path to log file (optional)
    """
    # Get from settings if not provided
    level = level or settings.LOG_LEVEL
    log_format = log_format or settings.LOG_FORMAT
    log_file = log_file or settings.LOG_FILE

    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Choose formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger for a module

    Usage:
        logger = get_logger(__name__)
        logger.info("Message", extra={"key": "value"})
    """
    return logging.getLogger(name)


class LogContext:
    """
    Context manager for adding context to all logs within a block

    Usage:
        with LogContext(request_id="abc123", user_id=456):
            logger.info("Processing")
            # All logs will include request_id and user_id

        # Or use as decorator
        @LogContext(operation="upload")
        async def upload_file():
            logger.info("Uploading")
    """

    def __init__(self, **kwargs):
        """Initialize with context data"""
        self.context_data = kwargs
        self.token = None

    def __enter__(self):
        """Enter context"""
        current = log_context.get()
        new_context = {**current, **self.context_data}
        self.token = log_context.set(new_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context"""
        if self.token:
            log_context.reset(self.token)

    def __call__(self, func):
        """Decorator support"""
        async def wrapper(*args, **kwargs):
            with self:
                return await func(*args, **kwargs)
        return wrapper


# Helper class for structured logging with extra fields
class StructuredLogger:
    """
    Wrapper for logger that makes it easier to add extra fields

    Usage:
        logger = StructuredLogger(__name__)
        logger.info("Processing image", media_id=123, user_id=456)
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: int, msg: str, **kwargs):
        """Internal log method with extra fields"""
        extra = {"extra_fields": kwargs} if kwargs else {}
        self.logger.log(level, msg, extra=extra)

    def debug(self, msg: str, **kwargs):
        """Debug level log"""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """Info level log"""
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """Warning level log"""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        """Error level log"""
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        """Critical level log"""
        self._log(logging.CRITICAL, msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        """Log exception with traceback"""
        extra = {"extra_fields": kwargs} if kwargs else {}
        self.logger.exception(msg, extra=extra)


# Initialize logging on import
setup_logging()


# Convenience function to create structured logger
def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get structured logger for a module

    Usage:
        logger = get_structured_logger(__name__)
        logger.info("Processing", media_id=123, user_id=456)
    """
    return StructuredLogger(name)
