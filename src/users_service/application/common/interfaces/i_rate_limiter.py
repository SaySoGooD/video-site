from abc import ABC, abstractmethod

from users_service.application.common.dto import RateLimitDecision


class IRateLimiter(ABC):
    """Port for counting attempts inside a sliding window.

    Deliberately not the cache port: a limiter needs an *atomic*
    increment-and-expire, which ``ICache.get``/``set`` cannot provide without
    a race, and it must keep working when no cache is configured.
    """

    @abstractmethod
    async def hit(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        """Count one attempt against ``key`` and say whether it is allowed."""
        ...

    @abstractmethod
    async def peek(self, key: str, limit: int) -> RateLimitDecision:
        """Report the state of ``key`` without counting an attempt.

        ``allowed`` here answers "may one more attempt be made?", so a key
        that has exactly reached its limit is already refused — unlike
        :meth:`hit`, which has charged the attempt it is judging.
        """
        ...

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Clear the counter (a successful login forgives past failures)."""
        ...
