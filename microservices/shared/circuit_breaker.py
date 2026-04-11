"""Circuit breaker pattern implementation"""
import asyncio
import time
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps
from shared.logger import setup_logger

logger = setup_logger("circuit_breaker")


class CircuitState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """Circuit breaker with exponential backoff"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
        half_open_attempts: int = 1
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.half_open_attempts = half_open_attempts

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.half_open_success_count = 0

        # Metrics
        try:
            from metrics import circuit_breaker_state, circuit_breaker_failures_total
            self.metrics_state = circuit_breaker_state
            self.metrics_failures = circuit_breaker_failures_total
        except ImportError:
            self.metrics_state = None
            self.metrics_failures = None

    def _update_state_metric(self):
        """Update Prometheus metric for circuit state"""
        if self.metrics_state:
            self.metrics_state.labels(service=self.name).set(self.state.value)

    def _record_failure(self):
        """Record failure in metrics"""
        if self.metrics_failures:
            self.metrics_failures.labels(service=self.name).inc()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"Circuit breaker '{self.name}' entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
                self.half_open_success_count = 0
                self._update_state_metric()
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Retry after {self.recovery_timeout - (time.time() - self.last_failure_time):.1f}s"
                )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Success
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_success_count += 1
                if self.half_open_success_count >= self.half_open_attempts:
                    logger.info(f"Circuit breaker '{self.name}' recovered, entering CLOSED state")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self._update_state_metric()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

            return result

        except self.expected_exception as e:
            self._record_failure()
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}' failed in HALF_OPEN, reopening")
                self.state = CircuitState.OPEN
                self._update_state_metric()
            elif self.failure_count >= self.failure_threshold:
                logger.error(
                    f"Circuit breaker '{self.name}' threshold reached "
                    f"({self.failure_count}/{self.failure_threshold}), opening circuit"
                )
                self.state = CircuitState.OPEN
                self._update_state_metric()

            raise

    def __call__(self, func: Callable) -> Callable:
        """Decorator usage"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper


# Global circuit breakers
_circuit_breakers = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0
) -> CircuitBreaker:
    """Get or create a circuit breaker"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    return _circuit_breakers[name]
