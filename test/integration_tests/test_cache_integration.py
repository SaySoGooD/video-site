from collections.abc import Iterator

import fakeredis.aioredis
import pytest
from conftest import API, _build_client, auth_header, login, register
from dependency_injector import providers
from fastapi.testclient import TestClient

from users_service.adapter.cache.redis_cache import RedisCache


@pytest.fixture
def cached_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The token-mode app with a (fake) Redis cache enabled.

    Overrides the ``cache`` provider with a RedisCache backed by fakeredis, so
    the full caching + invalidation path runs without a real Redis server.
    """
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
    client = _build_client()
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    client.app.state.container.cache.override(  # type: ignore[attr-defined]
        providers.Object(RedisCache(fake))
    )

    with client as test_client:
        yield test_client


class TestCachingWithRedis:
    def test_auth_still_works_with_cache(self, cached_client: TestClient) -> None:
        headers = auth_header(login(cached_client, "viewer@example.com", "viewer123"))
        # First call populates the cache, second call serves from it.
        assert cached_client.get(f"{API}/auth/me", headers=headers).status_code == 200
        assert cached_client.get(f"{API}/auth/me", headers=headers).status_code == 200

    def test_role_grant_invalidates_cache(self, cached_client: TestClient) -> None:
        admin = auth_header(login(cached_client, "admin@example.com", "admin123"))

        created = register(cached_client, "cached@example.com", "cacheduser")
        user = auth_header(login(cached_client, "cached@example.com", "password123"))

        # Caches the user with only the default (permission-less) role.
        assert cached_client.get(f"{API}/admin/users", headers=user).status_code == 403

        roles = cached_client.get(f"{API}/admin/roles", headers=admin).json()
        admin_role_id = next(r["id"] for r in roles if r["name"] == "admin")
        granted = cached_client.post(
            f"{API}/admin/users/{created['id']}/roles",
            headers=admin,
            json={"role_id": admin_role_id},
        )
        assert granted.status_code == 200, granted.text

        # Cache was invalidated on grant -> the new role is visible immediately.
        assert cached_client.get(f"{API}/admin/users", headers=user).status_code == 200

    def test_logout_is_immediate_despite_cache(
        self, cached_client: TestClient
    ) -> None:
        headers = auth_header(login(cached_client, "viewer@example.com", "viewer123"))
        assert cached_client.get(f"{API}/auth/me", headers=headers).status_code == 200
        cached_client.post(f"{API}/auth/logout", headers=headers)
        # The session is checked in the DB every request, so logout is not cached.
        assert cached_client.get(f"{API}/auth/me", headers=headers).status_code == 401
