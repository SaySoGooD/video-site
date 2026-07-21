from collections.abc import Iterator

import pytest
from conftest import auth_header, login
from fastapi.testclient import TestClient

from auth_test.bootstrap import bootstrap


@pytest.fixture
def memory_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A TestClient running entirely on the in-memory mock backend.

    No database engine is touched — ``MOCK_DB=True`` selects the in-memory
    unit of work, and the lifespan hook seeds the demo data into the storage
    singleton.
    """
    monkeypatch.setenv("MOCK_DB", "true")
    app = bootstrap()
    with TestClient(app) as test_client:
        yield test_client


class TestMemoryBackend:
    def test_health(self, memory_client: TestClient) -> None:
        assert memory_client.get("/health").status_code == 200

    def test_seeded_admin_can_reach_admin_api(
        self, memory_client: TestClient
    ) -> None:
        token = login(memory_client, "admin@example.com", "admin123")
        response = memory_client.get("/admin/roles", headers=auth_header(token))
        assert response.status_code == 200
        assert {r["name"] for r in response.json()} == {"admin", "editor", "viewer"}

    def test_authorization_rules_hold(self, memory_client: TestClient) -> None:
        assert memory_client.get("/documents").status_code == 401

        token = login(memory_client, "viewer@example.com", "viewer123")
        assert (
            memory_client.get("/documents", headers=auth_header(token)).status_code
            == 200
        )
        assert (
            memory_client.post("/documents", headers=auth_header(token)).status_code
            == 403
        )

    def test_register_login_persists_across_requests(
        self, memory_client: TestClient
    ) -> None:
        register = memory_client.post(
            "/auth/register",
            json={
                "email": "mem@example.com",
                "password": "password1",
                "password_repeat": "password1",
                "first_name": "Mem",
            },
        )
        assert register.status_code == 201

        token = login(memory_client, "mem@example.com", "password1")
        me = memory_client.get("/auth/me", headers=auth_header(token))
        assert me.status_code == 200
        assert me.json()["email"] == "mem@example.com"

    def test_admin_grant_takes_effect(self, memory_client: TestClient) -> None:
        admin = auth_header(login(memory_client, "admin@example.com", "admin123"))

        memory_client.post(
            "/auth/register",
            json={
                "email": "grant@example.com",
                "password": "password1",
                "password_repeat": "password1",
                "first_name": "Grant",
            },
        )
        user_token = auth_header(login(memory_client, "grant@example.com", "password1"))
        assert memory_client.get("/documents", headers=user_token).status_code == 403

        users = memory_client.get("/admin/users", headers=admin).json()
        uid = next(u["id"] for u in users if u["email"] == "grant@example.com")
        memory_client.post(
            f"/admin/users/{uid}/roles", headers=admin, json={"role_id": 3}
        )

        assert memory_client.get("/documents", headers=user_token).status_code == 200
