from auth_test.application.common.interfaces.i_cache import ICache


class NullCache(ICache):
    """No-op cache used when Redis is not configured.

    Every ``get`` misses, so the application always falls through to the
    database. This keeps caching strictly optional.
    """

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None

    async def delete(self, key: str) -> None:
        return None
