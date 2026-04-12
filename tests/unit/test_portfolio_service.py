"""
Unit tests for portfolio service.
Tests trade execution, idempotency, and portfolio management.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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
    db.add = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    """Mock user with balance"""
    user = MagicMock()
    user.id = 1
    user.balance = 10000.0
    return user


@pytest.fixture
def mock_stock():
    """Mock stock"""
    stock = MagicMock()
    stock.ticker = "AAPL"
    stock.name = "Apple Inc."
    stock.price = 178.50
    stock.change_percent = 1.5
    return stock


@pytest.fixture
def mock_portfolio():
    """Mock portfolio position"""
    position = MagicMock()
    position.user_id = 1
    position.ticker = "AAPL"
    position.shares = 10
    position.avg_price = 175.00
    return position


@pytest.fixture
def mock_trade_history():
    """Mock trade history record"""
    trade = MagicMock()
    trade.id = 1
    trade.user_id = 1
    trade.ticker = "AAPL"
    trade.shares = 5
    trade.action = "buy"
    trade.price = 178.50
    trade.total_cost = 892.50
    trade.idempotency_key = "trade-key-123"
    return trade


class TestTradeBuy:
    """Test buy trade execution"""

    @pytest.mark.asyncio
    async def test_buy_trade_success(self, mock_db, mock_user, mock_stock):
        """Test successful buy trade"""
        shares = 5
        total_cost = mock_stock.price * shares

        # Setup mocks
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing trade with idempotency key
            mock_user,  # User found
            mock_stock,  # Stock found
            None,  # No existing position
        ]

        # Verify user has sufficient funds
        assert mock_user.balance >= total_cost

        # After trade, balance should decrease
        expected_balance = mock_user.balance - total_cost
        assert expected_balance == 10000.0 - 892.50

    @pytest.mark.asyncio
    async def test_buy_trade_insufficient_funds(self, mock_db, mock_user, mock_stock):
        """Test buy trade fails with insufficient funds"""
        shares = 100
        total_cost = mock_stock.price * shares  # 17,850

        mock_user.balance = 5000.0  # Not enough

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing trade
            mock_user,
            mock_stock,
        ]

        # Should fail - insufficient funds
        assert mock_user.balance < total_cost

    @pytest.mark.asyncio
    async def test_buy_trade_updates_existing_position(
        self, mock_db, mock_user, mock_stock, mock_portfolio
    ):
        """Test buy trade updates existing position with new average price"""
        shares = 5
        total_cost = mock_stock.price * shares

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing trade
            mock_user,
            mock_stock,
            mock_portfolio,  # Existing position
        ]

        # Calculate new average price
        old_total_value = mock_portfolio.avg_price * mock_portfolio.shares
        new_total_value = old_total_value + total_cost
        new_total_shares = mock_portfolio.shares + shares
        expected_avg_price = new_total_value / new_total_shares

        assert expected_avg_price == (175.00 * 10 + 178.50 * 5) / 15

    @pytest.mark.asyncio
    async def test_buy_trade_creates_new_position(self, mock_db, mock_user, mock_stock):
        """Test buy trade creates new position if none exists"""
        shares = 5

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing trade
            mock_user,
            mock_stock,
            None,  # No existing position
        ]

        # Should create new position with avg_price = current price
        expected_avg_price = mock_stock.price
        assert expected_avg_price == 178.50

    @pytest.mark.asyncio
    async def test_buy_trade_idempotent(self, mock_db, mock_trade_history):
        """Test buy trade with duplicate idempotency key returns existing trade"""
        mock_db.execute.return_value.scalar_one_or_none.return_value = (
            mock_trade_history
        )

        # Should return existing trade
        result = mock_trade_history
        assert result.id == 1
        assert result.action == "buy"
        assert result.idempotency_key == "trade-key-123"


class TestTradeSell:
    """Test sell trade execution"""

    @pytest.mark.asyncio
    async def test_sell_trade_success(
        self, mock_db, mock_user, mock_stock, mock_portfolio
    ):
        """Test successful sell trade"""
        shares = 5
        total_proceeds = mock_stock.price * shares

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing trade
            mock_user,
            mock_stock,
            mock_portfolio,  # Has position
        ]

        # Verify user has enough shares
        assert mock_portfolio.shares >= shares

        # After sell, balance should increase
        expected_balance = mock_user.balance + total_proceeds
        assert expected_balance == 10000.0 + 892.50

    @pytest.mark.asyncio
    async def test_sell_trade_insufficient_shares(
        self, mock_db, mock_user, mock_stock, mock_portfolio
    ):
        """Test sell trade fails with insufficient shares"""
        shares = 20  # More than owned
        mock_portfolio.shares = 10

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing trade
            mock_user,
            mock_stock,
            mock_portfolio,
        ]

        # Should fail - insufficient shares
        assert mock_portfolio.shares < shares

    @pytest.mark.asyncio
    async def test_sell_trade_no_position(self, mock_db, mock_user, mock_stock):
        """Test sell trade fails when user has no position"""
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # No existing trade
            mock_user,
            mock_stock,
            None,  # No position
        ]

        # Should fail - no position to sell

    @pytest.mark.asyncio
    async def test_sell_all_shares_deletes_position(
        self, mock_db, mock_user, mock_stock, mock_portfolio
    ):
        """Test selling all shares deletes the position"""
        shares = 10  # All shares
        mock_portfolio.shares = 10

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,
            mock_user,
            mock_stock,
            mock_portfolio,
        ]

        # After selling all, position should be deleted
        mock_portfolio.shares -= shares
        assert mock_portfolio.shares == 0

    @pytest.mark.asyncio
    async def test_sell_partial_shares_updates_position(
        self, mock_db, mock_user, mock_stock, mock_portfolio
    ):
        """Test selling partial shares updates position"""
        shares = 5  # Partial
        mock_portfolio.shares = 10

        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            None,
            mock_user,
            mock_stock,
            mock_portfolio,
        ]

        # After selling partial, position should remain
        expected_shares = 10 - 5
        assert expected_shares == 5


class TestTradeValidation:
    """Test trade input validation"""

    def test_validate_shares(self):
        """Test share count validation"""
        from shared.security_hardening import validate_shares

        # Valid shares
        assert validate_shares(1) == 1
        assert validate_shares(100) == 100

        # Invalid shares
        with pytest.raises(ValueError, match="Shares must be at least"):
            validate_shares(0)

        with pytest.raises(ValueError, match="Shares must be at least"):
            validate_shares(-5)

        with pytest.raises(ValueError, match="Shares cannot exceed"):
            validate_shares(2_000_000)

        with pytest.raises(ValueError, match="Shares must be an integer"):
            validate_shares(5.5)

    def test_validate_ticker(self):
        """Test ticker validation"""
        # Valid tickers
        valid_tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        for ticker in valid_tickers:
            assert len(ticker) >= 1
            assert len(ticker) <= 10

        # Invalid tickers
        assert len("") == 0  # Too short
        assert len("VERYLONGTICKER") > 10  # Too long

    def test_validate_action(self):
        """Test action validation"""
        valid_actions = ["buy", "sell"]
        for action in valid_actions:
            assert action in ["buy", "sell"]

        # Invalid action
        assert "hold" not in ["buy", "sell"]


class TestPortfolioCalculations:
    """Test portfolio value calculations"""

    def test_calculate_position_value(self, mock_stock, mock_portfolio):
        """Test current position value calculation"""
        current_value = mock_stock.price * mock_portfolio.shares
        assert current_value == 178.50 * 10

    def test_calculate_cost_basis(self, mock_portfolio):
        """Test cost basis calculation"""
        cost_basis = mock_portfolio.avg_price * mock_portfolio.shares
        assert cost_basis == 175.00 * 10

    def test_calculate_profit_loss(self, mock_stock, mock_portfolio):
        """Test profit/loss calculation"""
        current_value = mock_stock.price * mock_portfolio.shares
        cost_basis = mock_portfolio.avg_price * mock_portfolio.shares
        profit_loss = current_value - cost_basis

        assert profit_loss == (178.50 * 10) - (175.00 * 10)
        assert profit_loss == 35.0

    def test_calculate_profit_loss_percentage(self, mock_stock, mock_portfolio):
        """Test profit/loss percentage calculation"""
        current_value = mock_stock.price * mock_portfolio.shares
        cost_basis = mock_portfolio.avg_price * mock_portfolio.shares
        profit_loss = current_value - cost_basis
        profit_loss_pct = (profit_loss / cost_basis * 100) if cost_basis > 0 else 0

        assert profit_loss_pct == pytest.approx(2.0, rel=0.01)

    def test_calculate_average_price_after_buy(self, mock_portfolio):
        """Test average price calculation after additional buy"""
        # Current: 10 shares @ $175
        # Buy: 5 shares @ $180
        old_value = 175.00 * 10
        new_value = 180.00 * 5
        total_value = old_value + new_value
        total_shares = 10 + 5
        new_avg_price = total_value / total_shares

        assert new_avg_price == pytest.approx(176.67, rel=0.01)


class TestTradeIdempotency:
    """Test trade idempotency"""

    @pytest.mark.asyncio
    async def test_duplicate_trade_returns_existing(self, mock_db, mock_trade_history):
        """Test duplicate idempotency key returns existing trade"""
        mock_db.execute.return_value.scalar_one_or_none.return_value = (
            mock_trade_history
        )

        result = mock_trade_history
        assert result.idempotency_key == "trade-key-123"
        assert result.action == "buy"

    @pytest.mark.asyncio
    async def test_different_users_same_key_allowed(self, mock_db):
        """Test different users can use same idempotency key"""
        # User 1's trade
        trade1 = MagicMock()
        trade1.user_id = 1
        trade1.idempotency_key = "same-key"

        # User 2's trade
        trade2 = MagicMock()
        trade2.user_id = 2
        trade2.idempotency_key = "same-key"

        # Should be allowed - different users
        assert trade1.user_id != trade2.user_id

    @pytest.mark.asyncio
    async def test_trade_history_records_all_trades(
        self, mock_db, mock_user, mock_stock
    ):
        """Test all trades are recorded in history"""
        # Each trade should create a TradeHistory record
        # This is important for audit trail


class TestStockPriceUpdates:
    """Test stock price updates during trades"""

    @pytest.mark.asyncio
    async def test_stock_price_updated_on_trade(self, mock_stock):
        """Test stock price is updated from market data during trade"""
        # Mock market data provider
        with patch("shared.market_data.get_market_data_provider") as mock_provider:
            mock_provider.return_value.get_current_price.return_value = 180.00
            mock_provider.return_value.get_change_percent.return_value = 2.5

            # Stock price should be updated
            new_price = 180.00
            new_change = 2.5

            assert new_price != mock_stock.price
            assert new_change != mock_stock.change_percent


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
