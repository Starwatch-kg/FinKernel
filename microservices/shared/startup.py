"""Startup validation and initialization"""

import sys

sys.path.append("/app")

from shared.config import init_config
from shared.logger import setup_logger

logger = setup_logger("startup")


def validate_startup():
    """Validate configuration and dependencies on startup"""
    try:
        # Initialize and validate config
        config = init_config()

        logger.info("✓ Configuration validated successfully")

        # Check critical dependencies
        try:
            import redis.asyncio as redis

            logger.info("✓ Redis client available")
        except ImportError as e:
            logger.error(f"✗ Redis client not available: {e}")
            sys.exit(1)

        try:
            import sqlalchemy

            logger.info("✓ SQLAlchemy available")
        except ImportError as e:
            logger.error(f"✗ SQLAlchemy not available: {e}")
            sys.exit(1)

        logger.info("=" * 60)
        logger.info("Service ready to start")
        logger.info("=" * 60)

        return config

    except Exception as e:
        logger.error(f"FATAL: Startup validation failed: {e}")
        sys.exit(1)
