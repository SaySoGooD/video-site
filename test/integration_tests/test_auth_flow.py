from conftest import auth_header, login
from fastapi.testclient import TestClient


class TestAuthFlow:
    def test_health(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_register_login_and_me(self, client: TestClient) -> None:
        register = client.post(
            "/auth/register",
            json={
                "email": "new@example.com",
                "password": "password1",
                "password_repeat": "password1",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert register.status_code == 201, register.text
        assert register.json()["email"] == "new@example.com"

        token = login(client, "new@example.com", "password1")
        me = client.get("/auth/me", headers=auth_header(token))
        assert me.status_code == 200
        assert me.json()["email"] == "new@example.com"

    def test_register_password_mismatch_is_422(self, client: TestClient) -> None:
        response = client.post(
            "/auth/register",
            json={
                "email": "mismatch@example.com",
                "password": "password1",
                "password_repeat": "password2",
                "first_name": "Mis",
            },
        )
        assert response.status_code == 422

    def test_register_duplicate_email_is_409(self, client: TestClient) -> None:
        response = client.post(
            "/auth/register",
            json={
                "email": "admin@example.com",
                "password": "password1",
                "password_repeat": "password1",
                "first_name": "Dup",
            },
        )
        assert response.status_code == 409

    def test_login_bad_password_is_401(self, client: TestClient) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "nope"},
        )
        assert response.status_code == 401

    def test_update_profile(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        response = client.patch(
            "/auth/me",
            headers=auth_header(token),
            json={"first_name": "Victoria"},
        )
        assert response.status_code == 200
        assert response.json()["first_name"] == "Victoria"

    def test_logout_invalidates_token(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        assert (
            client.post("/auth/logout", headers=auth_header(token)).status_code
            == 204
        )

        after = client.get("/auth/me", headers=auth_header(token))
        assert after.status_code == 401

    def test_soft_delete_blocks_login(self, client: TestClient) -> None:
        client.post(
            "/auth/register",
            json={
                "email": "temp@example.com",
                "password": "password1",
                "password_repeat": "password1",
                "first_name": "Temp",
            },
        )
        token = login(client, "temp@example.com", "password1")

        assert (
            client.delete("/auth/me", headers=auth_header(token)).status_code == 204
        )
        assert client.get("/auth/me", headers=auth_header(token)).status_code == 401
        relogin = client.post(
            "/auth/login",
            json={"email": "temp@example.com", "password": "password1"},
        )
        assert relogin.status_code == 401


class TestRefreshFlow:
    @staticmethod
    def _login_pair(client: TestClient) -> tuple[str, str]:
        r = client.post(
            "/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        return body["access_token"], body["refresh_token"]

    def test_login_returns_both_tokens(self, client: TestClient) -> None:
        access, refresh = self._login_pair(client)
        assert access and refresh and access != refresh

    def test_refresh_issues_working_access(self, client: TestClient) -> None:
        _, refresh = self._login_pair(client)
        r = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert r.status_code == 200, r.text
        new_access = r.json()["access_token"]
        me = client.get("/auth/me", headers=auth_header(new_access))
        assert me.status_code == 200

    def test_old_refresh_rejected_after_rotation(self, client: TestClient) -> None:
        _, refresh = self._login_pair(client)
        assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 200
        # rotation revoked the presented refresh token -> replay fails
        replay = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert replay.status_code == 401

    def test_refresh_token_is_not_accepted_as_access(self, client: TestClient) -> None:
        _, refresh = self._login_pair(client)
        assert client.get("/auth/me", headers=auth_header(refresh)).status_code == 401

    def test_access_token_is_not_accepted_for_refresh(self, client: TestClient) -> None:
        access, _ = self._login_pair(client)
        assert client.post("/auth/refresh", json={"refresh_token": access}).status_code == 401
