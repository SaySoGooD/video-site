"""Changing a password from inside a session, and what it costs the sessions."""

from conftest import (
    API,
    RecordingEmailSender,
    auth_header,
    browser_login,
    login,
    login_pair,
    register,
)
from fastapi.testclient import TestClient

NEW = "brand-new-password"


def _change(
    client: TestClient,
    token: str,
    current: str = "password123",
    new: str = NEW,
    repeat: str | None = None,
):
    return client.post(
        f"{API}/users/me/password",
        headers=auth_header(token),
        json={
            "current_password": current,
            "new_password": new,
            "new_password_repeat": new if repeat is None else repeat,
        },
    )


class TestChangePassword:
    def test_sets_the_new_password(self, client: TestClient) -> None:
        register(client, "changer@example.com", "changeruser")
        token = login(client, "changer@example.com", "password123")

        response = _change(client, token)
        assert response.status_code == 200, response.text

        assert login(client, "changer@example.com", NEW)
        stale = client.post(
            f"{API}/auth/login",
            json={"email": "changer@example.com", "password": "password123"},
        )
        assert stale.status_code == 401

    def test_signs_every_device_out_including_the_caller(
        self, client: TestClient
    ) -> None:
        register(client, "devices@example.com", "devicesuser")
        elsewhere = login(client, "devices@example.com", "password123")
        here, refresh = login_pair(client, "devices@example.com", "password123")

        response = _change(client, here)
        assert response.status_code == 200
        assert response.json()["sessions_revoked"] == 2

        assert client.get(f"{API}/auth/me", headers=auth_header(here)).status_code == 401
        assert (
            client.get(f"{API}/auth/me", headers=auth_header(elsewhere)).status_code
            == 401
        )
        replay = client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
        assert replay.status_code == 401

    def test_wrong_current_password_is_401_and_changes_nothing(
        self, client: TestClient
    ) -> None:
        register(client, "guard@example.com", "guarduser")
        token = login(client, "guard@example.com", "password123")

        response = _change(client, token, current="not-the-password")
        assert response.status_code == 401

        # The session survives, and the old password still works.
        assert client.get(f"{API}/auth/me", headers=auth_header(token)).status_code == 200
        assert login(client, "guard@example.com", "password123")

    def test_mismatched_repeat_is_422(self, client: TestClient) -> None:
        register(client, "typo@example.com", "typouser")
        token = login(client, "typo@example.com", "password123")

        response = _change(client, token, repeat="something-else-entirely")
        assert response.status_code == 422

    def test_reusing_the_same_password_is_422(self, client: TestClient) -> None:
        register(client, "same@example.com", "sameuser")
        token = login(client, "same@example.com", "password123")

        response = _change(client, token, new="password123")
        assert response.status_code == 422

    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/users/me/password",
            json={
                "current_password": "password123",
                "new_password": NEW,
                "new_password_repeat": NEW,
            },
        )
        assert response.status_code == 401

    def test_spends_any_outstanding_reset_link(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        """A reset email must not outlive the password it was meant to replace."""
        register(client, "both@example.com", "bothuser")
        token = login(client, "both@example.com", "password123")
        client.post(f"{API}/auth/forgot-password", json={"email": "both@example.com"})
        reset_token = mailbox.last_token()

        assert _change(client, token).status_code == 200

        stale = client.post(
            f"{API}/auth/reset-password",
            json={
                "token": reset_token,
                "password": "hijacked-password",
                "password_repeat": "hijacked-password",
            },
        )
        assert stale.status_code == 400
        assert login(client, "both@example.com", NEW)

    def test_is_recorded_in_the_audit_log(self, client: TestClient) -> None:
        import asyncio

        from sqlalchemy import text

        register(client, "tracked@example.com", "trackeduser")
        token = login(client, "tracked@example.com", "password123")
        _change(client, token)
        engine = client.app.state.container.engine()  # type: ignore[attr-defined]

        async def last_action() -> str:
            async with engine.connect() as connection:
                result = await connection.execute(
                    text("SELECT action FROM audit_logs ORDER BY id DESC LIMIT 1")
                )
                return str(result.scalar_one())

        assert asyncio.run(last_action()) == "PASSWORD_CHANGED"


class TestChangePasswordInTheBrowser:
    def test_clears_the_auth_cookies(self, browser: TestClient) -> None:
        csrf = browser_login(browser, "viewer@example.com", "viewer123")

        response = browser.post(
            f"{API}/users/me/password",
            headers=csrf,
            json={
                "current_password": "viewer123",
                "new_password": NEW,
                "new_password_repeat": NEW,
            },
        )

        assert response.status_code == 200, response.text
        assert "access_token" not in browser.cookies
        assert browser.get(f"{API}/auth/me").status_code == 401
