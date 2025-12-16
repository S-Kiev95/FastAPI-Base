"""
Cache service using Redis for improved performance.
Completely optional - only activates if Redis is configured.
"""
import json
import hashlib
from typing import Any, Optional, List
from datetime import timedelta

import redis
from redis.exceptions import ConnectionError, RedisError

from app.config import settings


class CacheService:
    """
    Redis cache service for caching API responses.

    Features:
    - Optional: Only works if REDIS_ENABLED=True
    - Automatic key generation based on parameters
    - TTL (Time To Live) configurable
    - Pattern-based invalidation
    - JSON serialization
    - Safe fallbacks on Redis errors
    """

    def __init__(self):
        """Initialize Redis connection (if enabled)"""
        self.enabled = settings.REDIS_ENABLED
        self.ttl = settings.CACHE_TTL
        self.client: Optional[redis.Redis] = None

        if self.enabled:
            try:
                # Create Redis client
                self.client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                    decode_responses=True,  # Auto-decode bytes to strings
                    socket_connect_timeout=2,
                    socket_timeout=2
                )

                # Test connection
                self.client.ping()
                print(f"[OK] Redis cache enabled at {settings.REDIS_HOST}:{settings.REDIS_PORT}")

            except (ConnectionError, RedisError) as e:
                print(f"[ERROR] Redis connection failed: {str(e)}")
                print("  Cache will be disabled for this session")
                self.enabled = False
                self.client = None
        else:
            print("  Cache disabled (REDIS_ENABLED=False)")

    def _generate_key(self, prefix: str, **params) -> str:
        """
        Generate cache key from prefix and parameters.

        Args:
            prefix: Key prefix (e.g., "users", "posts:filter")
            **params: Key-value pairs to include in the key

        Returns:
            Generated cache key

        Example:
            key = _generate_key("users", id=1)  # "users:1"
            key = _generate_key("posts:list", skip=0, limit=10)  # "posts:list:hash123"
        """
        if not params:
            return prefix

        # Sort parameters for consistent keys
        sorted_params = sorted(params.items())

        # For simple cases (single id), use direct key
        if len(params) == 1 and "id" in params:
            return f"{prefix}:{params['id']}"

        # For complex queries, use hash
        params_str = json.dumps(sorted_params, sort_keys=True)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return f"{prefix}:{params_hash}"

    def get(self, prefix: str, **params) -> Optional[Any]:
        """
        Get cached value.

        Args:
            prefix: Cache key prefix
            **params: Parameters to generate key

        Returns:
            Cached value or None if not found/disabled

        Example:
            user = cache_service.get("users", id=1)
            if not user:
                user = db.get_user(1)
                cache_service.set("users", user, id=1)
        """
        if not self.enabled or not self.client:
            return None

        try:
            key = self._generate_key(prefix, **params)
            value = self.client.get(key)

            if value:
                return json.loads(value)

            return None

        except (ConnectionError, RedisError, json.JSONDecodeError) as e:
            print(f"Cache GET error: {str(e)}")
            return None

    def set(
        self,
        prefix: str,
        value: Any,
        ttl: Optional[int] = None,
        **params
    ) -> bool:
        """
        Set cached value.

        Args:
            prefix: Cache key prefix
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: from config)
            **params: Parameters to generate key

        Returns:
            True if cached successfully, False otherwise

        Example:
            cache_service.set("users", user_data, id=1)
            cache_service.set("posts:list", posts, skip=0, limit=10, ttl=60)
        """
        if not self.enabled or not self.client:
            return False

        try:
            key = self._generate_key(prefix, **params)
            value_json = json.dumps(value, default=str)  # default=str handles datetime, etc.

            cache_ttl = ttl if ttl is not None else self.ttl
            self.client.setex(key, cache_ttl, value_json)

            return True

        except (ConnectionError, RedisError, TypeError) as e:
            print(f"Cache SET error: {str(e)}")
            return False

    def delete(self, prefix: str, **params) -> bool:
        """
        Delete specific cached value.

        Args:
            prefix: Cache key prefix
            **params: Parameters to generate key

        Returns:
            True if deleted, False otherwise

        Example:
            cache_service.delete("users", id=1)
        """
        if not self.enabled or not self.client:
            return False

        try:
            key = self._generate_key(prefix, **params)
            self.client.delete(key)
            return True

        except (ConnectionError, RedisError) as e:
            print(f"Cache DELETE error: {str(e)}")
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "users:*", "posts:filter:*")

        Returns:
            Number of keys deleted

        Example:
            # Invalidate all user caches
            cache_service.invalidate_pattern("users:*")

            # Invalidate all post filters
            cache_service.invalidate_pattern("posts:filter:*")
        """
        if not self.enabled or not self.client:
            return 0

        try:
            # Find all matching keys
            keys = list(self.client.scan_iter(match=pattern))

            if keys:
                # Delete in batch
                return self.client.delete(*keys)

            return 0

        except (ConnectionError, RedisError) as e:
            print(f"Cache INVALIDATE_PATTERN error: {str(e)}")
            return 0

    def invalidate_all(self, prefix: str) -> int:
        """
        Invalidate all caches for a specific resource.

        Args:
            prefix: Resource prefix (e.g., "users", "posts")

        Returns:
            Number of keys deleted

        Example:
            # After creating/updating/deleting a user, invalidate all user caches
            cache_service.invalidate_all("users")
        """
        return self.invalidate_pattern(f"{prefix}:*")

    def clear_all(self) -> bool:
        """
        Clear entire cache (use with caution).

        Returns:
            True if cleared, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.flushdb()
            print("✓ Cache cleared")
            return True

        except (ConnectionError, RedisError) as e:
            print(f"Cache CLEAR error: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or not self.client:
            return {
                "enabled": False,
                "message": "Cache is disabled"
            }

        try:
            info = self.client.info()
            return {
                "enabled": True,
                "connected": True,
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
                "db": settings.REDIS_DB,
                "total_keys": self.client.dbsize(),
                "used_memory": info.get("used_memory_human", "N/A"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "connected_clients": info.get("connected_clients", 0),
                "default_ttl": self.ttl
            }

        except (ConnectionError, RedisError) as e:
            return {
                "enabled": True,
                "connected": False,
                "error": str(e)
            }

    def is_available(self) -> bool:
        """
        Check if cache is available and working.

        Returns:
            True if Redis is available, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            self.client.ping()
            return True
        except (ConnectionError, RedisError):
            return False


# Singleton instance
cache_service = CacheService()
