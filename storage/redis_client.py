"""Redis client wrapper with fallback for Zoo Multi-Agent System."""

import asyncio
import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4

try:
    import redis.asyncio as redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    RedisError = Exception

from core.config import get_config


class RedisClient:
    """Redis client with automatic fallback and connection management."""

    def __init__(self):
        self.config = get_config()
        self._client: Any = None
        self._connected = False
        self._lock = asyncio.Lock()
        self._fallback_data: Dict[str, Any] = {}

    async def connect(self) -> bool:
        """Establish Redis connection."""
        async with self._lock:
            try:
                if self._client is None:
                    self._client = redis.Redis(
                        host=self.config.redis_host,
                        port=self.config.redis_port,
                        db=self.config.redis_db,
                        password=self.config.redis_password,
                        decode_responses=True,
                        encoding="utf-8"
                    )
                # Test connection
                await self._client.ping()
                self._connected = True
                return True
            except (RedisError, ConnectionError):
                self._connected = False
                return False

    async def disconnect(self) -> None:
        """Close Redis connection."""
        async with self._lock:
            if self._client:
                await self._client.close()
                self._client = None
            self._connected = False

    async def is_connected(self) -> bool:
        """Check if Redis is connected."""
        if not self._client:
            return False
        try:
            await self._client.ping()
            self._connected = True
            return True
        except RedisError:
            self._connected = False
            return False

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        if self._connected and self._client:
            try:
                return await self._client.get(key)
            except RedisError:
                self._connected = False
                # Return fallback data if available
                return self._fallback_data.get(key)
        return self._fallback_data.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis."""
        if self._connected and self._client:
            try:
                if expire:
                    await self._client.set(key, value, ex=expire)
                else:
                    await self._client.set(key, value)
                return True
            except RedisError:
                self._connected = False
        # Store in fallback
        self._fallback_data[key] = value
        return True

    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        if self._connected and self._client:
            try:
                await self._client.delete(key)
                return True
            except RedisError:
                self._connected = False
        # Remove from fallback
        if key in self._fallback_data:
            del self._fallback_data[key]
        return True

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if self._connected and self._client:
            try:
                return await self._client.exists(key) > 0
            except RedisError:
                self._connected = False
        return key in self._fallback_data

    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get field from hash in Redis."""
        if self._connected and self._client:
            try:
                return await self._client.hget(key, field)
            except RedisError:
                self._connected = False
        return None

    async def hset(
        self,
        key: str,
        field: str,
        value: str
    ) -> bool:
        """Set field in hash in Redis."""
        if self._connected and self._client:
            try:
                await self._client.hset(key, field, value)
                return True
            except RedisError:
                self._connected = False
        return False

    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields from hash in Redis."""
        if self._connected and self._client:
            try:
                return await self._client.hgetall(key)
            except RedisError:
                self._connected = False
        return {}

    async def lpush(self, key: str, value: str) -> int:
        """Push value to list head in Redis."""
        if self._connected and self._client:
            try:
                return await self._client.lpush(key, value)
            except RedisError:
                self._connected = False
        return 0

    async def rpush(self, key: str, value: str) -> int:
        """Push value to list tail in Redis."""
        if self._connected and self._client:
            try:
                return await self._client.rpush(key, value)
            except RedisError:
                self._connected = False
        return 0

    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range of values from list in Redis."""
        if self._connected and self._client:
            try:
                return await self._client.lrange(key, start, end)
            except RedisError:
                self._connected = False
        return []

    async def publish(self, channel: str, message: str) -> int:
        """Publish message to channel in Redis."""
        if self._connected and self._client:
            try:
                return await self._client.publish(channel, message)
            except RedisError:
                self._connected = False
        return 0

    async def subscribe(self, channels: List[str]):
        """Subscribe to channels in Redis."""
        if self._connected and self._client:
            try:
                pubsub = await self._client.pubsub()
                await pubsub.subscribe(*channels)
                return pubsub
            except RedisError:
                self._connected = False
        return None

    # JSON utilities
    async def get_json(self, key: str) -> Optional[Dict]:
        """Get JSON-decoded value from Redis."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(
        self,
        key: str,
        value: Dict,
        expire: Optional[int] = None
    ) -> bool:
        """Set JSON-encoded value in Redis."""
        try:
            serialized = json.dumps(value)
            return await self.set(key, serialized, expire)
        except (TypeError, json.JSONDecodeError):
            return False

    # Session utilities
    async def save_session(self, session_id: str, session_data: Dict) -> bool:
        """Save session data to Redis."""
        key = f"session:{session_id}"
        return await self.set_json(key, session_data)

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data from Redis."""
        key = f"session:{session_id}"
        return await self.get_json(key)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        key = f"session:{session_id}"
        return await self.delete(key)

    # Thread utilities
    async def save_thread(self, thread_id: str, thread_data: Dict) -> bool:
        """Save thread data to Redis."""
        key = f"thread:{thread_id}"
        return await self.set_json(key, thread_data)

    async def get_thread(self, thread_id: str) -> Optional[Dict]:
        """Get thread data from Redis."""
        key = f"thread:{thread_id}"
        return await self.get_json(key)


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """Get or create the global Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    elif not await _redis_client.is_connected():
        await _redis_client.connect()
    return _redis_client


async def reset_redis_client() -> None:
    """Reset the global Redis client (for testing)."""
    global _redis_client
    if _redis_client:
        await _redis_client.disconnect()
    _redis_client = None
