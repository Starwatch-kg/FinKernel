"""Retry logic with exponential backoff and jitter"""
import asyncio
import random
from typing import Callable, Any, Type, Tuple
from functools import wraps
from shared.logger import setup_logger

logger = setup_logger("retry")


async def retry_with_backoff(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs
) -> Any:
    """
    Retry async function with exponential backoff and jitter

    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to delay
        exceptions: Tuple of exceptions to catch and retry
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e

            if attempt == max_retries:
                logger.error(
                    f"Max retries ({max_retries}) reached for {func.__name__}: {e}"
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** attempt), max_delay)

            # Add jitter
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                f"after {delay:.2f}s: {e}"
            )

            await asyncio.sleep(delay)

    raise last_exception


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Decorator for retry with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_backoff(
                func, *args,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                exceptions=exceptions,
                **kwargs
            )
        return wrapper
    return decorator
