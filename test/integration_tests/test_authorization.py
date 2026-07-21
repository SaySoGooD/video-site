from conftest import auth_header, login
from fastapi.testclient import TestClient


class TestAuthorization:
    def test_anonymous_request_is_401(self, client: TestClient) -> None:
        assert client.get("/documents").status_code == 401

    def test_viewer_can_read_documents(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        response = client.get("/documents", headers=auth_header(token))
        assert response.status_code == 200
        assert response.json()["resource"] == "document"

    def test_viewer_cannot_create_documents_is_403(
        self, client: TestClient
    ) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        assert (
            client.post("/documents", headers=auth_header(token)).status_code == 403
        )

    def test_editor_can_create_documents(self, client: TestClient) -> None:
        token = login(client, "editor@example.com", "editor123")
        assert (
            client.post("/documents", headers=auth_header(token)).status_code == 200
        )

    def test_editor_cannot_delete_documents_is_403(
        self, client: TestClient
    ) -> None:
        token = login(client, "editor@example.com", "editor123")
        assert (
            client.delete("/documents/1", headers=auth_header(token)).status_code
            == 403
        )

    def test_admin_can_reach_admin_api(self, client: TestClient) -> None:
        token = login(client, "admin@example.com", "admin123")
        assert (
            client.get("/admin/roles", headers=auth_header(token)).status_code == 200
        )

    def test_non_admin_blocked_from_admin_api_is_403(
        self, client: TestClient
    ) -> None:
        token = login(client, "editor@example.com", "editor123")
        assert (
            client.get("/admin/roles", headers=auth_header(token)).status_code == 403
        )

    def test_admin_grants_permission_and_access_changes(
        self, client: TestClient
    ) -> None:
        admin_token = login(client, "admin@example.com", "admin123")
        headers = auth_header(admin_token)

        client.post(
            "/auth/register",
            json={
                "email": "grantee@example.com",
                "password": "password1",
                "password_repeat": "password1",
                "first_name": "Grant",
            },
        )
        grantee_token = login(client, "grantee@example.com", "password1")
        assert (
            client.get(
                "/documents", headers=auth_header(grantee_token)
            ).status_code
            == 403
        )

        permissions = client.get("/admin/permissions", headers=headers).json()
        doc_read = next(
            p
            for p in permissions
            if p["resource"] == "document" and p["action"] == "read"
        )

        new_role = client.post(
            "/admin/roles",
            headers=headers,
            json={"name": "doc-reader", "description": "reads docs"},
        ).json()
        client.post(
            f"/admin/roles/{new_role['id']}/permissions",
            headers=headers,
            json={"permission_id": doc_read["id"]},
        )

        users = client.get("/admin/users", headers=headers).json()
        grantee = next(u for u in users if u["email"] == "grantee@example.com")
        client.post(
            f"/admin/users/{grantee['id']}/roles",
            headers=headers,
            json={"role_id": new_role["id"]},
        )

        assert (
            client.get(
                "/documents", headers=auth_header(grantee_token)
            ).status_code
            == 200
        )
