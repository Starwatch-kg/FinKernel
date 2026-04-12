"""Alerting System with webhook and log integration"""

import asyncio
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from redis.asyncio import Redis
from shared.logger import setup_logger

logger = setup_logger("alerting")


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    WEBHOOK = "webhook"
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"


class Alert:
    """Alert model"""

    def __init__(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = f"alert_{int(datetime.utcnow().timestamp() * 1000)}"
        self.title = title
        self.message = message
        self.severity = severity
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class AlertingSystem:
    """Centralized alerting with deduplication and rate limiting"""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.webhook_url = None
        self.channels: List[AlertChannel] = [AlertChannel.LOG]
        self.alert_queue = asyncio.Queue(maxsize=1000)
        self.dedup_window = 300  # 5 minutes

    def configure(
        self,
        webhook_url: Optional[str] = None,
        channels: Optional[List[AlertChannel]] = None,
    ):
        """Configure alerting channels"""
        if webhook_url:
            self.webhook_url = webhook_url
            if AlertChannel.WEBHOOK not in self.channels:
                self.channels.append(AlertChannel.WEBHOOK)

        if channels:
            self.channels = channels

        logger.info(
            f"Alerting configured with channels: {[c.value for c in self.channels]}"
        )

    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Send alert with deduplication"""
        alert = Alert(title, message, severity, source, metadata)

        # Check deduplication
        dedup_key = f"alert_dedup:{source}:{title}"
        if await self.redis.exists(dedup_key):
            logger.debug(f"Alert deduplicated: {title}")
            return

        # Set dedup marker
        await self.redis.setex(dedup_key, self.dedup_window, "1")

        # Queue alert
        try:
            self.alert_queue.put_nowait(alert)
        except asyncio.QueueFull:
            logger.error("Alert queue full, dropping alert")

    async def process_alerts(self):
        """Background worker to process alerts"""
        logger.info("Alert processor started")

        while True:
            try:
                alert = await self.alert_queue.get()
                await self._dispatch_alert(alert)
                self.alert_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing alert: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def _dispatch_alert(self, alert: Alert):
        """Dispatch alert to configured channels"""
        for channel in self.channels:
            try:
                if channel == AlertChannel.LOG:
                    await self._send_to_log(alert)
                elif channel == AlertChannel.WEBHOOK:
                    await self._send_to_webhook(alert)
                elif channel == AlertChannel.SLACK:
                    await self._send_to_slack(alert)
            except Exception as e:
                logger.error(f"Failed to send alert to {channel.value}: {e}")

    async def _send_to_log(self, alert: Alert):
        """Log alert"""
        log_func = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(alert.severity, logger.info)

        log_func(
            f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.message} | {alert.metadata}"
        )

    async def _send_to_webhook(self, alert: Alert):
        """Send alert to webhook"""
        if not self.webhook_url:
            return

        payload = alert.to_dict()

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                logger.debug(f"Alert sent to webhook: {alert.id}")
        except Exception as e:
            logger.error(f"Webhook delivery failed: {e}")

    async def _send_to_slack(self, alert: Alert):
        """Send alert to Slack (mock)"""
        # Mock implementation - in production, use Slack webhook
        logger.info(f"[SLACK] {alert.title}: {alert.message}")


class AlertRules:
    """Pre-configured alert rules"""

    def __init__(self, alerting: AlertingSystem, redis: Redis):
        self.alerting = alerting
        self.redis = redis

    async def check_failed_logins(
        self, user_id: Optional[int] = None, email: Optional[str] = None
    ):
        """Alert on multiple failed login attempts"""
        key = f"failed_logins:{email or user_id}"
        count = await self.redis.get(key)

        if count and int(count) >= 5:
            await self.alerting.send_alert(
                title="Multiple Failed Login Attempts",
                message=f"User {email or user_id} has {count} failed login attempts",
                severity=AlertSeverity.WARNING,
                source="auth",
                metadata={"user_id": user_id, "email": email, "attempts": int(count)},
            )

    async def check_anomaly_detection(
        self, user_id: int, anomaly_type: str, details: dict
    ):
        """Alert on anomaly detection"""
        await self.alerting.send_alert(
            title=f"Anomaly Detected: {anomaly_type}",
            message=f"User {user_id} triggered anomaly detection",
            severity=AlertSeverity.WARNING,
            source="anti_abuse",
            metadata={"user_id": user_id, "type": anomaly_type, "details": details},
        )

    async def check_error_rate(
        self, service: str, error_count: int, total_requests: int
    ):
        """Alert on high error rate"""
        if total_requests == 0:
            return

        error_rate = error_count / total_requests

        if error_rate > 0.05:  # 5% error rate
            severity = (
                AlertSeverity.CRITICAL if error_rate > 0.1 else AlertSeverity.ERROR
            )

            await self.alerting.send_alert(
                title=f"High Error Rate: {service}",
                message=f"Error rate: {error_rate:.2%} ({error_count}/{total_requests})",
                severity=severity,
                source=service,
                metadata={
                    "error_count": error_count,
                    "total_requests": total_requests,
                    "error_rate": error_rate,
                },
            )

    async def check_ai_failure_rate(self, failure_count: int, total_predictions: int):
        """Alert on AI service failures"""
        if total_predictions == 0:
            return

        failure_rate = failure_count / total_predictions

        if failure_rate > 0.2:  # 20% failure rate
            await self.alerting.send_alert(
                title="High AI Failure Rate",
                message=f"AI service failure rate: {failure_rate:.2%}",
                severity=AlertSeverity.ERROR,
                source="ai_service",
                metadata={
                    "failure_count": failure_count,
                    "total_predictions": total_predictions,
                },
            )

    async def check_service_health(self, service: str, is_healthy: bool):
        """Alert on service health issues"""
        if not is_healthy:
            await self.alerting.send_alert(
                title=f"Service Unhealthy: {service}",
                message=f"{service} health check failed",
                severity=AlertSeverity.CRITICAL,
                source=service,
                metadata={"service": service},
            )

    async def check_database_connection(self, is_connected: bool):
        """Alert on database connection issues"""
        if not is_connected:
            await self.alerting.send_alert(
                title="Database Connection Lost",
                message="Unable to connect to database",
                severity=AlertSeverity.CRITICAL,
                source="database",
                metadata={},
            )

    async def check_redis_connection(self, is_connected: bool):
        """Alert on Redis connection issues"""
        if not is_connected:
            await self.alerting.send_alert(
                title="Redis Connection Lost",
                message="Unable to connect to Redis",
                severity=AlertSeverity.ERROR,
                source="redis",
                metadata={},
            )


# Global alerting instance
alerting_system = AlertingSystem(None)  # Redis will be injected at startup
