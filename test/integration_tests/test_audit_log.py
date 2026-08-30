"""The audit trail: what the service records about security-relevant events."""

import asyncio

from conftest import API, RecordingEmailSender, auth_header, login, register
from fastapi.testclient import TestClient
from sqlalchemy import text


def _events(client: TestClient) -> list[tuple[str, int | None, str | None]]:
    """Read the audit table directly — nothing exposes it over HTTP yet."""
    engine = client.app.state.container.engine()  # type: ignore[attr-defined]

    async def read() -> list[tuple[str, int | None, str | None]]:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT action, user_id, ip_address FROM audit_logs "
                    "ORDER BY id"
                )
            )
            return [(row[0], row[1], row[2]) for row in result]

    return asyncio.run(read())


def _actions(client: TestClient) -> list[str]:
    return [action for action, _, _ in _events(client)]


class TestAuditLog:
    def test_records_registration_and_login(self, client: TestClient) -> None:
        register(client, "audited@example.com", "audited")
        login(client, "audited@example.com", "password123")

        assert _actions(client) == ["REGISTER", "LOGIN"]

    def test_records_failed_logins_with_the_account(
        self, client: TestClient
    ) -> None:
        client.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "nope"},
        )

        action, user_id, _ = _events(client)[-1]
        assert action == "LOGIN_FAILED"
        assert user_id is not None

    def test_records_failed_login_for_an_unknown_address(
        self, client: TestClient
    ) -> None:
        client.post(
            f"{API}/auth/login",
            json={"email": "ghost@example.com", "password": "nope"},
        )

        action, user_id, _ = _events(client)[-1]
        assert action == "LOGIN_FAILED"
        assert user_id is None

    def test_records_logout(self, client: TestClient) -> None:
        token = login(client, "viewer@example.com", "viewer123")
        client.post(f"{API}/auth/logout", headers=auth_header(token))

        assert _actions(client)[-1] == "LOGOUT"

    def test_records_email_verification(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        register(client, "confirmed@example.com", "confirmed")
        client.get(
            f"{API}/auth/verify-email", params={"token": mailbox.last_token()}
        )

        assert _actions(client)[-1] == "EMAIL_VERIFIED"

    def test_records_password_reset(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        client.post(
            f"{API}/auth/forgot-password", json={"email": "viewer@example.com"}
        )
        client.post(
            f"{API}/auth/reset-password",
            json={
                "token": mailbox.last_token(),
                "password": "fresh-password",
                "password_repeat": "fresh-password",
            },
        )

        assert _actions(client)[-1] == "PASSWORD_RESET"

    def test_records_session_revocation(self, client: TestClient) -> None:
        first = login(client, "viewer@example.com", "viewer123")
        second = login(client, "viewer@example.com", "viewer123")
        sessions = client.get(
            f"{API}/users/me/sessions", headers=auth_header(second)
        ).json()
        other = next(s["id"] for s in sessions if not s["current"])

        client.delete(
            f"{API}/users/me/sessions/{other}", headers=auth_header(second)
        )

        assert _actions(client)[-1] == "SESSION_REVOKED"
        assert client.get(f"{API}/auth/me", headers=auth_header(first)).status_code == 401

    def test_records_self_deactivation(self, client: TestClient) -> None:
        register(client, "leaving@example.com", "leaving")
        token = login(client, "leaving@example.com", "password123")

        client.delete(f"{API}/users/me", headers=auth_header(token))

        assert _actions(client)[-1] == "USER_BANNED"

    def test_a_failed_registration_leaves_no_trace(
        self, client: TestClient
    ) -> None:
        """The audit row must not outlive a transaction that rolled back."""
        before = len(_events(client))

        conflict = client.post(
            f"{API}/auth/register",
            json={
                "email": "admin@example.com",
                "username": "brandnew",
                "password": "password123",
                "password_repeat": "password123",
            },
        )
        assert conflict.status_code == 409
        assert len(_events(client)) == before
