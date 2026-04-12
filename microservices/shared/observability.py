"""Observability: Prometheus metrics integration"""

import time
from functools import wraps

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from shared.logger import setup_logger

logger = setup_logger("metrics")

# Request metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)

# Auth metrics
auth_attempts_total = Counter(
    "auth_attempts_total", "Total authentication attempts", ["type", "status"]
)

# Transaction metrics
transactions_total = Counter(
    "transactions_total", "Total transactions", ["type", "status"]
)

transaction_amount = Histogram("transaction_amount", "Transaction amounts", ["type"])

# AI metrics
ai_predictions_total = Counter(
    "ai_predictions_total", "Total AI predictions", ["status"]
)

ai_prediction_duration_seconds = Histogram(
    "ai_prediction_duration_seconds", "AI prediction duration"
)

ai_confidence = Histogram("ai_confidence", "AI prediction confidence scores")

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["name"],
)

# Rate limiting metrics
rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total", "Total rate limit violations", ["resource"]
)

# Fraud detection metrics
fraud_score = Histogram("fraud_risk_score", "User fraud risk scores")

high_risk_users = Gauge("high_risk_users_total", "Total high-risk users flagged")

# Database metrics
db_connections_active = Gauge("db_connections_active", "Active database connections")

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds", "Database query duration", ["query_type"]
)

# Redis metrics
redis_operations_total = Counter(
    "redis_operations_total", "Total Redis operations", ["operation", "status"]
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds", "Redis operation duration", ["operation"]
)


def track_request_metrics(func):
    """Decorator to track HTTP request metrics"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status = "success"

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            # Metrics will be recorded by middleware
            logger.debug(f"Request completed in {duration:.3f}s with status {status}")

    return wrapper


def get_metrics_response() -> Response:
    """Generate Prometheus metrics response"""
    metrics = generate_latest()
    return Response(content=metrics, media_type=CONTENT_TYPE_LATEST)


class MetricsCollector:
    """Centralized metrics collection"""

    @staticmethod
    def record_auth_attempt(auth_type: str, success: bool):
        """Record authentication attempt"""
        status = "success" if success else "failure"
        auth_attempts_total.labels(type=auth_type, status=status).inc()

    @staticmethod
    def record_transaction(txn_type: str, amount: float, success: bool):
        """Record transaction"""
        status = "success" if success else "failure"
        transactions_total.labels(type=txn_type, status=status).inc()
        if success:
            transaction_amount.labels(type=txn_type).observe(amount)

    @staticmethod
    def record_ai_prediction(duration: float, confidence: float, success: bool):
        """Record AI prediction"""
        status = "success" if success else "failure"
        ai_predictions_total.labels(status=status).inc()
        if success:
            ai_prediction_duration_seconds.observe(duration)
            ai_confidence.observe(confidence)

    @staticmethod
    def record_circuit_breaker_state(name: str, state: str):
        """Record circuit breaker state"""
        state_value = {"closed": 0, "half_open": 1, "open": 2}.get(state, 0)
        circuit_breaker_state.labels(name=name).set(state_value)

    @staticmethod
    def record_rate_limit_exceeded(resource: str):
        """Record rate limit violation"""
        rate_limit_exceeded_total.labels(resource=resource).inc()

    @staticmethod
    def record_fraud_score(score: float):
        """Record fraud risk score"""
        fraud_score.observe(score)

    @staticmethod
    def set_high_risk_users(count: int):
        """Set high-risk users count"""
        high_risk_users.set(count)

    @staticmethod
    def record_db_query(query_type: str, duration: float):
        """Record database query"""
        db_query_duration_seconds.labels(query_type=query_type).observe(duration)


# Global metrics collector
metrics_collector = MetricsCollector()
