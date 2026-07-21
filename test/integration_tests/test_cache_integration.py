from collections.abc import Iterator

import fakeredis.aioredis
import pytest
from conftest import auth_header, login
from dependency_injector import providers
from fastapi.testclient import TestClient

from auth_test.adapter.cache.redis_cache import RedisCache
from auth_test.bootstrap import bootstrap


@pytest.fixture
def cached_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """App on the in-memory DB with a (fake) Redis cache enabled.

    Overrides the ``cache`` provider with a RedisCache backed by fakeredis, so
    the full caching + invalidation path runs without a real Redis server.
    """
    monkeypatch.setenv("MOCK_DB", "true")
    app = bootstrap()
    container = app.state.container
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    container.cache.override(providers.Object(RedisCache(fake)))

    with TestClient(app) as test_client:
        yield test_client


class TestCachingWithRedis:
    def test_auth_still_works_with_cache(self, cached_client: TestClient) -> None:
        token = login(cached_client, "viewer@example.com", "viewer123")
        # First call populates the cache, second call serves from it.
        assert cached_client.get("/auth/me", headers=auth_header(token)).status_code == 200
        assert cached_client.get("/auth/me", headers=auth_header(token)).status_code == 200

    def test_role_grant_invalidates_cache(self, cached_client: TestClient) -> None:
        admin = auth_header(login(cached_client, "admin@example.com", "admin123"))

        cached_client.post(
            "/auth/register",
            json={
                "email": "cached@example.com",
                "password": "password1",
                "password_repeat": "password1",
                "first_name": "Cached",
            },
        )
        user = auth_header(login(cached_client, "cached@example.com", "password1"))

        # Caches the user with no roles.
        assert cached_client.get("/documents", headers=user).status_code == 403

        users = cached_client.get("/admin/users", headers=admin).json()
        uid = next(u["id"] for u in users if u["email"] == "cached@example.com")
        cached_client.post(
            f"/admin/users/{uid}/roles", headers=admin, json={"role_id": 3}
        )

        # Cache was invalidated on grant -> new role is visible immediately.
        assert cached_client.get("/documents", headers=user).status_code == 200

    def test_logout_is_immediate_despite_cache(
        self, cached_client: TestClient
    ) -> None:
        token = login(cached_client, "viewer@example.com", "viewer123")
        assert cached_client.get("/auth/me", headers=auth_header(token)).status_code == 200
        cached_client.post("/auth/logout", headers=auth_header(token))
        # Session is checked in the DB every request, so logout is not cached.
        assert cached_client.get("/auth/me", headers=auth_header(token)).status_code == 401
