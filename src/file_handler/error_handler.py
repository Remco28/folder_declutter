"""
Error Handler - Maps file operation exceptions to user-friendly messages
"""

import logging
import os
from pathlib import Path


logger = logging.getLogger(__name__)


def to_message(exc: Exception, path: str = None) -> tuple[str, str]:
    """
    Convert exception to user-friendly message and log level

    Args:
        exc: Exception that occurred
        path: File/folder path related to error (optional)

    Returns:
        tuple: (message, level) where level is 'error', 'warning', etc.
    """
    path_info = f" ({path})" if path else ""

    if isinstance(exc, PermissionError):
        return f"Permission denied{path_info}", "error"

    elif isinstance(exc, FileNotFoundError):
        return f"File or folder not found{path_info}", "error"

    elif isinstance(exc, FileExistsError):
        return f"File already exists{path_info}", "error"

    elif isinstance(exc, OSError) and exc.errno == 28:  # No space left
        return f"Not enough disk space{path_info}", "error"

    elif isinstance(exc, OSError) and exc.errno == 36:  # File name too long
        return f"File name too long{path_info}", "error"

    elif isinstance(exc, OSError) and exc.errno == 13:  # Permission denied
        return f"Access denied{path_info}", "error"

    elif isinstance(exc, OSError) and exc.errno == 17:  # File exists
        return f"File already exists{path_info}", "error"

    elif isinstance(exc, OSError) and exc.errno == 39:  # Directory not empty
        return f"Directory not empty{path_info}", "error"

    elif isinstance(exc, IsADirectoryError):
        return f"Target is a directory{path_info}", "error"

    elif isinstance(exc, NotADirectoryError):
        return f"Path component is not a directory{path_info}", "error"

    elif isinstance(exc, OSError):
        # Generic OS error
        error_msg = getattr(exc, 'strerror', str(exc))
        return f"System error: {error_msg}{path_info}", "error"

    else:
        # Unexpected exception type
        return f"Unexpected error: {type(exc).__name__}: {exc}{path_info}", "error"


def log_error(exc: Exception, path: str = None, logger=None) -> str:
    """
    Log an error and return user-friendly message

    Args:
        exc: Exception that occurred
        path: File/folder path related to error (optional)
        logger: Logger to use (optional)

    Returns:
        str: User-friendly error message
    """
    if logger is None:
        logger = globals()['logger']

    message, level = to_message(exc, path)

    # Log at appropriate level
    if level == "error":
        logger.error(message)
    elif level == "warning":
        logger.warning(message)
    else:
        logger.info(message)

    return message