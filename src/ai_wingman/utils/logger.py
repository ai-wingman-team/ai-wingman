"""
Logging configuration for AI Wingman.

Uses loguru for better logging experience.
"""

import sys
from loguru import logger
from ai_wingman.config import settings


def setup_logging() -> None:
    """Configure application logging."""

    # Remove default logger
    logger.remove()

    # Console logging with color
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level=settings.log_level,
        colorize=True,
    )

    # File logging (if configured)
    if settings.log_file:
        logger.add(
            settings.log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=settings.log_level,
            rotation="10 MB",  # Rotate log file when it reaches 10MB
            retention="7 days",  # Keep logs for 7 days
            compression="zip",  # Compress rotated logs
        )

    logger.info("Logging configured")
    logger.debug(f"Log level: {settings.log_level}")
    if settings.log_file:
        logger.debug(f"Log file: {settings.log_file}")


# Initialize logging when module is imported
setup_logging()


# Export logger for use in other modules
__all__ = ["logger", "setup_logging"]
