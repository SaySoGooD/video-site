from redis.asyncio import Redis

from users_service.application.common.dto import RateLimitDecision
from users_service.application.common.interfaces.i_rate_limiter import IRateLimiter


class RedisRateLimiter(IRateLimiter):
    """Fixed-window counter kept in Redis.

    ``INCR`` plus an ``EXPIRE`` on first hit, pipelined so the two cannot be
    separated by a crash and leave an immortal counter. The window is fixed
    rather than sliding: an attacker can get up to 2x the limit across a window
    boundary, which is irrelevant when the limit is "5 passwords per 15
    minutes" and costs far less than storing a timestamp per attempt.

    Redis is what makes the limit hold across several API processes — an
    in-process counter would give an attacker one full budget per worker.
    """

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def hit(
        self, key: str, limit: int, window_seconds: int
    ) -> RateLimitDecision:
        pipeline = self._client.pipeline()
        pipeline.incr(key)
        pipeline.ttl(key)
        count, ttl = await pipeline.execute()

        if int(ttl) < 0:
            await self._client.expire(key, window_seconds)
            ttl = window_seconds

        return self._decide(int(count), limit, int(ttl), counted=True)

    async def peek(self, key: str, limit: int) -> RateLimitDecision:
        pipeline = self._client.pipeline()
        pipeline.get(key)
        pipeline.ttl(key)
        raw, ttl = await pipeline.execute()

        count = int(raw) if raw is not None else 0
        return self._decide(count, limit, max(int(ttl), 0), counted=False)

    async def reset(self, key: str) -> None:
        await self._client.delete(key)

    @staticmethod
    def _decide(
        count: int, limit: int, ttl: int, *, counted: bool
    ) -> RateLimitDecision:
        # ``hit`` has already charged the current attempt, so the budget is
        # blown once the counter passes the limit; ``peek`` asks about an
        # attempt not yet made, which needs room left before it.
        allowed = count <= limit if counted else count < limit
        return RateLimitDecision(
            allowed=allowed,
            remaining=max(limit - count, 0),
            retry_after_seconds=0 if allowed else max(ttl, 1),
        )
