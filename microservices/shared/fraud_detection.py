"""Fraud Detection Layer with risk scoring"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from redis.asyncio import Redis
from shared.logger import setup_logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = setup_logger("fraud_detection")


class RiskScore:
    """User risk score (0-1)"""

    def __init__(self, score: float, factors: List[str], details: Dict):
        self.score = max(0.0, min(1.0, score))
        self.factors = factors
        self.details = details
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.get_level(),
            "factors": self.factors,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    def get_level(self) -> str:
        """Get risk level"""
        if self.score < 0.3:
            return "low"
        elif self.score < 0.6:
            return "medium"
        elif self.score < 0.8:
            return "high"
        else:
            return "critical"


class FraudDetector:
    """Advanced fraud detection system"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def calculate_risk_score(self, user_id: int, db: AsyncSession) -> RiskScore:
        """Calculate comprehensive risk score for user"""
        factors = []
        details = {}
        score = 0.0

        # Check spending spike
        spending_risk = await self._check_spending_spike(user_id, db)
        if spending_risk > 0:
            score += spending_risk * 0.3
            factors.append("spending_spike")
            details["spending_spike"] = spending_risk

        # Check trading patterns
        trading_risk = await self._check_trading_patterns(user_id, db)
        if trading_risk > 0:
            score += trading_risk * 0.3
            factors.append("abnormal_trading")
            details["trading_risk"] = trading_risk

        # Check velocity
        velocity_risk = await self._check_velocity(user_id)
        if velocity_risk > 0:
            score += velocity_risk * 0.2
            factors.append("high_velocity")
            details["velocity_risk"] = velocity_risk

        # Check failed attempts
        failure_risk = await self._check_failed_attempts(user_id)
        if failure_risk > 0:
            score += failure_risk * 0.2
            factors.append("failed_attempts")
            details["failure_risk"] = failure_risk

        risk_score = RiskScore(score, factors, details)

        # Cache risk score
        await self._cache_risk_score(user_id, risk_score)

        # Flag high-risk users
        if risk_score.score >= 0.7:
            await self._flag_high_risk_user(user_id, risk_score)

        return risk_score

    async def _check_spending_spike(self, user_id: int, db: AsyncSession) -> float:
        """Detect unusual spending spikes"""
        from shared.models import Transaction

        # Get last 24 hours spending
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_result = await db.execute(
            select(func.sum(Transaction.amount)).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.timestamp >= yesterday,
            )
        )
        recent_spending = recent_result.scalar() or 0

        # Get average daily spending (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        avg_result = await db.execute(
            select(func.avg(Transaction.amount)).where(
                Transaction.user_id == user_id,
                Transaction.type == "expense",
                Transaction.timestamp >= thirty_days_ago,
            )
        )
        avg_spending = avg_result.scalar() or 0

        if avg_spending == 0:
            return 0.0

        # Calculate spike ratio
        spike_ratio = recent_spending / (avg_spending * 30)

        if spike_ratio > 5:
            return 1.0
        elif spike_ratio > 3:
            return 0.7
        elif spike_ratio > 2:
            return 0.4
        else:
            return 0.0

    async def _check_trading_patterns(self, user_id: int, db: AsyncSession) -> float:
        """Detect abnormal trading patterns"""
        from shared.models import Portfolio

        # Get user's portfolio activity
        result = await db.execute(select(Portfolio).where(Portfolio.user_id == user_id))
        positions = result.scalars().all()

        if not positions:
            return 0.0

        # Check for suspicious patterns
        risk = 0.0

        # Too many positions
        if len(positions) > 50:
            risk += 0.3

        # Check for pump-and-dump patterns (rapid buy/sell)
        recent_trades = await self.redis.lrange(f"user_trades:{user_id}", 0, 99)
        if len(recent_trades) > 20:
            risk += 0.4

        # Check for coordinated trading (same stocks as flagged users)
        # Simplified check
        if len(positions) > 30:
            risk += 0.3

        return min(risk, 1.0)

    async def _check_velocity(self, user_id: int) -> float:
        """Check action velocity"""
        # Get action count in last hour
        actions = await self.redis.lrange(f"user_actions:{user_id}", 0, -1)

        if not actions:
            return 0.0

        # Count recent actions
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_count = 0

        for action_json in actions:
            try:
                action = json.loads(action_json)
                action_time = datetime.fromisoformat(action["timestamp"])
                if action_time > one_hour_ago:
                    recent_count += 1
            except:
                continue

        # Risk based on velocity
        if recent_count > 100:
            return 1.0
        elif recent_count > 50:
            return 0.6
        elif recent_count > 30:
            return 0.3
        else:
            return 0.0

    async def _check_failed_attempts(self, user_id: int) -> float:
        """Check failed authentication/transaction attempts"""
        failed_logins = await self.redis.get(f"failed_logins:{user_id}")
        failed_txns = await self.redis.get(f"failed_transactions:{user_id}")

        total_failures = int(failed_logins or 0) + int(failed_txns or 0)

        if total_failures > 10:
            return 1.0
        elif total_failures > 5:
            return 0.6
        elif total_failures > 3:
            return 0.3
        else:
            return 0.0

    async def _cache_risk_score(self, user_id: int, risk_score: RiskScore):
        """Cache risk score"""
        key = f"risk_score:{user_id}"
        await self.redis.setex(key, 3600, json.dumps(risk_score.to_dict()))

    async def get_cached_risk_score(self, user_id: int) -> Optional[RiskScore]:
        """Get cached risk score"""
        key = f"risk_score:{user_id}"
        data = await self.redis.get(key)

        if data:
            score_dict = json.loads(data)
            return RiskScore(
                score=score_dict["score"],
                factors=score_dict["factors"],
                details=score_dict["details"],
            )

        return None

    async def _flag_high_risk_user(self, user_id: int, risk_score: RiskScore):
        """Flag high-risk user"""
        key = f"high_risk_user:{user_id}"
        await self.redis.setex(key, 86400, json.dumps(risk_score.to_dict()))
        logger.warning(
            f"User {user_id} flagged as high-risk: score={risk_score.score:.2f}, factors={risk_score.factors}"
        )

    async def is_high_risk(self, user_id: int) -> bool:
        """Check if user is flagged as high-risk"""
        key = f"high_risk_user:{user_id}"
        return bool(await self.redis.exists(key))

    async def get_high_risk_users(self) -> List[int]:
        """Get all high-risk users"""
        keys = []
        async for key in self.redis.scan_iter(match="high_risk_user:*"):
            user_id = int(key.split(":")[-1])
            keys.append(user_id)
        return keys

    async def clear_risk_flag(self, user_id: int):
        """Clear high-risk flag"""
        await self.redis.delete(f"high_risk_user:{user_id}")
        await self.redis.delete(f"risk_score:{user_id}")
        logger.info(f"Cleared risk flag for user {user_id}")
