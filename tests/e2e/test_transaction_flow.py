"""
End-to-end tests for transaction flow.
Tests complete transaction lifecycle through API gateway.
"""
import pytest
import asyncio
from httpx import AsyncClient
import uuid
from datetime import datetime
import sys
from pathlib import Path

# Add tests directory to path
tests_path = Path(__file__).parent.parent
sys.path.insert(0, str(tests_path))

from helpers import register_and_get_token


BASE_URL = "http://localhost:8000"


class TestTransactionE2E:
    """End-to-end transaction tests"""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_transaction(self, auth_client):
        """Test creating transaction and retrieving it"""
        # Create income transaction
        create_response = await auth_client.post("/api/transactions", json={
            "amount": 1000.0,
            "type": "income",
            "category": "salary",
            "description": "Monthly salary"
        })

        assert create_response.status_code == 200
        created = create_response.json()
        assert created["amount"] == 1000.0
        assert created["type"] == "income"
        assert "id" in created

        # Retrieve transactions
        list_response = await auth_client.get("/api/transactions?limit=10")
        assert list_response.status_code == 200

        transactions = list_response.json()
        assert len(transactions) > 0
        assert any(t["id"] == created["id"] for t in transactions)

    @pytest.mark.asyncio
    async def test_transaction_affects_balance(self, auth_client):
        """Test transaction updates balance correctly"""
        # Get initial balance
        dashboard = await auth_client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Create income transaction
        await auth_client.post("/api/transactions", json={
            "amount": 500.0,
            "type": "income",
            "category": "salary",
            "description": "Bonus"
        })

        # Check balance increased
        dashboard = await auth_client.get("/api/dashboard")
        new_balance = dashboard.json()["balance"]["current"]
        assert new_balance == initial_balance + 500.0

        # Create expense transaction
        await auth_client.post("/api/transactions", json={
            "amount": 200.0,
            "type": "expense",
            "category": "food",
            "description": "Groceries"
        })

        # Check balance decreased
        dashboard = await auth_client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]
        assert final_balance == new_balance - 200.0

    @pytest.mark.asyncio
    async def test_delete_transaction_reverses_balance(self, auth_client):
        """Test deleting transaction reverses balance change"""
        # Get initial balance
        dashboard = await auth_client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Create expense
        create_response = await auth_client.post("/api/transactions", json={
            "amount": 100.0,
            "type": "expense",
            "category": "food",
            "description": "Test expense"
        })
        transaction_id = create_response.json()["id"]

        # Balance should decrease
        dashboard = await auth_client.get("/api/dashboard")
        after_expense = dashboard.json()["balance"]["current"]
        assert after_expense == initial_balance - 100.0

        # Delete transaction
        delete_response = await auth_client.delete(f"/api/transactions/{transaction_id}")
        assert delete_response.status_code == 200

        # Balance should return to initial
        dashboard = await auth_client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]
        assert final_balance == initial_balance

    @pytest.mark.asyncio
    async def test_insufficient_funds_rejected(self, auth_client):
        """Test expense exceeding balance is rejected"""
        # Get current balance
        dashboard = await auth_client.get("/api/dashboard")
        balance = dashboard.json()["balance"]["current"]

        # Try to spend more than balance
        response = await auth_client.post("/api/transactions", json={
            "amount": balance + 1000.0,
            "type": "expense",
            "category": "food",
            "description": "Too expensive"
        })

        assert response.status_code == 400
        assert "insufficient" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_transaction_idempotency(self, auth_client):
        """Test idempotency prevents duplicate transactions"""
        idempotency_key = str(uuid.uuid4())

        # Get initial balance
        dashboard = await auth_client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Send same request twice with same idempotency key
        response1 = await auth_client.post("/api/transactions", json={
            "amount": 100.0,
            "type": "income",
            "category": "salary",
            "description": "Test income",
            "idempotency_key": idempotency_key
        })

        response2 = await auth_client.post("/api/transactions", json={
            "amount": 100.0,
            "type": "income",
            "category": "salary",
            "description": "Test income",
            "idempotency_key": idempotency_key
        })

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Should return same transaction ID
        assert response1.json()["id"] == response2.json()["id"]

        # Balance should only increase once
        dashboard = await auth_client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]
        assert final_balance == initial_balance + 100.0

    @pytest.mark.asyncio
    async def test_concurrent_transactions_no_race_condition(self, auth_client):
        """Test concurrent transactions maintain balance integrity"""
        # Get initial balance
        dashboard = await auth_client.get("/api/dashboard")
        initial_balance = dashboard.json()["balance"]["current"]

        # Create 10 concurrent income transactions
        tasks = []
        for i in range(10):
            task = auth_client.post("/api/transactions", json={
                "amount": 10.0,
                "type": "income",
                "category": "salary",
                "description": f"Concurrent income {i}",
                "idempotency_key": str(uuid.uuid4())
            })
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # Balance should increase by exactly 100
        dashboard = await auth_client.get("/api/dashboard")
        final_balance = dashboard.json()["balance"]["current"]
        assert final_balance == initial_balance + 100.0

    @pytest.mark.asyncio
    async def test_transaction_validation(self, auth_client):
        """Test transaction input validation"""
        # Negative amount
        response = await auth_client.post("/api/transactions", json={
            "amount": -100.0,
            "type": "income",
            "category": "salary",
            "description": "Invalid"
        })
        assert response.status_code == 422

        # Zero amount
        response = await auth_client.post("/api/transactions", json={
            "amount": 0.0,
            "type": "income",
            "category": "salary",
            "description": "Invalid"
        })
        assert response.status_code == 422

        # Invalid type
        response = await auth_client.post("/api/transactions", json={
            "amount": 100.0,
            "type": "invalid",
            "category": "salary",
            "description": "Invalid"
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_dashboard_aggregates_correctly(self, auth_client):
        """Test dashboard shows correct aggregated data"""
        # Create multiple transactions
        await auth_client.post("/api/transactions", json={
            "amount": 1000.0,
            "type": "income",
            "category": "salary",
            "description": "Salary"
        })

        await auth_client.post("/api/transactions", json={
            "amount": 200.0,
            "type": "expense",
            "category": "food",
            "description": "Groceries"
        })

        await auth_client.post("/api/transactions", json={
            "amount": 150.0,
            "type": "expense",
            "category": "transport",
            "description": "Gas"
        })

        # Get dashboard
        dashboard = await auth_client.get("/api/dashboard")
        data = dashboard.json()

        # Verify aggregations
        assert "balance" in data
        assert "income" in data
        assert "expenses" in data
        assert "transactions" in data
        assert "spending_chart" in data

        # Verify spending chart has categories
        spending_chart = data["spending_chart"]
        categories = [item["category"] for item in spending_chart]
        assert "Еда" in categories or "food" in str(spending_chart).lower()
        assert "Транспорт" in categories or "transport" in str(spending_chart).lower()


class TestTransactionPagination:
    """Test transaction list pagination"""

    @pytest.mark.asyncio
    async def test_transaction_limit(self, auth_client):
        """Test transaction list respects limit parameter"""
        # Create 20 transactions
        for i in range(20):
            await auth_client.post("/api/transactions", json={
                "amount": 10.0,
                "type": "income",
                "category": "salary",
                "description": f"Transaction {i}",
                "idempotency_key": str(uuid.uuid4())
            })

        # Request with limit
        response = await auth_client.get("/api/transactions?limit=5")
        transactions = response.json()

        assert len(transactions) <= 5

    @pytest.mark.asyncio
    async def test_transaction_max_limit(self, auth_client):
        """Test transaction list enforces max limit"""
        # Request with very high limit
        response = await auth_client.get("/api/transactions?limit=1000")
        transactions = response.json()

        # Should be capped at 100
        assert len(transactions) <= 100


class TestTransactionSecurity:
    """Test transaction security"""

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self):
        """Test unauthenticated requests are rejected"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.post("/api/transactions", json={
                "amount": 100.0,
                "type": "income",
                "category": "salary",
                "description": "Test"
            })

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cannot_access_other_user_transactions(self):
        """Test users cannot access other users' transactions"""
        # Create two users
        async with AsyncClient(base_url=BASE_URL) as client:
            # User 1
            auth_data1 = await register_and_get_token(client)
            token1 = auth_data1['token']

            # User 2
            auth_data2 = await register_and_get_token(client)
            token2 = auth_data2['token']

            # User 1 creates transaction
            client.headers["Authorization"] = f"Bearer {token1}"
            await client.post("/api/transactions", json={
                "amount": 100.0,
                "type": "income",
                "category": "salary",
                "description": "User 1 transaction"
            })

            # User 2 should only see their own transactions
            client.headers["Authorization"] = f"Bearer {token2}"
            response = await client.get("/api/transactions")
            transactions = response.json()

            # User 2 should have no transactions (or only their own)
            assert all(t["description"] != "User 1 transaction" for t in transactions)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
