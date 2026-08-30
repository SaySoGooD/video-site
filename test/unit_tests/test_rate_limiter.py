import fakeredis.aioredis
import pytest

from users_service.adapter.rate_limit.in_memory_rate_limiter import (
    InMemoryRateLimiter,
)
from users_service.adapter.rate_limit.redis_rate_limiter import RedisRateLimiter
from users_service.application.common.interfaces.i_rate_limiter import IRateLimiter


@pytest.fixture(params=["memory", "redis"])
def limiter(request: pytest.FixtureRequest) -> IRateLimiter:
    """Both implementations must behave identically.

    Built per test rather than per module, so counters never leak from one
    case into the next.
    """
    if request.param == "memory":
        return InMemoryRateLimiter()
    return RedisRateLimiter(fakeredis.aioredis.FakeRedis(decode_responses=True))


class TestRateLimiter:
    async def test_allows_up_to_the_limit(self, limiter: IRateLimiter) -> None:
        for _ in range(3):
            assert (await limiter.hit("k", limit=3, window_seconds=60)).allowed

    async def test_refuses_past_the_limit(self, limiter: IRateLimiter) -> None:
        for _ in range(3):
            await limiter.hit("k", limit=3, window_seconds=60)

        decision = await limiter.hit("k", limit=3, window_seconds=60)
        assert not decision.allowed
        assert decision.retry_after_seconds > 0

    async def test_peek_refuses_once_the_limit_is_reached(
        self, limiter: IRateLimiter
    ) -> None:
        for _ in range(2):
            await limiter.hit("k", limit=2, window_seconds=60)

        # hit() judged an attempt it had already counted and allowed it;
        # peek() is asked about the *next* attempt, which has no budget left.
        assert not (await limiter.peek("k", limit=2)).allowed

    async def test_peek_does_not_count(self, limiter: IRateLimiter) -> None:
        await limiter.hit("k", limit=2, window_seconds=60)
        for _ in range(5):
            await limiter.peek("k", limit=2)

        assert (await limiter.hit("k", limit=2, window_seconds=60)).allowed

    async def test_keys_are_independent(self, limiter: IRateLimiter) -> None:
        for _ in range(3):
            await limiter.hit("one", limit=3, window_seconds=60)

        assert (await limiter.hit("two", limit=3, window_seconds=60)).allowed

    async def test_reset_clears_the_counter(self, limiter: IRateLimiter) -> None:
        for _ in range(3):
            await limiter.hit("k", limit=3, window_seconds=60)
        await limiter.reset("k")

        assert (await limiter.peek("k", limit=3)).allowed
        assert (await limiter.hit("k", limit=3, window_seconds=60)).remaining == 2

    async def test_unknown_key_has_the_full_budget(
        self, limiter: IRateLimiter
    ) -> None:
        decision = await limiter.peek("never-seen", limit=5)
        assert decision.allowed
        assert decision.remaining == 5
