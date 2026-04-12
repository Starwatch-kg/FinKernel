"""Anti-Abuse and Anomaly Detection System"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from redis.asyncio import Redis
from shared.logger import setup_logger

logger = setup_logger("anti_abuse")


class AnomalyDetector:
    """Detect suspicious patterns and abuse"""

    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_rapid_trades(
        self, user_id: int, threshold: int = 10, window: int = 60
    ) -> bool:
        """Detect rapid trading bursts"""
        key = f"trade_burst:{user_id}"
        count = await self.redis.incr(key)

        if count == 1:
            await self.redis.expire(key, window)

        if count > threshold:
            logger.warning(
                f"Rapid trade burst detected for user {user_id}: {count} trades in {window}s"
            )
            await self.flag_user(
                user_id, "rapid_trades", f"{count} trades in {window}s"
            )
            return True

        return False

    async def check_repeated_failures(
        self, user_id: int, action: str, threshold: int = 5, window: int = 300
    ) -> bool:
        """Detect repeated failed attempts"""
        key = f"failures:{user_id}:{action}"
        count = await self.redis.incr(key)

        if count == 1:
            await self.redis.expire(key, window)

        if count > threshold:
            logger.warning(
                f"Repeated failures detected for user {user_id} on {action}: {count} in {window}s"
            )
            await self.flag_user(
                user_id, f"repeated_failures_{action}", f"{count} failures in {window}s"
            )
            return True

        return False

    async def check_abnormal_transaction_pattern(
        self, user_id: int, amount: float, avg_amount: float, std_dev: float
    ) -> bool:
        """Detect transactions significantly outside normal range"""
        if std_dev == 0:
            return False

        z_score = abs((amount - avg_amount) / std_dev)

        if z_score > 3:  # 3 standard deviations
            logger.warning(
                f"Abnormal transaction for user {user_id}: amount={amount}, z-score={z_score:.2f}"
            )
            await self.flag_user(
                user_id,
                "abnormal_transaction",
                f"amount={amount}, z-score={z_score:.2f}",
            )
            return True

        return False

    async def flag_user(self, user_id: int, reason: str, details: str):
        """Flag user for review"""
        key = f"flagged_user:{user_id}"
        flag_data = {
            "reason": reason,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.redis.setex(key, 3600, json.dumps(flag_data))
        logger.info(f"Flagged user {user_id}: {reason}")

    async def is_user_flagged(self, user_id: int) -> Optional[Dict]:
        """Check if user is flagged"""
        key = f"flagged_user:{user_id}"
        data = await self.redis.get(key)

        if data:
            return json.loads(data)
        return None

    async def block_user_temporarily(
        self, user_id: int, duration: int = 300, reason: str = "abuse_detected"
    ):
        """Temporarily block user"""
        key = f"blocked_user:{user_id}"
        block_data = {
            "reason": reason,
            "blocked_at": datetime.utcnow().isoformat(),
            "duration": duration,
        }

        await self.redis.setex(key, duration, json.dumps(block_data))
        logger.warning(f"Temporarily blocked user {user_id} for {duration}s: {reason}")

    async def is_user_blocked(self, user_id: int) -> Optional[Dict]:
        """Check if user is temporarily blocked"""
        key = f"blocked_user:{user_id}"
        data = await self.redis.get(key)

        if data:
            return json.loads(data)
        return None

    async def unblock_user(self, user_id: int):
        """Manually unblock user"""
        key = f"blocked_user:{user_id}"
        await self.redis.delete(key)
        logger.info(f"Unblocked user {user_id}")

    async def record_action(self, user_id: int, action: str):
        """Record user action for pattern analysis"""
        key = f"user_actions:{user_id}"
        action_data = {"action": action, "timestamp": datetime.utcnow().isoformat()}

        await self.redis.lpush(key, json.dumps(action_data))
        await self.redis.ltrim(key, 0, 99)  # Keep last 100 actions
        await self.redis.expire(key, 86400)  # 24 hour TTL

    async def get_user_actions(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get recent user actions"""
        key = f"user_actions:{user_id}"
        actions = await self.redis.lrange(key, 0, limit - 1)

        return [json.loads(action) for action in actions]

    async def check_velocity(
        self, user_id: int, action: str, max_per_minute: int = 30
    ) -> bool:
        """Check action velocity"""
        key = f"velocity:{user_id}:{action}"
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Use sorted set with timestamp as score
        await self.redis.zadd(key, {str(now.timestamp()): now.timestamp()})
        await self.redis.zremrangebyscore(key, 0, minute_ago.timestamp())
        await self.redis.expire(key, 60)

        count = await self.redis.zcard(key)

        if count > max_per_minute:
            logger.warning(
                f"Velocity limit exceeded for user {user_id} on {action}: {count}/min"
            )
            return False

        return True
