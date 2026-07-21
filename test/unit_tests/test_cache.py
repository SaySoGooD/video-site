from datetime import UTC, datetime

import fakeredis.aioredis

from auth_test.adapter.cache.null_cache import NullCache
from auth_test.adapter.cache.redis_cache import RedisCache
from auth_test.application.common import user_cache_codec
from auth_test.entities.permission.models import Permission
from auth_test.entities.permission.value_objects import PermissionId
from auth_test.entities.role.models import Role
from auth_test.entities.role.value_objects import RoleId
from auth_test.entities.user.models import User
from auth_test.entities.user.value_objects import Email, UserId


def _user() -> User:
    return User(
        id=UserId(5),
        email=Email("u@example.com"),
        password_hash="hash",
        first_name="U",
        last_name="Ser",
        middle_name=None,
        is_active=True,
        is_superuser=False,
        created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        roles=[
            Role(
                id=RoleId(3),
                name="viewer",
                description="reads",
                permissions=[
                    Permission(PermissionId(1), "document", "read", "View"),
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
