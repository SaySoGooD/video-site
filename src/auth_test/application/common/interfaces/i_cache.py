from abc import ABC, abstractmethod


class ICache(ABC):
    """Port for an optional key/value cache with per-key expiry.

    The application depends only on this interface; whether it is backed by
    Redis or by a no-op is a deployment detail. Values are opaque strings.
    """

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Return the cached value for ``key`` or ``None`` if absent/expired."""
        ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Store ``value`` under ``key`` for ``ttl_seconds`` seconds."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove ``key`` from the cache (idempotent)."""
        ...
