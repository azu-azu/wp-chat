# src/core/logging_config.py - Structured logging configuration
import logging
import os
import sys

from pythonjsonlogger import jsonlogger


def setup_logging(
    log_level: str | None = None, log_format: str | None = None, logger_name: str | None = None
) -> logging.Logger:
    """
    Setup structured logging with JSON format support

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to env LOG_LEVEL or INFO
        log_format: Log format (json or text). Defaults to env LOG_FORMAT or json
        logger_name: Logger name. Defaults to root logger

    Returns:
        Configured logger instance
    """
    # Get configuration from environment or use defaults
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_format = log_format or os.getenv("LOG_FORMAT", "json")

    # Get or create logger
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        logger = logging.getLogger()

    # Set log level
    logger.setLevel(log_level.upper())

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level.upper())

    # Configure formatter based on format type
    if log_format.lower() == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "module"},
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        # Text format
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # If logger is not configured, configure it
    if not logger.handlers:
        setup_logging(logger_name=name)

    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log message with additional context (useful for JSON logs)

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context as keyword arguments

    Example:
        log_with_context(
            logger,
            "info",
            "Generation completed",
            question="VBA",
            latency_ms=1234,
            token_count=456
        )
    """
    log_method = getattr(logger, level.lower())

    # For JSON formatter, extra fields are automatically included
    log_method(message, extra=context)


# Initialize default logger on module import
default_logger = setup_logging()
