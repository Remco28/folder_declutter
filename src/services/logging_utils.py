"""Utilities for configuring application logging."""

from __future__ import annotations

import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Tuple

from ..config import ConfigManager

# Generate a session identifier for the lifetime of the process.
_SESSION_ID = uuid.uuid4().hex[:8].upper()


class _SessionContextFilter(logging.Filter):
    """Inject the current session id into every log record."""

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self._session_id = session_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.session_id = self._session_id
        return True


def _resolve_log_level(default_level: int) -> Tuple[int, Optional[str]]:
    """Resolve the effective log level from DS_LOG_LEVEL."""
    env_value = os.getenv("DS_LOG_LEVEL")
    if not env_value:
        return default_level, None

    candidate = env_value.strip()
    if not candidate:
        return default_level, None

    upper_candidate = candidate.upper()
    if upper_candidate in logging._nameToLevel:
        return logging._nameToLevel[upper_candidate], None

    try:
        numeric_level = int(candidate)
    except ValueError:
        fallback = logging.getLevelName(default_level)
        warning = f"Invalid DS_LOG_LEVEL value '{candidate}', falling back to {fallback}"
        return default_level, warning

    return numeric_level, None


def configure_logging(default_level: int = logging.INFO) -> Tuple[str, Path]:
    """Configure console and rotating file handlers for the application."""
    level, pending_warning = _resolve_log_level(default_level)

    logs_dir = ConfigManager.get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "app.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Replace any pre-existing handlers so we control formatting/output.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    session_filter = _SessionContextFilter(_SESSION_ID)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
    )
    console_handler.addFilter(session_filter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_048_576,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s [%(threadName)s] [session:%(session_id)s] %(message)s"
        )
    )
    file_handler.addFilter(session_filter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    logging.captureWarnings(True)

    helper_logger = logging.getLogger(__name__)
    helper_logger.debug(
        "Logging configured with level=%s, log_path=%s",
        logging.getLevelName(level),
        log_path,
    )

    if pending_warning:
        helper_logger.warning(pending_warning)

    return _SESSION_ID, log_path


def get_session_id() -> str:
    """Return the current logging session identifier."""
    return _SESSION_ID


__all__ = ["configure_logging", "get_session_id"]
