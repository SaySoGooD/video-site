from datetime import UTC, datetime

import fakeredis.aioredis

from users_service.adapter.cache.null_cache import NullCache
from users_service.adapter.cache.redis_cache import RedisCache
from users_service.application.common import user_cache_codec
from users_service.entities.permission.models import Permission
from users_service.entities.permission.value_objects import PermissionId
from users_service.entities.role.models import Role
from users_service.entities.role.value_objects import RoleId
from users_service.entities.user.models import User
from users_service.entities.user.value_objects import (
    Email,
    UserId,
    Username,
    VisitorId,
)


def _user() -> User:
    return User(
        id=UserId(5),
        email=Email("u@example.com"),
        username=Username("user"),
        password_hash="hash",
        display_name="Ser",
        is_active=True,
        is_superuser=False,
        visitor_id=VisitorId("2f1c9d4e-0000-4000-8000-000000000001"),
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        roles=[
            Role(
                id=RoleId(3),
                name="viewer",
                description="reads",
                permissions=[
                    Permission(PermissionId(1), "account", "read", "View"),
                ],
            )
        ],
    )


class TestNullCache:
    async def test_always_misses(self) -> None:
        cache = NullCache()
        await cache.set("k", "v", 10)
        assert await cache.get("k") is None
        await cache.delete("k")


class TestRedisCache:
    async def test_set_get_delete(self) -> None:
        client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        cache = RedisCache(client)

        assert await cache.get("k") is None
        await cache.set("k", "v", 30)
        assert await cache.get("k") == "v"
        await cache.delete("k")
        assert await cache.get("k") is None


class TestUserCacheCodec:
    def test_round_trip_preserves_entity(self) -> None:
        user = _user()
        restored = user_cache_codec.loads(user_cache_codec.dumps(user))
        assert restored == user

    def test_cache_key(self) -> None:
        assert user_cache_codec.user_cache_key(UserId(5)) == "auth:user:5"
