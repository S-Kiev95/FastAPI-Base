"""
Rate Limiter Service using Redis

Implements sliding window rate limiting to protect API endpoints
from abuse and ensure fair usage.
"""
import time
from typing import Optional, Tuple
from redis.asyncio import Redis

from app.config import settings


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm

    Features:
    - Sliding window (more accurate than fixed window)
    - Per-IP or per-user rate limiting
    - Configurable limits per endpoint
    - Returns remaining requests info
    - Automatic cleanup of old entries

    Example:
        limiter = RateLimiter(redis_client)
        allowed, info = await limiter.check_rate_limit(
            key="ip:192.168.1.1",
            limit=100,
            window=60
        )
    """

    def __init__(self, redis: Optional[Redis] = None):
        """
        Initialize rate limiter

        Args:
            redis: Redis client (optional, will create if not provided)
        """
        self.redis = redis
        self.enabled = settings.REDIS_ENABLED

    async def initialize(self):
        """Initialize Redis connection if not provided"""
        if not self.enabled:
            return

        if not self.redis:
            self.redis = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True
            )

    async def check_rate_limit(
        self,
        key: str,
        limit: int = 100,
        window: int = 60
    ) -> Tuple[bool, dict]:
        """
        Check if request is within rate limit

        Args:
            key: Unique identifier (e.g., "ip:192.168.1.1" or "user:123")
            limit: Maximum number of requests
            window: Time window in seconds

        Returns:
            Tuple of (allowed: bool, info: dict)
            - allowed: True if within limit, False if exceeded
            - info: Dict with limit, remaining, reset_at

        Example:
            allowed, info = await limiter.check_rate_limit(
                key="ip:192.168.1.1",
                limit=100,
                window=60
            )
            # allowed = True
            # info = {
            #     "limit": 100,
            #     "remaining": 85,
            #     "reset_at": 1640000000,
            #     "retry_after": 0
            # }
        """
        if not self.enabled:
            # Rate limiting disabled, allow all requests
            return True, {
                "limit": limit,
                "remaining": limit,
                "reset_at": int(time.time()) + window,
                "retry_after": 0
            }

        if not self.redis:
            await self.initialize()

        now = time.time()
        rate_limit_key = f"rate_limit:{key}"

        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove requests outside the current window
        pipe.zremrangebyscore(rate_limit_key, 0, now - window)

        # Count requests in current window
        pipe.zcard(rate_limit_key)

        # Add current request
        pipe.zadd(rate_limit_key, {str(now): now})

        # Set expiration (cleanup old keys)
        pipe.expire(rate_limit_key, window + 10)

        # Execute pipeline
        results = await pipe.execute()
        request_count = results[1]  # Count before adding current

        # Calculate info
        allowed = request_count < limit
        remaining = max(0, limit - request_count - 1)
        reset_at = int(now + window)
        retry_after = 0 if allowed else window

        info = {
            "limit": limit,
            "remaining": remaining,
            "reset_at": reset_at,
            "retry_after": retry_after,
            "current_usage": request_count + 1
        }

        return allowed, info

    async def reset_limit(self, key: str):
        """
        Reset rate limit for a specific key

        Args:
            key: Unique identifier to reset

        Useful for:
        - Admin override
        - Testing
        - User upgrade (reset to new limits)
        """
        if not self.enabled or not self.redis:
            return

        rate_limit_key = f"rate_limit:{key}"
        await self.redis.delete(rate_limit_key)

    async def get_remaining(self, key: str, limit: int, window: int) -> dict:
        """
        Get remaining requests without incrementing counter

        Args:
            key: Unique identifier
            limit: Maximum requests
            window: Time window in seconds

        Returns:
            Dict with limit info
        """
        if not self.enabled:
            return {
                "limit": limit,
                "remaining": limit,
                "reset_at": int(time.time()) + window
            }

        if not self.redis:
            await self.initialize()

        now = time.time()
        rate_limit_key = f"rate_limit:{key}"

        # Remove old entries
        await self.redis.zremrangebyscore(rate_limit_key, 0, now - window)

        # Count current requests
        count = await self.redis.zcard(rate_limit_key)

        remaining = max(0, limit - count)
        reset_at = int(now + window)

        return {
            "limit": limit,
            "remaining": remaining,
            "reset_at": reset_at,
            "current_usage": count
        }


# Global instance
rate_limiter = RateLimiter()
