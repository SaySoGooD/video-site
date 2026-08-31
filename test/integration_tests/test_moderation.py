"""Moderator bans: who may issue one, what it does, and who is out of reach."""

import asyncio

from conftest import API, auth_header, login, register
from fastapi.testclient import TestClient
from sqlalchemy import text


def _moderator(client: TestClient) -> dict[str, str]:
    return auth_header(login(client, "moderator@example.com", "moderator123"))


def _last_event(client: TestClient) -> tuple[str, str]:
    """The newest audit row, as (action, metadata)."""
    engine = client.app.state.container.engine()  # type: ignore[attr-defined]

    async def read() -> tuple[str, str]:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT action, event_metadata FROM audit_logs "
                    "ORDER BY id DESC LIMIT 1"
                )
            )
            row = result.first()
            return str(row[0]), str(row[1])

    return asyncio.run(read())


class TestBan:
    def test_moderator_can_ban_a_user(self, client: TestClient) -> None:
        target = register(client, "rude@example.com", "rudeuser")

        response = client.post(
            f"{API}/admin/users/{target['id']}/ban",
            headers=_moderator(client),
            json={"reason": "spam in comments"},
        )

        assert response.status_code == 200, response.text
        assert response.json()["is_active"] is False

    def test_ban_signs_the_account_out_and_keeps_it_out(
        self, client: TestClient
    ) -> None:
        target = register(client, "loud@example.com", "louduser")
        token = login(client, "loud@example.com", "password123")
        assert client.get(f"{API}/auth/me", headers=auth_header(token)).status_code == 200

        client.post(
            f"{API}/admin/users/{target['id']}/ban", headers=_moderator(client)
        )

        assert client.get(f"{API}/auth/me", headers=auth_header(token)).status_code == 401
        relogin = client.post(
            f"{API}/auth/login",
            json={"email": "loud@example.com", "password": "password123"},
        )
        assert relogin.status_code == 401

    def test_banned_account_disappears_from_public_profiles(
        self, client: TestClient
    ) -> None:
        target = register(client, "hidden@example.com", "hiddenuser")
        assert client.get(f"{API}/users/{target['id']}").status_code == 200

        client.post(
            f"{API}/admin/users/{target['id']}/ban", headers=_moderator(client)
        )

        assert client.get(f"{API}/users/{target['id']}").status_code == 404

    def test_ban_is_recorded_with_the_actor_and_reason(
        self, client: TestClient
    ) -> None:
        target = register(client, "logged@example.com", "loggeduser")

        client.post(
            f"{API}/admin/users/{target['id']}/ban",
            headers=_moderator(client),
            json={"reason": "repeated reports"},
        )

        action, metadata = _last_event(client)
        assert action == "USER_BANNED"
        assert "repeated reports" in metadata
        assert "actor_id" in metadata

    def test_banning_twice_is_a_no_op(self, client: TestClient) -> None:
        target = register(client, "twice@example.com", "twiceuser")
        headers = _moderator(client)

        first = client.post(f"{API}/admin/users/{target['id']}/ban", headers=headers)
        second = client.post(f"{API}/admin/users/{target['id']}/ban", headers=headers)

        assert first.status_code == second.status_code == 200
        assert second.json()["is_active"] is False


class TestBanLimits:
    def test_a_plain_user_cannot_ban(self, client: TestClient) -> None:
        target = register(client, "victim@example.com", "victimuser")
        register(client, "nobody@example.com", "nobodyuser")
        headers = auth_header(login(client, "nobody@example.com", "password123"))

        response = client.post(
            f"{API}/admin/users/{target['id']}/ban", headers=headers
        )
        assert response.status_code == 403

    def test_anonymous_cannot_ban(self, client: TestClient) -> None:
        target = register(client, "safe@example.com", "safeuser")
        assert (
            client.post(f"{API}/admin/users/{target['id']}/ban").status_code == 401
        )

    def test_a_superuser_cannot_be_banned(self, client: TestClient) -> None:
        admin = client.get(
            f"{API}/auth/me",
            headers=auth_header(login(client, "admin@example.com", "admin123")),
        ).json()

        response = client.post(
            f"{API}/admin/users/{admin['id']}/ban", headers=_moderator(client)
        )
        assert response.status_code == 403

    def test_a_moderator_cannot_ban_themselves(self, client: TestClient) -> None:
        headers = _moderator(client)
        me = client.get(f"{API}/auth/me", headers=headers).json()

        response = client.post(f"{API}/admin/users/{me['id']}/ban", headers=headers)
        assert response.status_code == 422

    def test_unknown_user_is_404(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/admin/users/999999/ban", headers=_moderator(client)
        )
        assert response.status_code == 404


class TestUnban:
    def test_restores_the_account(self, client: TestClient) -> None:
        target = register(client, "back@example.com", "backuser")
        headers = _moderator(client)
        client.post(f"{API}/admin/users/{target['id']}/ban", headers=headers)

        response = client.delete(
            f"{API}/admin/users/{target['id']}/ban", headers=headers
        )

        assert response.status_code == 200, response.text
        assert response.json()["is_active"] is True
        assert login(client, "back@example.com", "password123")

    def test_old_sessions_stay_revoked(self, client: TestClient) -> None:
        target = register(client, "stale@example.com", "staleuser")
        token = login(client, "stale@example.com", "password123")
        headers = _moderator(client)

        client.post(f"{API}/admin/users/{target['id']}/ban", headers=headers)
        client.delete(f"{API}/admin/users/{target['id']}/ban", headers=headers)

        # The account works again, but the tokens issued before the ban do not.
        assert client.get(f"{API}/auth/me", headers=auth_header(token)).status_code == 401

    def test_unban_is_recorded(self, client: TestClient) -> None:
        target = register(client, "record@example.com", "recorduser")
        headers = _moderator(client)

        client.post(f"{API}/admin/users/{target['id']}/ban", headers=headers)
        client.delete(f"{API}/admin/users/{target['id']}/ban", headers=headers)

        action, _ = _last_event(client)
        assert action == "USER_UNBANNED"

    def test_unbanning_an_active_account_is_a_no_op(
        self, client: TestClient
    ) -> None:
        target = register(client, "fine@example.com", "fineuser")

        response = client.delete(
            f"{API}/admin/users/{target['id']}/ban", headers=_moderator(client)
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True
