"""
Redis client for caching sessions, JWT, and search results.
"""
import os
import json
from typing import Optional, Any
from datetime import timedelta

import redis.asyncio as redis

# Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Global redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


class RedisCache:
    """Redis cache wrapper with typed methods."""

    def __init__(self, client: redis.Redis):
        self.client = client

    # ============ Session Methods ============

    async def set_session(
        self,
        session_id: str,
        data: dict,
        expire_minutes: int = 30
    ) -> bool:
        """Store session data."""
        key = f"session:{session_id}"
        await self.client.setex(
            key,
            timedelta(minutes=expire_minutes),
            json.dumps(data)
        )
        return True

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        key = f"session:{session_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete_session(self, session_id: str) -> bool:
        """Delete session."""
        key = f"session:{session_id}"
        await self.client.delete(key)
        return True

    async def extend_session(self, session_id: str, expire_minutes: int = 30) -> bool:
        """Extend session TTL."""
        key = f"session:{session_id}"
        await self.client.expire(key, timedelta(minutes=expire_minutes))
        return True

    # ============ JWT Cache Methods ============

    async def cache_jwt(
        self,
        user_id: str,
        token: str,
        expire_minutes: int = 30
    ) -> bool:
        """Cache JWT token for quick validation."""
        key = f"jwt:{user_id}"
        await self.client.setex(
            key,
            timedelta(minutes=expire_minutes),
            token
        )
        return True

    async def get_cached_jwt(self, user_id: str) -> Optional[str]:
        """Get cached JWT."""
        key = f"jwt:{user_id}"
        return await self.client.get(key)

    async def invalidate_jwt(self, user_id: str) -> bool:
        """Invalidate cached JWT (for logout)."""
        key = f"jwt:{user_id}"
        await self.client.delete(key)
        return True

    # ============ Rate Limiting Methods ============

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int = 100,
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check rate limit. Returns (allowed, remaining).
        """
        key = f"rate:{identifier}"
        current = await self.client.get(key)

        if current is None:
            await self.client.setex(key, window_seconds, "1")
            return True, limit - 1

        count = int(current)
        if count >= limit:
            return False, 0

        await self.client.incr(key)
        return True, limit - count - 1

    # ============ Search Cache Methods ============

    async def cache_search(
        self,
        search_key: str,
        results: Any,
        expire_minutes: int = 15
    ) -> bool:
        """Cache flight search results."""
        key = f"search:{search_key}"
        await self.client.setex(
            key,
            timedelta(minutes=expire_minutes),
            json.dumps(results, ensure_ascii=False)
        )
        return True

    async def get_cached_search(self, search_key: str) -> Optional[Any]:
        """Get cached search results."""
        key = f"search:{search_key}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    # ============ Agent State Methods ============

    async def save_agent_state(
        self,
        session_id: str,
        state: dict,
        expire_minutes: int = 60
    ) -> bool:
        """Save LangGraph agent state."""
        key = f"agent_state:{session_id}"
        await self.client.setex(
            key,
            timedelta(minutes=expire_minutes),
            json.dumps(state, ensure_ascii=False, default=str)
        )
        return True

    async def get_agent_state(self, session_id: str) -> Optional[dict]:
        """Get agent state."""
        key = f"agent_state:{session_id}"
        data = await self.client.get(key)
        if data:
            return json.loads(data)
        return None

    # ============ Generic Methods ============

    async def set(
        self,
        key: str,
        value: Any,
        expire_seconds: Optional[int] = None
    ) -> bool:
        """Generic set with optional expiration."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)

        if expire_seconds:
            await self.client.setex(key, expire_seconds, value)
        else:
            await self.client.set(key, value)
        return True

    async def get(self, key: str) -> Optional[str]:
        """Generic get."""
        return await self.client.get(key)

    async def delete(self, key: str) -> bool:
        """Generic delete."""
        await self.client.delete(key)
        return True

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.client.exists(key) > 0
