"""RBAC as seen through the only protected surface this service owns: /admin."""

from conftest import auth_header, login, register
from fastapi.testclient import TestClient


class TestAdminAccess:
    def test_anonymous_is_401(self, client: TestClient) -> None:
        assert client.get("/admin/users").status_code == 401

    def test_default_role_is_403(self, client: TestClient) -> None:
        register(client, "plain@example.com", "plainuser")
        token = login(client, "plain@example.com", "password123")
        assert client.get("/admin/users", headers=auth_header(token)).status_code == 403

    def test_moderator_lacking_the_permission_is_403(
        self, client: TestClient
    ) -> None:
        token = login(client, "moderator@example.com", "moderator123")
        # The moderator role carries account:*, not access_control:manage.
        assert client.get("/admin/roles", headers=auth_header(token)).status_code == 403

    def test_admin_is_allowed(self, client: TestClient) -> None:
        token = login(client, "admin@example.com", "admin123")
        response = client.get("/admin/roles", headers=auth_header(token))
        assert response.status_code == 200
        assert {r["name"] for r in response.json()} == {"admin", "moderator", "user"}

    def test_granting_a_role_changes_what_a_user_may_do(
        self, client: TestClient
    ) -> None:
        admin = auth_header(login(client, "admin@example.com", "admin123"))
        created = register(client, "promoted@example.com", "promoted")
        user = auth_header(login(client, "promoted@example.com", "password123"))

        assert client.get("/admin/users", headers=user).status_code == 403

        roles = client.get("/admin/roles", headers=admin).json()
        admin_role_id = next(r["id"] for r in roles if r["name"] == "admin")
        client.post(
            f"/admin/users/{created['id']}/roles",
            headers=admin,
            json={"role_id": admin_role_id},
        )

        assert client.get("/admin/users", headers=user).status_code == 200
