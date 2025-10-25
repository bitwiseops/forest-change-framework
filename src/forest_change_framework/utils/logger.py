"""
Structured logging configuration.

This module provides centralized logging setup with support for both console
and file output, with configurable verbosity and formatting.
"""

import logging
import logging.handlers
import os
from typing import Optional


def setup_logging(
    name: str = "forest_change_framework",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Configure structured logging for the framework.

    Sets up logging with a consistent format for both console and optional
    file output.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional path to log file. If provided, logs are written to file.
        format_string: Custom format string. Uses default if not provided.

    Returns:
        Configured logger instance.

    Example:
        >>> logger = setup_logging(__name__, level=logging.DEBUG)
        >>> logger.debug("Debug message")
        >>> logger = setup_logging(__name__, log_file="/var/log/app.log")
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if requested)
    if log_file:
        # Create directory if needed
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance by name.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Logger instance.

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)


class LoggerMixin:
    """
    Mixin that provides logging capability to classes.

    Provides a logger property that returns a logger with the class name.
    """

    @property
    def logger(self) -> logging.Logger:
        """Get a logger for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
