"""Logging configuration using structlog."""
import logging
import sys
from typing import Any, Dict

import structlog


def configure_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to output logs in JSON format (useful for production)
    """
    # Configure stdlib logging to work with structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Configure structlog
    processors = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add timestamp to event dict
        structlog.processors.TimeStamper(fmt="iso"),
        # If the "exc_info" key is set, format exception info
        structlog.processors.format_exc_info,
        # If some value is a datetime, format it
        structlog.processors.JSONRenderer() if json_format else structlog.dev.ConsoleRenderer(),
    ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__ of the calling module)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Global logger instance for convenience
logger = get_logger("claw_service_hub")