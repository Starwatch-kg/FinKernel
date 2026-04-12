"""Health check system with degradation detection"""

import asyncio
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from shared.logger import setup_logger

logger = setup_logger("health_check")


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health status for a system component"""

    def __init__(self, name: str):
        self.name = name
        self.status = HealthStatus.HEALTHY
        self.last_check = datetime.utcnow()
        self.error_count = 0
        self.consecutive_failures = 0
        self.message: Optional[str] = None

    def mark_healthy(self, message: Optional[str] = None):
        """Mark component as healthy"""
        self.status = HealthStatus.HEALTHY
        self.error_count = 0
        self.consecutive_failures = 0
        self.message = message
        self.last_check = datetime.utcnow()

    def mark_degraded(self, message: str):
        """Mark component as degraded"""
        self.status = HealthStatus.DEGRADED
        self.message = message
        self.last_check = datetime.utcnow()
        logger.warning(f"Component {self.name} degraded: {message}")

    def mark_unhealthy(self, message: str):
        """Mark component as unhealthy"""
        self.status = HealthStatus.UNHEALTHY
        self.error_count += 1
        self.consecutive_failures += 1
        self.message = message
        self.last_check = datetime.utcnow()
        logger.error(f"Component {self.name} unhealthy: {message}")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "error_count": self.error_count,
            "consecutive_failures": self.consecutive_failures,
            "last_check": self.last_check.isoformat(),
        }


class HealthCheckSystem:
    """System-wide health monitoring"""

    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}

    def register_component(self, name: str) -> ComponentHealth:
        """Register a component for health monitoring"""
        if name not in self.components:
            self.components[name] = ComponentHealth(name)
        return self.components[name]

    def get_component(self, name: str) -> Optional[ComponentHealth]:
        """Get component health"""
        return self.components.get(name)

    def get_overall_status(self) -> HealthStatus:
        """Get overall system health"""
        if not self.components:
            return HealthStatus.HEALTHY

        statuses = [comp.status for comp in self.components.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def get_health_report(self) -> dict:
        """Get comprehensive health report"""
        overall = self.get_overall_status()

        return {
            "status": overall.value,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                name: comp.to_dict() for name, comp in self.components.items()
            },
        }

    async def check_database(self, db_session_factory) -> bool:
        """Check database health"""
        component = self.register_component("database")

        try:
            async with db_session_factory() as session:
                await session.execute("SELECT 1")
            component.mark_healthy("Database connection OK")
            return True
        except Exception as e:
            component.mark_unhealthy(f"Database error: {str(e)}")
            return False

    async def check_redis(self, redis_client) -> bool:
        """Check Redis health"""
        component = self.register_component("redis")

        try:
            await redis_client.ping()
            component.mark_healthy("Redis connection OK")
            return True
        except Exception as e:
            component.mark_degraded(f"Redis error: {str(e)}")
            return False

    async def check_service(self, name: str, health_url: str) -> bool:
        """Check external service health"""
        import httpx

        component = self.register_component(name)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    component.mark_healthy(f"{name} service OK")
                    return True
                else:
                    component.mark_degraded(f"{name} returned {response.status_code}")
                    return False
        except Exception as e:
            component.mark_unhealthy(f"{name} unreachable: {str(e)}")
            return False


# Global health check system
health_check_system = HealthCheckSystem()
