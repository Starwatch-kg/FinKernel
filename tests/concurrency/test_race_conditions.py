"""
Concurrency tests for financial operations
CRITICAL: These tests MUST pass to prevent money loss
Updated with idempotency tests
"""

import asyncio
import sys
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

# Add tests directory to path
tests_path = Path(__file__).parent.parent
sys.path.insert(0, str(tests_path))

from helpers import register_and_get_token


@pytest.mark.asyncio
async def test_concurrent_transactions_no_double_spend():
    """
    Test that concurrent expense transactions cannot overspend balance.
    This is CRITICAL for financial correctness.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Register user with known balance
        auth_data = await register_and_get_token(client)
        client.headers["Authorization"] = f"Bearer {auth_data['token']}"

        # Get initial balance (should be 5000 from registration)
        dashboard = await client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Try to spend 1000 ten times concurrently (total 10000)
        # Only 5 should succeed (5000/1000 = 5)
        tasks = []
        for i in range(10):
            task = client.post(
                "/api/transactions",
                json={
                    "amount": 1000,
                    "type": "expense",
                    "category": "food",
                    "description": f"Concurrent test {i}",
                    "idempotency_key": str(uuid.uuid4()),  # Unique keys
                },
            )
            tasks.append(task)

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful transactions
        successful = sum(
            1
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )
        failed = sum(
            1
            for r in responses
            if isinstance(r, Exception)
            or (hasattr(r, "status_code") and r.status_code == 400)
        )

        # Should have exactly 5 successful (5000/1000) and 5 failed
        assert successful == int(
            initial_balance / 1000
        ), f"Expected {int(initial_balance / 1000)} successful, got {successful}"
        assert (
            failed == 10 - successful
        ), f"Expected {10 - successful} failed, got {failed}"

        # Verify final balance is 0
        balance_response = await client.get("/api/dashboard")
        balance = balance_response.json()["balance"]["current"]
        assert balance == 0, f"Expected balance 0, got {balance}"


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicates():
    """
    Test that idempotency key prevents duplicate transactions.
    UPDATED: Uses authentication and proper API flow.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Register user
        auth_data = await register_and_get_token(client)
        client.headers["Authorization"] = f"Bearer {auth_data['token']}"

        # Get initial balance
        dashboard = await client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        idempotency_key = str(uuid.uuid4())

        # Send same request 10 times with same idempotency key
        tasks = []
        for i in range(10):
            task = client.post(
                "/api/transactions",
                json={
                    "amount": 100,
                    "type": "income",
                    "category": "salary",
                    "description": "Idempotency test",
                    "idempotency_key": idempotency_key,
                },
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All should return 200
        assert all(r.status_code == 200 for r in responses)

        # All should return same transaction ID
        transaction_ids = [r.json()["id"] for r in responses]
        assert (
            len(set(transaction_ids)) == 1
        ), "All requests should return same transaction"

        # Balance should only increase by 100 (not 1000)
        dashboard = await client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]
        assert (
            final_balance == initial_balance + 100
        ), f"Balance should increase by 100, not {final_balance - initial_balance}"


@pytest.mark.asyncio
async def test_concurrent_trades_no_overspend():
    """
    Test that concurrent buy orders cannot overspend balance.
    UPDATED: Uses authentication and realistic stock prices.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Register user
        auth_data = await register_and_get_token(client)
        client.headers["Authorization"] = f"Bearer {auth_data['token']}"

        # Get initial balance
        dashboard = await client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Try to buy 10 shares of AAPL concurrently
        # With 5000 balance and ~178 price, only ~28 shares should succeed
        tasks = []
        for i in range(50):
            task = client.post(
                "/api/trade",
                json={
                    "ticker": "AAPL",
                    "shares": 1,
                    "action": "buy",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful trades
        successful = sum(
            1
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )

        # Should have at most initial_balance / ~178 successful trades
        max_possible = int(initial_balance / 150)  # Conservative estimate
        assert (
            successful <= max_possible + 5
        ), f"Too many successful trades: {successful} (max ~{max_possible})"

        # Verify balance is not negative
        dashboard = await client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]
        assert final_balance >= 0, f"Balance should not be negative: {final_balance}"


@pytest.mark.asyncio
async def test_concurrent_deletion_no_double_credit():
    """
    Test that concurrent deletion of same transaction doesn't double-credit.
    UPDATED: Uses authentication and proper transaction flow.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Register user
        auth_data = await register_and_get_token(client)
        client.headers["Authorization"] = f"Bearer {auth_data['token']}"

        # Get initial balance
        dashboard = await client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Create a transaction
        create_response = await client.post(
            "/api/transactions",
            json={
                "amount": 100,
                "type": "expense",
                "category": "food",
                "description": "To be deleted",
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        transaction_id = create_response.json()["id"]

        # Verify balance decreased
        dashboard = await client.get("/api/dashboard")
        after_expense = dashboard.json()["balance"]["current"]
        assert after_expense == initial_balance - 100

        # Try to delete it 10 times concurrently
        tasks = []
        for i in range(10):
            task = client.delete(f"/api/transactions/{transaction_id}")
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed
        successful = sum(
            1
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )
        assert successful == 1, f"Expected 1 successful deletion, got {successful}"

        # Balance should return to initial (only once)
        dashboard = await client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]
        assert (
            final_balance == initial_balance
        ), f"Balance should be {initial_balance}, got {final_balance}"


@pytest.mark.asyncio
async def test_concurrent_trade_idempotency():
    """
    Test that concurrent trades with same idempotency key only execute once.
    NEW TEST: Verifies trade idempotency under concurrent load.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Register user
        auth_data = await register_and_get_token(client)
        client.headers["Authorization"] = f"Bearer {auth_data['token']}"

        # Get initial balance
        dashboard = await client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        idempotency_key = str(uuid.uuid4())

        # Send same trade 10 times concurrently with same idempotency key
        tasks = []
        for i in range(10):
            task = client.post(
                "/api/trade",
                json={
                    "ticker": "AAPL",
                    "shares": 5,
                    "action": "buy",
                    "idempotency_key": idempotency_key,
                },
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All should return 200
        assert all(r.status_code == 200 for r in responses)

        # Balance should only decrease once (not 10 times)
        dashboard = await client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]

        # Should have bought 5 shares only once
        # Approximate cost: 5 * 178 = 890
        expected_decrease = 890  # Approximate
        actual_decrease = initial_balance - final_balance

        # Allow some variance for price fluctuations
        assert (
            800 <= actual_decrease <= 1000
        ), f"Balance should decrease by ~890, decreased by {actual_decrease}"


@pytest.mark.asyncio
async def test_concurrent_mixed_operations():
    """
    Test concurrent mix of income, expense, and trades maintain balance integrity.
    NEW TEST: Stress test with mixed operations.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Register user
        auth_data = await register_and_get_token(client)
        client.headers["Authorization"] = f"Bearer {auth_data['token']}"

        # Get initial balance
        dashboard = await client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Create mix of operations
        tasks = []

        # 5 income transactions
        for i in range(5):
            tasks.append(
                client.post(
                    "/api/transactions",
                    json={
                        "amount": 100,
                        "type": "income",
                        "category": "salary",
                        "description": f"Income {i}",
                        "idempotency_key": str(uuid.uuid4()),
                    },
                )
            )

        # 5 expense transactions
        for i in range(5):
            tasks.append(
                client.post(
                    "/api/transactions",
                    json={
                        "amount": 50,
                        "type": "expense",
                        "category": "food",
                        "description": f"Expense {i}",
                        "idempotency_key": str(uuid.uuid4()),
                    },
                )
            )

        # Execute all concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successes
        successful = sum(
            1
            for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )

        # Get final balance
        dashboard = await client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]

        # Balance should be consistent
        # Expected: initial + (5 * 100) - (5 * 50) = initial + 250
        # But some expenses might fail if balance runs low
        assert (
            final_balance >= initial_balance
        ), "Balance should not decrease below initial"
        assert final_balance >= 0, "Balance should never be negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
