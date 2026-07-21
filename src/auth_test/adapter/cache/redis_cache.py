from redis.asyncio import Redis

from auth_test.application.common.interfaces.i_cache import ICache


class RedisCache(ICache):
    """Redis-backed implementation of :class:`ICache`.

    Uses the async Redis client with ``decode_responses`` so values are plain
    strings. Per-key TTL is delegated to Redis (``SET ... EX``).
    """

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._client.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)
