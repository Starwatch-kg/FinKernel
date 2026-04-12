"""Production-safe logging configuration"""

import logging
import sys
from typing import Optional


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Setup structured logger with proper formatting"""
    logger = logging.getLogger(name)

    # Set level from env or default to INFO
    log_level = level or "INFO"
    logger.setLevel(getattr(logging, log_level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler with structured format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    # Format: timestamp | level | service | message
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    return logger
