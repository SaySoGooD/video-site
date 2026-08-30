from collections.abc import Iterator

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from users_service.bootstrap import bootstrap


def _build_client() -> TestClient:
    """Wire the real stack onto a throwaway in-memory SQLite database.

    Only the ``engine`` provider is overridden, so the DI container, unit of
    work, repositories, use cases and routers all stay in play while the test
    run avoids depending on a PostgreSQL server. Entering the client's context
    triggers the lifespan hook, which creates the schema and seeds demo data.
    """
    app = bootstrap()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    app.state.container.engine.override(providers.Object(engine))
    return TestClient(app)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Token mode: tokens come back in the body, sent as bearer headers."""
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "false")
    with _build_client() as test_client:
        yield test_client


@pytest.fixture
def browser(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Cookie mode, as a real browser frontend would use the service.

    ``COOKIE_SECURE`` is off because the test client speaks plain HTTP and
    would otherwise drop every ``Secure`` cookie.
    """
    monkeypatch.setenv("COOKIE_AUTH_ENABLED", "true")
    monkeypatch.setenv("COOKIE_SECURE", "false")
    with _build_client() as test_client:
        yield test_client


def login(client: TestClient, email: str, password: str) -> str:
    """Log in (token mode) and return the access token."""
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["tokens"]["access_token"]


def login_pair(client: TestClient, email: str, password: str) -> tuple[str, str]:
    """Log in (token mode) and return the access + refresh pair."""
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    tokens = response.json()["tokens"]
    return tokens["access_token"], tokens["refresh_token"]


def browser_login(client: TestClient, email: str, password: str) -> dict[str, str]:
    """Log in (cookie mode) and return the CSRF header to send with writes."""
    response = client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return csrf_header(response.json()["csrf_token"])


def csrf_header(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(
    client: TestClient,
    email: str,
    username: str,
    password: str = "password123",
    **extra: object,
) -> dict[str, object]:
    """Register an account and return the created profile."""
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "password_repeat": password,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
