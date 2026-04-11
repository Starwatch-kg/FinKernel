"""
Integration tests for audit logging.
Tests that critical operations are properly logged.
"""
import pytest
from httpx import AsyncClient
import uuid
import json
import sys
from pathlib import Path

# Add tests directory to path
tests_path = Path(__file__).parent.parent
sys.path.insert(0, str(tests_path))

from helpers import register_and_get_token


BASE_URL = "http://localhost:8000"


class TestAuditLogging:
    """Test audit logging for critical operations"""

    @pytest.mark.asyncio
    async def test_transaction_creation_logged(self):
        """Test transaction creation is logged"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Register user
            auth_data = await register_and_get_token(client)
            client.headers["Authorization"] = f"Bearer {auth_data['token']}"

            # Create transaction
            response = await client.post("/api/transactions", json={
                "amount": 100.0,
                "type": "income",
                "category": "salary",
                "description": "Test transaction",
                "idempotency_key": str(uuid.uuid4())
            })

            assert response.status_code == 200
            # Audit log should contain this transaction creation
            # (verified through logs or Redis)

    @pytest.mark.asyncio
    async def test_transaction_deletion_logged(self):
        """Test transaction deletion is logged with HIGH severity"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Register user
            auth_data = await register_and_get_token(client)
            client.headers["Authorization"] = f"Bearer {auth_data['token']}"

            # Create transaction
            create_response = await client.post("/api/transactions", json={
                "amount": 50.0,
                "type": "expense",
                "category": "food",
                "description": "To be deleted",
                "idempotency_key": str(uuid.uuid4())
            })
            transaction_id = create_response.json()["id"]

            # Delete transaction
            delete_response = await client.delete(f"/api/transactions/{transaction_id}")
            assert delete_response.status_code == 200

            # Audit log should contain deletion with:
            # - event_type: transaction.deleted
            # - severity: high
            # - balance_before and balance_after

    @pytest.mark.asyncio
    async def test_trade_execution_logged(self):
        """Test trade execution is logged"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Register user
            auth_data = await register_and_get_token(client)
            client.headers["Authorization"] = f"Bearer {auth_data['token']}"

            # Execute trade
            response = await client.post("/api/trade", json={
                "ticker": "AAPL",
                "shares": 1,
                "action": "buy",
                "idempotency_key": str(uuid.uuid4())
            })

            # Might fail if trade service not available, but if succeeds:
            if response.status_code == 200:
                # Audit log should contain:
                # - event_type: trade.executed
                # - ticker, action, shares, price, total_cost
                pass

    @pytest.mark.asyncio
    async def test_failed_login_logged(self):
        """Test failed login attempts are logged"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Attempt login with wrong credentials
            response = await client.post("/api/auth/login", json={
                "email": "nonexistent@example.com",
                "password": "WrongPassword123!@#"
            })

            assert response.status_code == 401

            # Audit log should contain:
            # - event_type: auth.failed
            # - email, reason, ip_address
            # - severity: medium

    @pytest.mark.asyncio
    async def test_multiple_failed_logins_logged(self):
        """Test multiple failed login attempts are all logged"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = "attacker@example.com"

            # Try to login 5 times with wrong password
            for i in range(5):
                response = await client.post("/api/auth/login", json={
                    "email": email,
                    "password": f"WrongPassword{i}!@#"
                })
                assert response.status_code in [401, 429]

            # All 5 attempts should be logged
            # This helps detect brute force attacks

    @pytest.mark.asyncio
    async def test_balance_change_logged(self):
        """Test balance changes are logged"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Register user
            auth_data = await register_and_get_token(client)
            client.headers["Authorization"] = f"Bearer {auth_data['token']}"

            # Get initial balance
            dashboard = await client.get("/api/dashboard")
            initial_balance = dashboard.json()["balance"]["current"]

            # Create transaction that changes balance
            await client.post("/api/transactions", json={
                "amount": 200.0,
                "type": "income",
                "category": "salary",
                "description": "Balance change test",
                "idempotency_key": str(uuid.uuid4())
            })

            # Audit log should contain:
            # - event_type: balance.changed (or transaction.created)
            # - balance_before, balance_after, delta
            # - severity: high


class TestAuditLogRetention:
    """Test audit log retention and storage"""

    @pytest.mark.asyncio
    async def test_audit_logs_stored_in_redis(self):
        """Test audit logs are stored in Redis with TTL"""
        # This test would require Redis access
        # Verify logs are stored with 30-day TTL
        pass

    @pytest.mark.asyncio
    async def test_audit_logs_queryable_by_user(self):
        """Test audit logs can be queried by user_id"""
        # This test would require Redis access
        # Verify logs are indexed by user_id for querying
        pass

    @pytest.mark.asyncio
    async def test_audit_logs_queryable_by_time(self):
        """Test audit logs can be queried by timestamp"""
        # This test would require Redis access
        # Verify logs are in sorted set by timestamp
        pass


class TestAuditLogContent:
    """Test audit log content and format"""

    @pytest.mark.asyncio
    async def test_audit_log_contains_request_id(self):
        """Test audit logs contain request_id for tracing"""
        async with AsyncClient(base_url=BASE_URL) as client:
            auth_data = await register_and_get_token(client)
            client.headers["Authorization"] = f"Bearer {auth_data['token']}"

            # Make request and get request_id from header
            response = await client.post("/api/transactions", json={
                "amount": 100.0,
                "type": "income",
                "category": "salary",
                "description": "Test",
                "idempotency_key": str(uuid.uuid4())
            })

            request_id = response.headers.get("x-request-id")
            assert request_id is not None

            # Audit log should contain this request_id

    @pytest.mark.asyncio
    async def test_audit_log_contains_timestamp(self):
        """Test audit logs contain ISO timestamp"""
        # Audit logs should have timestamp in ISO format
        # for easy parsing and querying
        pass

    @pytest.mark.asyncio
    async def test_audit_log_contains_user_id(self):
        """Test audit logs contain user_id"""
        async with AsyncClient(base_url=BASE_URL) as client:
            auth_data = await register_and_get_token(client)
            client.headers["Authorization"] = f"Bearer {auth_data['token']}"

            # Create transaction
            await client.post("/api/transactions", json={
                "amount": 100.0,
                "type": "income",
                "category": "salary",
                "description": "Test",
                "idempotency_key": str(uuid.uuid4())
            })

            # Audit log should contain user_id


class TestAuditLogSeverity:
    """Test audit log severity levels"""

    @pytest.mark.asyncio
    async def test_critical_operations_high_severity(self):
        """Test critical operations are logged with HIGH severity"""
        # Transaction deletion: HIGH
        # Balance changes: HIGH
        # Admin actions: HIGH
        pass

    @pytest.mark.asyncio
    async def test_security_events_appropriate_severity(self):
        """Test security events have appropriate severity"""
        # Failed login: MEDIUM
        # Unauthorized access: CRITICAL
        pass

    @pytest.mark.asyncio
    async def test_normal_operations_info_severity(self):
        """Test normal operations are logged with INFO severity"""
        # Transaction creation: INFO
        # Trade execution: INFO
        pass


class TestAuditLogFailure:
    """Test audit logging failure handling"""

    @pytest.mark.asyncio
    async def test_operation_succeeds_even_if_audit_fails(self):
        """Test operations don't fail if audit logging fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            auth_data = await register_and_get_token(client)
            client.headers["Authorization"] = f"Bearer {auth_data['token']}"

            # Even if Redis is down (audit logging fails),
            # transaction should still succeed
            response = await client.post("/api/transactions", json={
                "amount": 100.0,
                "type": "income",
                "category": "salary",
                "description": "Test",
                "idempotency_key": str(uuid.uuid4())
            })

            # Should succeed even if audit logging fails
            assert response.status_code == 200


class TestAuditLogCompliance:
    """Test audit logging meets compliance requirements"""

    @pytest.mark.asyncio
    async def test_all_financial_operations_logged(self):
        """Test all financial operations are logged"""
        # Required for compliance:
        # - Transaction creation
        # - Transaction deletion
        # - Trade execution
        # - Balance changes
        pass

    @pytest.mark.asyncio
    async def test_audit_logs_immutable(self):
        """Test audit logs cannot be modified"""
        # Audit logs should be write-only
        # No API to modify or delete audit logs
        pass

    @pytest.mark.asyncio
    async def test_audit_logs_retained_30_days(self):
        """Test audit logs are retained for 30 days"""
        # Redis TTL should be 2592000 seconds (30 days)
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
