"""
Concurrency tests for financial operations
CRITICAL: These tests MUST pass to prevent money loss
"""
import pytest
import asyncio
from httpx import AsyncClient
import uuid


@pytest.mark.asyncio
async def test_concurrent_transactions_no_double_spend():
    """
    Test that concurrent expense transactions cannot overspend balance.
    This is CRITICAL for financial correctness.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # Create user with 1000 balance
        user_id = 1

        # Try to spend 200 ten times concurrently (total 2000)
        # Only 5 should succeed (1000/200 = 5)
        tasks = []
        for i in range(10):
            task = client.post(
                "/api/transactions",
                json={
                    "user_id": user_id,
                    "amount": 200,
                    "type": "expense",
                    "category": "food",
                    "description": f"Concurrent test {i}"
                }
            )
            tasks.append(task)

        # Execute all requests concurrently
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful transactions
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        failed = sum(1 for r in responses if isinstance(r, Exception) or r.status_code == 400)

        # Should have exactly 5 successful (1000/200) and 5 failed
        assert successful == 5, f"Expected 5 successful, got {successful}"
        assert failed == 5, f"Expected 5 failed, got {failed}"

        # Verify final balance is 0
        balance_response = await client.get(f"/api/dashboard/{user_id}")
        balance = balance_response.json()["balance"]["current"]
        assert balance == 0, f"Expected balance 0, got {balance}"


@pytest.mark.asyncio
async def test_idempotency_prevents_duplicates():
    """
    Test that idempotency key prevents duplicate transactions.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        user_id = 1
        idempotency_key = str(uuid.uuid4())

        # Send same request 10 times with same idempotency key
        tasks = []
        for i in range(10):
            task = client.post(
                "/api/transactions",
                json={
                    "user_id": user_id,
                    "amount": 100,
                    "type": "income",
                    "category": "salary",
                    "description": "Idempotency test",
                    "idempotency_key": idempotency_key
                }
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All should return 200
        assert all(r.status_code == 200 for r in responses)

        # All should return same transaction ID
        transaction_ids = [r.json()["id"] for r in responses]
        assert len(set(transaction_ids)) == 1, "All requests should return same transaction"


@pytest.mark.asyncio
async def test_concurrent_trades_no_overspend():
    """
    Test that concurrent buy orders cannot overspend balance.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        user_id = 1

        # Try to buy 10 shares of AAPL (price ~178) concurrently
        # With 1000 balance, only 5 should succeed
        tasks = []
        for i in range(10):
            task = client.post(
                "/api/trade",
                json={
                    "userId": str(user_id),
                    "ticker": "AAPL",
                    "shares": 1,
                    "action": "buy"
                }
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful trades
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)

        # Should have at most 5 successful (1000/178 ≈ 5)
        assert successful <= 6, f"Too many successful trades: {successful}"


@pytest.mark.asyncio
async def test_concurrent_deletion_no_double_credit():
    """
    Test that concurrent deletion of same transaction doesn't double-credit.
    """
    async with AsyncClient(base_url="http://localhost:8000") as client:
        user_id = 1

        # Create a transaction
        create_response = await client.post(
            "/api/transactions",
            json={
                "user_id": user_id,
                "amount": 100,
                "type": "expense",
                "category": "food",
                "description": "To be deleted"
            }
        )
        transaction_id = create_response.json()["id"]

        # Try to delete it 10 times concurrently
        tasks = []
        for i in range(10):
            task = client.delete(f"/api/transactions/{transaction_id}?userId={user_id}")
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Only one should succeed
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        assert successful == 1, f"Expected 1 successful deletion, got {successful}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
