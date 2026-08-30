from conftest import (
    API,
    RecordingEmailSender,
    auth_header,
    login,
    login_pair,
    register,
)
from fastapi.testclient import TestClient


def _request_reset(client: TestClient, email: str) -> None:
    response = client.post(f"{API}/auth/forgot-password", json={"email": email})
    assert response.status_code == 200, response.text


class TestForgotPassword:
    def test_answers_the_same_for_unknown_addresses(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        known = client.post(
            f"{API}/auth/forgot-password", json={"email": "viewer@example.com"}
        )
        unknown = client.post(
            f"{API}/auth/forgot-password", json={"email": "nobody@example.com"}
        )

        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()
        # ...and only the real account actually got mail.
        assert [m.to for m in mailbox.messages] == ["viewer@example.com"]  # type: ignore[attr-defined]


class TestResetPassword:
    def test_sets_the_new_password(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        _request_reset(client, "viewer@example.com")
        token = mailbox.last_token()

        response = client.post(
            f"{API}/auth/reset-password",
            json={
                "token": token,
                "password": "brand-new-pass",
                "password_repeat": "brand-new-pass",
            },
        )
        assert response.status_code == 200, response.text

        assert login(client, "viewer@example.com", "brand-new-pass")
        stale = client.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )
        assert stale.status_code == 401

    def test_revokes_every_existing_session(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        access, refresh = login_pair(client, "viewer@example.com", "viewer123")
        assert client.get(f"{API}/auth/me", headers=auth_header(access)).status_code == 200

        _request_reset(client, "viewer@example.com")
        client.post(
            f"{API}/auth/reset-password",
            json={
                "token": mailbox.last_token(),
                "password": "another-new-pass",
                "password_repeat": "another-new-pass",
            },
        )

        # The device that was logged in before the reset is out, tokens and all.
        assert client.get(f"{API}/auth/me", headers=auth_header(access)).status_code == 401
        replay = client.post(
            f"{API}/auth/refresh", json={"refresh_token": refresh}
        )
        assert replay.status_code == 401

    def test_token_is_single_use(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        _request_reset(client, "viewer@example.com")
        token = mailbox.last_token()
        body = {
            "token": token,
            "password": "first-new-pass",
            "password_repeat": "first-new-pass",
        }

        assert client.post(f"{API}/auth/reset-password", json=body).status_code == 200
        assert client.post(f"{API}/auth/reset-password", json=body).status_code == 400

    def test_requesting_again_invalidates_the_older_link(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        _request_reset(client, "viewer@example.com")
        first = mailbox.last_token()
        _request_reset(client, "viewer@example.com")
        second = mailbox.last_token()

        assert first != second
        stale = client.post(
            f"{API}/auth/reset-password",
            json={
                "token": first,
                "password": "should-not-work",
                "password_repeat": "should-not-work",
            },
        )
        assert stale.status_code == 400

        fresh = client.post(
            f"{API}/auth/reset-password",
            json={
                "token": second,
                "password": "should-work-fine",
                "password_repeat": "should-work-fine",
            },
        )
        assert fresh.status_code == 200

    def test_mismatched_passwords_are_422(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        _request_reset(client, "viewer@example.com")
        response = client.post(
            f"{API}/auth/reset-password",
            json={
                "token": mailbox.last_token(),
                "password": "one-password",
                "password_repeat": "other-password",
            },
        )
        assert response.status_code == 422

    def test_unknown_token_is_400(self, client: TestClient) -> None:
        response = client.post(
            f"{API}/auth/reset-password",
            json={
                "token": "made-up-token",
                "password": "whatever-pass",
                "password_repeat": "whatever-pass",
            },
        )
        assert response.status_code == 400

    def test_reset_link_works_for_a_newly_registered_account(
        self, client: TestClient, mailbox: RecordingEmailSender
    ) -> None:
        register(client, "forgetful@example.com", "forgetful")
        _request_reset(client, "forgetful@example.com")

        response = client.post(
            f"{API}/auth/reset-password",
            json={
                "token": mailbox.last_token(),
                "password": "recovered-pass",
                "password_repeat": "recovered-pass",
            },
        )
        assert response.status_code == 200
        assert login(client, "forgetful@example.com", "recovered-pass")
