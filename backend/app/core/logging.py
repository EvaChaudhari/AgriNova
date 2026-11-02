"""Krishi Mitra / AgriNova Structured JSON Logging System.

Implements high-performance, RFC-compliant structured JSON logging with
contextual correlation ID tracking, request profiling, and sensitive data sanitization.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Optional

# Context variable to hold the correlation ID for the active request thread/task
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")

# Sensitive keys that must never appear unmasked in application logs
SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "gemini_api_key",
    "bhashini_api_key",
    "authorization",
    "kisan_id",
    "phone_number",
    "audio_file",
    "image_file",
    "audio_content",
    "audio_base64_url",
    "image_bytes",
}


def get_correlation_id() -> str:
    """Retrieve the correlation ID of the current request context."""
    return correlation_id_ctx.get()


def set_correlation_id(cid: str) -> None:
    """Set the correlation ID for the current request context."""
    correlation_id_ctx.set(cid)


def sanitize_value(key: str, value: Any) -> Any:
    """Mask sensitive parameters to prevent confidential leakage into logs."""
    if any(s_key in key.lower() for s_key in SENSITIVE_KEYS):
        return "***REDACTED***"
    if isinstance(value, dict):
        return {k: sanitize_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_value(key, item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        # Avoid logging massive base64 strings or binary representations
        return value[:100] + "...[TRUNCATED]"
    return value


class StructuredJsonFormatter(logging.Formatter):
    """Custom logging formatter that serializes log records into structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Contextual correlation ID
        cid = getattr(record, "correlation_id", None) or get_correlation_id()
        if cid:
            log_entry["correlation_id"] = cid

        # Request HTTP metrics
        for attr in ("method", "path", "status_code", "duration_ms", "client_ip"):
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)

        # Exception information (if present)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logger to output structured JSON to stdout."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicate log outputs
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(handler)

    # Silence excessively verbose third-party loggers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = False

