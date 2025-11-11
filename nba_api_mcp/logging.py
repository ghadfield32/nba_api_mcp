"""
Structured logging for NBA MCP Server.

Provides production-ready JSON logging for log aggregation tools like
Datadog, Splunk, ELK Stack, etc.

Features:
- Structured JSON output with consistent fields
- Contextual information (tool, endpoint, request_id, etc.)
- Performance metrics (execution time, cache hits)
- Error tracking with error kinds
- Backward compatible with text logging

Usage:
    from nba_api_mcp.logging import setup_logging, get_logger

    # Setup logging (call once at startup)
    setup_logging()

    # Get logger with context
    logger = get_logger(__name__)

    # Log with extra context
    logger.info("Fetching data", extra={
        "tool": "get_player_stats",
        "endpoint": "player_career_stats",
        "request_id": "abc123",
        "exec_ms": 45.2,
        "from_cache": True
    })
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

from nba_api_mcp.config import settings

# Context variables for request tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
tool_ctx: ContextVar[Optional[str]] = ContextVar("tool", default=None)
endpoint_ctx: ContextVar[Optional[str]] = ContextVar("endpoint", default=None)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON with consistent fields for easy parsing by
    log aggregation tools.

    Standard fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (INFO, WARNING, ERROR, etc.)
    - logger: Logger name
    - message: Log message
    - request_id: Request identifier (from context)
    - tool: MCP tool name (from context)
    - endpoint: NBA API endpoint (from context)
    - exec_ms: Execution time in milliseconds
    - from_cache: Whether data came from cache
    - error_kind: Type of error (for ERROR level)
    - error_details: Error details dictionary
    - extra: Any additional fields passed via extra={}
    """

    def __init__(self):
        super().__init__()
        self.hostname = self._get_hostname()

    def _get_hostname(self) -> str:
        """Get hostname for logging."""
        try:
            import socket

            return socket.gethostname()
        except Exception:
            return "unknown"

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON string
        """
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "hostname": self.hostname,
            "process": record.process,
            "thread": record.thread,
        }

        # Add context from context vars
        request_id = request_id_ctx.get()
        if request_id:
            log_entry["request_id"] = request_id

        tool = tool_ctx.get()
        if tool:
            log_entry["tool"] = tool

        endpoint = endpoint_ctx.get()
        if endpoint:
            log_entry["endpoint"] = endpoint

        # Add extra fields from record
        extra_fields = [
            "exec_ms",
            "from_cache",
            "cache_hit",
            "error_kind",
            "error_details",
            "retries",
            "retry_after",
            "status_code",
            "rows",
            "columns",
            "filters_applied",
            "params",
            "user_id",
            "session_id",
        ]

        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
                if record.exc_info
                else None,
            }

        # Add stack info if present
        if record.stack_info:
            log_entry["stack_info"] = record.stack_info

        # Serialize to JSON
        try:
            return json.dumps(log_entry, default=str)
        except (TypeError, ValueError) as e:
            # Fallback if JSON serialization fails
            return json.dumps(
                {
                    "timestamp": self.formatTime(record),
                    "level": "ERROR",
                    "logger": __name__,
                    "message": f"Failed to serialize log record: {e}",
                    "original_message": str(record.getMessage()),
                }
            )

    def formatTime(self, record: logging.LogRecord, datefmt: Optional[str] = None) -> str:
        """
        Format timestamp as ISO 8601.

        Args:
            record: Log record
            datefmt: Date format (unused, kept for compatibility)

        Returns:
            ISO 8601 timestamp
        """
        dt = datetime.fromtimestamp(record.created)
        return dt.isoformat()


class TextFormatter(logging.Formatter):
    """
    Enhanced text formatter with color support (for development).

    Provides human-readable logs with optional color coding.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def __init__(self, use_color: bool = True):
        super().__init__(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.use_color = use_color and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format record with optional color."""
        # Add color to level name
        if self.use_color and record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )

        # Add context if available
        extras = []
        if hasattr(record, "tool"):
            extras.append(f"tool={record.tool}")
        if hasattr(record, "endpoint"):
            extras.append(f"endpoint={record.endpoint}")
        if hasattr(record, "exec_ms"):
            extras.append(f"exec_ms={record.exec_ms:.2f}")
        if hasattr(record, "from_cache"):
            extras.append(f"cache={'HIT' if record.from_cache else 'MISS'}")

        if extras:
            record.msg = f"{record.msg} [{', '.join(extras)}]"

        return super().format(record)


def setup_logging(
    level: Optional[str] = None,
    format: Optional[str] = None,
    force: bool = False,
) -> None:
    """
    Setup logging for NBA MCP Server.

    Configures logging based on settings from config.py. Can be called
    multiple times, but will only configure once unless force=True.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Defaults to settings.NBA_MCP_LOG_LEVEL
        format: Log format ('text' or 'json')
                Defaults to settings.LOG_FORMAT
        force: Force reconfiguration even if already configured

    Example:
        # Use defaults from config
        setup_logging()

        # Override format
        setup_logging(format='json')

        # Override both
        setup_logging(level='DEBUG', format='text')
    """
    # Check if already configured
    root = logging.getLogger()
    if root.handlers and not force:
        return

    # Get configuration
    log_level = level or settings.NBA_MCP_LOG_LEVEL
    log_format = format or settings.LOG_FORMAT

    # Convert level string to logging constant
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    numeric_level = level_map.get(log_level.upper(), logging.INFO)

    # Remove existing handlers
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    # Create handler with appropriate formatter
    handler = logging.StreamHandler(sys.stderr)

    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter(use_color=True)

    handler.setFormatter(formatter)
    handler.setLevel(numeric_level)

    # Configure root logger
    root.setLevel(numeric_level)
    root.addHandler(handler)

    # Log configuration
    root.info(
        f"Logging configured: level={log_level}, format={log_format}",
        extra={"config": {"level": log_level, "format": log_format}},
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get logger with name.

    Simple wrapper around logging.getLogger for consistency.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Context managers for setting request context

class RequestContext:
    """
    Context manager for setting request-level context.

    Sets context variables for the duration of the context,
    automatically including them in all log messages.

    Example:
        with RequestContext(
            request_id="abc123",
            tool="get_player_stats",
            endpoint="player_career_stats"
        ):
            logger.info("Fetching data")  # Will include request_id, tool, endpoint
    """

    def __init__(
        self,
        request_id: Optional[str] = None,
        tool: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        self.request_id = request_id or str(uuid.uuid4())
        self.tool = tool
        self.endpoint = endpoint
        self._tokens = []

    def __enter__(self):
        """Enter context, setting context variables."""
        self._tokens.append(request_id_ctx.set(self.request_id))
        if self.tool:
            self._tokens.append(tool_ctx.set(self.tool))
        if self.endpoint:
            self._tokens.append(endpoint_ctx.set(self.endpoint))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context, resetting context variables."""
        for token in reversed(self._tokens):
            if hasattr(token, "var"):  # Context var token
                token.var.reset(token)


class TimedOperation:
    """
    Context manager for timing operations.

    Logs operation duration on exit with execution time.

    Example:
        with TimedOperation("fetch_data", logger):
            data = await fetch_from_api()
        # Logs: "fetch_data completed" with exec_ms
    """

    def __init__(
        self,
        operation: str,
        logger: logging.Logger,
        level: int = logging.INFO,
        **extra_context,
    ):
        self.operation = operation
        self.logger = logger
        self.level = level
        self.extra_context = extra_context
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.perf_counter()
        self.logger.log(self.level, f"{self.operation} started", extra=self.extra_context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log completion with duration."""
        if self.start_time:
            exec_ms = (time.perf_counter() - self.start_time) * 1000
            extra = {**self.extra_context, "exec_ms": exec_ms}

            if exc_type:
                extra["error_kind"] = exc_type.__name__
                extra["error_message"] = str(exc_val)
                self.logger.error(f"{self.operation} failed", extra=extra, exc_info=True)
            else:
                self.logger.log(self.level, f"{self.operation} completed", extra=extra)


# Convenience functions for common logging patterns


def log_fetch_start(
    logger: logging.Logger,
    endpoint: str,
    params: Dict[str, Any],
    request_id: Optional[str] = None,
) -> None:
    """Log start of data fetch operation."""
    logger.info(
        f"Fetching {endpoint}",
        extra={
            "endpoint": endpoint,
            "params": params,
            "request_id": request_id,
            "operation": "fetch_start",
        },
    )


def log_fetch_complete(
    logger: logging.Logger,
    endpoint: str,
    rows: int,
    exec_ms: float,
    from_cache: bool,
    request_id: Optional[str] = None,
) -> None:
    """Log completion of data fetch operation."""
    logger.info(
        f"Fetch {endpoint} complete: {rows} rows in {exec_ms:.2f}ms (cache {'HIT' if from_cache else 'MISS'})",
        extra={
            "endpoint": endpoint,
            "rows": rows,
            "exec_ms": exec_ms,
            "from_cache": from_cache,
            "cache_hit": from_cache,
            "request_id": request_id,
            "operation": "fetch_complete",
        },
    )


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log error with context."""
    extra = {
        "error_kind": type(error).__name__,
        "error_message": str(error),
        **(context or {}),
    }

    if hasattr(error, "code"):
        extra["error_code"] = error.code
    if hasattr(error, "details"):
        extra["error_details"] = error.details

    logger.error(f"Error: {error}", extra=extra, exc_info=True)


# Export public API
__all__ = [
    "setup_logging",
    "get_logger",
    "RequestContext",
    "TimedOperation",
    "log_fetch_start",
    "log_fetch_complete",
    "log_error",
]
