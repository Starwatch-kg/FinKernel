"""Deterministic market data provider - NO random generation in production"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class MarketDataProvider:
    """
    Provides deterministic market data.
    In production, this should be replaced with real market data API.
    Uses deterministic algorithms instead of random generation.
    """

    # Base stock data - static reference prices
    STOCK_REFERENCE_DATA = {
        "AAPL": {
            "name": "Apple Inc.",
            "base_price": 178.50,
            "sector": "Technology",
            "volatility": 0.02,
        },
        "GOOGL": {
            "name": "Alphabet Inc.",
            "base_price": 142.30,
            "sector": "Technology",
            "volatility": 0.025,
        },
        "MSFT": {
            "name": "Microsoft Corp.",
            "base_price": 415.20,
            "sector": "Technology",
            "volatility": 0.018,
        },
        "TSLA": {
            "name": "Tesla Inc.",
            "base_price": 248.90,
            "sector": "Automotive",
            "volatility": 0.04,
        },
        "AMZN": {
            "name": "Amazon.com Inc.",
            "base_price": 178.25,
            "sector": "E-commerce",
            "volatility": 0.022,
        },
        "NVDA": {
            "name": "NVIDIA Corp.",
            "base_price": 875.40,
            "sector": "Technology",
            "volatility": 0.035,
        },
        "META": {
            "name": "Meta Platforms",
            "base_price": 485.60,
            "sector": "Technology",
            "volatility": 0.028,
        },
        "JPM": {
            "name": "JPMorgan Chase",
            "base_price": 195.80,
            "sector": "Finance",
            "volatility": 0.015,
        },
        "V": {
            "name": "Visa Inc.",
            "base_price": 278.30,
            "sector": "Finance",
            "volatility": 0.016,
        },
        "WMT": {
            "name": "Walmart Inc.",
            "base_price": 165.40,
            "sector": "Retail",
            "volatility": 0.012,
        },
    }

    def __init__(self):
        self.reference_date = datetime(2026, 1, 1)

    def get_current_price(
        self, ticker: str, current_time: Optional[datetime] = None
    ) -> float:
        """
        Get deterministic current price based on time.
        Uses sine wave to simulate market movement - deterministic, not random.
        """
        if ticker not in self.STOCK_REFERENCE_DATA:
            raise ValueError(f"Unknown ticker: {ticker}")

        data = self.STOCK_REFERENCE_DATA[ticker]
        base_price = data["base_price"]
        volatility = data["volatility"]

        if current_time is None:
            current_time = datetime.utcnow()

        # Days since reference date
        days_elapsed = (current_time - self.reference_date).days

        # Deterministic price movement using sine wave
        # Different phase for each ticker (based on hash of ticker name)
        phase = sum(ord(c) for c in ticker) % 360
        cycle = math.sin(math.radians(days_elapsed * 10 + phase))

        # Price oscillates around base price
        price_change = base_price * volatility * cycle
        current_price = base_price + price_change

        return round(current_price, 2)

    def get_change_percent(
        self, ticker: str, current_time: Optional[datetime] = None
    ) -> float:
        """Get deterministic daily change percentage"""
        if current_time is None:
            current_time = datetime.utcnow()

        current_price = self.get_current_price(ticker, current_time)
        yesterday_price = self.get_current_price(
            ticker, current_time - timedelta(days=1)
        )

        change_pct = ((current_price - yesterday_price) / yesterday_price) * 100
        return round(change_pct, 2)

    def get_historical_prices(
        self, ticker: str, days: int = 30, end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get deterministic historical price data.
        NO random generation - uses same deterministic algorithm.
        """
        if end_date is None:
            end_date = datetime.utcnow()

        history = []
        for i in range(days, 0, -1):
            date = end_date - timedelta(days=i)
            price = self.get_current_price(ticker, date)

            # Volume is deterministic based on day of week
            # Higher volume on weekdays, lower on weekends
            day_of_week = date.weekday()
            base_volume = 10_000_000
            if day_of_week < 5:  # Weekday
                volume = base_volume + (day_of_week * 2_000_000)
            else:  # Weekend
                volume = base_volume // 2

            history.append({"date": date.isoformat(), "price": price, "volume": volume})

        return history

    def get_stock_metrics(self, ticker: str) -> Dict:
        """Get deterministic stock metrics"""
        if ticker not in self.STOCK_REFERENCE_DATA:
            raise ValueError(f"Unknown ticker: {ticker}")

        data = self.STOCK_REFERENCE_DATA[ticker]
        current_price = self.get_current_price(ticker)

        # Deterministic metrics based on ticker characteristics
        ticker_hash = sum(ord(c) for c in ticker)

        return {
            "pe_ratio": round(15 + (ticker_hash % 25), 2),
            "dividend_yield": round((ticker_hash % 5) * 0.5, 2),
            "52w_high": round(current_price * 1.2, 2),
            "52w_low": round(current_price * 0.8, 2),
            "market_cap": data["base_price"]
            * (100_000_000 + (ticker_hash * 10_000_000)),
        }

    def get_all_stocks(self) -> List[Dict]:
        """Get current data for all stocks"""
        stocks = []
        current_time = datetime.utcnow()

        for ticker, data in self.STOCK_REFERENCE_DATA.items():
            price = self.get_current_price(ticker, current_time)
            change_pct = self.get_change_percent(ticker, current_time)

            # Deterministic volume based on ticker
            ticker_hash = sum(ord(c) for c in ticker)
            volume = 5_000_000 + (ticker_hash * 100_000)

            stocks.append(
                {
                    "ticker": ticker,
                    "name": data["name"],
                    "price": price,
                    "change_percent": change_pct,
                    "volume": volume,
                    "market_cap": self.get_stock_metrics(ticker)["market_cap"],
                    "sector": data["sector"],
                }
            )

        return stocks

    def get_stock_recommendation(self, ticker: str) -> Dict:
        """
        Get deterministic stock recommendation.
        Based on current price vs base price - NOT random.
        """
        if ticker not in self.STOCK_REFERENCE_DATA:
            raise ValueError(f"Unknown ticker: {ticker}")

        data = self.STOCK_REFERENCE_DATA[ticker]
        current_price = self.get_current_price(ticker)
        base_price = data["base_price"]

        # Deterministic recommendation based on price deviation
        deviation = (current_price - base_price) / base_price

        if deviation < -0.05:
            action = "buy"
            confidence = 0.85
            target_price = round(base_price * 1.1, 2)
            reason = f"Trading below historical average - {data['sector']} sector fundamentals strong"
        elif deviation > 0.05:
            action = "sell"
            confidence = 0.75
            target_price = round(base_price * 0.95, 2)
            reason = f"Trading above historical average - consider taking profits"
        else:
            action = "hold"
            confidence = 0.70
            target_price = round(current_price * 1.05, 2)
            reason = f"Fair value - {data['sector']} sector stable"

        return {
            "ticker": ticker,
            "name": data["name"],
            "action": action,
            "confidence": confidence,
            "target_price": target_price,
            "reason": reason,
        }


# Global instance
_market_data_provider = None


def get_market_data_provider() -> MarketDataProvider:
    """Get singleton market data provider"""
    global _market_data_provider
    if _market_data_provider is None:
        _market_data_provider = MarketDataProvider()
    return _market_data_provider
