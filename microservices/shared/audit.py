"""Enterprise Audit Logging System"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, Optional

from shared.logger import setup_logger
from sqlalchemy import JSON, Column, DateTime, Index, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base

logger = setup_logger("audit")

Base = declarative_base()


class AuditLog(Base):
    """Audit log table for compliance"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=True)
    action = Column(String, index=True)
    resource = Column(String, index=True)
    resource_id = Column(String, nullable=True)
    status = Column(String, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    request_id = Column(String, index=True, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_user_action_time", "user_id", "action", "timestamp"),
        Index("idx_resource_time", "resource", "timestamp"),
    )


class AuditLogger:
    """Async audit logger for fintech compliance"""

    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10000)
        self.worker_task = None

    async def log(
        self,
        action: str,
        resource: str,
        status: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Queue audit log entry (non-blocking)"""
        entry = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "resource_id": resource_id,
            "status": status,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            self.queue.put_nowait(entry)
        except asyncio.QueueFull:
            logger.error("Audit queue full - dropping log entry")

    async def log_auth(
        self,
        action: str,
        status: str,
        user_id: Optional[int] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        reason: Optional[str] = None,
    ):
        """Log authentication events"""
        await self.log(
            action=action,
            resource="auth",
            status=status,
            user_id=user_id,
            ip_address=ip_address,
            request_id=request_id,
            details={"email": email, "reason": reason},
        )

    async def log_data_access(
        self,
        user_id: int,
        resource: str,
        resource_id: str,
        action: str,
        status: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Log data access events"""
        await self.log(
            action=action,
            resource=resource,
            resource_id=resource_id,
            status=status,
            user_id=user_id,
            ip_address=ip_address,
            request_id=request_id,
        )

    async def log_trade(
        self,
        user_id: int,
        action: str,
        ticker: str,
        shares: int,
        price: float,
        status: str,
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        """Log trading activity"""
        await self.log(
            action=action,
            resource="trade",
            resource_id=ticker,
            status=status,
            user_id=user_id,
            ip_address=ip_address,
            request_id=request_id,
            details={
                "ticker": ticker,
                "shares": shares,
                "price": price,
                "total_value": shares * price,
            },
        )

    async def log_admin_action(
        self,
        admin_id: int,
        action: str,
        target_user_id: Optional[int] = None,
        status: str = "success",
        ip_address: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        """Log admin actions"""
        await self.log(
            action=action,
            resource="admin",
            status=status,
            user_id=admin_id,
            resource_id=str(target_user_id) if target_user_id else None,
            ip_address=ip_address,
            request_id=request_id,
            details=details,
        )

    async def start_worker(self, db_session_factory):
        """Start background worker to persist logs"""
        logger.info("Starting audit log worker")

        while True:
            try:
                entry = await self.queue.get()

                async with db_session_factory() as session:
                    audit_log = AuditLog(**entry)
                    session.add(audit_log)
                    await session.commit()

                self.queue.task_done()

            except Exception as e:
                logger.error(f"Error persisting audit log: {e}", exc_info=True)
                await asyncio.sleep(1)


# Global audit logger instance
audit_logger = AuditLogger()


async def get_client_ip(request) -> str:
    """Extract client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_request_id(request) -> Optional[str]:
    """Extract request ID from request state"""
    return getattr(request.state, "request_id", None)
