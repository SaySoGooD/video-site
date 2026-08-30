from conftest import API, auth_header, login, login_pair, register
from fastapi.testclient import TestClient


class TestAuthFlow:
    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_register_login_and_me(self, client: TestClient) -> None:
        created = register(client, "new@example.com", "newbie")
        assert created["email"] == "new@example.com"
        assert created["username"] == "newbie"

        token = login(client, "new@example.com", "password123")
        me = client.get(f"{API}/auth/me", headers=auth_header(token))
        assert me.status_code == 200
        assert me.json()["email"] == "new@example.com"

    def test_registration_grants_the_default_role(
        self, client: TestClient
    ) -> None:
        created = register(client, "roled@example.com", "roled")
        assert [r["name"] for r in created["roles"]] == ["user"]

    def test_register_password_mismatch_is_422(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "mismatch@example.com",
                "username": "mismatch",
                "password": "password123",
                "password_repeat": "password124",
            },
        )
        assert response.status_code == 422

    def test_register_duplicate_email_is_409(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "admin@example.com",
                "username": "notadmin",
                "password": "password123",
                "password_repeat": "password123",
            },
        )
        assert response.status_code == 409

    def test_register_duplicate_username_is_409(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/auth/register",
            json={
                "email": "other@example.com",
                "username": "admin",
                "password": "password123",
                "password_repeat": "password123",
            },
        )
        assert response.status_code == 409

    def test_login_bad_password_is_401(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/auth/login",
            json={"email": "admin@example.com", "password": "nope"},
        )
        assert response.status_code == 401

    def test_update_profile(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        response = client.patch(
            f"{API}/users/me",
            headers=auth_header(token),
            json={"display_name": "Victoria", "username": "victoria"},
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Victoria"
        assert response.json()["username"] == "victoria"

    def test_username_taken_on_update_is_409(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        response = client.patch(
            f"{API}/users/me", headers=auth_header(token), json={"username": "admin"}
        )
        assert response.status_code == 409

    def test_logout_invalidates_token(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        assert (
            client.post(f"{API}/auth/logout", headers=auth_header(token)).status_code
            == 204
        )

        after = client.get(f"{API}/auth/me", headers=auth_header(token))
        assert after.status_code == 401

    def test_soft_delete_blocks_login(self, client: TestClient) -> None:
        register(client, "temp@example.com", "tempuser")
        token = login(client, "temp@example.com", "password123")

        assert (
            client.delete(f"{API}/users/me", headers=auth_header(token)).status_code == 204
        )
        assert client.get(f"{API}/auth/me", headers=auth_header(token)).status_code == 401
        relogin = client.post(
            f"{API}/auth/login",
            json={"email": "temp@example.com", "password": "password123"},
        )
        assert relogin.status_code == 401


class TestRefreshFlow:
    def test_login_returns_both_tokens(self, client: TestClient) -> None:
        access, refresh = login_pair(client, "viewer@example.com", "viewer123")
        assert access and refresh and access != refresh

    def test_refresh_issues_working_access(self, client: TestClient) -> None:
        _, refresh = login_pair(client, "viewer@example.com", "viewer123")
        response = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
        assert response.status_code == 200, response.text
        new_access = response.json()["tokens"]["access_token"]
        assert client.get(f"{API}/auth/me", headers=auth_header(new_access)).status_code == 200

    def test_old_refresh_rejected_after_rotation(self, client: TestClient) -> None:
        _, refresh = login_pair(client, "viewer@example.com", "viewer123")
        first = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
        assert first.status_code == 200
        replay = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
        assert replay.status_code == 401

    def test_refresh_token_is_not_accepted_as_access(
        self, client: TestClient
    ) -> None:
        _, refresh = login_pair(client, "viewer@example.com", "viewer123")
        assert client.get(f"{API}/auth/me", headers=auth_header(refresh)).status_code == 401

    def test_access_token_is_not_accepted_for_refresh(
        self, client: TestClient
    ) -> None:
        access, _ = login_pair(client, "viewer@example.com", "viewer123")
        response = client.post(f"{API}/auth/refresh", json={"refresh_token": access})
        assert response.status_code == 401
