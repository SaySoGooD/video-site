from conftest import API, auth_header, login, login_pair, register
from fastapi.testclient import TestClient


class TestPublicProfile:
    def test_returns_only_public_fields(self, client: TestClient) -> None:
        created = register(
            client, "pub@example.com", "publicguy", display_name="Public Guy"
        )

        response = client.get(f"{API}/users/{created['id']}")
        assert response.status_code == 200
        body = response.json()
        assert body == {
            "id": created["id"],
            "username": "publicguy",
            "display_name": "Public Guy",
            "created_at": body["created_at"],
        }

    def test_unknown_user_is_404(self, client: TestClient) -> None:
        assert client.get(f"{API}/users/424242").status_code == 404

    def test_soft_deleted_user_is_404(self, client: TestClient) -> None:
        created = register(client, "gone@example.com", "goneuser")
        token = login(client, "gone@example.com", "password123")
        assert client.delete(f"{API}/users/me", headers=auth_header(token)).status_code == 204

        assert client.get(f"{API}/users/{created['id']}").status_code == 404


class TestOwnSessions:
    def test_lists_each_login_and_marks_the_current_one(
        self, client: TestClient
    ) -> None:
        first = login(client, "viewer@example.com", "viewer123")
        second = login(client, "viewer@example.com", "viewer123")

        response = client.get(f"{API}/users/me/sessions", headers=auth_header(second))
        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) == 2
        assert [s["current"] for s in sessions].count(True) == 1

        current = next(s for s in sessions if s["current"])
        other = next(s for s in sessions if not s["current"])
        assert current["id"] > other["id"]
        assert client.get(f"{API}/auth/me", headers=auth_header(first)).status_code == 200

    def test_revoking_a_session_signs_that_device_out(
        self, client: TestClient
    ) -> None:
        first = login(client, "viewer@example.com", "viewer123")
        second = login(client, "viewer@example.com", "viewer123")

        sessions = client.get(
            f"{API}/users/me/sessions", headers=auth_header(second)
        ).json()
        other_id = next(s["id"] for s in sessions if not s["current"])

        killed = client.delete(
            f"{API}/users/me/sessions/{other_id}", headers=auth_header(second)
        )
        assert killed.status_code == 204

        assert client.get(f"{API}/auth/me", headers=auth_header(first)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=auth_header(second)).status_code == 200

    def test_cannot_revoke_someone_elses_session(self, client: TestClient) -> None:
        victim = login(client, "viewer@example.com", "viewer123")
        victim_session = client.get(
            f"{API}/users/me/sessions", headers=auth_header(victim)
        ).json()[0]["id"]

        register(client, "attacker@example.com", "attacker")
        attacker = login(client, "attacker@example.com", "password123")

        response = client.delete(
            f"{API}/users/me/sessions/{victim_session}", headers=auth_header(attacker)
        )
        assert response.status_code == 404
        assert client.get(f"{API}/auth/me", headers=auth_header(victim)).status_code == 200

    def test_refresh_replaces_the_session_rather_than_adding_one(
        self, client: TestClient
    ) -> None:
        access, refresh = login_pair(client, "viewer@example.com", "viewer123")
        before = client.get(f"{API}/users/me/sessions", headers=auth_header(access)).json()

        new_access = client.post(
            f"{API}/auth/refresh", json={"refresh_token": refresh}
        ).json()["tokens"]["access_token"]
        after = client.get(
            f"{API}/users/me/sessions", headers=auth_header(new_access)
        ).json()

        assert len(before) == len(after) == 1

    def test_sessions_require_authentication(self, client: TestClient) -> None:
        assert client.get(f"{API}/users/me/sessions").status_code == 401


class TestProfileAlias:
    def test_patch_users_me_updates_the_profile(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        response = client.patch(
            f"{API}/users/me", headers=auth_header(token), json={"display_name": "Vicky"}
        )
        assert response.status_code == 200
        assert response.json()["display_name"] == "Vicky"


class TestRevokeAllSessions:
    def test_signs_every_device_out_including_this_one(
        self, client: TestClient
    ) -> None:
        first = login(client, "viewer@example.com", "viewer123")
        second = login(client, "viewer@example.com", "viewer123")

        response = client.delete(
            f"{API}/users/me/sessions", headers=auth_header(second)
        )
        assert response.status_code == 200, response.text
        assert response.json()["revoked"] == 2

        assert client.get(f"{API}/auth/me", headers=auth_header(first)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=auth_header(second)).status_code == 401

    def test_keep_current_spares_the_calling_device(
        self, client: TestClient
    ) -> None:
        first = login(client, "viewer@example.com", "viewer123")
        second = login(client, "viewer@example.com", "viewer123")

        response = client.delete(
            f"{API}/users/me/sessions",
            params={"keep_current": True},
            headers=auth_header(second),
        )
        assert response.status_code == 200
        assert response.json()["revoked"] == 1

        assert client.get(f"{API}/auth/me", headers=auth_header(first)).status_code == 401
        assert client.get(f"{API}/auth/me", headers=auth_header(second)).status_code == 200

    def test_touches_only_the_callers_sessions(self, client: TestClient) -> None:
        victim = login(client, "admin@example.com", "admin123")
        mine = login(client, "viewer@example.com", "viewer123")

        client.delete(f"{API}/users/me/sessions", headers=auth_header(mine))

        assert client.get(f"{API}/auth/me", headers=auth_header(victim)).status_code == 200

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.delete(f"{API}/users/me/sessions").status_code == 401
