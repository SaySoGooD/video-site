"""Brute-force protection: per-IP limits, per-account lockout, 429 + Retry-After."""

from collections.abc import Iterator

import pytest
from conftest import API, _build_client, _with_mailbox, auth_header, login
from fastapi.testclient import TestClient


@pytest.fixture
def strict(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """An app with tiny limits, so a test can exhaust them in a few calls."""
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
    monkeypatch.setenv("LOGIN_MAX_ATTEMPTS_PER_ACCOUNT", "3")
    monkeypatch.setenv("LOGIN_MAX_ATTEMPTS_PER_IP", "5")
    monkeypatch.setenv("REGISTER_MAX_PER_IP", "2")
    monkeypatch.setenv("FORGOT_PASSWORD_MAX_PER_EMAIL", "2")
    client = _build_client()
    _with_mailbox(client)
    with client as started:
        yield started


def _bad_login(client: TestClient, email: str = "viewer@example.com"):
    return client.post(
        f"{API}/auth/login", json={"email": email, "password": "wrong-password"}
    )


class TestAccountLockout:
    def test_locks_the_account_after_the_limit(self, strict: TestClient) -> None:
        for _ in range(3):
            assert _bad_login(strict).status_code == 401

        locked = _bad_login(strict)
        assert locked.status_code == 429
        assert int(locked.headers["Retry-After"]) > 0

    def test_lockout_blocks_even_the_correct_password(
        self, strict: TestClient
    ) -> None:
        for _ in range(3):
            _bad_login(strict)

        response = strict.post(
            f"{API}/auth/login",
            json={"email": "viewer@example.com", "password": "viewer123"},
        )
        assert response.status_code == 429

    def test_lockout_is_per_account_not_global(self, strict: TestClient) -> None:
        for _ in range(3):
            _bad_login(strict, "viewer@example.com")

        # A different account on the same IP still has budget left.
        other = strict.post(
            f"{API}/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        assert other.status_code == 200

    def test_success_clears_the_counter(self, strict: TestClient) -> None:
        _bad_login(strict)
        _bad_login(strict)
        assert login(strict, "viewer@example.com", "viewer123")

        # Two more failures would have tripped the limit without the reset.
        assert _bad_login(strict).status_code == 401
        assert _bad_login(strict).status_code == 401


class TestIpLimits:
    def test_registration_is_capped_per_ip(self, strict: TestClient) -> None:
        for index in range(2):
            created = strict.post(
                f"{API}/auth/register",
                json={
                    "email": f"flood{index}@example.com",
                    "username": f"flood{index}",
                    "password": "password123",
                    "password_repeat": "password123",
                },
            )
            assert created.status_code == 201

        blocked = strict.post(
            f"{API}/auth/register",
            json={
                "email": "flood2@example.com",
                "username": "flood2",
                "password": "password123",
                "password_repeat": "password123",
            },
        )
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers

    def test_forgot_password_is_capped_per_address(
        self, strict: TestClient
    ) -> None:
        for _ in range(2):
            allowed = strict.post(
                f"{API}/auth/forgot-password",
                json={"email": "viewer@example.com"},
            )
            assert allowed.status_code == 200

        blocked = strict.post(
            f"{API}/auth/forgot-password", json={"email": "viewer@example.com"}
        )
        assert blocked.status_code == 429


class TestLimitsCanBeDisabled:
    def test_no_lockout_when_rate_limiting_is_off(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        client = _build_client()
        _with_mailbox(client)

        with client as started:
            for _ in range(8):
                assert _bad_login(started).status_code == 401
            token = login(started, "viewer@example.com", "viewer123")
            assert (
                started.get(
                    f"{API}/auth/me", headers=auth_header(token)
                ).status_code
                == 200
            )
