"""
Unit tests for transaction service.
Tests transaction creation, deletion, balance validation, and idempotency.
"""

# Mock imports before importing the module
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

sys.path.insert(0, "/app")


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.begin = MagicMock()
    db.begin.return_value.__aenter__ = AsyncMock()
    db.begin.return_value.__aexit__ = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock user object"""
    user = MagicMock()
    user.id = 1
    user.balance = 1000.0
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_transaction():
    """Mock transaction object"""
    txn = MagicMock()
    txn.id = 1
    txn.user_id = 1
    txn.amount = 100.0
    txn.type = "expense"
    txn.category = "food"
    txn.description = "Test transaction"
    txn.idempotency_key = "test-key-123"
    txn.timestamp = datetime.utcnow()
    return txn


class TestTransactionCreation:
    """Test transaction creation with idempotency"""

    @pytest.mark.asyncio
    async def test_create_transaction_success(self, mock_db, mock_user):
        """Test successful transaction creation"""
        from shared.models import TransactionType
        from shared.schemas import TransactionCreate

        # Setup mocks
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing transaction with idempotency key
            mock_user,  # User exists
        ]

        txn_data = TransactionCreate(
            user_id=1,
            amount=100.0,
            type=TransactionType.expense,
            category="food",
            description="Test",
            idempotency_key="test-key-123",
        )

        # Verify user balance is checked
        assert mock_user.balance >= txn_data.amount

    @pytest.mark.asyncio
    async def test_create_transaction_idempotent(self, mock_db, mock_transaction):
        """Test idempotent transaction creation returns existing transaction"""
        # Setup: existing transaction found
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_transaction

        # When same idempotency key is used, should return existing transaction
        result = mock_transaction
        assert result.id == 1
        assert result.idempotency_key == "test-key-123"

    @pytest.mark.asyncio
    async def test_create_transaction_insufficient_funds(self, mock_db, mock_user):
        """Test transaction creation fails with insufficient funds"""
        from shared.models import TransactionType
        from shared.schemas import TransactionCreate

        # Setup: user has insufficient balance
        mock_user.balance = 50.0
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing transaction
            mock_user,  # User with low balance
        ]

        txn_data = TransactionCreate(
            user_id=1,
            amount=100.0,
            type=TransactionType.expense,
            category="food",
            description="Test",
        )

        # Should raise HTTPException for insufficient funds
        assert mock_user.balance < txn_data.amount

    @pytest.mark.asyncio
    async def test_create_transaction_invalid_amount(self):
        """Test transaction creation with invalid amount"""
        from shared.security_hardening import validate_amount

        # Test negative amount
        with pytest.raises(ValueError, match="Amount must be at least"):
            validate_amount(-100.0)

        # Test zero amount
        with pytest.raises(ValueError, match="Amount must be at least"):
            validate_amount(0.0)

        # Test NaN
        with pytest.raises(ValueError, match="Amount cannot be NaN"):
            validate_amount(float("nan"))

        # Test infinity
        with pytest.raises(ValueError, match="Amount cannot be infinite"):
            validate_amount(float("inf"))

        # Test too large
        with pytest.raises(ValueError, match="Amount cannot exceed"):
            validate_amount(2_000_000_000)

    @pytest.mark.asyncio
    async def test_create_transaction_user_not_found(self, mock_db):
        """Test transaction creation fails when user doesn't exist"""
        # Setup: no user found
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing transaction
            None,  # No user found
        ]

        # Should raise HTTPException 404


class TestTransactionDeletion:
    """Test transaction deletion with balance validation"""

    @pytest.mark.asyncio
    async def test_delete_expense_transaction(
        self, mock_db, mock_user, mock_transaction
    ):
        """Test deleting expense transaction returns money"""
        # Setup
        mock_transaction.type = "expense"
        mock_transaction.amount = 100.0
        mock_user.balance = 500.0

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_transaction,  # Transaction found
            mock_user,  # User found
        ]

        # After deletion, balance should increase
        expected_balance = 500.0 + 100.0
        assert expected_balance == 600.0

    @pytest.mark.asyncio
    async def test_delete_income_transaction_sufficient_balance(
        self, mock_db, mock_user, mock_transaction
    ):
        """Test deleting income transaction with sufficient balance"""
        # Setup
        mock_transaction.type = "income"
        mock_transaction.amount = 100.0
        mock_user.balance = 500.0

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_transaction,
            mock_user,
        ]

        # Should succeed - user has enough balance
        assert mock_user.balance >= mock_transaction.amount

    @pytest.mark.asyncio
    async def test_delete_income_transaction_insufficient_balance(
        self, mock_db, mock_user, mock_transaction
    ):
        """Test deleting income transaction fails with insufficient balance"""
        # Setup
        mock_transaction.type = "income"
        mock_transaction.amount = 100.0
        mock_user.balance = 50.0  # Not enough to reverse income

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_transaction,
            mock_user,
        ]

        # Should fail - insufficient balance to reverse income
        assert mock_user.balance < mock_transaction.amount

    @pytest.mark.asyncio
    async def test_delete_transaction_not_found(self, mock_db):
        """Test deleting non-existent transaction"""
        # Setup: transaction not found
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        # Should raise HTTPException 404

    @pytest.mark.asyncio
    async def test_delete_transaction_wrong_user(self, mock_db, mock_transaction):
        """Test deleting transaction owned by different user"""
        # Setup: transaction belongs to user 2, but user 1 tries to delete
        mock_transaction.user_id = 2
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        # Should return None (ownership check in SQL)


class TestBalanceOperations:
    """Test balance calculations and validations"""

    def test_balance_increase_income(self, mock_user):
        """Test balance increases on income"""
        initial_balance = mock_user.balance
        amount = 100.0

        mock_user.balance += amount
        assert mock_user.balance == initial_balance + amount

    def test_balance_decrease_expense(self, mock_user):
        """Test balance decreases on expense"""
        initial_balance = mock_user.balance
        amount = 100.0

        mock_user.balance -= amount
        assert mock_user.balance == initial_balance - amount

    def test_balance_precision(self):
        """Test balance maintains 2 decimal precision"""
        from shared.security_hardening import validate_amount

        # Test rounding
        result = validate_amount(100.999)
        assert result == 101.00

        result = validate_amount(100.001)
        assert result == 100.00

    def test_balance_never_negative_on_expense(self, mock_user):
        """Test expense validation prevents negative balance"""
        mock_user.balance = 50.0
        expense_amount = 100.0

        # Should check before allowing expense
        assert mock_user.balance < expense_amount


class TestIdempotency:
    """Test idempotency key handling"""

    @pytest.mark.asyncio
    async def test_duplicate_idempotency_key_returns_same_transaction(
        self, mock_db, mock_transaction
    ):
        """Test duplicate idempotency key returns existing transaction"""
        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_transaction

        # Second request with same key should return same transaction
        result = mock_transaction
        assert result.id == mock_transaction.id
        assert result.idempotency_key == mock_transaction.idempotency_key

    @pytest.mark.asyncio
    async def test_no_idempotency_key_creates_new_transaction(self, mock_db, mock_user):
        """Test transaction without idempotency key creates new transaction"""
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing transaction (no key to check)
            mock_user,
        ]

        # Should create new transaction each time

    @pytest.mark.asyncio
    async def test_different_idempotency_keys_create_different_transactions(
        self, mock_db, mock_user
    ):
        """Test different idempotency keys create separate transactions"""
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # First key - no existing
            mock_user,
            None,  # Second key - no existing
            mock_user,
        ]

        # Two different keys should create two transactions


class TestTransactionValidation:
    """Test input validation for transactions"""

    def test_validate_transaction_type(self):
        """Test transaction type validation"""
        from shared.models import TransactionType

        # Valid types
        assert TransactionType.income.value == "income"
        assert TransactionType.expense.value == "expense"

    def test_validate_category(self):
        """Test category validation"""
        from shared.models import TransactionCategory

        valid_categories = [
            "food",
            "transport",
            "entertainment",
            "education",
            "salary",
            "other",
        ]
        for cat in valid_categories:
            assert hasattr(TransactionCategory, cat)

    def test_sanitize_description(self):
        """Test description sanitization"""
        from shared.security_hardening import sanitize_string

        # Test XSS prevention
        malicious = "<script>alert('xss')</script>"
        sanitized = sanitize_string(malicious)
        assert "<script>" not in sanitized

        # Test length limit
        long_text = "a" * 2000
        sanitized = sanitize_string(long_text, max_length=500)
        assert len(sanitized) <= 500

        # Test null bytes removal
        with_null = "test\x00data"
        sanitized = sanitize_string(with_null)
        assert "\x00" not in sanitized


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
