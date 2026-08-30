import time

from users_service.application.common.dto import RateLimitDecision
from users_service.application.common.interfaces.i_rate_limiter import IRateLimiter


class InMemoryRateLimiter(IRateLimiter):
    """Per-process fallback used when no Redis is configured.

    Good enough for a single worker and for tests, and deliberately *not* good
    enough for production: with several API processes each gets its own
    counters, so the effective limit is multiplied by the worker count. That is
    the tradeoff for keeping Redis optional — the service still rate-limits
    when it is absent instead of silently not limiting at all.
    """

    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = {}

    async def hit(
        self, key: str, limit: int, window_seconds: int
    ) -> RateLimitDecision:
        now = time.monotonic()
        count, expires_at = self._counters.get(key, (0, 0.0))

        if expires_at <= now:
            count, expires_at = 0, now + window_seconds

        count += 1
        self._counters[key] = (count, expires_at)
        return self._decide(count, limit, expires_at - now, counted=True)

    async def peek(self, key: str, limit: int) -> RateLimitDecision:
        now = time.monotonic()
        count, expires_at = self._counters.get(key, (0, 0.0))
        if expires_at <= now:
            return self._decide(0, limit, 0.0, counted=False)
        return self._decide(count, limit, expires_at - now, counted=False)

    async def reset(self, key: str) -> None:
        self._counters.pop(key, None)

    @staticmethod
    def _decide(
        count: int, limit: int, ttl: float, *, counted: bool
    ) -> RateLimitDecision:
        # ``hit`` has already charged the current attempt, so the budget is
        # blown once the counter passes the limit; ``peek`` asks about an
        # attempt not yet made, which needs room left before it.
        allowed = count <= limit if counted else count < limit
        return RateLimitDecision(
            allowed=allowed,
            remaining=max(limit - count, 0),
            retry_after_seconds=0 if allowed else max(int(ttl), 1),
        )
