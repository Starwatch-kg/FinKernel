"""
Audit logging for critical financial operations.
Logs are immutable and stored separately for compliance.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from shared.logger import setup_logger
from shared.redis import client as redis_client

logger = setup_logger("audit")


class AuditLogger:
    """
    Audit logger for financial operations.
    Logs critical events that must be retained for compliance.
    """

    @staticmethod
    async def log_transaction_created(
        user_id: int,
        transaction_id: int,
        amount: float,
        transaction_type: str,
        request_id: str,
        idempotency_key: Optional[str] = None,
    ):
        """Log transaction creation"""
        await AuditLogger._log_event(
            event_type="transaction.created",
            user_id=user_id,
            details={
                "transaction_id": transaction_id,
                "amount": amount,
                "type": transaction_type,
                "idempotency_key": idempotency_key,
            },
            request_id=request_id,
        )

    @staticmethod
    async def log_transaction_deleted(
        user_id: int,
        transaction_id: int,
        amount: float,
        transaction_type: str,
        request_id: str,
        balance_before: float,
        balance_after: float,
    ):
        """Log transaction deletion (critical for audit trail)"""
        await AuditLogger._log_event(
            event_type="transaction.deleted",
            user_id=user_id,
            details={
                "transaction_id": transaction_id,
                "amount": amount,
                "type": transaction_type,
                "balance_before": balance_before,
                "balance_after": balance_after,
            },
            request_id=request_id,
            severity="high",
        )

    @staticmethod
    async def log_trade_executed(
        user_id: int,
        ticker: str,
        action: str,
        shares: int,
        price: float,
        total_cost: float,
        request_id: str,
        idempotency_key: Optional[str] = None,
    ):
        """Log trade execution"""
        await AuditLogger._log_event(
            event_type="trade.executed",
            user_id=user_id,
            details={
                "ticker": ticker,
                "action": action,
                "shares": shares,
                "price": price,
                "total_cost": total_cost,
                "idempotency_key": idempotency_key,
            },
            request_id=request_id,
        )

    @staticmethod
    async def log_balance_change(
        user_id: int,
        balance_before: float,
        balance_after: float,
        reason: str,
        request_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log balance changes (critical for financial audit)"""
        await AuditLogger._log_event(
            event_type="balance.changed",
            user_id=user_id,
            details={
                "balance_before": balance_before,
                "balance_after": balance_after,
                "delta": balance_after - balance_before,
                "reason": reason,
                **(details or {}),
            },
            request_id=request_id,
            severity="high",
        )

    @staticmethod
    async def log_auth_failure(
        email: Optional[str],
        reason: str,
        request_id: str,
        ip_address: Optional[str] = None,
    ):
        """Log authentication failures (security monitoring)"""
        await AuditLogger._log_event(
            event_type="auth.failed",
            user_id=None,
            details={"email": email, "reason": reason, "ip_address": ip_address},
            request_id=request_id,
            severity="medium",
        )

    @staticmethod
    async def log_unauthorized_access(
        user_id: int,
        resource_type: str,
        resource_id: Any,
        request_id: str,
        attempted_action: str,
    ):
        """Log unauthorized access attempts (IDOR attempts)"""
        await AuditLogger._log_event(
            event_type="access.unauthorized",
            user_id=user_id,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "attempted_action": attempted_action,
            },
            request_id=request_id,
            severity="critical",
        )

    @staticmethod
    async def log_admin_action(
        admin_user_id: int,
        action: str,
        target_user_id: Optional[int],
        request_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Log admin actions for accountability"""
        await AuditLogger._log_event(
            event_type="admin.action",
            user_id=admin_user_id,
            details={
                "action": action,
                "target_user_id": target_user_id,
                **(details or {}),
            },
            request_id=request_id,
            severity="high",
        )

    @staticmethod
    async def _log_event(
        event_type: str,
        user_id: Optional[int],
        details: Dict[str, Any],
        request_id: str,
        severity: str = "info",
    ):
        """
        Internal method to log audit events.
        Logs to both application logger and Redis for persistence.
        """
        timestamp = datetime.utcnow().isoformat()

        audit_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "user_id": user_id,
            "request_id": request_id,
            "severity": severity,
            "details": details,
        }

        # Log to application logger
        log_message = f"[AUDIT] {event_type} | user={user_id} | request={request_id} | {json.dumps(details)}"

        if severity == "critical":
            logger.critical(log_message)
        elif severity == "high":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Store in Redis for short-term retention (30 days)
        try:
            audit_key = f"audit:{event_type}:{timestamp}:{request_id}"
            await redis_client.setex(
                audit_key, 2592000, json.dumps(audit_entry)  # 30 days in seconds
            )

            # Add to sorted set for querying by time
            await redis_client.zadd(
                f"audit:timeline:{event_type}",
                {audit_key: datetime.utcnow().timestamp()},
            )

            # Add to user-specific audit trail
            if user_id:
                await redis_client.zadd(
                    f"audit:user:{user_id}", {audit_key: datetime.utcnow().timestamp()}
                )

        except Exception as e:
            logger.error(f"Failed to store audit log in Redis: {e}")
            # Don't fail the operation if audit logging fails


# Singleton instance
audit_logger = AuditLogger()
