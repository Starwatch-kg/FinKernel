"""Retry logic with exponential backoff"""

import asyncio
from typing import Any, Callable, Optional, Type

from shared.logger import setup_logger

logger = setup_logger("retry")


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    **kwargs,
) -> Any:
    """Retry function with exponential backoff"""
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            if attempt == max_retries:
                logger.error(
                    f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}"
                )
                raise

            logger.warning(
                f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {delay}s: {e}"
            )
            await asyncio.sleep(delay)
            delay = min(delay * exponential_base, max_delay)


class RetryConfig:
    """Retry configuration"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        exceptions: tuple = (Exception,),
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.exceptions = exceptions


# Pre-configured retry policies
RETRY_POLICIES = {
    "default": RetryConfig(max_retries=3, initial_delay=1.0),
    "aggressive": RetryConfig(max_retries=5, initial_delay=0.5),
    "conservative": RetryConfig(max_retries=2, initial_delay=2.0),
    "critical": RetryConfig(max_retries=10, initial_delay=1.0, max_delay=30.0),
}


async def retry_with_policy(
    func: Callable, policy: str = "default", *args, **kwargs
) -> Any:
    """Retry with named policy"""
    config = RETRY_POLICIES.get(policy, RETRY_POLICIES["default"])

    return await retry_with_backoff(
        func,
        *args,
        max_retries=config.max_retries,
        initial_delay=config.initial_delay,
        max_delay=config.max_delay,
        exponential_base=config.exponential_base,
        exceptions=config.exceptions,
        **kwargs,
    )
